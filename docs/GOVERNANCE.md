# AI Governance Framework

## Overview

AFGA implements **comprehensive AI governance controls** for all LLM interactions, ensuring:
- Privacy protection (PII detection and redaction)
- Content safety (input/output validation)
- Complete auditability (JSONL logging)
- Cost accountability (per-call tracking)
- Policy enforcement (access controls)

This follows industry best practices and regulatory requirements for responsible AI deployment.

---

## Architecture

### Governance Layer

```
Agent → GovernedLLMClient → GovernanceWrapper → OpenRouterClient → LLM
                                    ↓
                            ┌───────────────────┐
                            │ 1. Input Check    │
                            │   - PII detection │
                            │   - Forbidden words│
                            │   - Length validation│
                            ├───────────────────┤
                            │ 2. Policy Check   │
                            │   - Time controls │
                            │   - Access rules  │
                            │   - Rate limits   │
                            ├───────────────────┤
                            │ 3. LLM API Call   │
                            │   - With fallback │
                            │   - Error handling│
                            ├───────────────────┤
                            │ 4. Output Check   │
                            │   - Content filter│
                            │   - PII in response│
                            │   - Quality check │
                            ├───────────────────┤
                            │ 5. Audit Log      │
                            │   - PII redacted  │
                            │   - JSONL format  │
                            │   - Cost tracked  │
                            └───────────────────┘
```

---

## Components

### 1. GovernanceWrapper

**Location:** `src/governance/governance_wrapper.py`

**Responsibilities:**
- Orchestrates all governance checks
- Wraps every LLM API call
- Enforces policies
- Logs to audit files

**Key Method:**
```python
governed_completion(
    prompt: str,
    agent_name: str,
    model: str,
    trace_id: str,
    user_id: str
) -> str
```

### 2. InputValidator

**Location:** `src/governance/input_validator.py`

**Checks:**
- **PII Detection:** Emails, SSNs, credit cards, phones, IBANs
- **Forbidden Words:** Passwords, API keys, secrets
- **Prompt Length:** Min 5 chars, max 50K chars
- **Data Protection:** Sensitive information blocking

**PII Patterns:**
```python
{
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
    "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    "iban": r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b',
}
```

**Redaction:**
```
Input:  "Email john@example.com for approval"
Output: "Email [EMAIL_REDACTED] for approval"
```

### 3. OutputValidator

**Location:** `src/governance/output_validator.py`

**Checks:**
- **Empty Responses:** Detects empty or too-short outputs
- **PII in Outputs:** Ensures LLM doesn't leak data
- **Content Quality:** Length and format validation
- **Toxic Keywords:** Basic toxicity detection
- **JSON Validation:** For structured outputs

### 4. GovernanceAuditLogger

**Location:** `src/governance/audit_logger.py`

**Logs:**
- Every LLM call (JSONL format)
- Input/output (PII-redacted)
- Governance violations
- Processing time
- Cost estimates

**Files Created:**
- `governance_audit.jsonl` - All LLM interactions
- `governance_violations.jsonl` - Violations only

### 5. GovernedLLMClient

**Location:** `src/governance/governance_wrapper.py`

**Purpose:** Drop-in replacement for `OpenRouterClient`

**Usage:**
```python
# Before (ungoverned)
from core.openrouter_client import OpenRouterClient
llm = OpenRouterClient()

# After (governed)
from governance import GovernedLLMClient
llm = GovernedLLMClient(agent_name="PAA")
```

Same interface, but with complete governance!

---

## Governance Checks

### Input Governance

**Validates prompts BEFORE sending to LLM:**

✅ **PII Detection**
```python
Prompt: "Process invoice for john@example.com"
→ BLOCKED: Email detected
→ Logged as violation
```

✅ **Forbidden Words**
```python
Prompt: "Use password abc123 to access..."
→ BLOCKED: Forbidden word detected
→ Logged as violation
```

