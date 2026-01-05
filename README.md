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



In this example, we use [CocoIndex Custom Source](https://cocoindex.io/docs/custom_ops/custom_targets) to define a source to get HackerNews recent content by calling [HackerNews API](https://hn.algolia.com/api).
We build an index for HackerNews threads and their comments, and use LLM to extract trending topics from the text.

The pipeline uses `ExtractByLlm` to identify topics like product names, technologies, models, and company names mentioned in threads and comments, storing them in canonical form (avoiding acronyms unless very popular).

We appreciate a star ⭐ at [CocoIndex Github](https://github.com/cocoindex-io/cocoindex) if this is helpful.


## Features

- **Custom Source Integration**: Fetches HackerNews threads and comments via API
- **LLM Topic Extraction**: Automatically extracts topics using `ExtractByLlm` function
- **Canonical Topic Forms**: Topics are stored in canonical form (e.g., "Large Language Model" instead of "LLM")
- **Multiple Query Handlers**:
  - `search_by_topic`: Search content by specific topic
  - `get_trending_topics`: Get trending topics ranked by mention count

## Steps

### Indexing Flow
<img width="2732" height="2648" alt="flow" src="https://github.com/user-attachments/assets/04172792-7266-4b97-8957-bb481ed2602f" />


1. We define a custom source connector `HackerNews` to get HackerNews recent threads by calling HackerNews API.
2. For each thread and comment, we extract topics using LLM (`ExtractByLlm`).
3. We build two indexes:
   - `hn_messages`: Full text of threads and comments
   - `hn_topics`: Extracted topics with references to their source content, keyed by (topic, message_id)

## Prerequisite

[Install Postgres](https://cocoindex.io/docs/getting_started/installation#-install-postgres) if you don't have one.

## Run

Install dependencies:

```sh
pip install -e .
```

Update the target:

```sh
cocoindex update main
```

Each time when you run the `update` command, cocoindex will only re-process threads that have changed, and keep the target in sync with the recent 500 threads from HackerNews.

You can also run `update` command in live mode, which will keep the target in sync with the source continuously:

```sh
cocoindex update -L main.py
```

## Query Examples

After running the pipeline, you can query the extracted topics:

```sh
# Get trending topics
cocoindex query main.py get_trending_topics --limit 20

# Search content by specific topic
cocoindex query main.py search_by_topic --topic "Claude"

# Search by text content
cocoindex query main.py search_text --query "artificial intelligence"
```

## CocoInsight

I used CocoInsight (Free beta now) to troubleshoot the index generation and understand the data lineage of the pipeline.
It just connects to your local CocoIndex server, with Zero pipeline data retention. Run following command to start CocoInsight:

```
cocoindex server -ci -L main
```

<img width="2736" height="1384" alt="cocoinsight" src="https://github.com/user-attachments/assets/05f754b2-77c4-4cbe-a74e-04b70f9add76" />



Then open the CocoInsight UI at [https://cocoindex.io/cocoinsight](https://cocoindex.io/cocoinsight).
