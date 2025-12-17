#!/usr/bin/env python3
"""Batch process all mock invoices through AFGA classification system."""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class InvoiceBatchProcessor:
    """Batch process invoices through AFGA API."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000/api/v1",
        timeout: int = 60,
        concurrent_limit: int = 5,
    ):
        self.api_base_url = api_base_url
        self.timeout = timeout
        self.concurrent_limit = concurrent_limit
        self.client = httpx.Client(timeout=timeout)

    def load_invoice(self, invoice_path: Path) -> Optional[Dict]:
        """Load invoice JSON from file."""
        try:
            with open(invoice_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {invoice_path}: {e}")
            return None

    def submit_invoice(self, invoice: Dict, trace_id: Optional[str] = None) -> Dict:
        """Submit invoice to AFGA API."""
        try:
            url = f"{self.api_base_url}/transactions/submit"
            payload = {"invoice": invoice}
            if trace_id:
                payload["trace_id"] = trace_id

            logger.info(f"Submitting invoice {invoice['invoice_id']}...")
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Extract risk score from nested structure
            risk_score = result.get('risk_score') or result.get('risk_assessment', {}).get('risk_score', 0)
            processing_time = result.get('processing_time_ms', 0)
            
            logger.info(
                f"✓ {invoice['invoice_id']}: {result['final_decision']} "
                f"(Risk: {risk_score:.1f}, Processing: {processing_time}ms)"
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"✗ {invoice['invoice_id']}: HTTP {e.response.status_code} - {e.response.text}")
            return {"error": str(e), "invoice_id": invoice["invoice_id"]}
        except Exception as e:
            logger.error(f"✗ {invoice['invoice_id']}: {type(e).__name__}: {e}")
            return {"error": str(e), "invoice_id": invoice["invoice_id"]}

    def process_directory(
        self,
        invoice_dir: Path,
        pattern: str = "INV-*.json",
        skip_processed: bool = True,
    ) -> Dict[str, any]:
        """Process all invoices in directory."""
        invoice_files = sorted(invoice_dir.glob(pattern))
        
        if not invoice_files:
            logger.warning(f"No invoices found matching pattern '{pattern}' in {invoice_dir}")
            return {"total": 0, "processed": 0, "errors": 0, "results": []}

        logger.info(f"Found {len(invoice_files)} invoices to process")

        results = []
        errors = 0
        processed = 0

        # Check which invoices are already processed (optional optimization)
        already_processed = set()
        if skip_processed:
            try:
                stats_url = f"{self.api_base_url}/transactions/stats"
                response = self.client.get(stats_url)
                if response.status_code == 200:
                    stats = response.json()
                    # We'd need an endpoint to list processed invoice IDs
                    # For now, we'll process all
                    pass
            except Exception:
                pass

        for invoice_file in invoice_files:
            invoice = self.load_invoice(invoice_file)
            if not invoice:
                errors += 1
                continue

            # Check if already processed
            if skip_processed and invoice.get("invoice_id") in already_processed:
                logger.info(f"⊘ {invoice['invoice_id']}: Already processed, skipping")
                continue

            result = self.submit_invoice(invoice)
            results.append(result)
            
            if "error" in result:
                errors += 1
            else:
                processed += 1

            # Rate limiting
            time.sleep(0.1)

        return {
            "total": len(invoice_files),
            "processed": processed,
            "errors": errors,
            "results": results,
        }

    def generate_summary_report(self, batch_result: Dict) -> None:
        """Generate summary report of batch processing."""
        logger.info("\n" + "=" * 70)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total Invoices: {batch_result['total']}")
        logger.info(f"Successfully Processed: {batch_result['processed']}")
        logger.info(f"Errors: {batch_result['errors']}")

        # Count decisions
        decision_counts = {"APPROVED": 0, "REJECTED": 0, "HITL": 0, "ERROR": 0}
        total_risk = 0
        total_processing_time = 0
        hitl_invoices = []

        for result in batch_result["results"]:
            if "error" in result:
                decision_counts["ERROR"] += 1
            else:
                decision = result.get("final_decision", "UNKNOWN")
                decision_counts[decision] = decision_counts.get(decision, 0) + 1
                # Handle nested risk_score
                risk_score = result.get('risk_score') or result.get('risk_assessment', {}).get('risk_score', 0)
                total_risk += risk_score
                total_processing_time += result.get("processing_time_ms", 0)
                
                if decision == "HITL":
                    hitl_invoices.append({
                        "invoice_id": result["invoice_id"],
                        "vendor": result.get("invoice", {}).get("vendor", "Unknown"),
                        "amount": result.get("invoice", {}).get("amount", 0),
                        "reason": result.get("decision_reasoning", "N/A"),
                    })

        logger.info("\nDecision Breakdown:")
        for decision, count in decision_counts.items():
            if count > 0:
                percentage = (count / batch_result["total"]) * 100
                logger.info(f"  {decision}: {count} ({percentage:.1f}%)")

        if batch_result["processed"] > 0:
            avg_risk = total_risk / batch_result["processed"]
            avg_time = total_processing_time / batch_result["processed"]
            logger.info(f"\nAverage Risk Score: {avg_risk:.2f}")
            logger.info(f"Average Processing Time: {avg_time:.0f}ms")

        if hitl_invoices:
            logger.info(f"\n⚠️  INVOICES REQUIRING HUMAN REVIEW ({len(hitl_invoices)}):")
            for hitl in hitl_invoices:
                logger.info(
                    f"  • {hitl['invoice_id']} - {hitl['vendor']} "
                    f"(${hitl['amount']:.2f})"
                )
                logger.info(f"    Reason: {hitl['reason']}")

        logger.info("=" * 70 + "\n")

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Batch process invoices through AFGA")
    parser.add_argument(
        "--invoice-dir",
        type=Path,
        default=Path("data/mock_invoices"),
        help="Directory containing invoice JSON files",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="INV-*.json",
        help="Glob pattern for invoice files",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000/api/v1",
        help="AFGA API base URL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Process all invoices even if already processed",
    )

    args = parser.parse_args()

    if not args.invoice_dir.exists():
        logger.error(f"Invoice directory not found: {args.invoice_dir}")
        sys.exit(1)

    processor = InvoiceBatchProcessor(
        api_base_url=args.api_url,
        timeout=args.timeout,
    )

    try:
        logger.info(f"Starting batch processing from {args.invoice_dir}")
        logger.info(f"API endpoint: {args.api_url}")
        
        batch_result = processor.process_directory(
            args.invoice_dir,
            pattern=args.pattern,
            skip_processed=not args.no_skip,
        )

        processor.generate_summary_report(batch_result)

        # Exit code based on errors
        if batch_result["errors"] > 0:
            sys.exit(1)
        
        logger.info("✓ Batch processing completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("\nBatch processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Batch processing failed: {e}")
        sys.exit(1)
    finally:
        processor.close()


if __name__ == "__main__":
    main()