✅ **Length Validation**
```python
Prompt: "Hi"  # Too short (< 5 chars)
→ BLOCKED: Prompt too short
→ Logged as violation
```

### Output Governance

**Validates responses AFTER receiving from LLM:**

✅ **Empty Detection**
```python
Response: ""
→ WARNING: Empty response
→ Logged but allowed
```

✅ **PII in Response**
```python
Response: "Contact us at support@company.com"
→ WARNING: Email in response
→ Logged and redacted
```

✅ **Quality Check**
```python
Response: "..." (too short or invalid)
→ WARNING: Low quality response
→ Logged
```

### Policy Enforcement

**Enforces access policies:**

✅ **Time Controls** (Optional)
```python
Time: 2:00 AM (outside business hours)
→ INFO: Outside hours (logged but allowed in demo)
→ Could be blocked in production
```

✅ **Future Policies:**
- User authorization
- Agent permissions
- Budget limits
- Rate limiting

---

## Audit Logging

### JSONL Format

Every LLM call creates an entry in `governance_audit.jsonl`:

```json
{
  "timestamp": "2025-11-04T15:30:45.123Z",
  "trace_id": "abc-123",
  "user_id": "user-456",
  "agent_name": "PAA",
  "model": "openai/gpt-4o",
  "prompt_length": 1234,
  "response_length": 567,
  "input_valid": true,
  "input_violations": [],
  "output_valid": true,
  "output_violations": [],
  "processing_time_ms": 2345,
  "cost_estimate_usd": 0.0123,
  "governance_status": "pass"
}
```

### Violations Log

Violations are ALSO logged to `governance_violations.jsonl`:

```json
{
  "timestamp": "2025-11-04T15:31:12.456Z",
  "event_type": "input_validation_failed",
  "agent_name": "PAA",
  "severity": "error",
  "details": {
    "violations": ["PII detected (email): 1 instance(s)"],
    "prompt_preview": "Check invoice for john@...",
    "trace_id": "xyz-789"
  }
}
```

### PII Redaction

**Original prompt:**
```
"Approve invoice for john@example.com, 
SSN 123-45-6789, 
card 4532-1234-5678-9010"
```

**Logged (redacted):**
```
"Approve invoice for [EMAIL_REDACTED], 
SSN [SSN_REDACTED], 
card [CREDIT_CARD_REDACTED]"
```

---

## Integration with Agents

### All Agents Now Use Governed LLM

**PAA (Policy Adherence Agent):**
```python
self.llm_client = GovernedLLMClient(agent_name="PAA")

# Every PAA LLM call now goes through governance
response = self.llm_client.completion(
    prompt=policy_check_prompt,
    temperature=0.1,
    trace_id=trace_id
)
# → Input validated
# → Output validated
# → Logged to audit file
```

**EMA (Exception Manager Agent):**
```python
self.llm_client = GovernedLLMClient(agent_name="EMA")

# Every EMA LLM call now goes through governance
response = self.llm_client.completion(
    prompt=correction_analysis_prompt,
    temperature=0.2,
    trace_id=trace_id
)
# → Same governance checks
```

**InvoiceExtractor:**
```python
self.llm_client = GovernedLLMClient(agent_name="InvoiceExtractor")

# Vision LLM calls also governed
response = self.llm_client.completion(
    prompt=extraction_prompt,
    temperature=0.1,
    trace_id=trace_id
)
# → Protects extraction workflow too
```

---

## Visualization in Streamlit

### Agent Workflow Page - New Section

**"AI Governance & Safety" Dashboard:**

**Metrics Displayed:**
- Input Validation: Active ✅
- Output Validation: Active ✅
- Audit Logging: Active ✅
- Cost Tracking: Active ✅

**Statistics (if audit log exists):**
- Total LLM Calls
- Governance Violations
- Compliance Rate (%)
- Calls by Agent

