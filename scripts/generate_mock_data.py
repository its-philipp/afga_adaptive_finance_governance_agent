"""Generate mock invoices and policy documents for AFGA testing."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


# Mock vendor data
VENDORS = [
    "Acme Corporation",
    "TechSupply Inc",
    "Office Essentials Ltd",
    "Global Services Group",
    "Consulting Partners LLC",
    "Marketing Solutions Co",
    "IT Infrastructure Pro",
    "Software Licensing Corp",
    "Facilities Management Inc",
    "Training Academy Ltd",
]

CATEGORIES = [
    "Software",
    "Hardware",
    "Office Supplies",
    "Professional Services",
    "Consulting",
    "Marketing",
    "Travel",
    "Training",
    "Facilities",
    "Utilities",
]

# Vendor reputation scores (0-100)
VENDOR_REPUTATION = {vendor: random.randint(50, 100) for vendor in VENDORS}


def generate_compliant_invoice(invoice_id: int) -> dict:
    """Generate a compliant invoice (70% of dataset)."""
    vendor = random.choice(VENDORS)
    category = random.choice(CATEGORIES)
    amount = round(random.uniform(100, 8000), 2)
    date = datetime.now() - timedelta(days=random.randint(1, 30))
    
    return {
        "invoice_id": f"INV-{invoice_id:04d}",
        "vendor": vendor,
        "vendor_reputation": VENDOR_REPUTATION[vendor],
        "amount": amount,
        "currency": "USD",
        "category": category,
        "date": date.strftime("%Y-%m-%d"),
        "po_number": f"PO-{random.randint(1000, 9999)}",
        "line_items": [
            {
                "description": f"{category} item {i+1}",
                "quantity": random.randint(1, 10),
                "unit_price": round(amount / random.randint(1, 5), 2),
            }
            for i in range(random.randint(1, 3))
        ],
        "tax": round(amount * 0.08, 2),
        "total": round(amount * 1.08, 2),
        "payment_terms": "Net 30",
        "notes": "Standard invoice, fully compliant",
        "compliance_status": "compliant",
    }


def generate_non_compliant_invoice(invoice_id: int) -> dict:
    """Generate a non-compliant invoice requiring rejection (15% of dataset)."""
    vendor = random.choice(VENDORS)
    category = random.choice(CATEGORIES)
    date = datetime.now() - timedelta(days=random.randint(1, 30))
    
    # Different types of non-compliance
    non_compliance_type = random.choice([
        "missing_po",
        "over_limit",
        "unapproved_vendor",
        "invalid_category"
    ])
    
    if non_compliance_type == "missing_po":
        amount = round(random.uniform(100, 8000), 2)
        po_number = None  # Missing PO
        reason = "Missing purchase order number"
    elif non_compliance_type == "over_limit":
        amount = round(random.uniform(15000, 50000), 2)  # Way over limit
        po_number = f"PO-{random.randint(1000, 9999)}"
        reason = "Amount exceeds approval threshold"
    elif non_compliance_type == "unapproved_vendor":
        amount = round(random.uniform(1000, 8000), 2)
        po_number = f"PO-{random.randint(1000, 9999)}"
        vendor = "Unapproved Vendor LLC"  # Not in approved list
        reason = "Vendor not on approved vendor list"
    else:  # invalid_category
        amount = round(random.uniform(1000, 8000), 2)
        po_number = f"PO-{random.randint(1000, 9999)}"
        category = "Prohibited Expense"  # Invalid category
        reason = "Invalid expense category"
    
    return {
        "invoice_id": f"INV-{invoice_id:04d}",
        "vendor": vendor,
        "vendor_reputation": VENDOR_REPUTATION.get(vendor, 30),
        "amount": amount,
        "currency": "USD",
        "category": category,
        "date": date.strftime("%Y-%m-%d"),
        "po_number": po_number,
        "line_items": [
            {
                "description": f"{category} item {i+1}",
                "quantity": random.randint(1, 10),
                "unit_price": round(amount / random.randint(1, 5), 2),
            }
            for i in range(random.randint(1, 3))
        ],
        "tax": round(amount * 0.08, 2),
        "total": round(amount * 1.08, 2),
        "payment_terms": "Net 30",
        "notes": f"Non-compliant: {reason}",
        "compliance_status": "non_compliant",
        "non_compliance_reason": reason,
    }


def generate_edge_case_invoice(invoice_id: int) -> dict:
    """Generate an edge case invoice requiring human review (15% of dataset)."""
    vendor = random.choice(VENDORS)
    category = random.choice(CATEGORIES)
    date = datetime.now() - timedelta(days=random.randint(1, 30))
    
    # Different types of edge cases
    edge_case_type = random.choice([
        "near_threshold",
        "international",
        "recurring_vendor_exception",
        "rush_payment"
    ])
    
    if edge_case_type == "near_threshold":
        amount = round(random.uniform(9500, 10500), 2)  # Near high risk threshold
        reason = "Amount near approval threshold, requires review"
        international = False
    elif edge_case_type == "international":
        amount = round(random.uniform(1000, 8000), 2)
        reason = "International transaction, requires compliance check"
        international = True
    elif edge_case_type == "recurring_vendor_exception":
        amount = round(random.uniform(1000, 8000), 2)
        reason = "Vendor has history of exceptions, review recommended"
        international = False
    else:  # rush_payment
        amount = round(random.uniform(1000, 8000), 2)
        reason = "Rush payment requested, expedited review needed"
        international = False
    
    return {
        "invoice_id": f"INV-{invoice_id:04d}",
        "vendor": vendor,
        "vendor_reputation": VENDOR_REPUTATION[vendor],
        "amount": amount,
        "currency": "USD" if not international else random.choice(["EUR", "GBP", "JPY"]),
        "category": category,
        "date": date.strftime("%Y-%m-%d"),
        "po_number": f"PO-{random.randint(1000, 9999)}",
        "line_items": [
            {
                "description": f"{category} item {i+1}",
                "quantity": random.randint(1, 10),
                "unit_price": round(amount / random.randint(1, 5), 2),
            }
            for i in range(random.randint(1, 3))
        ],
        "tax": round(amount * 0.08, 2),
        "total": round(amount * 1.08, 2),
        "payment_terms": "Net 30",
        "notes": f"Edge case: {reason}",
        "compliance_status": "edge_case",
        "edge_case_reason": reason,
        "international": international if edge_case_type == "international" else False,
    }


def generate_invoices(num_invoices: int = 50) -> list[dict]:
    """Generate a dataset of mock invoices with various compliance scenarios."""
    invoices = []
    
    # 70% compliant, 15% non-compliant, 15% edge cases
    num_compliant = int(num_invoices * 0.7)
    num_non_compliant = int(num_invoices * 0.15)
    num_edge_cases = num_invoices - num_compliant - num_non_compliant
    
    invoice_id = 1
    
    # Generate compliant invoices
    for _ in range(num_compliant):
        invoices.append(generate_compliant_invoice(invoice_id))
        invoice_id += 1
    
    # Generate non-compliant invoices
    for _ in range(num_non_compliant):
        invoices.append(generate_non_compliant_invoice(invoice_id))
        invoice_id += 1
    
    # Generate edge case invoices
    for _ in range(num_edge_cases):
        invoices.append(generate_edge_case_invoice(invoice_id))
        invoice_id += 1
    
    # Shuffle to randomize order
    random.shuffle(invoices)
    
    return invoices


def create_policy_documents():
    """Create policy documents for compliance checking."""
    policies = {
        "vendor_approval_policy.txt": """VENDOR APPROVAL POLICY

