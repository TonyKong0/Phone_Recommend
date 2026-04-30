from rag.indexer import load_or_build_index
from langchain_chroma import Chroma

_vectorstore: Chroma | None = None


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = load_or_build_index()
    return _vectorstore


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return top_k phones most semantically similar to query."""
    results = _get_vectorstore().similarity_search(query, k=top_k)
    return [{"content": doc.page_content, **doc.metadata} for doc in results]
