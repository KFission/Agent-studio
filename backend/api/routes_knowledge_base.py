"""
Knowledge Base API routes — create/manage knowledge bases backed by
GCS buckets + Vertex AI Discovery Engine datastores.

Routes use /knowledge-bases (plural) to match the existing frontend.
Response shape matches the frontend's expected format:
  kb_id, name, description, provider, status, documents, chunks,
  index_id, endpoint, embedding_model, dimension, created_at,
  last_synced, metadata
"""
import logging
import os
import json
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.engine import get_db_session
from backend.db.models import KnowledgeBaseModel, FileUploadModel, ProviderCredentialModel
from backend.config.settings import settings

logger = logging.getLogger(__name__)


# ── Request / Response Models ─────────────────────────────────────────────────

class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: str = ""
    chunk_size: int = Field(default=500, ge=100, le=2000)
    overlap: int = Field(default=64, ge=0, le=500)
    embedding_model: str = "text-embedding-004"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _kb_to_frontend_response(kb: KnowledgeBaseModel) -> dict:
    """Convert a KnowledgeBaseModel to the response shape the frontend expects."""
    meta = kb.metadata_json or {}
    ds_info = meta.get("datastore_info", {})
    ds_full_name = ds_info.get("datastore_full_name", "")

    # Collect unique file types from uploaded files
    file_types = list({f.file_type for f in (kb.files or []) if f.file_type})

    return {
        "kb_id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "provider": "vertex-ai",
        "status": kb.status,
        "documents": kb.file_count or 0,
        "chunks": sum(f.chunk_count for f in (kb.files or [])),
        "index_id": kb.datastore_id,
        "endpoint": ds_full_name or f"projects/{kb.gcp_project_id}/locations/{kb.gcp_location}/collections/default_collection/dataStores/{kb.datastore_id}",
        "embedding_model": "text-embedding-004",
        "dimension": 768,
        "created_at": kb.created_at.isoformat() + "Z" if kb.created_at else "",
        "last_synced": kb.updated_at.isoformat() + "Z" if kb.updated_at else None,
        "metadata": {
            "avg_chunk_size": kb.chunk_size,
            "overlap": kb.chunk_overlap,
            "file_types": file_types,
            "bucket_name": kb.bucket_name,
            "parser_type": kb.parser_type,
        },
    }


async def _get_gcp_service(session: AsyncSession):
    """
    Create the GCP Knowledge Base service.

    Credential resolution order:
    1. GOOGLE_APPLICATION_CREDENTIALS env var / settings path
    2. Active 'google' provider credential stored in the DB
    3. Application Default Credentials (ADC) — e.g. workload identity on GKE
    """
    from backend.knowledge_base.gcp_service import GCPKnowledgeBaseService
    from backend.db.credential_store import _decrypt

    sa_info = None

    # 1. Env var / settings path
    sa_path = settings.google_application_credentials or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if sa_path and os.path.exists(sa_path):
        with open(sa_path) as f:
            sa_info = json.load(f)

    # 2. DB-stored credential (encrypted service account JSON uploaded via UI)
    if not sa_info:
        try:
            result = await session.execute(
                select(ProviderCredentialModel)
                .where(ProviderCredentialModel.provider == "google")
                .where(ProviderCredentialModel.is_active.is_(True))
                .order_by(ProviderCredentialModel.created_at.desc())
                .limit(1)
            )
            cred_row = result.scalar_one_or_none()
            if cred_row:
                sa_info = json.loads(_decrypt(cred_row.credential_blob))
                logger.info("Using Google credentials from DB credential store")
        except Exception as e:
            logger.warning(f"Could not load Google credentials from DB: {e}")

    project_id = (sa_info.get("project_id") if sa_info else None) or settings.gcp_project_id

    return GCPKnowledgeBaseService(
        project_id=project_id,
        location="global",
        service_account_info=sa_info,
    )


# Module-level set keeps strong references to background tasks so Python's GC
# cannot collect them before they finish (asyncio.create_task returns a weak ref).
_bg_tasks: set = set()