This policy outlines the requirements for vendor approval and engagement.

1. APPROVED VENDOR LIST
All transactions must be conducted with vendors on the approved vendor list. The current approved vendors are:
- Acme Corporation
- TechSupply Inc
- Office Essentials Ltd
- Global Services Group
- Consulting Partners LLC
- Marketing Solutions Co
- IT Infrastructure Pro
- Software Licensing Corp
- Facilities Management Inc
- Training Academy Ltd

2. VENDOR REPUTATION REQUIREMENTS
All vendors must maintain a minimum reputation score of 60/100. Vendors below this threshold require additional approval.

3. NEW VENDOR ONBOARDING
New vendors must complete the following:
- Business verification
- Tax ID validation
- Insurance certificate submission
- Reference checks
- Compliance review

Transactions with unapproved vendors will be automatically rejected.
""",
        
        "expense_limits_policy.txt": """EXPENSE LIMITS AND APPROVAL AUTHORITY

This policy defines the expense limits and approval requirements for all transactions.

1. APPROVAL THRESHOLDS BY AMOUNT
- Under $1,000: Automatic approval (low risk)
- $1,000 - $5,000: Manager approval required (medium risk)
- $5,000 - $10,000: Director approval required (high risk)
- Over $10,000: VP approval required (critical risk)

2. CATEGORY-SPECIFIC LIMITS
Software & Licensing: Up to $15,000 per transaction
Hardware: Up to $20,000 per transaction
Professional Services: Up to $25,000 per transaction
Marketing: Up to $10,000 per transaction
Office Supplies: Up to $5,000 per transaction
Travel: Up to $8,000 per transaction
Training: Up to $5,000 per transaction

3. CUMULATIVE LIMITS
Total monthly spend per vendor should not exceed $50,000 without executive review.

