# Quick Start: Automated Invoice Classification

## 🚀 Quick Setup (5 Minutes)

### Prerequisites
- AFGA installed and configured
- API running on `http://localhost:8000`
- Python virtual environment activated

### Step 1: Test Invoice Generation
```bash
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

# Generate 5 test invoices
python scripts/generate_mock_invoices.py --count 5
```

**Expected Output:**
```
Generating 5 invoices starting from INV-0051
Output directory: data/mock_invoices

✓ Generated INV-0051: Consulting Partners LLC - $4996.91
✓ Generated INV-0052: Office Supplies Inc - $8234.56
✓ Generated INV-0053: Tech Solutions GmbH - $12450.00
✓ Generated INV-0054: Cloud Services Corp - $3210.75
✓ Generated INV-0055: Marketing Agency Pro - $45000.00

✓ Summary saved to data/mock_invoices/invoices_summary.json

✓ Successfully generated 5 invoices
```

### Step 2: Test Batch Processing
```bash
# Process all mock invoices
python scripts/batch_process_invoices.py
```

**Expected Output:**
```
Starting batch processing from data/mock_invoices
API endpoint: http://localhost:8000/api/v1
Found 55 invoices to process

Submitting invoice INV-0001...
✓ INV-0001: APPROVED (Risk: 35.2, Processing: 1250ms)
Submitting invoice INV-0002...
✓ INV-0002: APPROVED (Risk: 28.5, Processing: 1180ms)
...
✓ INV-0055: HITL (Risk: 68.3, Processing: 1450ms)

======================================================================
BATCH PROCESSING SUMMARY
======================================================================
Total Invoices: 55
Successfully Processed: 55
Errors: 0

Decision Breakdown:
  APPROVED: 33 (60.0%)
  REJECTED: 14 (25.5%)
  HITL: 8 (14.5%)

Average Risk Score: 42.3
Average Processing Time: 1245ms

⚠️  INVOICES REQUIRING HUMAN REVIEW (8):
  • INV-0055 - Marketing Agency Pro ($45,000.00)
    Reason: High-value transaction exceeds threshold
  • INV-0023 - Consulting Partners LLC ($38,500.00)
    Reason: High-value transaction requiring additional review
  ...
======================================================================

✓ Batch processing completed successfully
```

### Step 3: View Results in Streamlit

1. **Start Streamlit** (if not already running):
```bash
streamlit run streamlit_app/Home.py
```

2. **Navigate to Classifications Dashboard:**
   - Open browser: `http://localhost:8501`
   - Click on **"📊 Classifications Dashboard"** in sidebar

3. **Explore the Dashboard:**
   - View summary cards (Total, Approved, Rejected, HITL)
   - Check decision distribution chart
   - Review performance metrics
   - **Focus on HITL cases** - cases requiring your review!

### Step 4: Setup Automation (Optional)
```bash
# Run interactive setup
./scripts/setup_automation.sh

# Choose option 4: Full setup (test + cron + wrappers)
# This will:
# 1. Test both scripts
# 2. Create wrapper scripts
# 3. Setup cron jobs for 6-hour cycle
```

## 📊 Classifications Dashboard Features

### Summary Section
- **Total Transactions:** All processed invoices
- **Approved:** Auto-approved invoices (green indicator)
- **Rejected:** Auto-rejected invoices (red indicator)
- **Requires Review:** HITL cases needing human evaluation (yellow indicator)

### HITL Cases (Most Important!)
This section shows invoices that need your attention:
- Expandable cards with full details
- Risk scores and policy violations
- Decision reasoning from PAA agent
- Quick action buttons (approve/reject)
- Link to detailed HITL Review page

### All Transactions Table
- Filter by decision type
- Color-coded rows for easy scanning
- Shows transaction ID, vendor, amount, risk score
- Indicates human override status

## 🔄 Daily Workflow

### Morning Routine (Manual)
```bash
# 1. Generate new invoices
python scripts/generate_mock_invoices.py --count 10

# 2. Process invoices
python scripts/batch_process_invoices.py

# 3. Open Classifications Dashboard
# Review HITL cases
# Provide feedback via HITL Review page
```

### Automated Routine (With Cron)
```bash
# Cron handles generation and processing every 6 hours
# You just need to:

# 1. Open Classifications Dashboard
# 2. Check "Requires Review" count
# 3. Review HITL cases
# 4. Submit feedback
```

