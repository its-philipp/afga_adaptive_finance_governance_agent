"""Invoice extraction service for processing PDFs and images of expense reports."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from PIL import Image

from ..core.config import get_settings
from ..governance import GovernedLLMClient
from ..models.schemas import Invoice


logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """Extracts structured invoice data from PDFs and images using OCR + LLM parsing."""

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = GovernedLLMClient(agent_name="InvoiceExtractor")  # Governed LLM with AI governance
        logger.info("Invoice Extractor initialized with OCR + AI governance pipeline")

    def extract_from_document(
        self,
        file_bytes: bytes,
        filename: str,
        source: str = "uploaded",
    ) -> Invoice:
        """Extract invoice data from a document (PDF or image).
        
        Args:
            file_bytes: Document content as bytes
            filename: Original filename
            source: Source identifier
            
        Returns:
            Structured Invoice object
            
        Raises:
            ValueError: If extraction fails or document is invalid
        """
        logger.info(f"Extracting invoice data from {filename}")
        file_ext = Path(filename).suffix.lower()

        if file_ext == '.pdf':
            images = self._pdf_to_images(file_bytes)
            image = images[0]
        elif file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
            image = Image.open(io.BytesIO(file_bytes))
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Supported: PDF, PNG, JPG, JPEG, WEBP")

        ocr_text = self._extract_text_from_image(image)

        if not ocr_text or len(ocr_text.strip()) < 10:
            raise ValueError("Unable to extract readable text from the uploaded document. Ensure the scan is clear.")

        invoice_data = self._parse_text_with_llm(ocr_text, filename)

        try:
            invoice = Invoice(**invoice_data)
            logger.info(f"Successfully extracted invoice: {invoice.invoice_id}")
            return invoice
        except Exception as e:
            logger.error(f"Failed to create Invoice object: {e}")
            raise ValueError(f"Extracted data validation failed: {str(e)}")

    def _pdf_to_images(self, pdf_bytes: bytes) -> list[Image.Image]:
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_bytes)
            logger.info(f"Converted PDF to {len(images)} image(s)")
            return images
        except ImportError:
            raise ImportError(
                "pdf2image not installed. Run: uv add pdf2image\n"
                "Also requires poppler: brew install poppler (macOS) or apt-get install poppler-utils (Linux)"
            )
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def _extract_text_from_image(self, image: Image.Image) -> str:
        try:
            import pytesseract
        except ImportError as exc:
            raise ImportError(
                "pytesseract not installed. Install with `uv add pytesseract` and ensure tesseract OCR binary is available (brew install tesseract)."
            ) from exc

        try:
            # Convert to grayscale for better OCR fidelity
            grayscale = image.convert("L")
            text = pytesseract.image_to_string(grayscale, lang="deu+eng")
            logger.debug(f"OCR extracted text snippet: {text[:200].strip()}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text via OCR: {e}")
            raise ValueError(f"OCR extraction failed: {str(e)}")

    def _parse_text_with_llm(self, ocr_text: str, filename: str) -> dict:
        cleaned_text = ocr_text.strip()
        if len(cleaned_text) > 6000:
            cleaned_text = cleaned_text[:6000]

        prompt = f"""You are an invoice data parser. Given the OCR text of an expense receipt, extract structured information.

Filename: {filename}
-------------------------------
{cleaned_text}
-------------------------------

Extract the following fields:
1. invoice_id (if missing, derive from venue + date, e.g. 'EXT-<date>-<hash>')
2. vendor (merchant/company name)
3. amount (TOTAL paid including tax)
4. currency (prioritize EUR or USD, infer from symbols)
5. category (choose from: Software, Hardware, Office Supplies, Professional Services, Consulting, Marketing, Travel, Training, Facilities, Utilities, Meals & Entertainment)
6. date (ISO YYYY-MM-DD)
7. po_number (or null if not specified)
8. line_items (list of {"description", "quantity", "unit_price"})
9. tax (numeric)
10. total (numeric)
11. payment_terms (string or null)
12. notes (string summarizing purpose)
13. international (true if currency not USD)
14. vendor_reputation (leave at 75)

Rules:
- Use values from the text literally whenever possible.
- Quantities and prices should reflect the receipt's line items. If only totals are present, create one line item with the gross amount.
- For currency, detect symbols like €, EUR, $, USD.
- Validate totals: sum(line_items) + tax should match the total (allow +/-0.5 rounding).
- Output strictly valid JSON matching the exact schema below.

Return ONLY JSON:
{{
  "invoice_id": "string",
  "vendor": "string",
  "vendor_reputation": 75,
  "amount": number,
  "currency": "EUR",
  "category": "string",
  "date": "YYYY-MM-DD",
  "po_number": "string or null",
  "line_items": [{{"description": "string", "quantity": number, "unit_price": number}}],
  "tax": number,
  "total": number,
  "payment_terms": "string or null",
  "notes": "string or null",
  "international": false
}}"""

        try:
            response = self.llm_client.completion(prompt=prompt, temperature=0)
            if "```json" in response:
                response = response.split("```json")[1].split("```", 1)[0].strip()
            elif "```" in response:
                response = response.split("```", 1)[1].split("```", 1)[0].strip()

            invoice_data = json.loads(response)

            if "currency" not in invoice_data or not invoice_data["currency"]:
                invoice_data["currency"] = "EUR" if "€" in cleaned_text else "USD"

            if not invoice_data.get("vendor_reputation"):
                invoice_data["vendor_reputation"] = 75

            if not invoice_data.get("payment_terms"):
                invoice_data["payment_terms"] = "Net 30"

            if "international" not in invoice_data or invoice_data["international"] is None:
                invoice_data["international"] = invoice_data.get("currency", "USD") != "USD"

            logger.info(f"Parsed invoice via OCR text: {invoice_data.get('invoice_id', 'N/A')}")
            return invoice_data
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {response}")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing invoice text: {e}")
            raise

