"""ChromaDB vector store for policy chunks."""

from pathlib import Path
from typing import Any

from src.config import get_config

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None


class PolicyVectorStore:
    """ChromaDB-backed store for policy text chunks."""

    def __init__(self, persist_directory: str | Path | None = None, collection_name: str | None = None) -> None:
        if chromadb is None:
            raise ImportError("chromadb required. Install with: pip install chromadb")
        config = get_config()
        paths = config.get("paths", {})
        vs_config = config.get("vector_store", {})

        base = Path(__file__).resolve().parent.parent.parent
        persist = persist_directory or paths.get("chroma_db", "chroma_db")
        if not Path(persist).is_absolute():
            persist = base / persist
        self.persist_directory = str(persist)
        self.collection_name = collection_name or vs_config.get("collection_name", "authlookup_policies")
        self._client = chromadb.PersistentClient(path=self.persist_directory, settings=Settings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(name=self.collection_name, metadata={"description": "Policy chunks"})

    def add_chunks(self, chunks: list[dict], ids: list[str] | None = None) -> None:
        """Add policy chunks to the store."""
        texts = [c["text"] for c in chunks]
        metadatas = []
        for c in chunks:
            meta = dict(c.get("metadata", {}))
            for k, v in list(meta.items()):
                if v is None or (isinstance(v, (list, dict)) and len(str(v)) > 500):
                    meta[k] = str(v)[:500]
            metadatas.append(meta)
        if ids is None:
            ids = [f"chunk_{i}" for i in range(len(chunks))]
        self._collection.add(documents=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, n_results: int = 5, where: dict | None = None) -> list[dict]:
        """Search for relevant chunks."""
        kwargs = {"n_results": n_results}
        if where:
            kwargs["where"] = where
        results = self._collection.query(query_texts=[query], **kwargs)
        docs = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = (results["metadatas"][0][i] if results["metadatas"] else {}) or {}
                docs.append({"text": doc, "metadata": meta})
        return docs

    def count(self) -> int:
        """Return number of chunks in collection."""
        return self._collection.count()
