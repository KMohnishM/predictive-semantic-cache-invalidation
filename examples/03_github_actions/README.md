# GitHub Actions CI/CD Integration

This example demonstrates how to set up automated, incremental Vector Database re-indexing every time code is pushed or merged into your `main` branch.

## Setup Instructions

1. **Add Workflow File**:
   Copy `workflow.yml` to `.github/workflows/reindex.yml` in your repository.

2. **Add Update Script**:
   Copy `update_vector_db.py` to your repository's `scripts/` or `ci/` directory and configure your Vector DB client (Pinecone, Chroma, Qdrant, Weaviate, etc.).

3. **Configure Secrets**:
   Add your Vector DB and Embedding API keys (`OPENAI_API_KEY`, `PINECONE_API_KEY`, etc.) in GitHub repository settings under **Settings -> Secrets and variables -> Actions**.

4. **Enjoy Low Embedding Costs**:
   Whenever PRs are merged, only functions and classes that experienced semantic drift are re-embedded. Fresh entities bypass embedding APIs completely.
