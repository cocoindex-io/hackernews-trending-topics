<p align="center">
    <img src="https://cocoindex.io/images/github.svg" alt="CocoIndex">
</p>

<h1 align="center">HackerNews Trending Topics</h1>

<div align="center">

[![GitHub](https://img.shields.io/github/stars/cocoindex-io/cocoindex?color=5B5BD6)](https://github.com/cocoindex-io/cocoindex)
[![Documentation](https://img.shields.io/badge/Documentation-394e79?logo=readthedocs&logoColor=00B9FF)](https://cocoindex.io/docs/getting_started/quickstart)
[![License](https://img.shields.io/badge/license-Apache%202.0-5B5BD6?logoColor=white)](https://opensource.org/licenses/Apache-2.0)
[![PyPI version](https://img.shields.io/pypi/v/cocoindex?color=5B5BD6)](https://pypi.org/project/cocoindex/)
<!--[![PyPI - Downloads](https://img.shields.io/pypi/dm/cocoindex)](https://pypistats.org/packages/cocoindex) -->
[![PyPI Downloads](https://static.pepy.tech/badge/cocoindex/month)](https://pepy.tech/projects/cocoindex)
[![CI](https://github.com/cocoindex-io/cocoindex/actions/workflows/CI.yml/badge.svg?event=push&color=5B5BD6)](https://github.com/cocoindex-io/cocoindex/actions/workflows/CI.yml)
[![release](https://github.com/cocoindex-io/cocoindex/actions/workflows/release.yml/badge.svg?event=push&color=5B5BD6)](https://github.com/cocoindex-io/cocoindex/actions/workflows/release.yml)
[![Link Check](https://github.com/cocoindex-io/cocoindex/actions/workflows/links.yml/badge.svg)](https://github.com/cocoindex-io/cocoindex/actions/workflows/links.yml)
[![Discord](https://img.shields.io/discord/1314801574169673738?logo=discord&color=5B5BD6&logoColor=white)](https://discord.com/invite/zpA9S2DR7s)

</div>

<div align="center">

[Step By Step Tutorial](https://cocoindex.io/examples/hackernews-trending-topics)

</div>

<img width="2732" height="1540" alt="hackernews trending topics" src="https://github.com/user-attachments/assets/8bd2f55b-13b5-4a0c-a763-7a125ff7b191" />



In this example, we call the [HackerNews API](https://hn.algolia.com/api) to fetch recent threads and their comments, then use an LLM to extract trending topics from the text. Each thread becomes one CocoIndex processing component (`mount_each`), and the results are stored in two Postgres tables — so re-running only re-processes threads that changed.

The LLM extracts topics like product names, technologies, models, and company names, storing them in canonical form (avoiding acronyms unless very popular). Topic extraction is memoized (`@coco.fn(memo=True)`), so unchanged threads don't trigger new LLM calls.

We appreciate a star ⭐ at [CocoIndex Github](https://github.com/cocoindex-io/cocoindex) if this is helpful.


## Features

- **HackerNews ingestion**: Fetches recent threads and comments via the HN API.
- **LLM topic extraction**: Extracts topics from each thread/comment via an LLM (LiteLLM — swap any model with `LLM_MODEL`).
- **Canonical topic forms**: Topics are stored canonically (e.g., "Large Language Model" instead of "LLM").
- **Incremental by default**: Memoized extraction + managed Postgres targets — re-run to refresh; only the delta is re-processed and orphaned rows are cleaned up.
- **Trending + search queries**: Rank topics by a thread/comment-weighted mention score, or search messages by topic.

## Steps

### Indexing Flow
<img width="2732" height="2648" alt="flow" src="https://github.com/user-attachments/assets/04172792-7266-4b97-8957-bb481ed2602f" />


1. Fetch recent HackerNews thread IDs from the HN API, and mount one processing component per thread.
2. Each component fetches its thread + comments and extracts topics with an LLM.
3. We build two tables:
   - `hn_messages`: Full text of threads and comments.
   - `hn_topics`: Extracted topics referencing their source content, keyed by (topic, message_id).

## Prerequisite

- [Install Postgres](https://cocoindex.io/docs/getting_started/installation#-install-postgres) if you don't have one.
- Copy `.env.example` to `.env` and set `POSTGRES_URL` and an LLM provider key (`GEMINI_API_KEY` by default, or set `LLM_MODEL=openai/gpt-5-mini` with `OPENAI_API_KEY`).

## Run

Install dependencies:

```sh
pip install -e .
```

Build / update the index:

```sh
cocoindex update main
```

Each run keeps the target in sync with the most recent HackerNews threads: unchanged threads are skipped (memoized), new threads are added, and threads that aged out of the feed have their rows cleaned up. Re-run whenever you want to refresh; set `MAX_THREADS` to control how many recent threads to index.

## Query Examples

After building the index, query it from the terminal:

```sh
# Show the top trending topics, then search interactively
python main.py

# Search messages mentioning a specific topic
python main.py "Claude"
```