4. RUSH PAYMENTS
Rush payments (payment due within 5 business days) require additional approval regardless of amount.
""",
        
        "po_matching_requirements.txt": """PURCHASE ORDER MATCHING REQUIREMENTS

This policy defines the requirements for PO matching and invoice validation.

1. MANDATORY PO REQUIREMENT
All invoices over $500 must have a valid purchase order (PO) number.

2. PO VALIDATION RULES
- PO number must exist in the system
- PO must be approved and active
- Invoice amount must not exceed PO amount by more than 5%
- Vendor on invoice must match PO vendor
- Invoice date must be within PO validity period

3. PO EXCEPTIONS
The following categories may proceed without a PO with manager approval:
- Utilities (under $2,000)
- Recurring subscriptions (pre-approved)
- Emergency repairs (under $3,000)

4. THREE-WAY MATCH
For amounts over $5,000, three-way match is required:
- Purchase order
- Receipt/delivery confirmation
- Invoice

Missing any component triggers HITL review.
""",
        
        "international_transaction_rules.txt": """INTERNATIONAL TRANSACTION POLICY

This policy governs cross-border payments and foreign currency transactions.

1. SUPPORTED CURRENCIES
Primary currencies: USD, EUR, GBP, CAD, AUD
Secondary currencies require treasury approval: JPY, CHF, SGD

2. FOREIGN EXCHANGE REQUIREMENTS
- All foreign transactions must use current exchange rates
- Exchange rate variance over 2% requires reapproval
- Forward contracts available for transactions over $50,000

3. COMPLIANCE REQUIREMENTS
International transactions require:
- Tax treaty verification
- Export control compliance check
- OFAC/sanctions screening
- VAT/GST validation where applicable

4. REVIEW THRESHOLDS
All international transactions over $5,000 require compliance team review.
Transactions to high-risk countries always require executive approval.

5. DOCUMENTATION
Required documents for international payments:
- Commercial invoice
- Proof of delivery
- Tax documentation
- Compliance certificate
""",
        
        "exception_management_policy.txt": """EXCEPTION MANAGEMENT AND LEARNING POLICY

This policy defines how exceptions are handled and how the system learns from human decisions.

1. EXCEPTION TYPES
- Temporary exception: One-time override for specific circumstances
- Recurring exception: Pattern-based rule for similar future transactions
- Policy gap: Situation not covered by existing policies

2. EXCEPTION APPROVAL AUTHORITY
- Low-value exceptions (under $5,000): Manager approval
- High-value exceptions ($5,000-$15,000): Director approval
- Policy exceptions (over $15,000): VP approval

3. LEARNING FROM EXCEPTIONS
When a human approves an exception:
- System captures the rationale
- Similar patterns are identified
- Memory is updated with learned rule
- Future similar transactions apply the learned exception

4. EXCEPTION REVIEW CYCLE
All exceptions are reviewed quarterly to:
- Confirm validity
- Update policies if needed
- Remove obsolete exceptions
- Measure exception frequency trends

5. EXCEPTION DOCUMENTATION
Each exception must include:
- Business justification
- Risk assessment
- Approver identification
- Duration (temporary vs permanent)
- Review date

The goal is continuous learning to reduce human intervention over time while maintaining compliance.
"""
    }
    
    return policies


def main():
    """Main function to generate all mock data."""
    # Create output directories
    invoices_dir = Path("data/mock_invoices")
    policies_dir = Path("data/policies")
    invoices_dir.mkdir(parents=True, exist_ok=True)
    policies_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate invoices
    print("Generating 50 mock invoices...")
    invoices = generate_invoices(50)
    
    # Save individual invoice files
    for invoice in invoices:
        filename = f"{invoice['invoice_id']}.json"
        filepath = invoices_dir / filename
        with open(filepath, 'w') as f:
            json.dump(invoice, f, indent=2)
    
    # Save summary file
    summary_path = invoices_dir / "invoices_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(invoices, f, indent=2)
    
    print(f"✅ Generated {len(invoices)} invoices in {invoices_dir}")
    print(f"   - Compliant: {sum(1 for inv in invoices if inv['compliance_status'] == 'compliant')}")
    print(f"   - Non-compliant: {sum(1 for inv in invoices if inv['compliance_status'] == 'non_compliant')}")
    print(f"   - Edge cases: {sum(1 for inv in invoices if inv['compliance_status'] == 'edge_case')}")
    
    # Generate policy documents
    print("\nGenerating policy documents...")
    policies = create_policy_documents()
    
    for filename, content in policies.items():
        filepath = policies_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
    
    print(f"✅ Generated {len(policies)} policy documents in {policies_dir}")
    print(f"   - {', '.join(policies.keys())}")
    
    print("\n🎉 Mock data generation complete!")


if __name__ == "__main__":
    main()

