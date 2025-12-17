#!/bin/bash
# Setup automated invoice generation and processing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "AFGA Automated Invoice Processing Setup"
echo "========================================"
echo ""

# Configuration
PYTHON_PATH="${PROJECT_ROOT}/adaptive_finance_governance_agent/bin/python"
GENERATE_SCRIPT="${PROJECT_ROOT}/scripts/generate_mock_invoices.py"
PROCESS_SCRIPT="${PROJECT_ROOT}/scripts/batch_process_invoices.py"
INVOICE_DIR="${PROJECT_ROOT}/data/mock_invoices"

# Check if Python environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Python virtual environment not found at: $PYTHON_PATH"
    echo "Please run: python -m venv adaptive_finance_governance_agent"
    exit 1
fi

# Check if scripts exist
if [ ! -f "$GENERATE_SCRIPT" ]; then
    echo "❌ Generator script not found: $GENERATE_SCRIPT"
    exit 1
fi

if [ ! -f "$PROCESS_SCRIPT" ]; then
    echo "❌ Processor script not found: $PROCESS_SCRIPT"
    exit 1
fi

# Create invoice directory if it doesn't exist
mkdir -p "$INVOICE_DIR"

echo "✓ Environment validated"
echo ""

# Function to create cron job entries
setup_cron() {
    echo "Setting up cron jobs..."
    echo ""
    
    # Generate cron entries
    GENERATE_CRON="0 */6 * * * cd $PROJECT_ROOT && $PYTHON_PATH $GENERATE_SCRIPT --count 10 >> ${PROJECT_ROOT}/logs/generate_invoices.log 2>&1"
    PROCESS_CRON="5 */6 * * * cd $PROJECT_ROOT && $PYTHON_PATH $PROCESS_SCRIPT >> ${PROJECT_ROOT}/logs/process_invoices.log 2>&1"
    
    echo "Suggested cron entries (runs every 6 hours):"
    echo ""
    echo "# Generate 10 new mock invoices every 6 hours"
    echo "$GENERATE_CRON"
    echo ""
    echo "# Process all pending invoices 5 minutes after generation"
    echo "$PROCESS_CRON"
    echo ""
    echo "# Weekly Databricks backfill (Sunday 02:15) to ensure historical coverage"
    echo "15 2 * * 0 cd $PROJECT_ROOT && $PYTHON_PATH ${PROJECT_ROOT}/scripts/backfill_databricks_uploads.py --limit 1000 >> ${PROJECT_ROOT}/logs/backfill.log 2>&1"
    echo ""
    
    read -p "Would you like to add these cron jobs now? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Create logs directory
        mkdir -p "${PROJECT_ROOT}/logs"
        
        # Add to crontab
                (crontab -l 2>/dev/null; \
                    echo "# AFGA Invoice Generation"; echo "$GENERATE_CRON"; \
                    echo "# AFGA Invoice Processing"; echo "$PROCESS_CRON"; \
                    echo "# AFGA Weekly Databricks Backfill"; echo "15 2 * * 0 cd $PROJECT_ROOT && $PYTHON_PATH ${PROJECT_ROOT}/scripts/backfill_databricks_uploads.py --limit 1000 >> ${PROJECT_ROOT}/logs/backfill.log 2>&1" \
                ) | crontab -
        
        echo "✓ Cron jobs added successfully"
        echo ""
        echo "View cron jobs with: crontab -l"
        echo "View logs in: ${PROJECT_ROOT}/logs/"
    else
        echo "⊘ Skipped cron setup. You can manually add the entries above."
    fi
}

# Function to create systemd timer (alternative to cron for Linux)
setup_systemd() {
    echo "Systemd timer setup not yet implemented."
    echo "Use cron setup for now."
}

# Function to test scripts
test_scripts() {
    echo "Testing scripts..."
    echo ""
    
    # Test generator
    echo "Testing invoice generator (generating 3 test invoices)..."
    $PYTHON_PATH "$GENERATE_SCRIPT" --count 3 --output-dir "${PROJECT_ROOT}/data/test_invoices"
    
    if [ $? -eq 0 ]; then
        echo "✓ Generator test passed"
    else
        echo "❌ Generator test failed"
        return 1
    fi
    
    echo ""
    
    # Check if API is running
    API_URL="http://localhost:8000/api/v1/health"
    echo "Checking if AFGA API is running at $API_URL..."
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL")
    
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✓ API is running"
        echo ""
        echo "Testing batch processor (processing test invoices)..."
        $PYTHON_PATH "$PROCESS_SCRIPT" --invoice-dir "${PROJECT_ROOT}/data/test_invoices" --no-skip
        
        if [ $? -eq 0 ]; then
            echo "✓ Processor test passed"
            # Clean up test invoices
            rm -rf "${PROJECT_ROOT}/data/test_invoices"
        else
            echo "❌ Processor test failed"
            return 1
        fi
    else
        echo "⚠️  API is not running (HTTP $HTTP_CODE)"
        echo "Start API with: uvicorn src.api.main:app --reload"
        echo "Skipping batch processor test"
    fi
    
    echo ""
    echo "✓ All tests completed"
}

# Function to create wrapper scripts
create_wrapper_scripts() {
    echo "Creating wrapper scripts..."
    echo ""
    
    # Generate wrapper
    cat > "${PROJECT_ROOT}/scripts/run_generate.sh" << EOF
#!/bin/bash
cd "$PROJECT_ROOT"
"$PYTHON_PATH" "$GENERATE_SCRIPT" "\$@"
EOF
    chmod +x "${PROJECT_ROOT}/scripts/run_generate.sh"
    
    # Process wrapper
    cat > "${PROJECT_ROOT}/scripts/run_process.sh" << EOF
#!/bin/bash
cd "$PROJECT_ROOT"
"$PYTHON_PATH" "$PROCESS_SCRIPT" "\$@"
EOF
    chmod +x "${PROJECT_ROOT}/scripts/run_process.sh"
    
    echo "✓ Created wrapper scripts:"
    echo "  - scripts/run_generate.sh"
    echo "  - scripts/run_process.sh"
    echo ""
}

# Main menu
show_menu() {
    echo "Choose setup option:"
    echo "1) Test scripts only"
    echo "2) Setup cron jobs (macOS/Linux)"
    echo "3) Create wrapper scripts"
    echo "4) Full setup (test + cron + wrappers)"
    echo "5) Exit"
    echo ""
    read -p "Enter choice [1-5]: " choice
    
    case $choice in
        1)
            test_scripts
            ;;
        2)
            setup_cron
            ;;
        3)
            create_wrapper_scripts
            ;;
        4)
            test_scripts && create_wrapper_scripts && setup_cron
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
}

# Run menu
show_menu

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "Manual commands:"
echo "  Generate invoices: ./scripts/run_generate.sh --count 10"
echo "  Process invoices:  ./scripts/run_process.sh"
echo ""
echo "Check logs:"
echo "  Generation: tail -f logs/generate_invoices.log"
echo "  Processing: tail -f logs/process_invoices.log"
echo "  Backfill:   tail -f logs/backfill.log"
echo ""
