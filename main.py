"""
HackerNews Trending Topics - CocoIndex v1 pipeline example.

Index (one-shot catch-up; re-run to refresh against the latest HN threads):
    cocoindex update main

Query the index:
    python main.py                # show top trending topics, then search interactively
    python main.py "your topic"   # search messages mentioning a topic

Pipeline: scrape HN threads + comments -> extract topics via LLM -> store in Postgres.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from typing import Any, AsyncIterator

import aiohttp
import asyncpg
from litellm import acompletion

import cocoindex as coco
from cocoindex.connectors import postgres

from models import TopicsResponse


# Configuration
DATABASE_URL = os.environ.get(
    "POSTGRES_URL", "postgres://cocoindex:cocoindex@localhost/cocoindex"
)
# Any LiteLLM-supported model, e.g. "openai/gpt-5-mini" or "gemini/gemini-2.5-flash".
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini/gemini-2.5-flash")
MAX_THREADS = int(os.environ.get("MAX_THREADS", "10"))

# Scoring weights for the trending-topics query.
THREAD_LEVEL_MENTION_SCORE = 5
COMMENT_LEVEL_MENTION_SCORE = 1

PG_DB = coco.ContextKey[asyncpg.Pool]("hn_db")


# ============================================================================
# Data models for HackerNews content
# ============================================================================


@dataclass
class Comment:
    id: str
    author: str | None
    text: str | None
    created_at: datetime | None


@dataclass
class Thread:
    id: str
    author: str | None
    text: str
    url: str | None
    created_at: datetime | None
    comments: list[Comment]


# ============================================================================
# Table schemas as dataclasses (for the PostgreSQL target)
# ============================================================================


@dataclass
class HnMessage:
    """Schema for the hn_messages table."""

    id: str
    thread_id: str
    content_type: str
    author: str | None
    text: str | None
    url: str | None
    created_at: datetime | None


@dataclass
class HnTopic:
    """Schema for the hn_topics table."""

    topic: str
    message_id: str
    thread_id: str
    content_type: str
    created_at: datetime | None


# ============================================================================
# LLM topic extraction
# ============================================================================


@coco.fn(memo=True)
async def extract_topics(text: str | None) -> list[str]:
    """Extract canonical topics from a piece of text using an LLM."""
    if not text or not text.strip():
        return []

    response = await acompletion(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": f"Extract topics from the following text:\n\n{text[:4000]}",
            }
        ],
        response_format=TopicsResponse,
    )

    content = response.choices[0].message.content
    return TopicsResponse.model_validate_json(content).topics


# ============================================================================
# HackerNews API functions
# ============================================================================


async def fetch_thread_list(
    session: aiohttp.ClientSession, max_results: int = MAX_THREADS
) -> list[str]:
    """Fetch a list of recent thread IDs from HackerNews."""
    search_url = "https://hn.algolia.com/api/v1/search_by_date"
    params: dict[str, str | int] = {"tags": "story", "hitsPerPage": max_results}

    async with session.get(search_url, params=params) as response:
        response.raise_for_status()
        data = await response.json()
        return [hit["objectID"] for hit in data.get("hits", []) if hit.get("objectID")]


async def fetch_thread(session: aiohttp.ClientSession, thread_id: str) -> Thread:
    """Fetch a single thread with all of its comments."""
    item_url = f"https://hn.algolia.com/api/v1/items/{thread_id}"

    async with session.get(item_url) as response:
        response.raise_for_status()
        data = await response.json()

        comments: list[Comment] = []

        def parse_comments(parent: dict[str, Any]) -> None:
            for child in parent.get("children", []):
                if comment_id := child.get("id"):
                    ctime = child.get("created_at")
                    comments.append(
                        Comment(
                            id=str(comment_id),
                            author=child.get("author"),
                            text=child.get("text"),
                            created_at=datetime.fromisoformat(ctime) if ctime else None,
                        )
                    )
                parse_comments(child)

        parse_comments(data)

        ctime = data.get("created_at")
        text = data.get("title", "")
        if more_text := data.get("text"):
            text += "\n\n" + more_text

        return Thread(
            id=thread_id,
            author=data.get("author"),
            text=text,
            url=data.get("url"),
            created_at=datetime.fromisoformat(ctime) if ctime else None,
            comments=comments,
        )


# ============================================================================
# CocoIndex pipeline
# ============================================================================


@coco.lifespan
async def coco_lifespan(builder: coco.EnvironmentBuilder) -> AsyncIterator[None]:
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        builder.provide(PG_DB, pool)
        yield


@dataclass
class TableTargets:
    """Container bundling the two Postgres table targets."""

    messages: postgres.TableTarget[HnMessage]
    topics: postgres.TableTarget[HnTopic]


@coco.fn(memo=True)
async def process_thread(thread_id: str, targets: TableTargets) -> None:
    """Fetch a single thread + its comments, extract topics, declare target rows."""
    async with aiohttp.ClientSession() as session:
        thread = await fetch_thread(session, thread_id)
    thread_topics = await extract_topics(thread.text)

    targets.messages.declare_row(
        row=HnMessage(
            id=thread.id,
            thread_id=thread.id,
            content_type="thread",
            author=thread.author,
            text=thread.text,
            url=thread.url,
            created_at=thread.created_at,
        ),
    )
    for topic in thread_topics:
        targets.topics.declare_row(
            row=HnTopic(
                topic=topic,
                message_id=thread.id,
                thread_id=thread.id,
                content_type="thread",
                created_at=thread.created_at,
            ),
        )

    for comment in thread.comments:
        comment_topics = await extract_topics(comment.text)

        targets.messages.declare_row(
            row=HnMessage(
                id=comment.id,
                thread_id=thread.id,
                content_type="comment",
                author=comment.author,
                text=comment.text,
                url="",
                created_at=comment.created_at,
            ),
        )
        for topic in comment_topics:
            targets.topics.declare_row(
                row=HnTopic(
                    topic=topic,
                    message_id=comment.id,
                    thread_id=thread.id,
                    content_type="comment",
                    created_at=comment.created_at,
                ),
            )


@coco.fn
async def app_main() -> None:
    messages_table = await postgres.mount_table_target(
        PG_DB,
        table_name="hn_messages",
        table_schema=await postgres.TableSchema.from_class(
            HnMessage, primary_key=["id"]
        ),
    )
    topics_table = await postgres.mount_table_target(
        PG_DB,
        table_name="hn_topics",
        table_schema=await postgres.TableSchema.from_class(
            HnTopic, primary_key=["topic", "message_id"]
        ),
    )
    targets = TableTargets(messages=messages_table, topics=topics_table)

    async with aiohttp.ClientSession() as session:
        thread_ids = await fetch_thread_list(session)

    # One processing component per thread; each fetches its own thread data.
    await coco.mount_each(process_thread, ((tid, tid) for tid in thread_ids), targets)


app = coco.App(
    coco.AppConfig(name="HNTrendingTopics"),
    app_main,
)


# ============================================================================
# Query demo
# ============================================================================


async def get_trending_topics(
    pool: asyncpg.Pool, limit: int = 20
) -> list[dict[str, Any]]:
    """Get trending topics ranked by a thread/comment-weighted mention score."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                topic,
                SUM(CASE WHEN content_type = 'thread'
                         THEN {THREAD_LEVEL_MENTION_SCORE}
                         ELSE {COMMENT_LEVEL_MENTION_SCORE} END) AS score,
                MAX(created_at) AS latest_mention,
                COUNT(DISTINCT thread_id) AS thread_count
            FROM hn_topics
            GROUP BY topic
            ORDER BY score DESC, latest_mention DESC
            LIMIT $1
            """,
            limit,
        )

    return [
        {
            "topic": r["topic"],
            "score": r["score"],
            "latest_mention": r["latest_mention"].isoformat()
            if r["latest_mention"]
            else None,
            "thread_count": r["thread_count"],
        }
        for r in rows
    ]


async def search_by_topic(pool: asyncpg.Pool, topic: str) -> list[dict[str, Any]]:
    """Search messages mentioning a topic (substring, case-insensitive)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.thread_id, m.author, m.content_type, m.text, m.created_at, t.topic
            FROM hn_topics t
            JOIN hn_messages m ON t.message_id = m.id
            WHERE LOWER(t.topic) LIKE LOWER($1)
            ORDER BY m.created_at DESC
            """,
            f"%{topic}%",
        )

    return [
        {
            "id": r["id"],
            "url": f"https://news.ycombinator.com/item?id={r['thread_id']}",
            "author": r["author"],
            "type": r["content_type"],
            "text": r["text"][:500] if r["text"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "topic": r["topic"],
        }
        for r in rows
    ]


async def _print_topic_search(pool: asyncpg.Pool, topic: str) -> None:
    print(f"Searching for '{topic}' related content:")
    print("-" * 60)
    for result in (await search_by_topic(pool, topic))[:5]:
        text = (result["text"] or "")[:100]
        print(f"[{result['type']}] by {result['author']}: {text}...")


async def query_demo(initial_query: str | None = None) -> None:
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        if initial_query is not None:
            await _print_topic_search(pool, initial_query)
            return

        print("Top 20 Trending Topics:")
        print("-" * 60)
        for i, topic in enumerate(await get_trending_topics(pool, limit=20), 1):
            print(
                f"{i:2}. {topic['topic']:<30} "
                f"(score: {topic['score']}, threads: {topic['thread_count']})"
            )
        print()

        while True:
            try:
                q = input("Enter topic to search (or Enter to quit): ").strip()
            except EOFError:
                break
            if not q:
                break
            await _print_topic_search(pool, q)


if __name__ == "__main__":
    load_dotenv()
    initial = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(query_demo(initial))