# ── Route Registration ────────────────────────────────────────────────────────

def register_knowledge_base_routes(app: FastAPI, model_library=None, provider_factory=None, integration_manager=None):
    """Register all knowledge base routes at /knowledge-bases."""

    def _build_llm(model_id: str, temperature: float = 0.4, max_tokens: int = 4096):
        """Create an LLM instance via the shared provider factory."""
        if provider_factory is None:
            raise HTTPException(500, "LLM provider not available")
        extra_kwargs: dict = {}
        credential_data = None
        if model_library and integration_manager:
            entry = model_library.get(model_id)
            if entry:
                intg_id = (entry.metadata or {}).get("integration_id")
                if intg_id:
                    intg = integration_manager.get(intg_id)
                    if intg:
                        if intg.auth_type == "api_key" and intg.api_key:
                            extra_kwargs["google_api_key"] = intg.api_key
                        elif intg.auth_type == "service_account" and intg.service_account_json:
                            credential_data = intg.service_account_json
        return provider_factory.create(
            model_id, temperature=temperature, max_tokens=max_tokens,
            credential_data=credential_data, **extra_kwargs,
        )

    # ── List Knowledge Bases ──────────────────────────────────────────────

    @app.get("/knowledge-bases", tags=["Knowledge Base"])
    async def list_knowledge_bases(
        session: AsyncSession = Depends(get_db_session),
    ):
        """List all knowledge bases."""
        result = await session.execute(
            select(KnowledgeBaseModel).order_by(KnowledgeBaseModel.created_at.desc())
        )
        kbs = result.scalars().all()
        items = [_kb_to_frontend_response(kb) for kb in kbs]
        return {"knowledge_bases": items, "count": len(items)}

    # ── Get Knowledge Base ────────────────────────────────────────────────

    @app.get("/knowledge-bases/{kb_id}", tags=["Knowledge Base"])
    async def get_knowledge_base(
        kb_id: str,
        session: AsyncSession = Depends(get_db_session),
    ):
        """Get a knowledge base by ID."""
        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(404, "Knowledge base not found")
        return _kb_to_frontend_response(kb)

    # ── Create Knowledge Base ─────────────────────────────────────────────

    @app.post("/knowledge-bases", tags=["Knowledge Base"])
    async def create_knowledge_base(
        req: CreateKnowledgeBaseRequest,
        session: AsyncSession = Depends(get_db_session),
    ):
        """
        Create a new knowledge base:
        1. Create GCS bucket
        2. Create Vertex AI Discovery Engine datastore with layout parser
        3. Grant Discovery Engine service agent access to bucket
        4. Persist to DB
        """
        gcp_svc = await _get_gcp_service(session)

        # Discovery Engine layout-based chunking supports max 500
        effective_chunk_size = min(req.chunk_size, 500)

        # Create GCP resources (synchronous GCP calls in a thread)
        try:
            result = await asyncio.to_thread(
                gcp_svc.create_knowledge_base,
                name=req.name,
                chunk_size=effective_chunk_size,
                chunk_overlap=req.overlap,
            )
        except Exception as e:
            logger.error(f"Failed to create knowledge base GCP resources: {e}")
            raise HTTPException(500, f"Failed to create GCP resources: {e}")

        # Persist to DB
        kb = KnowledgeBaseModel(
            name=req.name,
            description=req.description,
            bucket_name=result["bucket"]["bucket_name"],
            datastore_id=result["datastore"]["datastore_id"],
            datastore_name=result["datastore"]["datastore_name"],
            chunk_size=req.chunk_size,
            chunk_overlap=req.overlap,
            parser_type="layout",
            gcp_project_id=settings.gcp_project_id,
            gcp_location="global",
            status="active",
            metadata_json={
                "resource_name": result["resource_name"],
                "bucket_info": result["bucket"],
                "datastore_info": result["datastore"],
                "iam_info": result["iam"],
            },
        )
        session.add(kb)
        await session.flush()
        await session.refresh(kb)

        logger.info(f"Knowledge base created: {kb.id} ({kb.name})")

        # Fire background full sync with Discovery Engine after creation
        kb_id_created = kb.id
        ds_id = kb.datastore_id
        bkt = kb.bucket_name

        async def _post_create_sync():
            try:
                await asyncio.to_thread(
                    gcp_svc.import_documents,
                    datastore_id=ds_id,
                    gcs_uri=f"gs://{bkt}/*",
                    mode="full",
                )
                logger.info(f"Post-creation full sync completed for KB {kb_id_created}")
            except Exception as e:
                logger.warning(f"Post-creation full sync failed for KB {kb_id_created} (expected if bucket is empty): {e}")

        _task = asyncio.create_task(_post_create_sync())
        _bg_tasks.add(_task)
        _task.add_done_callback(_bg_tasks.discard)

        return _kb_to_frontend_response(kb)

    # ── Delete Knowledge Base ─────────────────────────────────────────────

    @app.delete("/knowledge-bases/{kb_id}", tags=["Knowledge Base"])
    async def delete_knowledge_base(
        kb_id: str,
        session: AsyncSession = Depends(get_db_session),
    ):
        """Delete a knowledge base and its GCP resources."""
        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(404, "Knowledge base not found")

        gcp_svc = await _get_gcp_service(session)

        # Delete GCP resources (best-effort)
        errors = []
        try:
            await asyncio.to_thread(gcp_svc.delete_datastore, kb.datastore_id)
        except Exception as e:
            logger.error(f"Failed to delete datastore {kb.datastore_id}: {e}")
            errors.append(f"datastore: {e}")

        try:
            await asyncio.to_thread(gcp_svc.delete_bucket, kb.bucket_name, True)
        except Exception as e:
            logger.error(f"Failed to delete bucket {kb.bucket_name}: {e}")
            errors.append(f"bucket: {e}")

        # Delete from DB
        await session.delete(kb)

        return {"success": True, "deleted": kb_id, "gcp_cleanup_errors": errors if errors else None}

    # ── Upload File to Knowledge Base ─────────────────────────────────────

    @app.post("/knowledge-bases/{kb_id}/upload", tags=["Knowledge Base"])
    async def upload_file(
        kb_id: str,
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_db_session),
    ):
        """Upload a file to a knowledge base's GCS bucket."""
        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(404, "Knowledge base not found")

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Upload to GCS
        gcp_svc = await _get_gcp_service(session)
        try:
            def _upload():
                bucket = gcp_svc._storage_client.bucket(kb.bucket_name)
                blob = bucket.blob(file.filename)
                blob.upload_from_string(content, content_type=file.content_type)
                return f"gs://{kb.bucket_name}/{file.filename}"

            gcs_uri = await asyncio.to_thread(_upload)
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise HTTPException(500, f"Failed to upload file: {e}")

        # Determine file type from extension
        file_type = ""
        if file.filename:
            parts = file.filename.rsplit(".", 1)
            if len(parts) > 1:
                file_type = parts[1].lower()

        # Record in DB
        file_record = FileUploadModel(
            knowledge_base_id=kb_id,
            file_name=file.filename or "unknown",
            file_type=file_type,
            file_size_bytes=file_size,
            content_type=file.content_type or "application/octet-stream",
            gcs_uri=gcs_uri,
            status="syncing",
        )
        session.add(file_record)

        # Update KB counts
        kb.file_count = (kb.file_count or 0) + 1
        kb.total_size_bytes = (kb.total_size_bytes or 0) + file_size
        kb.updated_at = datetime.utcnow()

        await session.flush()
        await session.refresh(file_record)

        file_id = file_record.id
        datastore_id = kb.datastore_id
        bucket_name = kb.bucket_name

        # Fire background incremental sync with Discovery Engine
        async def _background_sync():
            from backend.db.engine import get_session_factory
            try:
                import_result = await asyncio.to_thread(
                    gcp_svc.import_documents,
                    datastore_id=datastore_id,
                    gcs_uri=f"gs://{bucket_name}/*",
                )
                new_status = "indexed"
                error_msg = ""
                if import_result.get("error_samples"):
                    error_msg = "; ".join(
                        e.get("message", "") for e in import_result["error_samples"]
                    )
                    if error_msg:
                        new_status = "failed"
                logger.info(f"Background sync completed for file {file_id}: {new_status}")
            except Exception as e:
                logger.error(f"Background sync failed for file {file_id}: {e}")
                new_status = "failed"
                error_msg = str(e)

            # Update file status in a fresh DB session
            try:
                factory = get_session_factory()
                async with factory() as bg_session:
                    async with bg_session.begin():
                        res = await bg_session.execute(
                            select(FileUploadModel).where(FileUploadModel.id == file_id)
                        )
                        f = res.scalar_one_or_none()
                        if f:
                            f.status = new_status
                            f.error_message = error_msg
                        # Also update KB status
                        kb_res = await bg_session.execute(
                            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
                        )
                        kb_obj = kb_res.scalar_one_or_none()
                        if kb_obj:
                            kb_obj.updated_at = datetime.utcnow()
            except Exception as db_err:
                logger.error(f"Failed to update file status after sync: {db_err}")

        _task = asyncio.create_task(_background_sync())
        _bg_tasks.add(_task)
        _task.add_done_callback(_bg_tasks.discard)

        return {
            "success": True,
            "documents_added": 1,
            "chunks_created": 0,
            "total_documents": kb.file_count,
            "total_chunks": sum(f.chunk_count for f in (kb.files or [])),
            "file_id": file_id,
            "file_name": file_record.file_name,
            "gcs_uri": file_record.gcs_uri,
            "status": "syncing",
        }

    # ── List Files in Knowledge Base ──────────────────────────────────────

    @app.get("/knowledge-bases/{kb_id}/files", tags=["Knowledge Base"])
    async def list_files(
        kb_id: str,
        session: AsyncSession = Depends(get_db_session),
    ):
        """List all files in a knowledge base."""
        result = await session.execute(
            select(FileUploadModel)
            .where(FileUploadModel.knowledge_base_id == kb_id)
            .order_by(FileUploadModel.created_at.desc())
        )
        files = result.scalars().all()
        return [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_type": f.file_type,
                "file_size_bytes": f.file_size_bytes,
                "content_type": f.content_type,
                "gcs_uri": f.gcs_uri,
                "status": f.status,
                "error_message": f.error_message,
                "chunk_count": f.chunk_count,
                "uploaded_by": f.uploaded_by,
                "created_at": f.created_at.isoformat() if f.created_at else "",
            }
            for f in files
        ]

    # ── Trigger Indexing ──────────────────────────────────────────────────

    @app.post("/knowledge-bases/{kb_id}/index", tags=["Knowledge Base"])
    async def trigger_indexing(
        kb_id: str,
        session: AsyncSession = Depends(get_db_session),
    ):
        """
        Trigger a full import/indexing of all documents in the knowledge base's
        GCS bucket into the Vertex AI Discovery Engine datastore.
        """
        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(404, "Knowledge base not found")

        gcp_svc = await _get_gcp_service(session)
        gcs_uri = f"gs://{kb.bucket_name}/*"

        try:
            import_result = await asyncio.to_thread(
                gcp_svc.import_documents,
                datastore_id=kb.datastore_id,
                gcs_uri=gcs_uri,
                mode="full",
            )
        except Exception as e:
            logger.error(f"Failed to trigger indexing: {e}")
            raise HTTPException(500, f"Failed to trigger indexing: {e}")

        # Update file statuses to "indexed"
        file_result = await session.execute(
            select(FileUploadModel)
            .where(FileUploadModel.knowledge_base_id == kb_id)
            .where(FileUploadModel.status == "uploaded")
        )
        for f in file_result.scalars().all():
            f.status = "indexed"

        kb.status = "indexed"
        kb.updated_at = datetime.utcnow()

        return {
            "knowledge_base_id": kb_id,
            "datastore_id": kb.datastore_id,
            "gcs_uri": gcs_uri,
            "import_result": import_result,
        }

    # ── Test Knowledge Base (search) ──────────────────────────────────────

    @app.post("/knowledge-bases/{kb_id}/test", tags=["Knowledge Base"])
    async def test_knowledge_base(
        kb_id: str,
        req: Request,
        session: AsyncSession = Depends(get_db_session),
    ):
        """Search a knowledge base using Vertex AI Discovery Engine."""
        import time as _time

        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(404, "Knowledge base not found")

        body = await req.json()
        query = body.get("query", "").strip()
        top_k = int(body.get("top_k", 5))

        if not query:
            raise HTTPException(400, "query is required")

        gcp_svc = await _get_gcp_service(session)

        start = _time.time()
        try:
            results = await asyncio.to_thread(
                gcp_svc.search_documents,
                datastore_id=kb.datastore_id,
                query=query,
                page_size=top_k,
            )
        except Exception as e:
            logger.error(f"Discovery Engine search failed for KB {kb_id}: {e}")
            raise HTTPException(500, f"Search failed: {e}")

        latency_ms = round((_time.time() - start) * 1000)
        return {
            "query": query,
            "results": results,
            "kb_id": kb_id,
            "latency_ms": latency_ms,
        }

    # ── Generate Test Data ────────────────────────────────────────────────

    @app.post("/knowledge-bases/{kb_id}/generate-test-data", tags=["Knowledge Base"])
    async def generate_test_data(
        kb_id: str,
        req: Request,
        session: AsyncSession = Depends(get_db_session),
    ):
        """
        Generate Q&A test pairs from the knowledge base documents using an LLM.
        Body: { model_id, num_questions, prompt_template }
        """
        result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if not kb:
            raise HTTPException(404, "Knowledge base not found")

        body = await req.json()
        model_id: str = body.get("model_id", "gemini-2.5-flash")
        num_questions: int = int(body.get("num_questions", 5))
        prompt_template: str = body.get("prompt_template", "")

        gcp_svc = await _get_gcp_service(session)

        # Primary: use indexed chunks from Discovery Engine — works for ALL file types
        # (PDFs, DOCX, etc.) because Vertex AI already extracted the text during indexing.
        chunks = []
        try:
            chunks = await asyncio.to_thread(
                gcp_svc.get_indexed_content_samples,
                datastore_id=kb.datastore_id,
                num_chunks=10,
            )
        except Exception as e:
            logger.warning(f"Could not get indexed content for KB {kb_id}: {e}")

        if chunks:
            doc_content_parts = [
                f"[Document: {c['document']}, Page: {c['page']}]\n{c['text']}"
                for c in chunks if c.get("text")
            ]
            document_content = "\n\n".join(doc_content_parts)
            content_source = f"indexed ({len(chunks)} chunks)"
        else:
            # Fallback: read raw GCS text (works for .txt, .md, .json, .csv, .html only)
            logger.info(f"No indexed chunks found for KB {kb_id}, falling back to raw GCS read")
            try:
                samples = await asyncio.to_thread(
                    gcp_svc.get_document_content_samples,
                    bucket_name=kb.bucket_name,
                    max_files=3,
                    max_bytes_per_file=8000,
                )
            except Exception as e:
                logger.error(f"Failed to read GCS samples for KB {kb_id}: {e}")
                raise HTTPException(500, f"Failed to read documents: {e}")

            if not samples:
                raise HTTPException(
                    422,
                    "No documents found. Upload and index files before generating test data.",
                )

            doc_content_parts = []
            for s in samples:
                header = f"--- {s['name']} ({s['extension'].upper() or 'file'}, {s['size_bytes']} bytes) ---"
                body_text = s["content"] or "(binary file — cannot extract text without indexing)"
                doc_content_parts.append(f"{header}\n{body_text}")
            document_content = "\n\n".join(doc_content_parts)
            content_source = f"raw GCS ({len(samples)} files)"

        if not document_content.strip():
            raise HTTPException(
                422,
                "Documents are uploaded but not yet indexed. "
                "Click 'Index All' and wait for indexing to complete, then try again.",
            )

        # Build the final prompt
        if prompt_template:
            prompt = (
                prompt_template
                .replace("{document_content}", document_content)
                .replace("{num_questions}", str(num_questions))
            )
        else:
            prompt = (
                f"You are a QA test case generator for a RAG knowledge base.\n\n"
                f"## Document Content\n{document_content}\n\n"
                f"## Instructions\n"
                f"- Generate {num_questions} question-answer pairs\n"
                f"- Cover different topics and question types\n"
                f"- Each answer must be directly supported by the document content\n"
                f"- Format as JSON array: "
                f'[{{"question": "...", "expected_answer": "...", "category": "..."}}]\n\n'
                f"Return ONLY the JSON array, no commentary."
            )

        try:
            llm = _build_llm(model_id, temperature=0.4, max_tokens=4096)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to initialise LLM: {e}")

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: llm.invoke([{"role": "user", "content": prompt}])
            )
            content = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"LLM call failed for generate-test-data KB {kb_id}: {e}")
            raise HTTPException(500, f"LLM generation failed: {e}")

        # Parse JSON from the LLM response
        test_data = []
        try:
            # Strip markdown code fences if present
            raw = content.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.rsplit("```", 1)[0].strip()
            test_data = json.loads(raw)
            if not isinstance(test_data, list):
                test_data = []
        except Exception:
            logger.warning(f"Could not parse LLM JSON for test data, returning raw: {content[:200]}")
            test_data = [{"question": "Parse error", "expected_answer": content, "category": "raw"}]

        return {
            "test_data": test_data,
            "kb_id": kb_id,
            "model_used": model_id,
            "content_source": content_source,
        }

    # ── Delete File ───────────────────────────────────────────────────────

    @app.delete("/knowledge-bases/{kb_id}/files/{file_id}", tags=["Knowledge Base"])
    async def delete_file(
        kb_id: str,
        file_id: str,
        session: AsyncSession = Depends(get_db_session),
    ):
        """Delete a file from the knowledge base (GCS + DB)."""
        result = await session.execute(
            select(FileUploadModel)
            .where(FileUploadModel.id == file_id)
            .where(FileUploadModel.knowledge_base_id == kb_id)
        )
        file_record = result.scalar_one_or_none()
        if not file_record:
            raise HTTPException(404, f"File '{file_id}' not found in knowledge base '{kb_id}'")

        # Delete from GCS
        gcp_svc = await _get_gcp_service(session)
        try:
            def _delete():
                bucket = gcp_svc._storage_client.bucket(
                    file_record.gcs_uri.replace("gs://", "").split("/")[0]
                )
                blob_name = "/".join(file_record.gcs_uri.replace("gs://", "").split("/")[1:])
                blob = bucket.blob(blob_name)
                blob.delete()

            await asyncio.to_thread(_delete)
        except Exception as e:
            logger.warning(f"Failed to delete file from GCS (continuing): {e}")

        # Update KB counts
        kb_result = await session.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        ds_id = kb.datastore_id if kb else None
        bkt = kb.bucket_name if kb else None
        if kb:
            kb.file_count = max(0, (kb.file_count or 0) - 1)
            kb.total_size_bytes = max(0, (kb.total_size_bytes or 0) - file_record.file_size_bytes)
            kb.updated_at = datetime.utcnow()

        await session.delete(file_record)

        # Fire background full sync so Discovery Engine removes the deleted document
        if ds_id and bkt:
            async def _post_delete_sync():
                try:
                    await asyncio.to_thread(
                        gcp_svc.import_documents,
                        datastore_id=ds_id,
                        gcs_uri=f"gs://{bkt}/*",
                        mode="full",
                    )
                    logger.info(f"Post-delete full sync completed for KB {kb_id}")
                except Exception as e:
                    logger.warning(f"Post-delete full sync failed for KB {kb_id}: {e}")

            _task = asyncio.create_task(_post_delete_sync())
            _bg_tasks.add(_task)
            _task.add_done_callback(_bg_tasks.discard)

        return {"deleted": file_id, "file_name": file_record.file_name}
