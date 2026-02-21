"""
GCP Knowledge Base Service — creates GCS buckets, Vertex AI Search datastores,
grants IAM permissions, and triggers full indexing.
"""
import logging
import random
import string
from typing import Any, Dict, Optional

from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
from google.oauth2 import service_account
from google.iam.v1 import iam_policy_pb2, policy_pb2
from google.protobuf import field_mask_pb2

logger = logging.getLogger(__name__)

PLATFORM_SUFFIX = "ag-plat"


def _random_suffix(length: int = 4) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use in GCP resource names (lowercase, hyphens only)."""
    sanitized = name.lower().strip()
    sanitized = "".join(c if c.isalnum() or c == "-" else "-" for c in sanitized)
    # Collapse multiple hyphens
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    return sanitized.strip("-")


class GCPKnowledgeBaseService:
    """
    Manages GCP resources for knowledge bases:
    - GCS buckets for document storage
    - Vertex AI Search datastores for indexing and retrieval
    """

    def __init__(
        self,
        project_id: str,
        location: str = "global",
        service_account_path: Optional[str] = None,
        service_account_info: Optional[Dict[str, Any]] = None,
    ):
        self.project_id = project_id
        self.location = location
        self._credentials = None

        # Build credentials
        if service_account_info:
            self._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        elif service_account_path:
            self._credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        # Initialize clients
        client_kwargs = {}
        if self._credentials:
            client_kwargs["credentials"] = self._credentials

        self._storage_client = storage.Client(
            project=self.project_id, **client_kwargs
        )
        self._ds_client = discoveryengine.DataStoreServiceClient(
            **client_kwargs
        )
        self._doc_client = discoveryengine.DocumentServiceClient(
            **client_kwargs
        )

    def generate_resource_name(self, user_name: str) -> str:
        """Generate a GCP-compliant resource name: <name>-ag-plat-<random4>"""
        sanitized = _sanitize_name(user_name)
        suffix = _random_suffix(4)
        return f"{sanitized}-{PLATFORM_SUFFIX}-{suffix}"

    # ── GCS Bucket ────────────────────────────────────────────────────────────

    def create_bucket(
        self,
        bucket_name: str,
        location: str = "us-central1",
    ) -> Dict[str, Any]:
        """
        Create a GCS bucket for storing knowledge base documents.

        Args:
            bucket_name: Globally unique bucket name
            location: GCS bucket location

        Returns:
            Dict with bucket info

        Raises:
            Exception: If bucket creation fails
        """
        bucket = self._storage_client.bucket(bucket_name)
        bucket.storage_class = "STANDARD"
        new_bucket = self._storage_client.create_bucket(bucket, location=location)
        logger.info(f"Created GCS bucket: {new_bucket.name} in {new_bucket.location}")
        return {
            "bucket_name": new_bucket.name,
            "location": new_bucket.location,
            "storage_class": new_bucket.storage_class,
            "self_link": new_bucket.self_link,
        }

    def delete_bucket(self, bucket_name: str, force: bool = True) -> None:
        """Delete a GCS bucket and optionally all its contents."""
        bucket = self._storage_client.bucket(bucket_name)
        if force:
            blobs = list(bucket.list_blobs())
            for blob in blobs:
                blob.delete()
                logger.info(f"Deleted blob: {blob.name}")
        bucket.delete()
        logger.info(f"Deleted GCS bucket: {bucket_name}")

    # ── IAM Permissions ───────────────────────────────────────────────────────

    def grant_discovery_engine_access(self, bucket_name: str) -> Dict[str, Any]:
        """
        Grant the Vertex AI Discovery Engine Service Agent 'Storage Object Viewer'
        permission on the bucket.
        This is required for the service agent to read documents during import.

        Args:
            bucket_name: Name of the GCS bucket

        Returns:
            Dict with permission grant information

        Raises:
            Exception: If permission grant fails
        """
        # The Discovery Engine service agent email follows this pattern:
        service_agent_email = (
            f"service-{self._get_project_number()}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
        )

        bucket = self._storage_client.bucket(bucket_name)
        policy = bucket.get_iam_policy(requested_policy_version=3)
        policy.version = 3

        role = "roles/storage.objectViewer"
        member = f"serviceAccount:{service_agent_email}"

        # Check if binding already exists
        binding_exists = False
        for binding in policy.bindings:
            if binding["role"] == role and member in binding["members"]:
                binding_exists = True
                break

        if not binding_exists:
            policy.bindings.append({
                "role": role,
                "members": {member},
            })
            bucket.set_iam_policy(policy)
            logger.info(
                f"Granted {role} to {service_agent_email} on bucket {bucket_name}"
            )
        else:
            logger.info(
                f"Permission {role} already exists for {service_agent_email} on {bucket_name}"
            )

        return {
            "bucket_name": bucket_name,
            "service_agent": service_agent_email,
            "role": role,
            "action": "granted" if not binding_exists else "already_exists",
        }

    def _get_project_number(self) -> str:
        """Get the GCP project number from the project ID using the Resource Manager API."""
        try:
            from google.cloud import resourcemanager_v3
            client_kwargs = {}
            if self._credentials:
                client_kwargs["credentials"] = self._credentials
            rm_client = resourcemanager_v3.ProjectsClient(**client_kwargs)
            project = rm_client.get_project(name=f"projects/{self.project_id}")
            # project.name is "projects/<number>"
            project_number = project.name.split("/")[-1]
            logger.info(f"Resolved project number: {project_number} for {self.project_id}")
            return project_number
        except Exception as e:
            logger.error(f"Failed to get project number: {e}")
            raise

    # ── Vertex AI Search Datastore ────────────────────────────────────────────

    def create_datastore(
        self,
        datastore_name: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ) -> Dict[str, Any]:
        """
        Create a Vertex AI Search datastore with layout parser and chunking config.

        Args:
            datastore_name: Display name / ID for the datastore
            chunk_size: Number of tokens per chunk
            chunk_overlap: Overlap between chunks in tokens

        Returns:
            Dict with datastore info including datastore_id

        Raises:
            Exception: If datastore creation fails
        """
        parent = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection"

        # Build the document processing config with layout parser + chunking
        document_processing_config = discoveryengine.DocumentProcessingConfig(
            default_parsing_config=discoveryengine.DocumentProcessingConfig.ParsingConfig(
                layout_parsing_config=discoveryengine.DocumentProcessingConfig.ParsingConfig.LayoutParsingConfig(),
            ),
            chunking_config=discoveryengine.DocumentProcessingConfig.ChunkingConfig(
                layout_based_chunking_config=discoveryengine.DocumentProcessingConfig.ChunkingConfig.LayoutBasedChunkingConfig(
                    chunk_size=chunk_size,
                    include_ancestor_headings=True,
                ),
            ),
        )

        datastore = discoveryengine.DataStore(
            display_name=datastore_name,
            industry_vertical=discoveryengine.IndustryVertical.GENERIC,
            solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
            content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
            document_processing_config=document_processing_config,
        )

        request = discoveryengine.CreateDataStoreRequest(
            parent=parent,
            data_store=datastore,
            data_store_id=datastore_name,
        )

        # This is a long-running operation
        operation = self._ds_client.create_data_store(request=request)
        logger.info(f"Creating datastore '{datastore_name}', waiting for operation...")

        # Wait for the operation to complete
        result = operation.result(timeout=120)
        logger.info(f"Created datastore: {result.name}")

        return {
            "datastore_id": datastore_name,
            "datastore_name": result.display_name,
            "datastore_full_name": result.name,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "parser_type": "layout",
        }

    def delete_datastore(self, datastore_id: str) -> None:
        """Delete a Vertex AI Search datastore."""
        name = (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/collections/default_collection/dataStores/{datastore_id}"
        )
        operation = self._ds_client.delete_data_store(name=name)
        operation.result(timeout=120)
        logger.info(f"Deleted datastore: {datastore_id}")

    # ── Document Import / Indexing ────────────────────────────────────────────

    def import_documents(
        self,
        datastore_id: str,
        gcs_uri: str,
        mode: str = "incremental",
    ) -> Dict[str, Any]:
        """
        Trigger an import/indexing of documents from GCS into the datastore.

        Args:
            datastore_id: The datastore ID
            gcs_uri: GCS URI pattern, e.g. gs://bucket-name/*
            mode: "full" or "incremental"
                  - full: replaces all documents in the datastore with what is in GCS
                  - incremental: only adds/updates new documents

        Returns:
            Dict with import operation info

        Raises:
            Exception: If import fails
        """
        parent = (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/collections/default_collection/dataStores/{datastore_id}"
            f"/branches/default_branch"
        )

        recon_mode = (
            discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL
            if mode == "full"
            else discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
        )

        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=[gcs_uri],
                data_schema="content",
            ),
            reconciliation_mode=recon_mode,
        )

        operation = self._doc_client.import_documents(request=request)
        logger.info(f"Import started for datastore {datastore_id} from {gcs_uri}")

        # Wait for import to complete
        result = operation.result(timeout=600)
        logger.info(f"Import completed for datastore {datastore_id}")

        error_samples = []
        if hasattr(result, "error_samples"):
            error_samples = [
                {"code": e.code, "message": e.message}
                for e in result.error_samples
            ]

        return {
            "datastore_id": datastore_id,
            "gcs_uri": gcs_uri,
            "status": "completed",
            "error_samples": error_samples,
        }

    # ── Search ────────────────────────────────────────────────────────────────

    @staticmethod
    def _struct_to_dict(struct) -> dict:
        """
        Convert a google.protobuf.Struct to a plain Python dict.

        dict(struct) gives you Value wrapper objects, not plain types.
        MessageToDict is the correct way to get real Python values.
        """
        from google.protobuf.json_format import MessageToDict
        try:
            return MessageToDict(struct)
        except Exception:
            return {}

    def search_documents(
        self,
        datastore_id: str,
        query: str,
        page_size: int = 10,
    ) -> list:
        """
        Search documents in the Vertex AI Discovery Engine datastore.

        Returns a list of dicts with keys: document, page, score, text.
        """
        client_kwargs = {}
        if self._credentials:
            client_kwargs["credentials"] = self._credentials

        search_client = discoveryengine.SearchServiceClient(**client_kwargs)

        serving_config = (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/collections/default_collection/dataStores/{datastore_id}"
            f"/servingConfigs/default_config"
        )

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=page_size,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                    max_extractive_segment_count=1,
                    return_extractive_segment_score=True,
                ),
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=2,
                ),
            ),
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO,
            ),
        )

        response = search_client.search(request=request)

        results = []
        for result in response.results:
            doc = result.document

            # Convert protobuf Struct → plain Python dict (dict() gives Value wrappers)
            derived = self._struct_to_dict(doc.derived_struct_data) if (
                hasattr(doc, "derived_struct_data") and doc.derived_struct_data
            ) else {}

            # Document name: prefer the GCS URI link, fall back to doc id
            link = derived.get("link", "")
            doc_name = str(link).split("/")[-1] if link else (doc.id or "Unknown")

            # Page identifier (Discovery Engine stores it as a string)
            # Field name may appear as "pageIdentifier" (MessageToDict camelCase)
            page_val = derived.get("pageIdentifier", derived.get("page_identifier", "1"))
            try:
                page = int(str(page_val))
            except (ValueError, TypeError):
                page = 1

            # Extractive segments carry the actual text + relevance score.
            # MessageToDict uses camelCase for proto fields, but derived_struct_data
            # keys are freeform strings set by the service — try both conventions.
            text = ""
            score = 0.0
            segments = derived.get("extractiveSegments", derived.get("extractive_segments", []))
            if segments and isinstance(segments, list):
                seg = segments[0]
                if isinstance(seg, dict):
                    text = seg.get("content", "")
                    raw_score = seg.get("relevanceScore", seg.get("relevance_score", 0.0))
                    try:
                        score = float(raw_score)
                    except (TypeError, ValueError):
                        score = 0.0

            # Fallback: use snippet text when no extractive segment was returned
            if not text:
                snippets = derived.get("snippets", [])
                if snippets and isinstance(snippets, list):
                    snip = snippets[0]
                    if isinstance(snip, dict):
                        text = snip.get("snippet", "")

            results.append({
                "document": doc_name,
                "page": page,
                "score": round(float(score), 4),
                "text": text,
            })

        return results

    def get_indexed_content_samples(
        self,
        datastore_id: str,
        num_chunks: int = 10,
    ) -> list:
        """
        Retrieve a diverse sample of document chunks via broad Discovery Engine
        searches. Works for all indexed file types including PDFs and DOCX —
        the text was already extracted by Vertex AI's layout parser during indexing.
        Useful as document content input for LLM-based test data generation.
        """
        broad_queries = [
            "overview introduction summary",
            "key concepts main topics",
            "process steps procedure details",
            "specifications requirements information",
        ]

        seen_texts: set = set()
        chunks: list = []

        for query in broad_queries:
            try:
                results = self.search_documents(datastore_id, query, page_size=5)
                for r in results:
                    txt = (r.get("text") or "").strip()
                    if txt and txt not in seen_texts:
                        seen_texts.add(txt)
                        chunks.append(r)
                        if len(chunks) >= num_chunks:
                            break
            except Exception as e:
                logger.warning(f"Broad search failed for query '{query}': {e}")
            if len(chunks) >= num_chunks:
                break

        return chunks

    # ── Document Content Sampling (for test data generation) ──────────────────

    def get_document_content_samples(
        self,
        bucket_name: str,
        max_files: int = 3,
        max_bytes_per_file: int = 8000,
    ) -> list:
        """
        Download a text sample from each document in the GCS bucket.
        Binary formats (PDF, DOCX, PPTX, XLSX) are listed by name only —
        the LLM uses the filename as a hint about content.
        """
        TEXT_EXTENSIONS = {".txt", ".md", ".html", ".csv", ".json"}

        bucket = self._storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs())

        samples = []
        for blob in blobs[:max_files]:
            ext = ("." + blob.name.rsplit(".", 1)[-1].lower()) if "." in blob.name else ""
            content = ""
            if ext in TEXT_EXTENSIONS:
                try:
                    raw = blob.download_as_bytes(end=max_bytes_per_file)
                    content = raw.decode("utf-8", errors="replace")
                except Exception as e:
                    logger.warning(f"Could not read {blob.name}: {e}")
            samples.append({
                "name": blob.name,
                "extension": ext.lstrip("."),
                "size_bytes": blob.size or 0,
                "content": content,
            })

        return samples

    # ── Full Knowledge Base Creation ──────────────────────────────────────────

    def create_knowledge_base(
        self,
        name: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        bucket_location: str = "us-central1",
    ) -> Dict[str, Any]:
        """
        End-to-end knowledge base creation:
        1. Create GCS bucket
        2. Create Vertex AI Search datastore (layout parser + chunking)
        3. Grant Discovery Engine service agent access to bucket
        4. Return all resource info

        Args:
            name: User-provided name for the knowledge base
            chunk_size: Chunk size in tokens
            chunk_overlap: Chunk overlap in tokens
            bucket_location: GCS bucket location

        Returns:
            Dict with all created resource info
        """
        resource_name = self.generate_resource_name(name)
        logger.info(f"Creating knowledge base: {name} -> {resource_name}")

        # Step 1: Create GCS bucket
        bucket_info = self.create_bucket(
            bucket_name=resource_name,
            location=bucket_location,
        )
        logger.info(f"Step 1/3: Bucket created: {bucket_info['bucket_name']}")

        # Step 2: Create Vertex AI Search datastore
        try:
            datastore_info = self.create_datastore(
                datastore_name=resource_name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            logger.info(f"Step 2/3: Datastore created: {datastore_info['datastore_id']}")
        except Exception as e:
            # Cleanup bucket if datastore creation fails
            logger.error(f"Datastore creation failed, cleaning up bucket: {e}")
            try:
                self.delete_bucket(resource_name)
            except Exception:
                pass
            raise

        # Step 3: Grant IAM permissions
        try:
            iam_info = self.grant_discovery_engine_access(
                bucket_name=resource_name,
            )
            logger.info(f"Step 3/3: IAM granted: {iam_info['action']}")
        except Exception as e:
            logger.error(f"IAM grant failed (non-fatal, can be retried): {e}")
            iam_info = {"error": str(e), "action": "failed"}

        return {
            "resource_name": resource_name,
            "bucket": bucket_info,
            "datastore": datastore_info,
            "iam": iam_info,
        }
