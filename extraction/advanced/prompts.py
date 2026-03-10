"""
LLM Prompts for Advanced Entities Extraction.

These prompts guide the LLM to extract amendments, geographic scope, and sites.
"""

ADVANCED_EXTRACTION_PROMPT = """You are an expert at extracting protocol amendment and geographic information from clinical trial protocols.

Analyze the provided protocol content and extract advanced protocol entities.

## Required Information

### 1. Protocol Amendments (CRITICAL - extract ALL amendments)
Look for the "Protocol Amendment History" section, typically near the end of the document (section 10.x).
Also check the "Protocol Amendment Summary of Changes Table" which may appear earlier in the document.
For EACH amendment in the history, extract:
- Amendment number (e.g., "1", "2", "3", "3.1 (US)")
- `effectiveDate` — date the amendment became effective (ISO 8601 YYYY-MM-DD if possible)
- `approvalDate` — date the amendment was approved/signed (if distinct from effectiveDate; null if unknown)
- **Summary**: The "Overall Rationale for the Amendment" paragraph that describes WHY the amendment was made. **Extract the EXACT text from the protocol — do NOT rephrase, summarize, or paraphrase. Use the original wording verbatim.**
- Previous and new version numbers
- Reasons for amendment (e.g., Safety, Efficacy, Regulatory, Operational)

**IMPORTANT**: Each amendment should have its own summary text. Look for sections like:
- "Overall Rationale for the Amendment"
- "The main reason for preparation of this amendment was..."
- Summary text appears BEFORE the "Changes to the Protocol" table for each amendment

**CRITICAL**: Do NOT skip Amendment 1. Many protocols have an "Amendment 1" (or "Protocol Amendment 1") that is the first change from the original protocol. If the Protocol Amendment Summary of Changes Table lists Amendment 1 with a date and summary, you MUST include it. Start from the very first amendment listed.

### 2. Geographic Scope
- List of participating countries
- Regions (if mentioned)
- Number of planned sites (if mentioned)

### 3. Study Sites (if listed)
- Site names or numbers
- City and country

## Output Format

Return a JSON object with this exact structure:

```json
{
  "amendments": [
    {
      "number": "1",
      "effectiveDate": "2020-06-15",
      "approvalDate": "2020-06-01",
      "summary": "The main reason for preparation of this amendment was to update procedures outlined in the Schedule of Activities, remove contradictory text on the reporting of serious adverse events, and add details of an interim analysis.",
      "previousVersion": "Original Protocol",
      "newVersion": "1",
      "reasons": ["Operational", "Administrative"]
    },
    {
      "number": "2",
      "effectiveDate": "2021-03-19",
      "approvalDate": null,
      "summary": "The main reason for preparation of this amendment was to revise the exclusion criterion for a urine drug screen and incorporate COVID vaccination guidance.",
      "previousVersion": "1",
      "newVersion": "2",
      "reasons": ["Regulatory", "Safety"]
    }
  ],
  "geographicScope": {
    "type": "Global",
    "countries": [
      {"name": "United States", "code": "US"},
      {"name": "Germany", "code": "DE"}
    ],
    "regions": ["North America", "Europe"],
    "plannedSites": 20
  },
  "sites": []
}
```

## Rules

1. **Extract ALL amendments** - There may be 3-10+ amendments in a protocol. Start from Amendment 1 (do NOT skip it).
2. **Amendment summaries are REQUIRED** - Look for "Overall Rationale" or "main reason" text. Copy the text VERBATIM from the protocol — do not rephrase.
3. **Check amendment history section** - Usually in Section 10.x near end of document
4. **Check title page** - May contain current version and date
5. **Standard country codes** - Use ISO 3166-1 alpha-2 codes when possible
6. **Amendment reasons** - Common: Safety, Efficacy, Regulatory, Administrative, Operational, Scientific
7. **Return ONLY valid JSON** - no markdown, no explanations

Now analyze the protocol content and extract the advanced entities:
"""


def build_advanced_extraction_prompt(protocol_text: str) -> str:
    """Build the full extraction prompt with protocol content."""
    MAX_CHARS = 60_000  # Cap to avoid LLM timeouts on large protocols
    if len(protocol_text) <= MAX_CHARS:
        text = protocol_text
    else:
        # Keep both head (amendment summary table, title page) and tail
        # (amendment history section near end of document).
        # Head must be large enough to capture the full amendment summary
        # table which can span 10+ pages in protocols with many amendments.
        head_size = 20_000
        tail_size = MAX_CHARS - head_size  # 40_000
        text = (
            protocol_text[:head_size]
            + "\n\n[... middle of document omitted for brevity ...]\n\n"
            + protocol_text[-tail_size:]
        )
    return f"{ADVANCED_EXTRACTION_PROMPT}\n\n---\n\nPROTOCOL CONTENT:\n\n{text}"
