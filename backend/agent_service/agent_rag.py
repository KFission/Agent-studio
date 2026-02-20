"""
Agent RAG Manager — Per-agent Retrieval-Augmented Generation.
Each agent can have its own collections, documents, and retrieval config.
Supports Pinecone (unstructured) and local in-memory vector store.
"""

import uuid
import hashlib
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RAGDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    collection_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""
    token_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RAGCollection(BaseModel):
    collection_id: str = Field(default_factory=lambda: f"col-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    agent_id: Optional[str] = None  # None = shared collection
    embedding_model: str = "text-embedding-004"
    document_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RetrievalResult(BaseModel):
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _col_from_row(row) -> RAGCollection:
    return RAGCollection(
        collection_id=row.id, name=row.name, description=row.description or "",
        agent_id=row.agent_id, embedding_model=row.embedding_model or "text-embedding-004",
        document_count=row.document_count or 0,
        metadata=row.metadata_json if isinstance(row.metadata_json, dict) else {},
        created_at=row.created_at or datetime.utcnow(),
    )


def _doc_from_row(row) -> RAGDocument:
    return RAGDocument(
        doc_id=row.id, collection_id=row.collection_id,
        content=row.content or "", content_hash=row.content_hash or "",
        token_count=row.token_count or 0,
        metadata=row.metadata_json if isinstance(row.metadata_json, dict) else {},
        created_at=row.created_at or datetime.utcnow(),
    )


class AgentRAGManager:
    """
    Manages per-agent RAG collections and documents.
    PostgreSQL-backed with in-memory fallback.
    Phase 1: keyword matching. Phase 2: Pinecone/ChromaDB.
    """

    def __init__(self):
        self._collections: Dict[str, RAGCollection] = {}
        self._documents: Dict[str, List[RAGDocument]] = {}  # collection_id -> docs
        self._db_available = False

    def _sf(self):
        from backend.db.sync_bridge import get_session_factory
        return get_session_factory()

    # ── Async DB helpers ──────────────────────────────────────────

    async def _db_create_collection(self, col: RAGCollection) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from backend.db.models import RAGCollectionModel
        async with factory() as session:
            row = RAGCollectionModel(
                id=col.collection_id, name=col.name, description=col.description,
                agent_id=col.agent_id, embedding_model=col.embedding_model,
                document_count=0, metadata_json=col.metadata,
            )
            session.add(row)
            await session.commit()
            return True

    async def _db_get_collection(self, collection_id) -> Optional[RAGCollection]:
        factory = self._sf()
        if not factory:
            return None
        from sqlalchemy import select
        from backend.db.models import RAGCollectionModel
        async with factory() as session:
            row = (await session.execute(
                select(RAGCollectionModel).where(RAGCollectionModel.id == collection_id)
            )).scalar_one_or_none()
            return _col_from_row(row) if row else None

    async def _db_list_collections(self, agent_id=None) -> List[RAGCollection]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select, or_
        from backend.db.models import RAGCollectionModel
        async with factory() as session:
            q = select(RAGCollectionModel)
            if agent_id:
                q = q.where(or_(
                    RAGCollectionModel.agent_id == agent_id,
                    RAGCollectionModel.agent_id == None,
                ))
            rows = (await session.execute(q)).scalars().all()
            return [_col_from_row(r) for r in rows]

    async def _db_delete_collection(self, collection_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import RAGCollectionModel
        async with factory() as session:
            row = (await session.execute(
                select(RAGCollectionModel).where(RAGCollectionModel.id == collection_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def _db_add_document(self, doc: RAGDocument) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import RAGDocumentModel, RAGCollectionModel
        async with factory() as session:
            row = RAGDocumentModel(
                id=doc.doc_id, collection_id=doc.collection_id,
                content=doc.content, content_hash=doc.content_hash,
                token_count=doc.token_count, metadata_json=doc.metadata,
            )
            session.add(row)
            # Update document count
            col_row = (await session.execute(
                select(RAGCollectionModel).where(RAGCollectionModel.id == doc.collection_id)
            )).scalar_one_or_none()
            if col_row:
                col_row.document_count = (col_row.document_count or 0) + 1
            await session.commit()
            return True

    async def _db_get_documents(self, collection_id, limit, offset) -> List[RAGDocument]:
        factory = self._sf()
        if not factory:
            return []
        from sqlalchemy import select
        from backend.db.models import RAGDocumentModel
        async with factory() as session:
            q = (select(RAGDocumentModel)
                 .where(RAGDocumentModel.collection_id == collection_id)
                 .order_by(RAGDocumentModel.created_at)
                 .offset(offset).limit(limit))
            rows = (await session.execute(q)).scalars().all()
            return [_doc_from_row(r) for r in rows]

    async def _db_delete_document(self, collection_id, doc_id) -> bool:
        factory = self._sf()
        if not factory:
            return False
        from sqlalchemy import select
        from backend.db.models import RAGDocumentModel, RAGCollectionModel
        async with factory() as session:
            row = (await session.execute(
                select(RAGDocumentModel).where(RAGDocumentModel.id == doc_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            col_row = (await session.execute(
                select(RAGCollectionModel).where(RAGCollectionModel.id == collection_id)
            )).scalar_one_or_none()
            if col_row:
                col_row.document_count = max(0, (col_row.document_count or 1) - 1)
            await session.commit()
            return True

    async def _db_stats(self) -> Dict[str, Any]:
        factory = self._sf()
        if not factory:
            return {}
        from sqlalchemy import select, func
        from backend.db.models import RAGCollectionModel, RAGDocumentModel
        async with factory() as session:
            total_cols = (await session.execute(select(func.count(RAGCollectionModel.id)))).scalar() or 0
            total_docs = (await session.execute(select(func.count(RAGDocumentModel.id)))).scalar() or 0
            return {"total_collections": total_cols, "total_documents": total_docs, "persistence": "postgresql"}

    # ── Collections ───────────────────────────────────────────────

    def create_collection(
        self, name: str, agent_id: Optional[str] = None,
        description: str = "", embedding_model: str = "text-embedding-004",
    ) -> RAGCollection:
        col = RAGCollection(
            name=name, description=description,
            agent_id=agent_id, embedding_model=embedding_model,
        )
        self._collections[col.collection_id] = col
        self._documents[col.collection_id] = []
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_create_collection(col))
            except Exception:
                pass
        return col

    def get_collection(self, collection_id: str) -> Optional[RAGCollection]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_get_collection(collection_id))
                if result:
                    return result
            except Exception:
                pass
        return self._collections.get(collection_id)

    def list_collections(self, agent_id: Optional[str] = None) -> List[RAGCollection]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_list_collections(agent_id))
            except Exception:
                pass
        cols = list(self._collections.values())
        if agent_id:
            cols = [c for c in cols if c.agent_id == agent_id or c.agent_id is None]
        return cols

    def delete_collection(self, collection_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_delete_collection(collection_id))
            except Exception:
                pass
        removed = self._collections.pop(collection_id, None)
        self._documents.pop(collection_id, None)
        return removed is not None

    # ── Documents ─────────────────────────────────────────────────

    def add_document(
        self, collection_id: str, content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[RAGDocument]:
        if collection_id not in self._collections:
            if self._db_available:
                col = self.get_collection(collection_id)
                if not col:
                    return None
            else:
                return None

        doc = RAGDocument(
            collection_id=collection_id,
            content=content,
            metadata=metadata or {},
            content_hash=hashlib.md5(content.encode()).hexdigest(),
            token_count=len(content) // 4,
        )
        self._documents.setdefault(collection_id, []).append(doc)
        col = self._collections.get(collection_id)
        if col:
            col.document_count += 1
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                run_async(self._db_add_document(doc))
            except Exception:
                pass
        return doc

    def add_documents_bulk(
        self, collection_id: str, documents: List[Dict[str, Any]]
    ) -> List[RAGDocument]:
        results = []
        for d in documents:
            doc = self.add_document(collection_id, d.get("content", ""), d.get("metadata"))
            if doc:
                results.append(doc)
        return results

    def get_documents(self, collection_id: str, limit: int = 50, offset: int = 0) -> List[RAGDocument]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                return run_async(self._db_get_documents(collection_id, limit, offset))
            except Exception:
                pass
        docs = self._documents.get(collection_id, [])
        return docs[offset:offset + limit]

    def delete_document(self, collection_id: str, doc_id: str) -> bool:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                ok = run_async(self._db_delete_document(collection_id, doc_id))
                if ok:
                    # Also update in-memory
                    docs = self._documents.get(collection_id, [])
                    self._documents[collection_id] = [d for d in docs if d.doc_id != doc_id]
                    col = self._collections.get(collection_id)
                    if col:
                        col.document_count = max(0, col.document_count - 1)
                    return True
            except Exception:
                pass
        docs = self._documents.get(collection_id, [])
        for i, d in enumerate(docs):
            if d.doc_id == doc_id:
                docs.pop(i)
                col = self._collections.get(collection_id)
                if col:
                    col.document_count = max(0, col.document_count - 1)
                return True
        return False

    # ── Retrieval ─────────────────────────────────────────────────

    def retrieve(
        self, collection_ids: List[str], query: str,
        top_k: int = 5, score_threshold: float = 0.0,
    ) -> List[RetrievalResult]:
        """
        Simple keyword-based retrieval (Phase 1).
        Phase 2: replace with embedding similarity via Pinecone/ChromaDB.
        """
        query_terms = set(query.lower().split())
        results: List[RetrievalResult] = []

        for cid in collection_ids:
            docs = self.get_documents(cid, limit=1000)
            for doc in docs:
                doc_terms = set(doc.content.lower().split())
                overlap = len(query_terms & doc_terms)
                if overlap == 0:
                    continue
                score = overlap / max(len(query_terms), 1)
                if score >= score_threshold:
                    results.append(RetrievalResult(
                        doc_id=doc.doc_id,
                        content=doc.content[:500],
                        score=round(score, 3),
                        metadata=doc.metadata,
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def retrieve_for_agent(
        self, agent_id: str, query: str, top_k: int = 5,
    ) -> List[RetrievalResult]:
        """Retrieve from all collections accessible to an agent."""
        cols = self.list_collections(agent_id)
        col_ids = [c.collection_id for c in cols]
        return self.retrieve(col_ids, query, top_k)

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        if self._db_available:
            from backend.db.sync_bridge import run_async
            try:
                result = run_async(self._db_stats())
                if result:
                    return result
            except Exception:
                pass
        total_docs = sum(len(v) for v in self._documents.values())
        return {
            "total_collections": len(self._collections),
            "total_documents": total_docs,
            "collections": [
                {"id": c.collection_id, "name": c.name, "docs": c.document_count, "agent": c.agent_id}
                for c in self._collections.values()
            ],
            "persistence": "in-memory",
        }