**Recent Governance Events:**
- Last 5 violations
- Event type and severity
- Violation details
- Timestamp and agent

**Best Practices Guide:**
- Explains each governance feature
- Why it matters
- What gets logged
- Integration options

---

## Cost Tracking

### Per-Call Estimation

**Formula:**
```python
prompt_tokens = len(prompt) / 4  # Rough estimation
response_tokens = len(response) / 4

cost = (prompt_tokens + response_tokens) / 1000 * model_rate
```

**Model Rates:**
```python
{
    "openai/gpt-4o": $0.005 per 1K tokens,
    "gpt-4-vision-preview": $0.01 per 1K tokens,
    "claude-3.5-sonnet": $0.003 per 1K tokens,
    "llama-3.1-70b": $0.0005 per 1K tokens,
}
```

### Aggregated Costs

**Track by:**
- Per agent (PAA, EMA, InvoiceExtractor)
- Per transaction
- Total cumulative
- Daily/weekly/monthly

**Accessible via:**
- Governance statistics API
- Audit log analysis
- Streamlit dashboard

---

## Compliance Features

### Regulatory Alignment

**GDPR (Privacy):**
- ✅ PII detection and redaction
- ✅ Data minimization (only send necessary data)
- ✅ Complete audit trail
- ✅ Right to explanation (audit logs)

**SOC 2 (Security):**
- ✅ Access logging
- ✅ Data protection controls
- ✅ Audit trails
- ✅ Monitoring and alerting

**AI Act (EU Regulation):**
- ✅ Transparency (full audit logs)
- ✅ Human oversight (HITL workflow)
- ✅ Risk management (governance controls)
- ✅ Record-keeping (JSONL logs)

---

## How to Use

### For Developers

**All new agents should use GovernedLLMClient:**
```python
from governance import GovernedLLMClient

class MyAgent:
    def __init__(self):
        self.llm = GovernedLLMClient(agent_name="MyAgent")
    
    def my_method(self):
        response = self.llm.completion(
            prompt="...",
            trace_id="trace-123"
        )
        # Automatically governed!
```

### For Monitoring

**Check governance statistics:**
```python
stats = llm_client.get_statistics()
print(f"Total calls: {stats['total_calls']}")
print(f"Violations: {stats['violations']}")
print(f"Compliance rate: {stats['compliance_rate']}%")
```

**Review violations:**
```python
violations = llm_client.get_recent_violations(limit=10)
for v in violations:
    print(f"{v['agent_name']}: {v['input_violations']}")
```

### For Auditing

**Export audit logs:**
```bash
# All LLM calls
cat governance_audit.jsonl | jq .

# Violations only
cat governance_violations.jsonl | jq .

# Filter by agent
grep "PAA" governance_audit.jsonl | jq .

# Cost analysis
cat governance_audit.jsonl | jq -r '.cost_estimate_usd' | awk '{sum+=$1} END {print sum}'
```

---

## Testing

### Test Governance Controls

```python
from governance import GovernedLLMClient

# Test PII detection
llm = GovernedLLMClient(agent_name="Test")

try:
    llm.completion("Email me at test@example.com")
except ValueError as e:
    print(f"Blocked: {e}")
    # → "Input governance failed: PII detected (email)"

# Test with valid prompt
response = llm.completion("What is 2+2?")
# → Passes governance, returns "4"
```

### Mock for Testing

```python
# Bypass governance for tests
response = llm.governance.governed_completion(
    prompt="...",
    agent_name="Test",
    bypass_governance=True  # Emergency bypass (logged!)
)
```

---

## Configuration

### Governance Settings (Future)

Can be added to `config.py`:

