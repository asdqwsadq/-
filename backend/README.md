# Backend

Python backend for the Kongming Agent.

## Stack

- FastAPI
- LangChain
- MySQL for persistent base records
- Milvus for vector storage
- DashScope embeddings for knowledge ingestion
- Optional OpenAI-compatible LLM and local Ollama via environment variables

## Run

Make sure local MySQL, Milvus, Ollama, and `DASHSCOPE_API_KEY` are ready first.

Command line:

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

PyCharm:

```bash
cd backend
python run_backend.py
```

Note:

- Do not use `--reload` during full knowledge ingestion. Reloads restart the server process and interrupt the rebuild job.
- `run_backend.py` will switch to a Python interpreter that has `uvicorn` installed if the current one does not.
- If you use the direct `uvicorn` command, prefer the stable `--host 127.0.0.1 --port 8000` form.

## Notes

- Knowledge sources are the four classic novel text files in the repo root.
- Full ingestion writes progress into the rebuild job and can be polled from `/api/v1/knowledge/rebuild/{job_id}`.
- Full ingestion now generates all embeddings with DashScope first, then writes the full batch to Milvus in one insert.
- MySQL stores the persistent base records. Use `MYSQL_DATABASE=kongming_agent` unless you want a different database name.
- The backend now persists base records in MySQL and keeps vector storage in Milvus.