### Check Logs
```bash
# Generation logs
tail -f logs/generate_invoices.log

# Processing logs
tail -f logs/process_invoices.log
```

## 🎯 Common Use Cases

### Use Case 1: Process All Existing Invoices
```bash
# Process all 50 mock invoices
python scripts/batch_process_invoices.py

# View results
# Navigate to: Classifications Dashboard
# Check: Total Transactions count increased by 50
```

### Use Case 2: Focus on HITL Cases
```bash
# In Classifications Dashboard:
# 1. Look at "Requires Review" metric
# 2. Scroll to "Cases Requiring Human Review" section
# 3. Expand each case
# 4. Review details and policy violations
# 5. Click "View Details" or navigate to HITL Review page
# 6. Submit feedback (approve/reject with reason)
```

### Use Case 3: Filter by Decision Type
```bash
# In Classifications Dashboard:
# 1. Use "Filter by Decision" dropdown
# 2. Select "HITL" to see only pending reviews
# 3. Or select "APPROVED" to audit auto-approvals
# 4. Or select "REJECTED" to review rejections
```

### Use Case 4: Generate Specific Scenarios
```bash
# Generate invoices with seed for reproducibility
python scripts/generate_mock_invoices.py --count 20 --seed 42

# This creates same set of invoices every time
# Useful for testing policy changes
```

### Use Case 5: Load Testing
```bash
# Generate large batch
python scripts/generate_mock_invoices.py --count 200

# Process all
python scripts/batch_process_invoices.py

# Monitor performance in Dashboard
# Check average processing times
# Verify no errors in batch summary
```

## 🔧 Troubleshooting

### Problem: "API is not running"
```bash
# Start the API
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent
source adaptive_finance_governance_agent/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

### Problem: "No invoices found"
```bash
# Check directory
ls -la data/mock_invoices/

# Generate invoices
python scripts/generate_mock_invoices.py --count 10
```

### Problem: "Failed to fetch data" in Dashboard
```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Check classifications endpoint
curl http://localhost:8000/api/v1/transactions/classifications/summary

# Restart API if needed
```

### Problem: No HITL cases showing
```bash
# Generate more diverse scenarios
python scripts/generate_mock_invoices.py --count 30

# Process them
python scripts/batch_process_invoices.py

# High-value and unusual invoices will trigger HITL
```

## 📈 Next Steps

1. **Review HITL Cases:**
   - Open Classifications Dashboard
   - Focus on "Cases Requiring Human Review"
   - Submit feedback to train the system

2. **Setup Automation:**
   - Run `./scripts/setup_automation.sh`
   - Choose option 4 for full setup
   - Let system run automatically every 6 hours

3. **Monitor Performance:**
   - Check Dashboard daily
   - Review average processing times
   - Ensure HITL cases are addressed within 24h

4. **Integrate with Databricks:**
   - Set `AZURE_STORAGE_CONNECTION_STRING` in `.env`
   - Processed invoices auto-upload to ADLS
   - Databricks generates embeddings every 6 hours
   - Future classifications benefit from historical patterns

## 🎉 Success Metrics

You'll know it's working when:
- ✅ New invoices appear in Classifications Dashboard
- ✅ Decision breakdown shows realistic distribution (60% approved, 25% rejected, 15% HITL)
- ✅ HITL cases are clearly highlighted
- ✅ Processing times are under 2 seconds per invoice
- ✅ Batch processing completes without errors
- ✅ You can filter and review transactions easily

## 📚 Additional Resources

- **Full Documentation:** `AUTOMATED_CLASSIFICATION_WORKFLOW.md`
- **Databricks Integration:** `FULL_INTEGRATION_SUMMARY.md`
- **API Documentation:** `http://localhost:8000/docs`
- **Streamlit Pages:**
  - Home: Overview and KPIs
  - Transaction Review: Submit invoices
  - HITL Review: Provide feedback
  - **Classifications Dashboard: View all classifications (NEW!)**
  - Embeddings Browser: Databricks similarity search

---

**Quick Commands Reference:**
```bash
# Generate invoices
python scripts/generate_mock_invoices.py --count 10

# Process invoices
python scripts/batch_process_invoices.py

# Setup automation
./scripts/setup_automation.sh

# View logs
tail -f logs/generate_invoices.log
tail -f logs/process_invoices.log

# Check cron jobs
crontab -l
```

**Happy Classifying! 🚀**
