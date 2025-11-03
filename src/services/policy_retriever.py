"""Policy retrieval service for PAA - simple RAG implementation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from sentence_transformers import SentenceTransformer

from ..models.schemas import Invoice


logger = logging.getLogger(__name__)


class PolicyRetriever:
    """Retrieves relevant policy documents for compliance checking."""

    def __init__(self, policies_dir: str = "data/policies"):
        self.policies_dir = Path(policies_dir)
        self.policies = {}
        self.embeddings_model = None
        self._load_policies()
        logger.info(f"PolicyRetriever initialized with {len(self.policies)} policies")

    def _load_policies(self) -> None:
        """Load all policy documents from the policies directory."""
        if not self.policies_dir.exists():
            logger.warning(f"Policies directory {self.policies_dir} does not exist")
            return

        for policy_file in self.policies_dir.glob("*.txt"):
            try:
                with open(policy_file, 'r') as f:
                    content = f.read()
                    self.policies[policy_file.stem] = {
                        "filename": policy_file.name,
                        "content": content,
                        "chunks": self._chunk_policy(content),
                    }
                logger.info(f"Loaded policy: {policy_file.name}")
            except Exception as e:
                logger.error(f"Error loading policy {policy_file}: {e}")

    def _chunk_policy(self, content: str, chunk_size: int = 500) -> List[str]:
        """Split policy content into chunks for retrieval."""
        # Simple chunking by paragraphs or sentences
        paragraphs = content.split("\n\n")
        chunks = []
        
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    def retrieve_relevant_policies(self, invoice: Invoice, top_k: int = 5) -> List[dict]:
        """Retrieve the most relevant policy chunks for an invoice.
        
        Args:
            invoice: Invoice to check
            top_k: Number of relevant chunks to return
            
        Returns:
            List of relevant policy chunks with metadata
        """
        if not self.policies:
            logger.warning("No policies loaded")
            return []

        # Build query from invoice characteristics
        query = self._build_query(invoice)
        
        # Simple keyword-based retrieval (can be upgraded to embeddings later)
        relevant_chunks = []
        
        for policy_name, policy_data in self.policies.items():
            for chunk_idx, chunk in enumerate(policy_data["chunks"]):
                score = self._calculate_relevance_score(query, chunk)
                relevant_chunks.append({
                    "policy_name": policy_name,
                    "chunk_index": chunk_idx,
                    "content": chunk,
                    "score": score,
                })
        
        # Sort by relevance score and return top_k
        relevant_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = relevant_chunks[:top_k]
        
        logger.info(f"Retrieved {len(top_chunks)} relevant policy chunks for {invoice.invoice_id}")
        return top_chunks

    def _build_query(self, invoice: Invoice) -> str:
        """Build a search query from invoice characteristics."""
        query_parts = []
        
        # Add vendor if present
        if invoice.vendor:
            query_parts.append(f"vendor {invoice.vendor}")
        
        # Add category
        if invoice.category:
            query_parts.append(invoice.category)
        
        # Add amount-related terms
        if invoice.amount > 10000:
            query_parts.append("approval threshold high amount")
        elif invoice.amount > 5000:
            query_parts.append("approval medium amount")
        
        # Add PO-related terms
        if not invoice.po_number:
            query_parts.append("purchase order PO requirement")
        
        # Add international terms
        if invoice.international or invoice.currency != "USD":
            query_parts.append("international foreign currency")
        
        return " ".join(query_parts).lower()

    def _calculate_relevance_score(self, query: str, chunk: str) -> float:
        """Calculate relevance score using simple keyword matching.
        
        This is a basic implementation. Can be upgraded to embeddings-based similarity.
        """
        query_terms = set(query.lower().split())
        chunk_terms = set(chunk.lower().split())
        
        # Jaccard similarity
        if not query_terms:
            return 0.0
        
        intersection = query_terms.intersection(chunk_terms)
        score = len(intersection) / len(query_terms)
        
        return score

    def get_all_policies_summary(self) -> List[dict]:
        """Get a summary of all loaded policies."""
        return [
            {
                "policy_name": name,
                "filename": data["filename"],
                "chunk_count": len(data["chunks"]),
            }
            for name, data in self.policies.items()
        ]

