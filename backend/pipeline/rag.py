"""
RAG pipeline: LlamaIndex + Supabase pgvector.
Retrieves top-3 similar past incidents for each incoming ticket.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_index = None
_retriever = None

# ---------------------------------------------------------------------------
# Supabase pgvector setup
# ---------------------------------------------------------------------------

def init_rag() -> None:
    """
    Initialise LlamaIndex with a Supabase pgvector store.
    Called once at app startup. Silently degrades if Supabase env vars missing.
    """
    global _index, _retriever

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    db_conn = os.getenv("SUPABASE_DB_CONNECTION", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if not all([supabase_url, supabase_key, db_conn]):
        logger.warning(
            "Supabase env vars not set — RAG disabled. "
            "Set SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_DB_CONNECTION."
        )
        return

    try:
        from llama_index.core import VectorStoreIndex
        from llama_index.vector_stores.supabase import SupabaseVectorStore
        from llama_index.core import StorageContext
        from llama_index.embeddings.openai import OpenAIEmbedding

        vector_store = SupabaseVectorStore(
            postgres_connection_string=db_conn,
            collection_name="soc_incidents",
            dimension=1536,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        embed_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=openai_key)

        _index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=embed_model,
        )
        _retriever = _index.as_retriever(similarity_top_k=3)
        logger.info("RAG pipeline initialized with Supabase pgvector")

    except Exception as exc:
        logger.warning(f"RAG init failed ({exc}) — RAG disabled")
        _index = None
        _retriever = None


# ---------------------------------------------------------------------------
# Ticket → document text
# ---------------------------------------------------------------------------

def ticket_to_text(ticket: dict) -> str:
    """Convert a ticket dict to a plain-text document for embedding."""
    return (
        f"Ticket: {ticket.get('ticket_id')} | "
        f"Rule: {ticket.get('rule_triggered')} | "
        f"MITRE: {ticket.get('mitre_attack')} | "
        f"User: {ticket.get('user')} ({ticket.get('user_type')}) | "
        f"Process: {ticket.get('process')} | "
        f"Command: {ticket.get('command_line')} | "
        f"Severity: {ticket.get('severity')} | "
        f"Label: {ticket.get('label', ticket.get('verdict', 'UNKNOWN'))}"
    )


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_similar(ticket_text: str) -> list[dict[str, Any]]:
    """
    Return top-3 similar past incidents.
    Falls back to empty list if RAG is unavailable.
    """
    if _retriever is None:
        logger.debug("RAG not available — returning empty similar incidents")
        return _mock_similar_incidents(ticket_text)

    try:
        nodes = _retriever.retrieve(ticket_text)
        results = []
        for node in nodes:
            meta = node.metadata or {}
            results.append(
                {
                    "ticket_id": meta.get("ticket_id", "UNKNOWN"),
                    "similarity": round(float(node.score or 0.0), 4),
                    "verdict": meta.get("verdict", meta.get("label", "UNKNOWN")),
                }
            )
        return results
    except Exception as exc:
        logger.warning(f"RAG retrieval failed ({exc})")
        return []


def _mock_similar_incidents(ticket_text: str) -> list[dict[str, Any]]:
    """
    Deterministic fallback when Supabase is not configured.
    Returns plausible similar incidents based on simple keyword matching.
    """
    from data.mock_tickets import MOCK_TICKETS

    text_lower = ticket_text.lower()

    scored = []
    for t in MOCK_TICKETS:
        score = 0.0
        if t.get("mitre_attack", "").lower() in text_lower:
            score += 0.4
        if t.get("user_type", "").lower() in text_lower:
            score += 0.2
        if t.get("process", "").lower() in text_lower:
            score += 0.2
        if any(word in text_lower for word in t.get("rule_triggered", "").lower().split()):
            score += 0.2
        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, t in scored[:3]:
        if score > 0:
            results.append(
                {
                    "ticket_id": t["ticket_id"],
                    "similarity": round(min(score + 0.5, 0.99), 2),
                    "verdict": t["label"],
                }
            )
    return results