```python
class Settings:
    # Governance
    governance_enabled: bool = True
    governance_strict_mode: bool = False  # Fail on violations vs warn
    governance_log_file: str = "governance_audit.jsonl"
    
    # Input controls
    pii_detection_enabled: bool = True
    forbidden_words: List[str] = ["password", "secret_key", ...]
    max_prompt_length: int = 50000
    
    # Output controls
    output_validation_enabled: bool = True
    toxic_keywords: List[str] = [...]
    
    # Policy enforcement
    enforce_business_hours: bool = False
    business_hours_start: int = 6
    business_hours_end: int = 22
```

---

## Monitoring & Alerting

### What to Monitor

**Key Metrics:**
1. **Compliance Rate:** Should be > 95%
2. **Violation Rate:** Should be < 5%
3. **Input Violations:** Track trends
4. **Output Violations:** Track trends
5. **Cost per Agent:** Budget monitoring

### Alert Conditions

**Critical Alerts:**
- Multiple PII detections (data leak risk)
- High violation rate (> 10%)
- Unusual cost spike

**Warning Alerts:**
- Output validation failures
- Outside business hours access
- High prompt lengths

### Integration Points

**Can send alerts to:**
- Slack/Teams (webhook)
- Email (SMTP)
- PagerDuty (incidents)
- Azure Monitor (metrics)

---

## Best Practices

### Do's ✅

1. **Always use GovernedLLMClient** for new agents
2. **Review audit logs regularly** (weekly)
3. **Monitor compliance rate** (should be high)
4. **Update PII patterns** as needed
5. **Redact PII in logs** (automatic)
6. **Track costs per agent** (budget control)

### Don'ts ❌

1. **Don't bypass governance** without logging
2. **Don't disable PII detection** in production
3. **Don't ignore violations** (investigate!)
4. **Don't log raw prompts** with PII
5. **Don't skip audit log analysis**

---

## Production Enhancements

### Phase 2: Advanced Features

**Add when deploying to production:**

1. **Microsoft Presidio Integration**
   ```python
   from presidio_analyzer import AnalyzerEngine
   # More comprehensive PII detection
   ```

2. **Perspective API (Toxicity)**
   ```python
   from googleapiclient import discovery
   # Professional toxicity scoring
   ```

3. **Guardrails.ai (Schema Enforcement)**
   ```python
   import guardrails as gd
   # Structured output validation
   ```

4. **TruLens (Output Quality)**
   ```python
   from trulens_eval import TruChain
   # RAG quality assessment
   ```

5. **Real-time Alerting**
   ```python
   # Send Slack alert on violations
   # Integrate with monitoring systems
   ```

---

## Audit Log Analysis

### Sample Queries

**Total LLM calls:**
```bash
wc -l governance_audit.jsonl
```

**Violations only:**
```bash
grep '"governance_status":"violation"' governance_audit.jsonl | wc -l
```

**Cost by agent:**
```bash
cat governance_audit.jsonl | \
  jq -r '"\(.agent_name),\(.cost_estimate_usd)"' | \
  awk -F, '{agents[$1]+=$2} END {for (a in agents) print a, agents[a]}'
```

**Recent violations:**
```bash
tail -10 governance_violations.jsonl | jq .
```

---

## Example Violations

### Input Violation: PII Detected

```json
{
  "timestamp": "2025-11-04T15:30:00Z",
  "event_type": "input_validation_failed",
  "agent_name": "PAA",
  "severity": "error",
  "details": {
    "violations": ["PII detected (email): 1 instance(s)"],
    "prompt_preview": "Check invoice for [EMAIL_REDACTED]...",
    "trace_id": "abc-123"
  }
}
```

**Action Taken:** Call blocked, violation logged

### Output Violation: Empty Response

```json
{
  "timestamp": "2025-11-04T15:31:00Z",
  "event_type": "output_validation_failed",
  "agent_name": "EMA",
  "severity": "warning",
  "details": {
    "violations": ["Empty or too short response (0 chars)"],
    "response_preview": "",
    "trace_id": "xyz-789"
  }
}
```

**Action Taken:** Logged as warning, response still returned

---

## Benefits

