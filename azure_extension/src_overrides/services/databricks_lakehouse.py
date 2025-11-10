from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..models.schemas import TransactionResult, Invoice, HITLFeedback

logger = logging.getLogger(__name__)

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.filedatalake import DataLakeServiceClient
    from azure.core.credentials import AzureNamedKeyCredential
    from azure.core.exceptions import ResourceExistsError

    AZURE_STORAGE_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    AZURE_STORAGE_AVAILABLE = False
    logger.warning(
        "Azure Storage SDK not available. Install azure-identity azure-storage-file-datalake "
        "to enable Databricks lakehouse replication."
    )

try:
    from databricks.sdk import WorkspaceClient

    DATABRICKS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    WorkspaceClient = None  # type: ignore
    DATABRICKS_AVAILABLE = False
    logger.warning(
        "Databricks SDK not available. Install databricks-sdk to trigger Databricks jobs automatically."
    )


class DatabricksLakehouseUploader:
    """Replicates AFGA transactions and feedback to the Databricks lakehouse."""

    def __init__(
        self,
        storage_account_name: str,
        container_name: str = "raw-transactions",
        use_managed_identity: bool = True,
        storage_account_key: Optional[str] = None,
        databricks_workspace_url: Optional[str] = None,
        databricks_job_id: Optional[int | str] = None,
        databricks_token: Optional[str] = None,
    ) -> None:
        if not AZURE_STORAGE_AVAILABLE:
            raise ImportError(
                "Azure Storage SDK required. Install with `uv add azure-identity azure-storage-file-datalake`."
            )

        if not storage_account_name:
            raise ValueError("storage_account_name is required for Databricks lakehouse replication.")

        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.use_managed_identity = use_managed_identity
        self.storage_account_key = storage_account_key

        account_url = f"https://{storage_account_name}.dfs.core.windows.net"
        if use_managed_identity:
            credential = DefaultAzureCredential()
        elif storage_account_key:
            credential = AzureNamedKeyCredential(storage_account_name, storage_account_key)
        else:
            raise ValueError("Either use a managed identity or provide an Azure Storage account key.")

        self.storage_client = DataLakeServiceClient(account_url=account_url, credential=credential)

        self.databricks_workspace_url = databricks_workspace_url
        self.databricks_job_id = int(databricks_job_id) if databricks_job_id else None
        self.databricks_token = databricks_token

        self.databricks_client = None
        if (
            self.databricks_workspace_url
            and self.databricks_job_id
            and self.databricks_token
            and DATABRICKS_AVAILABLE
        ):
            try:
                self.databricks_client = WorkspaceClient(
                    host=self.databricks_workspace_url,
                    token=self.databricks_token,
                )
                logger.info(
                    "Databricks job client initialized for job_id=%s", self.databricks_job_id
                )
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("Failed to initialize Databricks client: %s", exc)
                self.databricks_client = None
        elif self.databricks_job_id:
            logger.warning(
                "Databricks job ID provided but SDK/token not available. "
                "Automatic pipeline triggering will be skipped."
            )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def upload_transaction(self, result: TransactionResult) -> None:
        """Persist transaction artifacts (invoice + decision) to ADLS Gen2."""
        now = datetime.now(timezone.utc)
        base_dir = (
            f"transactions/{now.year}/{now.month:02d}/{now.day:02d}/{result.transaction_id}"
        )

        # Invoice payload
        invoice_payload = result.invoice.model_dump(mode="json")
        self._upload_json(
            directory=base_dir,
            filename="invoice.json",
            payload=invoice_payload,
        )

        # Transaction payload
        transaction_payload = result.model_dump(mode="json")
        transaction_payload.update(
            {
                "uploaded_at": now.isoformat(),
                "storage_source": "afga-backend",
            }
        )
        self._upload_json(
            directory=base_dir,
            filename="transaction.json",
            payload=transaction_payload,
        )

        self._trigger_databricks_job()

    def upload_hitl_feedback(self, feedback: HITLFeedback, invoice: Invoice) -> None:
        """Persist HITL feedback to ADLS Gen2 for downstream analytics."""
        now = datetime.now(timezone.utc)
        feedback_id = str(uuid.uuid4())[:8]
        base_dir = (
            f"hitl-feedback/{now.year}/{now.month:02d}/{now.day:02d}/{feedback.transaction_id}"
        )

        payload = {
            "feedback_id": feedback_id,
            "transaction_id": feedback.transaction_id,
            "human_decision": feedback.human_decision.value,
            "reasoning": feedback.reasoning,
            "submitted_at": now.isoformat(),
            "invoice": invoice.model_dump(mode="json"),
        }
        self._upload_json(
            directory=base_dir,
            filename=f"{feedback_id}.json",
            payload=payload,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _upload_json(self, directory: str, filename: str, payload: dict) -> None:
        """Upload a JSON payload to ADLS Gen2."""
        file_system_client = self.storage_client.get_file_system_client(self.container_name)
        directory_client = file_system_client.get_directory_client(directory)
        try:
            directory_client.create_directory()
        except ResourceExistsError:
            pass  # directory already exists

        file_client = directory_client.create_file(filename)
        data = json.dumps(payload, indent=2).encode("utf-8")

        file_client.append_data(data=data, offset=0, length=len(data))
        file_client.flush_data(len(data))
        logger.info(
            "Uploaded %s/%s to ADLS Gen2 storage account %s",
            directory,
            filename,
            self.storage_account_name,
        )

    def _trigger_databricks_job(self) -> None:
        """Optionally trigger the Databricks pipeline job after uploads."""
        if not self.databricks_client or not self.databricks_job_id:
            return

        try:
            run = self.databricks_client.jobs.run_now(job_id=self.databricks_job_id)
            logger.info(
                "Triggered Databricks job %s (run_id=%s)",
                self.databricks_job_id,
                getattr(run, "run_id", "unknown"),
            )
        except Exception as exc:  # pragma: no cover - non-critical
            logger.warning("Failed to trigger Databricks job: %s", exc)

