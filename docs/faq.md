# Frequently Asked Questions

## General

**Q: What file formats are supported?**
A: PDF only. The protocol must be a standard clinical trial protocol document.

**Q: Which LLM models are supported?**
A: Gemini 2.5 Pro/Flash and 3 Flash (via Vertex AI), Claude Opus 4.6/4.5 and Sonnet 4 (Anthropic), GPT-4o and GPT-5.x (OpenAI). Set via `PipelineConfig(model="...")` or `--model` CLI flag. Note: `claude-opus-4` aliases to `claude-opus-4-6`.

**Q: How long does extraction take?**
A: Typically 5-25 minutes per protocol depending on model, protocol size, and number of agents. The `result.md` file in the output directory shows per-agent timing.

**Q: What is USDM?**
A: The Unified Study Definitions Model (USDM) is a CDISC standard for representing clinical study designs in a structured, machine-readable format. Version 4.0 is the current release.

## Extraction Quality

**Q: How accurate is the extraction?**
A: Accuracy varies by domain. Metadata extraction is typically 95%+. Complex entities like Schedule of Activities may be 80-90%. Always review low-confidence entities.

**Q: Why are some entities missing?**
A: Common reasons: the information isn't in the protocol, the PDF text extraction failed (scanned PDFs), or the LLM didn't capture it. Check the provenance report for details.

**Q: How does vision vs text extraction work?**
A: Schedule of Activities tables are extracted twice — once from page images (vision) and once from PDF text. The reconciliation agent merges both results, boosting confidence when they agree.

**Q: What does "reconciled" mean?**
A: When vision and text agents both extract the same SoA table, the reconciliation agent compares cell-by-cell, resolves conflicts, and produces a merged result with adjusted confidence scores.

## Technical

**Q: Can I add custom extraction agents?**
A: Yes. See the Developer Guide (`docs/developer-guide.md`) for a step-by-step template.

**Q: How do I skip certain agents?**
A: Use `PipelineConfig(skip_agents=["agent_id_1", "agent_id_2"])`.

**Q: Can I use this without Docker?**
A: Yes. Install Python 3.9+, run `pip install -r requirements.txt`, set your API key, and use the CLI (`python run_extraction.py protocol.pdf`) or Python API directly.

**Q: Where are the output files?**
A: In a timestamped directory under `output/`, e.g., `output/NCT12345_Protocol_20260301_120000/`. Each agent's output is saved as a numbered JSON file (e.g., `01_extraction_metadata.json`). A `result.md` summary is also generated.

**Q: What is the postprocessing agent?**
A: The `PostprocessingAgent` runs after extraction to apply SoA post-processing including superscript/footnote normalization, activity-group linking, and name cleanup. Separate agents handle CDISC CORE validation, schema validation, and NCI EVS enrichment.

**Q: How do checkpoints work?**
A: After each wave of agents completes, the orchestrator saves a checkpoint with the current Context Store state. If the pipeline crashes, you can resume from the last checkpoint.

**Q: What happens if an agent fails?**
A: The pipeline continues with remaining agents (graceful degradation). Failed agents are listed in `result.failed_agents`. Transient errors (timeouts, rate limits) are retried automatically.

## Monitoring

**Q: How do I access Grafana dashboards?**
A: When running with Docker Compose, Grafana is at `http://localhost:3001`. Default credentials: admin / p2u_grafana.

**Q: What metrics are tracked?**
A: Agent execution time, success/failure rates, confidence scores, entity counts, queue depth, enrichment coverage, and USDM validation results.

**Q: How do I set up alerts?**
A: Alert rules are pre-configured in `infra/prometheus/alert_rules.yml`. Configure notification channels (email, Slack) in Grafana's alerting settings.
