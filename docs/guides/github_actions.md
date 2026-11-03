# GitHub Actions CI/CD Integration

Automate vector database updates whenever code is pushed or merged into your repository using GitHub Actions.

---

## 1. Overview

Instead of re-indexing the entire codebase or running fragile file diff scripts, configure a GitHub Action that uses `predictive-semantic-cache` to selectively update only drifted code entities.

---

## 2. Drop-in Workflow File

Create `.github/workflows/incremental_reindex.yml` in your repository:

```yaml
name: Incremental Vector DB Update

on:
  push:
    branches: [ main ]

jobs:
  reindex:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 2  # Required to compare against the previous commit

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install predictive-semantic-cache openai

      - name: Re-embed drifted code entities
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          # VECTOR_DB_KEY: ${{ secrets.VECTOR_DB_KEY }}
        run: |
          python scripts/update_vector_db.py \
            --from ${{ github.event.before }} \
            --to ${{ github.sha }}
```

---

## 3. The Re-indexing Script (`scripts/update_vector_db.py`)

```python
import argparse
from predictive_semantic_cache import PredictiveCache

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_commit", required=True)
    parser.add_argument("--to", dest="to_commit", required=True)
    args = parser.parse_args()

    # 1. Initialize invalidation engine
    cache = PredictiveCache(repo_path=".")

    # 2. Get drifted entities
    stale_entities = cache.get_stale_entities(args.from_commit, args.to_commit)

    print(f"Detected {len(stale_entities)} drifted functions/classes.")

    # 3. Only re-embed these entities in your Vector DB!
    for ent in stale_entities:
        print(f"Re-indexing {ent.entity_id} ({ent.file_path}:{ent.lineno})")
        # embedding = client.embeddings.create(input=ent.source_code, model="text-embedding-3-small")
        # vector_db.upsert(id=ent.entity_id, vector=embedding.data[0].embedding)

if __name__ == "__main__":
    main()
```
