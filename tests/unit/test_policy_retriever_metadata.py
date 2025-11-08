from src.models.schemas import Invoice, LineItem
from src.services.policy_retriever import PolicyRetriever


def test_retrieve_relevant_policies_includes_metadata(tmp_path):
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()

    policy_content = (
        "Travel expense approvals require manual review for amounts over $2000.\n\n"
        "Ensure vendor compliance and purchase order verification before approval."
    )
    policy_file = policies_dir / "travel_policy.txt"
    policy_file.write_text(policy_content, encoding="utf-8")

    retriever = PolicyRetriever(policies_dir=str(policies_dir))

    invoice = Invoice(
        invoice_id="INV-TEST",
        vendor="Travel Partners",
        vendor_reputation=85,
        amount=2500.0,
        currency="USD",
        category="Travel",
        date="2025-11-05",
        po_number=None,
        line_items=[LineItem(description="Flight", quantity=1, unit_price=2500.0)],
        tax=0.0,
        total=2500.0,
    )

    results = retriever.retrieve_relevant_policies(invoice, top_k=3)

    assert results, "Expected at least one policy chunk to be retrieved"

    first = results[0]
    assert first["policy_name"] == "travel_policy"
    assert first["policy_filename"] == "travel_policy.txt"
    assert first["snippet"].startswith("Travel expense approvals")
    assert first["matched_terms"], "Expected matched_terms metadata to be populated"
    assert first["score"] > 0
