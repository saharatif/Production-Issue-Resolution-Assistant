"""Pinecone retrieval wrapper used by RAG-enabled investigator flows."""

from __future__ import annotations

from typing import Any

from app.config import settings


def retrieve_similar(
    query: str,
    top_k: int = 4,
    filter_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not settings.openai_api_key or not settings.pinecone_api_key:
        return []

    from langchain_openai import OpenAIEmbeddings
    from pinecone import Pinecone

    embedding = OpenAIEmbeddings(model="text-embedding-3-small").embed_query(query)
    index = Pinecone(api_key=settings.pinecone_api_key).Index(settings.pinecone_index)
    response = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_meta,
    )

    results = []
    for match in response.get("matches", []):
        metadata = match.get("metadata", {})
        results.append(
            {
                "text": metadata.get("text", ""),
                "score": match.get("score", 0),
                "source": metadata.get("source") or match.get("id"),
            }
        )
    return results
