"""Databricks sink for uploading invoices, policies, and audit trails to ADLS Gen2."""

from __future__ import annotations

import json
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DatabricksSink:
    """Upload data to Azure Blob Storage for Databricks ingestion.
    
    Supports:
    - Invoice transactions
    - Policy documents
    - Adaptive memory exceptions
    - Agent execution trails
    """

    def __init__(self):
        """Initialize sink with Azure Blob Storage credentials."""
        self.enabled = self._check_enabled()
        if self.enabled:
            self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            self.container_invoices = os.getenv("AZURE_CONTAINER_INVOICES", "raw-transactions")
            self.container_audit = os.getenv("AZURE_CONTAINER_AUDIT", "audit-trails")
            self.registry_path = Path(os.getenv("DATABRICKS_UPLOAD_REGISTRY", "data/databricks_upload_registry.json"))
            self._uploaded_hashes: set[str] = set()
            self._init_clients()
            self._load_registry()
        else:
            logger.warning(
                "DatabricksSink disabled: AZURE_STORAGE_CONNECTION_STRING not set. "
                "Invoices will only be stored locally."
            )

    def _check_enabled(self) -> bool:
        """Check if Azure Blob Storage is configured."""
        return bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))

    def _init_clients(self):
        """Initialize Azure Blob Storage clients."""
        try:
            from azure.storage.blob import BlobServiceClient

            self.blob_service = BlobServiceClient.from_connection_string(self.connection_string)
            self.invoice_container = self.blob_service.get_container_client(self.container_invoices)
            self.audit_container = self.blob_service.get_container_client(self.container_audit)
            
            # Create containers if they don't exist
            try:
                self.invoice_container.create_container()
                logger.info(f"Created container: {self.container_invoices}")
            except Exception:
                pass  # Container already exists
            
            try:
                self.audit_container.create_container()
                logger.info(f"Created container: {self.container_audit}")
            except Exception:
                pass  # Container already exists
            
            logger.info("DatabricksSink initialized successfully")
        except ImportError:
            logger.error("azure-storage-blob not installed. Install with: pip install azure-storage-blob")
            self.enabled = False
        except Exception as exc:
            logger.error(f"Failed to initialize Azure Blob Storage clients: {exc}")
            self.enabled = False

    # ---------------- Registry (duplicate detection) -----------------
    def _load_registry(self):
        """Load previously uploaded invoice content hashes from disk."""
        try:
            if self.registry_path.exists():
                data = json.loads(self.registry_path.read_text())
                if isinstance(data, list):
                    self._uploaded_hashes = set(data)
                    logger.info(f"Loaded {len(self._uploaded_hashes)} uploaded invoice hashes")
        except Exception as exc:
            logger.warning(f"Failed to load upload registry: {exc}")

    def _save_registry(self):
        """Persist current invoice hash set to disk."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            self.registry_path.write_text(json.dumps(sorted(self._uploaded_hashes), indent=2))
        except Exception as exc:
            logger.warning(f"Failed to save upload registry: {exc}")

    @staticmethod
    def _compute_invoice_hash(invoice: dict) -> str:
        """Compute stable SHA256 hash of invoice content.

        Removes transient fields if present (e.g., uploaded_at) to avoid false positives.
        """
        # Create canonical JSON string with sorted keys
        canonical = json.dumps(invoice, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def upload_invoice(self, invoice: dict, transaction_id: str, created_at: str | None = None, force: bool = False) -> str | None:
        """Upload invoice JSON to ADLS Gen2 for Databricks ingestion.
        
        Args:
            invoice: Invoice data dictionary
            transaction_id: Unique transaction identifier
            created_at: Optional original creation timestamp (ISO). If provided, used for date path.
            force: If True, upload even if duplicate hash detected.
            
        Returns:
            Blob URL if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            inv_hash = self._compute_invoice_hash(invoice)
            if inv_hash in self._uploaded_hashes and not force:
                logger.info(f"Skipping duplicate invoice upload (hash={inv_hash[:12]}) transaction_id={transaction_id}")
                return None

            timestamp = datetime.utcnow()
            # Use original creation date for path if provided
            if created_at:
                try:
                    dt_for_path = datetime.fromisoformat(created_at.replace("Z", ""))
                except Exception:
                    dt_for_path = timestamp
            else:
                dt_for_path = timestamp

            payload = {
                "invoice": invoice,
                "transaction_id": transaction_id,
                "uploaded_at": timestamp.isoformat(),
                "source": "afga_api",
                "invoice_hash": inv_hash,
            }

            blob_name = f"invoices/{dt_for_path.strftime('%Y/%m/%d')}/{transaction_id}.json"
            blob_client = self.invoice_container.get_blob_client(blob_name)
            
            blob_client.upload_blob(
                data=json.dumps(payload, indent=2),
                overwrite=True,
                metadata={"transaction_id": transaction_id, "source": "afga_api", "invoice_hash": inv_hash},
            )
            
            blob_url = blob_client.url
            self._uploaded_hashes.add(inv_hash)
            self._save_registry()
            logger.info(f"Uploaded invoice {transaction_id} (hash={inv_hash[:12]}) to {blob_url}")
            return blob_url

        except Exception as exc:
            logger.error(f"Failed to upload invoice {transaction_id}: {exc}", exc_info=True)
            return None

    def upload_agent_trail(self, transaction_id: str, audit_trail: list[dict]) -> str | None:
        """Upload agent execution trail for audit purposes.
        
        Args:
            transaction_id: Transaction identifier
            audit_trail: List of agent execution steps
            
        Returns:
            Blob URL if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            payload = {
                "transaction_id": transaction_id,
                "audit_trail": audit_trail,
                "timestamp": datetime.utcnow().isoformat(),
                # Include invoice hash if known
                "invoice_hash": next((step.get("invoice_hash") for step in audit_trail if isinstance(step, dict) and step.get("invoice_hash")), None),
            }

            blob_name = f"agent-trails/{datetime.utcnow().strftime('%Y/%m/%d')}/{transaction_id}_trail.json"
            blob_client = self.audit_container.get_blob_client(blob_name)
            
            blob_client.upload_blob(
                data=json.dumps(payload, indent=2),
                overwrite=True,
                metadata={"transaction_id": transaction_id, "type": "agent_trail"},
            )
            
            blob_url = blob_client.url
            logger.info(f"Uploaded agent trail for {transaction_id} to {blob_url}")
            return blob_url

        except Exception as exc:
            logger.error(f"Failed to upload agent trail {transaction_id}: {exc}", exc_info=True)
            return None

    def upload_memory_snapshot(self, exceptions: list[dict]) -> str | None:
        """Upload adaptive memory snapshot for audit/training.
        
        Args:
            exceptions: List of memory exception records
            
        Returns:
            Blob URL if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            timestamp = datetime.utcnow()
            payload = {
                "snapshot_timestamp": timestamp.isoformat(),
                "total_exceptions": len(exceptions),
                "exceptions": exceptions,
            }

            blob_name = f"memory-snapshots/{timestamp.strftime('%Y/%m/%d')}/snapshot_{timestamp.strftime('%H%M%S')}.json"
            blob_client = self.audit_container.get_blob_client(blob_name)
            
            blob_client.upload_blob(
                data=json.dumps(payload, indent=2),
                overwrite=True,
                metadata={"type": "memory_snapshot", "count": str(len(exceptions))},
            )
            
            blob_url = blob_client.url
            logger.info(f"Uploaded memory snapshot ({len(exceptions)} exceptions) to {blob_url}")
            return blob_url

        except Exception as exc:
            logger.error(f"Failed to upload memory snapshot: {exc}", exc_info=True)
            return None

    def upload_policy_document(self, policy_path: Path, metadata: dict[str, Any] | None = None) -> str | None:
        """Upload policy document for centralized governance.
        
        Args:
            policy_path: Path to policy document
            metadata: Optional metadata dictionary
            
        Returns:
            Blob URL if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            with open(policy_path, "rb") as f:
                content = f.read()

            blob_name = f"policies/{policy_path.name}"
            blob_client = self.audit_container.get_blob_client(blob_name)
            
            upload_metadata = {
                "filename": policy_path.name,
                "uploaded_at": datetime.utcnow().isoformat(),
                "type": "policy_document",
            }
            if metadata:
                upload_metadata.update(metadata)
            
            blob_client.upload_blob(
                data=content,
                overwrite=True,
                metadata=upload_metadata,
            )
            
            blob_url = blob_client.url
            logger.info(f"Uploaded policy {policy_path.name} to {blob_url}")
            return blob_url

        except Exception as exc:
            logger.error(f"Failed to upload policy {policy_path}: {exc}", exc_info=True)
            return None

    def upload_kpi_snapshot(self, kpis: dict) -> str | None:
        """Upload KPI metrics snapshot for historical tracking.
        
        Args:
            kpis: KPI metrics dictionary
            
        Returns:
            Blob URL if successful, None otherwise
        """
        if not self.enabled:
            return None

        try:
            timestamp = datetime.utcnow()
            payload = {
                "snapshot_timestamp": timestamp.isoformat(),
                "kpis": kpis,
            }

            blob_name = f"kpi-snapshots/{timestamp.strftime('%Y/%m/%d')}/kpi_{timestamp.strftime('%H%M%S')}.json"
            blob_client = self.audit_container.get_blob_client(blob_name)
            
            blob_client.upload_blob(
                data=json.dumps(payload, indent=2),
                overwrite=True,
                metadata={"type": "kpi_snapshot"},
            )
            
            blob_url = blob_client.url
            logger.debug(f"Uploaded KPI snapshot to {blob_url}")
            return blob_url

        except Exception as exc:
            logger.error(f"Failed to upload KPI snapshot: {exc}", exc_info=True)
            return None


# Global singleton instance
_databricks_sink: DatabricksSink | None = None


def get_databricks_sink() -> DatabricksSink:
    """Get or create the global DatabricksSink instance."""
    global _databricks_sink
    if _databricks_sink is None:
        _databricks_sink = DatabricksSink()
    return _databricks_sink
