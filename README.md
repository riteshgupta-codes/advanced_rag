# Advanced Agentic RAG

An enterprise knowledge assistant that answers technical questions (Kubernetes, Intel hardware, networking) from your own documents. It combines guardrails, a LangGraph agent, two-stage retrieval, and an LLM gateway, with full tracing.

## Features

- **Multi-format ingestion**: PDF, HTML, TXT, DOCX, PPTX
- **Two-stage retrieval**: Qdrant vector search (top 15), then FlashRank cross-encoder reranking (top 5)
- **Agentic planner**: decides whether retrieval is needed and rewrites follow-up questions into standalone queries
- **Conversation memory**: per-thread history via LangGraph checkpointer
- **Guardrails**: NeMo Guardrails block jailbreaks and off-topic requests before the pipeline runs
- **LLM gateway**: Portkey provides retry, fallback across two keys, and response caching
- **Embedding fallback**: Gemini embeddings, with local `all-mpnet-base-v2` if Gemini is unavailable
- **Observability**: Logfire spans for every step
- **UI**: Streamlit chat with reasoning trace and retrieved sources

## Architecture

```
Streamlit UI
     |  POST /query
     v
FastAPI  -->  NeMo Guardrails  --(blocked)-->  scripted reply
                    |
                    v
             LangGraph agent
   planner --> retriever --> responder
      |        (Qdrant 15      (Portkey -> Groq)
      |         -> rerank 5)
      +-----------------------> responder   (conversational, no retrieval)
```

**Ingestion (offline):** load -> chunk -> embed -> upsert to Qdrant

## Tech Stack

| Area | Tool |
|---|---|
| API / UI | FastAPI, Streamlit |
| Agent | LangGraph |
| LLM | Groq (`openai/gpt-oss-20b`) via Portkey |
| Embeddings | Gemini (3072-d), fallback mpnet (768-d) |
| Vector DB | Qdrant |
| Reranker | FlashRank |
| Guardrails | NVIDIA NeMo Guardrails |
| Tracing | Logfire |

## Project Structure

```
app/
  main.py               FastAPI app (/, /graph, /query)
  config.py             Environment settings
  agents/               LangGraph state, graph, planner/retriever/responder nodes
  gateway/              Portkey client and cache-status helper
  guardrails/           Colang rules and NeMo wrapper
  ingestion/            Loaders, chunker, ingestion CLI
  services/retrieval/   Embeddings, Qdrant search, reranking
ui/app.py               Streamlit frontend
DATA/true_data/         Sample Kubernetes documents
```

## Setup

```bash
git clone <your-repo-url>
cd advanced_rag
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=
GROQ_API_KEY=
PORTKEY_API_KEY=
PORTKEY_CONFIG_SLUG=
GROQ_SLUG=
GROQ_SLUG_2=
QDRANT_API_KEY=
QDRANT_CLUSTER_ENDPOINT=
LOGFIRE_TOKEN=
BACKEND_URL=http://localhost:8000
```

## Run

```bash
# 1. Ingest documents (--wipe recreates the collection)
python -m app.ingestion.processor DATA --wipe

# 2. Start the API
uvicorn app.main:app --reload --port 8000

# 3. Start the UI (new terminal)
streamlit run ui/app.py
```

API docs: `http://localhost:8000/docs` | Agent graph image: `http://localhost:8000/graph`

## API

`POST /query`

```json
{ "q": "How do I run parallel jobs with a Redis work queue?", "thread_id": "user1" }
```

Response: `question`, `answer`, `thought_process`, `status`, `sources`

