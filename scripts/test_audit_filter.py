"""Test the audit trail filter logic."""

# Simulate the filter
taa_trail = [
    "TAA received transaction: INV-0001",
    "Vendor: Marketing Solutions Co, Amount: $2571.4, Category: Travel",
    "Performing risk assessment",
    "Risk assessed: medium (score: 25.0/100)",
    "Delegating to PAA for policy check (A2A)",
    "⚠️ PAA A2A integration pending - using mock response",
    "Evaluating PAA response",
    "⚠️ No PAA response available (using risk-based decision)",
    "Making final decision",
    "Final decision: hitl",
    "TAA workflow completed",
    "TAA: Decision updated based on PAA - APPROVED",
]

paa_trail = [
    "PAA received request for invoice INV-0001",
    "Checking: Marketing Solutions Co, $2571.4, Travel",
    "Retrieving relevant policies (RAG via MCP)",
    "Retrieved 5 policy chunks via MCP",
    "Checking adaptive memory for exceptions",
    "Found 1 applicable memory exceptions",
    "Evaluating compliance with LLM",
    "Compliance check: ✅ Compliant (confidence: 0.95)",
    "PAA compliance check completed",
]

warnings_to_remove = [
    "⚠️ PAA A2A integration pending - using mock response",
    "⚠️ No PAA response available (using risk-based decision)",
    "Delegating to PAA for policy check (A2A)",
]

print("🔬 Testing Audit Trail Filter")
print("=" * 80)
print(f"\n📋 TAA Trail ({len(taa_trail)} steps)")
print(f"📋 PAA Trail ({len(paa_trail)} steps)")
print(f"\n🚫 Warnings to filter: {len(warnings_to_remove)}")
for w in warnings_to_remove:
    print(f"   - {w}")

# Apply filter
merged = []
filtered_count = 0

for step in taa_trail:
    # Check if this step should be filtered
    should_filter = paa_trail and any(warning in step for warning in warnings_to_remove)
    
    if should_filter:
        print(f"\n🚫 FILTERING: {step}")
        filtered_count += 1
        continue
    
    merged.append(f"[TAA] {step}")

for step in paa_trail:
    merged.append(f"[PAA] {step}")

print(f"\n" + "=" * 80)
print(f"✅ Filtered out {filtered_count} warning(s)")
print(f"📊 Final audit trail has {len(merged)} steps")

print(f"\n📜 FINAL AUDIT TRAIL:")
print("-" * 80)
for idx, step in enumerate(merged, 1):
    print(f"{idx}. {step}")

# Check if warnings still present
print(f"\n" + "=" * 80)
print("🔍 Verification:")
has_warnings = any("⚠️" in step for step in merged)
if has_warnings:
    print("❌ FAIL: Warnings still present in audit trail!")
    for step in merged:
        if "⚠️" in step:
            print(f"   Found: {step}")
else:
    print("✅ PASS: No warnings in final audit trail!")

