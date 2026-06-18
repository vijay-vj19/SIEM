"""
One-time RAG seeding script — embeds mock tickets and stores in Supabase pgvector.
Run from the backend/ directory after creating the Supabase table:
    python scripts/seed_rag.py

Required SQL (run once in Supabase SQL editor):
    create extension if not exists vector;

    create table soc_incidents (
      id bigserial primary key,
      ticket_id text,
      content text,
      metadata jsonb,
      embedding vector(1536)
    );

    create index on soc_incidents
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

try:
    from dotenv import load_dotenv
    load_dotenv(".env", override=True)
except ImportError:
    pass
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

import json
from pipeline.rag import ticket_to_text

TICKETS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tickets_100.ndjson")


def load_tickets() -> list[dict]:
    with open(TICKETS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    db_conn = os.getenv("SUPABASE_DB_CONNECTION", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if not all([supabase_url, supabase_key, db_conn, openai_key]):
        print("ERROR: Missing required environment variables.")
        print("Set: SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_DB_CONNECTION, OPENAI_API_KEY")
        sys.exit(1)

    print("=" * 60)
    print("SOC Triage — Supabase RAG Seeding")
    print("=" * 60)

    try:
        from llama_index.core import Document, VectorStoreIndex
        from llama_index.vector_stores.supabase import SupabaseVectorStore
        from llama_index.core import StorageContext
        from llama_index.embeddings.openai import OpenAIEmbedding
    except ImportError as e:
        print(f"Import error: {e}")
        print("Run: pip install llama-index llama-index-vector-stores-supabase")
        sys.exit(1)

    tickets = load_tickets()

    documents = []
    for ticket in tickets:
        content = ticket_to_text(ticket)
        doc = Document(
            text=content,
            metadata={
                "ticket_id": ticket["ticket_id"],
                "verdict": ticket["label"],
                "severity": ticket["severity"],
                "mitre_attack": ticket["mitre_attack"],
                "user_type": ticket["user_type"],
            },
        )
        documents.append(doc)
        print(f"  Prepared: {ticket['ticket_id']} ({ticket['label']})")

    print(f"\nEmbedding {len(documents)} documents with text-embedding-3-small...")

    vector_store = SupabaseVectorStore(
        postgres_connection_string=db_conn,
        collection_name="soc_incidents",
        dimension=1536,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embed_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=openai_key)

    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )

    print("\nSeeding complete. Supabase pgvector store is ready.")


if __name__ == "__main__":
    main()
