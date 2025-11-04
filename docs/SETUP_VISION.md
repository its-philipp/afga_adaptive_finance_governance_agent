# Vision LLM Setup for Document Extraction

## Prerequisites

To use document extraction (PDF/image upload), you need:

### 1. System Dependencies

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**Windows:**
- Download poppler: https://github.com/oschwartz10612/poppler-windows
- Add to PATH

### 2. Python Dependencies

Already included in base installation:
```bash
uv sync  # Includes pillow, pdf2image, python-multipart
```

For optional OCR fallback:
```bash
uv sync --extra ml  # Adds unstructured, pytesseract
```

### 3. OpenRouter API Key

Vision LLM requires OpenRouter with vision-capable models:

1. Get API key: https://openrouter.ai/
2. Add to `.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

3. Ensure credit balance for vision models (GPT-4 Vision)

## Verify Setup

```bash
# Test poppler
pdftoppm -v

# Test Python dependencies
source .venv/bin/activate
python -c "from pdf2image import convert_from_path; print('✅ pdf2image works')"
python -c "from PIL import Image; print('✅ Pillow works')"

# Test API
curl http://localhost:8000/api/v1/health
```

## Using Document Upload

### Via Streamlit

1. Start the system: `./start.sh`
2. Go to http://localhost:8501
3. Navigate to **📋 Transaction Review**
4. Select **"Upload Receipt/Invoice (PDF/Image)"**
5. Upload your document
6. Click **"🔍 Extract & Process Invoice"**
7. View extracted data and decision

### Via API

```python
import httpx

# Upload a receipt
with open("receipt.pdf", "rb") as f:
    files = {"file": ("receipt.pdf", f, "application/pdf")}
    
    response = httpx.post(
        "http://localhost:8000/api/v1/transactions/upload-receipt",
        files=files
    )
    
    result = response.json()
    
    # View extracted invoice
    print(f"Extracted Invoice: {result['invoice']['invoice_id']}")
    print(f"Vendor: {result['invoice']['vendor']}")
    print(f"Amount: ${result['invoice']['amount']}")
    print(f"Decision: {result['final_decision']}")
```

## Supported Document Types

### Invoices (Rechnungen)
- Standard business invoices
- German invoices ("Rechnung")
- Itemized invoices with line items
- Summary invoices

### Expense Reports (Spesenabrechnungen)
- Travel expenses
- Meal receipts
- Hotel bills
- Transportation costs

### Receipts (Belege)
- Store receipts
- Restaurant bills
- Service receipts
- Cash register receipts

## Cost Considerations

### Vision LLM Pricing (via OpenRouter)

**GPT-4 Vision:**
- Input: ~$0.01 per image
- Output: ~$0.03 per 1K tokens
- Average cost per document: **$0.02-0.05**

### Optimization Tips

1. **Use for complex documents only** - Simple receipts can use OCR
2. **Batch processing** - Extract multiple documents together
3. **Cache results** - Don't re-extract same document
4. **Choose models wisely** - Some vision models are cheaper

### Free Alternatives

For testing without costs:
- Use mock JSON data (already included)
- Implement local OCR (tesseract - free)
- Use text-based extraction for TXT files

## Troubleshooting

### "pdf2image not working"

```bash
# Install poppler
brew install poppler  # macOS
sudo apt-get install poppler-utils  # Linux

# Verify
which pdftoppm
```

### "Vision API fails"

Check:
1. OpenRouter API key is valid
2. Account has credits
3. Vision model is available
4. Image is base64 encoded correctly

### "Extraction accuracy low"

Tips:
- Use higher quality scans (300+ DPI)
- Ensure good lighting (for photos)
- Crop to relevant area
- Straighten skewed images

### "Foreign language invoices"

Vision LLM supports multiple languages:
- German: ✅ Fully supported
- French: ✅ Supported
- Spanish: ✅ Supported
- Others: ✅ Most languages work

## Advanced Configuration

### Custom Vision Model

Edit `src/services/invoice_extractor.py`:

```python
# Change model in _call_vision_api()
payload = {
    "model": "anthropic/claude-3-opus",  # Alternative
    # or "openai/gpt-4-vision-preview"  # Current default
}
```

### Adjust Extraction Prompt

Modify the prompt in `InvoiceExtractor._extract_with_vision_llm()` to:
- Add custom fields
- Change categorization logic
- Handle specific vendor formats
- Extract additional metadata

### Enable OCR Fallback

```python
# Install OCR dependencies
uv sync --extra ml
brew install tesseract  # macOS

# OCR automatically used if Vision LLM fails
```

## Next Steps

1. **Test with real documents** - Upload your own expense reports
2. **Validate extraction accuracy** - Check extracted fields
3. **Provide corrections** - Use HITL to improve accuracy
4. **Monitor costs** - Track Vision LLM usage
5. **Optimize** - Adjust models and prompts as needed

---

**Document extraction is now fully integrated into AFGA!** 🎉

Upload any receipt or invoice (PDF/image) and let the AI handle the rest.

