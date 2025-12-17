#!/usr/bin/env python3
"""Generate realistic mock invoices for testing AFGA classification system."""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


class MockInvoiceGenerator:
    """Generate realistic invoice data for testing."""

    VENDORS = [
        ("Consulting Partners LLC", 68, ["Consulting", "Software"]),
        ("Office Supplies Inc", 85, ["Office Supplies", "Equipment"]),
        ("Tech Solutions GmbH", 72, ["Software", "Hardware", "IT Services"]),
        ("Cloud Services Corp", 90, ["Cloud Services", "Software"]),
        ("Marketing Agency Pro", 65, ["Marketing", "Advertising"]),
        ("Legal Advisory LLP", 95, ["Legal", "Consulting"]),
        ("Hardware Direct", 78, ["Hardware", "Equipment"]),
        ("Training Institute", 88, ["Training", "Education"]),
        ("Facility Management Co", 82, ["Facilities", "Maintenance"]),
        ("Travel Services Ltd", 75, ["Travel", "Transportation"]),
        ("Catering Excellence", 80, ["Catering", "Food Services"]),
        ("Security Systems Inc", 92, ["Security", "Equipment"]),
        ("HR Solutions Group", 87, ["HR Services", "Consulting"]),
        ("Data Analytics Corp", 70, ["Software", "Consulting"]),
        ("Print & Design Studio", 77, ["Marketing", "Office Supplies"]),
    ]

    PAYMENT_TERMS = ["Net 30", "Net 60", "Due on Receipt", "Net 15", "Net 45"]

    CURRENCIES = ["USD", "EUR", "GBP"]

    # Compliance scenarios for realistic testing
    COMPLIANCE_SCENARIOS = [
        {"type": "compliant", "weight": 0.5, "notes": "Standard invoice, fully compliant"},
        {"type": "high_amount", "weight": 0.15, "notes": "High-value transaction requiring review"},
        {"type": "new_vendor", "weight": 0.1, "notes": "New vendor, additional verification needed"},
        {"type": "international", "weight": 0.1, "notes": "International transaction"},
        {"type": "unusual_category", "weight": 0.08, "notes": "Unusual category for this vendor"},
        {"type": "missing_po", "weight": 0.05, "notes": "Missing PO number"},
        {"type": "tax_anomaly", "weight": 0.02, "notes": "Tax calculation requires verification"},
    ]

    def __init__(self, seed: int = None):
        """Initialize generator with optional seed for reproducibility."""
        if seed is not None:
            random.seed(seed)
        self.invoice_counter = 0

    def generate_line_items(self, category: str, amount: float) -> List[Dict]:
        """Generate realistic line items for given category and amount."""
        num_items = random.randint(1, 5)
        base_amount = amount / num_items
        
        line_items = []
        for i in range(num_items):
            quantity = random.randint(1, 20)
            unit_price = round(base_amount / quantity, 2)
            
            line_items.append({
                "description": f"{category} item {i + 1}",
                "quantity": quantity,
                "unit_price": unit_price,
            })
        
        return line_items

    def select_scenario(self) -> Dict:
        """Select compliance scenario based on weights."""
        scenarios = self.COMPLIANCE_SCENARIOS
        weights = [s["weight"] for s in scenarios]
        return random.choices(scenarios, weights=weights)[0]

    def generate_invoice(self, invoice_id: str = None, scenario: Dict = None) -> Dict:
        """Generate a single mock invoice."""
        self.invoice_counter += 1
        
        if not invoice_id:
            invoice_id = f"INV-{self.invoice_counter:04d}"
        
        if not scenario:
            scenario = self.select_scenario()

        # Select vendor
        vendor_name, base_reputation, vendor_categories = random.choice(self.VENDORS)
        
        # Adjust reputation based on scenario
        reputation = base_reputation
        if scenario["type"] == "new_vendor":
            reputation = random.randint(40, 60)  # Lower reputation for new vendors
        
        # Select category
        category = random.choice(vendor_categories)
        if scenario["type"] == "unusual_category":
            # Pick a category not typical for this vendor
            all_categories = set()
            for _, _, cats in self.VENDORS:
                all_categories.update(cats)
            unusual_cats = list(all_categories - set(vendor_categories))
            if unusual_cats:
                category = random.choice(unusual_cats)
        
        # Generate amount based on scenario
        if scenario["type"] == "high_amount":
            amount = round(random.uniform(15000, 50000), 2)
        else:
            amount = round(random.uniform(500, 15000), 2)
        
        # Currency and international flag
        currency = "USD"
        international = False
        if scenario["type"] == "international":
            currency = random.choice(["EUR", "GBP"])
            international = True
        
        # Tax calculation
        tax_rate = 0.08 if currency == "USD" else 0.19  # Different tax rates
        tax = round(amount * tax_rate, 2)
        
        if scenario["type"] == "tax_anomaly":
            # Introduce slight tax discrepancy
            tax = round(tax * random.uniform(0.95, 1.05), 2)
        
        total = amount + tax
        
        # PO number
        po_number = f"PO-{random.randint(1000, 9999)}"
        if scenario["type"] == "missing_po":
            po_number = None
        
        # Generate invoice date (within last 90 days)
        days_ago = random.randint(0, 90)
        invoice_date = datetime.now() - timedelta(days=days_ago)
        
        # Generate line items
        line_items = self.generate_line_items(category, amount)
        
        invoice = {
            "invoice_id": invoice_id,
            "vendor": vendor_name,
            "vendor_reputation": reputation,
            "amount": amount,
            "currency": currency,
            "category": category,
            "date": invoice_date.strftime("%Y-%m-%d %H:%M:%S"),
            "po_number": po_number,
            "line_items": line_items,
            "tax": tax,
            "total": total,
            "payment_terms": random.choice(self.PAYMENT_TERMS),
            "notes": scenario["notes"],
            "compliance_status": scenario["type"],
        }
        
        if international:
            invoice["international"] = True
        
        return invoice

    def generate_batch(self, count: int, start_id: int = 1) -> List[Dict]:
        """Generate multiple invoices."""
        invoices = []
        for i in range(count):
            invoice_id = f"INV-{start_id + i:04d}"
            invoice = self.generate_invoice(invoice_id)
            invoices.append(invoice)
        return invoices

    def save_invoices(self, invoices: List[Dict], output_dir: Path) -> None:
        """Save invoices to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for invoice in invoices:
            invoice_id = invoice["invoice_id"]
            output_file = output_dir / f"{invoice_id}.json"
            
            with open(output_file, "w") as f:
                json.dump(invoice, f, indent=2)
            
            print(f"✓ Generated {invoice_id}: {invoice['vendor']} - ${invoice['amount']:.2f}")

    def generate_summary(self, invoices: List[Dict], output_dir: Path) -> None:
        """Generate summary file with all invoices."""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(invoices),
            "total_value": sum(inv["amount"] for inv in invoices),
            "invoices": invoices,
        }
        
        summary_file = output_dir / "invoices_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✓ Summary saved to {summary_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate mock invoices for AFGA testing")
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of invoices to generate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/mock_invoices"),
        help="Output directory for invoice JSON files",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=None,
        help="Starting invoice number (auto-detected if not specified)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    # Auto-detect next invoice ID if not specified
    start_id = args.start_id
    if start_id is None:
        existing_invoices = list(args.output_dir.glob("INV-*.json"))
        if existing_invoices:
            # Extract highest ID
            existing_ids = [
                int(f.stem.split("-")[1])
                for f in existing_invoices
                if f.stem.startswith("INV-")
            ]
            start_id = max(existing_ids) + 1
        else:
            start_id = 1

    print(f"Generating {args.count} invoices starting from INV-{start_id:04d}")
    print(f"Output directory: {args.output_dir}")
    if args.seed is not None:
        print(f"Using random seed: {args.seed}")
    print()

    generator = MockInvoiceGenerator(seed=args.seed)
    invoices = generator.generate_batch(args.count, start_id)
    generator.save_invoices(invoices, args.output_dir)
    generator.generate_summary(invoices, args.output_dir)

    print(f"\n✓ Successfully generated {args.count} invoices")


if __name__ == "__main__":
    main()
