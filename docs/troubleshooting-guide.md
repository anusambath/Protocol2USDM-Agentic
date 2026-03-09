# Troubleshooting Guide

## Common Issues

### "Pipeline not initialized" RuntimeError

**Cause:** Called `pipeline.run()` before `pipeline.initialize()`.

**Fix:** Always call `initialize()` first:
```python
pipeline = ExtractionPipeline(config)
pipeline.initialize()  # Must call this first
result = pipeline.run("protocol.pdf")
```

### API Key Errors

**Symptom:** Extraction agents fail with authentication errors.

**Fix:** Ensure your API key is set:
```bash
export GOOGLE_API_KEY=your-key-here
```
Or in `.env` file. The key must have access to the Gemini API.

### Agent Timeout Errors

**Symptom:** Agents fail with timeout errors on large protocols.

**Fix:** Increase timeout in agent capabilities or use a faster model:
```python
config = PipelineConfig(model="gemini-2.5-flash")
```

### Rate Limit Errors (429)

**Symptom:** Transient errors with "rate limit exceeded" messages.

**Fix:** The error handler retries transient errors automatically with exponential backoff. If persistent:
- Reduce `max_workers` to lower parallel API calls
- Use a model with higher rate limits
- Add delays between protocol runs

### SoA Vision Extraction Failures

**Symptom:** SoA vision agent returns empty results.

**Fix:**
- Ensure `enable_vision=True` in config
- Check that PDF pages contain actual SoA table images (not just text)
- Verify DPI setting is sufficient (try `dpi=200` or `dpi=300`)

### Empty Context Store After Extraction

**Symptom:** `pipeline.context_store.entity_count == 0` after run.

**Fix:**
- Check `result.failed_agents` for which agents failed
- Check logs for error details
- Verify the PDF is a valid clinical trial protocol

### Checkpoint Recovery Issues

**Symptom:** Cannot resume from checkpoint.

**Fix:**
- Ensure `checkpoints_dir` exists and is writable
- Checkpoint files are JSON — verify they're not corrupted
- Use `EnhancedCheckpoint.load()` to inspect checkpoint contents

## Error Categories

The error handler classifies errors into:

| Category | Retry? | Examples |
|---|---|---|
| TRANSIENT | Yes (with backoff) | Timeouts, rate limits, connection errors |
| PERMANENT | No | Invalid input, schema errors, bad API keys |
| CONFIGURATION | No | Missing config, wrong model name |

## Debugging

Enable debug logging for detailed agent execution traces:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check individual agent results in the pipeline result:
```python
result = pipeline.run("protocol.pdf")
for agent_id, success in result.agent_results.items():
    if not success:
        print(f"FAILED: {agent_id}")
```