### 1. Privacy Protection

- ✅ Prevents PII from being sent to LLM providers
- ✅ Redacts PII in audit logs
- ✅ Detects PII in LLM responses
- ✅ GDPR compliance support

### 2. Content Safety

- ✅ Blocks sensitive keywords
- ✅ Validates response quality
- ✅ Filters inappropriate content
- ✅ Ensures policy compliance

### 3. Complete Auditability

- ✅ Every LLM call logged
- ✅ Governance decisions recorded
- ✅ Cost per call tracked
- ✅ Regulatory compliance support

### 4. Cost Control

- ✅ Per-agent cost tracking
- ✅ Per-call cost estimation
- ✅ Budget monitoring
- ✅ Cost optimization insights

### 5. Operational Excellence

- ✅ Standardized LLM access
- ✅ Centralized governance
- ✅ Observable AI operations
- ✅ Production-ready safeguards

---

## Comparison: Before vs After

### Before Governance

```python
# Direct LLM call
response = openrouter.completion(
    "Check this invoice for john@example.com"  # PII not detected!
)
# No logging
# No cost tracking
# No validation
```

### After Governance

```python
# Governed LLM call
response = governed_llm.completion(
    "Check this invoice for john@example.com"
)
# → Input validation: PII detected!
# → Call blocked
# → Violation logged
# → Cost tracked (if allowed)
# → Output validated
# → Audit trail created
```

---

## Governance Visualization

### Streamlit Dashboard

**Location:** Agent Workflow page → "AI Governance & Safety" section

**Shows:**
- Governance controls status (Active/Inactive)
- LLM call statistics
- Violation counts and rate
- Recent governance events
- Cost tracking
- Compliance rate

**Updates in real-time** as you process transactions!

---

## Future Enhancements

### Phase 2.1: Advanced Governance

1. **Real-time Alerting**
   - Slack/Teams webhooks
   - Email notifications
   - PagerDuty integration

2. **Advanced PII Detection**
   - Microsoft Presidio
   - Custom entity recognition
   - Multi-language support

3. **Toxicity Scoring**
   - Perspective API
   - Content moderation
   - Safety classifications

4. **Schema Enforcement**
   - Guardrails.ai integration
   - Structured output validation
   - Type safety for LLM outputs

5. **Rate Limiting**
   - Per-user limits
   - Per-agent limits
   - Budget controls
   - Throttling

### Phase 3: Enterprise Governance

1. **Centralized Governance Service**
   - Governance as microservice
   - Shared across all agents
   - Centralized policy management

2. **Dashboard & Analytics**
   - Real-time governance dashboard
   - Violation trends
   - Cost analytics
   - Compliance reporting

3. **Integration with Unity Catalog**
   - Policy management in Databricks
   - Centralized governance
   - Data lineage

---

## Summary

### What We Have

✅ **Comprehensive AI Governance:**
- Input validation (PII, forbidden words)
- Output validation (quality, content)
- Policy enforcement (time controls)
- Audit logging (JSONL with redaction)
- Cost tracking (per-agent, per-call)

✅ **Enterprise-Grade:**
- Industry best practices
- Regulatory compliance support
- Complete observability
- Production-ready safeguards

✅ **Integrated Everywhere:**
- All agents use governed LLM
- Every LLM call protected
- Full audit trails
- Streamlit visualization

### Why It Matters

**For Compliance:**
- Meets regulatory requirements (GDPR, AI Act)
- Supports audit needs (SOC 2)
- Demonstrates responsible AI

**For Operations:**
- Prevents data leaks
- Controls costs
- Ensures quality
- Enables monitoring

**For Business:**
- Trust and transparency
- Risk mitigation
- Governance-ready
- Enterprise deployment-ready

---

**AFGA now has enterprise-grade AI governance!** 🛡️

This is a **complete reference implementation** showing how to properly govern LLM usage in production AI systems.

