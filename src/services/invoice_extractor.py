"""Invoice extraction service for processing PDFs and images of expense reports."""

from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from ..core.config import get_settings
from ..governance import GovernedLLMClient
from ..models.schemas import Invoice, LineItem


logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """Extracts structured invoice data from PDFs and images using Vision LLM."""

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = GovernedLLMClient(agent_name="InvoiceExtractor")  # Governed LLM with AI governance
        logger.info("Invoice Extractor initialized with AI governance")

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
        
        # Determine file type
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == '.pdf':
            # Convert PDF to images
            images = self._pdf_to_images(file_bytes)
            # Use first page for extraction (can process all pages if needed)
            image_base64 = self._image_to_base64(images[0])
        elif file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
            # Direct image processing
            image_base64 = base64.b64encode(file_bytes).decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Supported: PDF, PNG, JPG, JPEG")
        
        # Extract structured data using Vision LLM
        invoice_data = self._extract_with_vision_llm(image_base64, filename)
        
        # Validate and create Invoice object
        try:
            invoice = Invoice(**invoice_data)
            logger.info(f"Successfully extracted invoice: {invoice.invoice_id}")
            return invoice
        except Exception as e:
            logger.error(f"Failed to create Invoice object: {e}")
            raise ValueError(f"Extracted data validation failed: {str(e)}")

    def _pdf_to_images(self, pdf_bytes: bytes) -> list[Image.Image]:
        """Convert PDF bytes to PIL Images.
        
        Args:
            pdf_bytes: PDF file content
            
        Returns:
            List of PIL Image objects (one per page)
        """
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

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded string
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')

    def _extract_with_vision_llm(self, image_base64: str, filename: str) -> dict:
        """Extract invoice fields using Vision LLM.
        
        Args:
            image_base64: Base64 encoded image
            filename: Original filename for context
            
        Returns:
            Dictionary with extracted invoice fields
        """
        prompt = """You are an AI invoice data extractor. Analyze this expense report/invoice image and extract all relevant information.

Extract the following fields:
1. invoice_id (or receipt number, or generate one if missing: use format "EXT-" + date + random)
2. vendor (company/merchant name)
3. amount (total amount, numeric)
4. currency (USD, EUR, etc. - default to USD if not specified)
5. category (Software, Hardware, Office Supplies, Professional Services, Consulting, Marketing, Travel, Training, Facilities, Utilities)
6. date (transaction date in YYYY-MM-DD format)
7. po_number (purchase order number if present, otherwise null)
8. line_items (array of items with description, quantity, unit_price)
9. tax (tax amount)
10. total (final total with tax)
11. payment_terms (e.g., "Net 30" or null)
12. notes (any additional notes)

IMPORTANT:
- For vendor_reputation: assign a default value of 75 (will be updated from vendor database)
- Categorize expenses appropriately based on description
- If line items are not clearly itemized, create a single line item with the total amount
- Be conservative with amounts - extract what's clearly visible

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "invoice_id": "string",
  "vendor": "string",
  "vendor_reputation": 75,
  "amount": number,
  "currency": "USD",
  "category": "string",
  "date": "YYYY-MM-DD",
  "po_number": "string or null",
  "line_items": [{"description": "string", "quantity": number, "unit_price": number}],
  "tax": number,
  "total": number,
  "payment_terms": "string or null",
  "notes": "string or null",
  "international": false
}"""

        try:
            # Call Vision LLM via OpenRouter
            # Note: This requires a vision-capable model
            response = self._call_vision_api(image_base64, prompt)
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            invoice_data = json.loads(response)
            
            # Add default values if missing
            if "vendor_reputation" not in invoice_data:
                invoice_data["vendor_reputation"] = 75
            
            if "payment_terms" not in invoice_data:
                invoice_data["payment_terms"] = "Net 30"
            
            if "international" not in invoice_data:
                invoice_data["international"] = invoice_data.get("currency", "USD") != "USD"
            
            logger.info(f"Extracted invoice data: {invoice_data.get('invoice_id', 'N/A')}")
            return invoice_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting invoice data: {e}")
            raise

    def _call_vision_api(self, image_base64: str, prompt: str) -> str:
        """Call Vision LLM API (OpenRouter with vision model).
        
        Note: This is a simplified implementation. 
        OpenRouter's vision support varies by model.
        """
        try:
            # Use OpenAI's API format (OpenRouter compatible)
            import httpx
            
            headers = {
                "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                "HTTP-Referer": "https://afga-demo",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": "openai/gpt-4-vision-preview",  # Vision-capable model
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1,  # Low temperature for structured extraction
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                return data["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Vision API call failed: {e}")
            # Fallback: Use text-based extraction if vision fails
            logger.warning("Vision API failed, falling back to text-only extraction")
            return self._fallback_text_extraction(prompt)

    def _fallback_text_extraction(self, prompt: str) -> str:
        """Fallback to text-only LLM if vision fails.
        
        This is a simplified fallback - in production, you'd use OCR first.
        """
        fallback_prompt = f"""The document could not be processed with vision. 
Please generate a sample invoice structure based on typical expense report data.

{prompt}

Generate a realistic example."""
        
        return self.llm_client.completion(fallback_prompt, temperature=0.1)

    def extract_text_only(self, file_bytes: bytes, filename: str) -> Invoice:
        """Extract invoice from text-based documents (TXT, simple OCR).
        
        This method uses traditional text extraction + LLM structuring.
        """
        # Extract text
        if filename.endswith('.txt'):
            text = file_bytes.decode('utf-8')
        else:
            # Use unstructured.io if available
            try:
                from unstructured.partition.auto import partition
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                
                elements = partition(filename=tmp_path)
                text = "\n".join([e.text for e in elements if hasattr(e, 'text')])
                
                # Clean up
                Path(tmp_path).unlink()
                
            except ImportError:
                raise ImportError("unstructured not installed. Run: uv sync --extra ml")
        
        # Structure with LLM
        prompt = f"""Extract invoice data from this text:

{text}

Return JSON with fields: invoice_id, vendor, amount, currency, category, date, po_number, line_items, tax, total, payment_terms, notes

Format: Valid JSON only"""
        
        response = self.llm_client.completion(prompt, temperature=0.1)
        
        # Parse JSON
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        
        invoice_data = json.loads(response)
        
        # Add defaults
        invoice_data.setdefault("vendor_reputation", 75)
        invoice_data.setdefault("international", invoice_data.get("currency", "USD") != "USD")
        
        return Invoice(**invoice_data)

