"""
Pipeline - Full system integration of all agents with the Orchestrator.

Provides a high-level API for running the complete extraction pipeline:
  PDF → Extraction Agents → Quality Agents → USDM + Provenance

Configures agent dependencies, execution waves, and the full workflow.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent
from agents.context_store import ContextStore
from agents.message_queue import MessageQueue
from agents.orchestrator import ExecutionPlan, ExecutionStatus, OrchestratorAgent
from agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


# Wave configuration: agent_id → wave number
# Wave 0: No dependencies (PDF parsing, metadata, SoA, narrative, docstructure)
# Wave 1: Depends on metadata (eligibility, objectives, studydesign, advanced)
# Wave 2: Depends on metadata + SoA (interventions, procedures)
# Wave 3: Depends on SoA + procedures (scheduling, execution)
# Wave 4: Quality agents (validation, enrichment, reconciliation)
# Wave 5: Support agents (USDM generator, provenance)
WAVE_CONFIG = {
    # Wave 0 - Independent agents
    "pdf-parser": 0,
    "metadata_agent": 0,
    "soa_vision_agent": 0,
    "soa_text_agent": 1,
    "narrative_agent": 0,
    "docstructure_agent": 0,
    # Wave 1 - Depends on metadata
    "eligibility_agent": 1,
    "objectives_agent": 1,
    "studydesign_agent": 1,
    "advanced_agent": 1,
    # Wave 2 - Depends on metadata + SoA
    "interventions_agent": 2,
    "procedures_agent": 2,
    # Wave 3 - Depends on SoA + procedures
    "scheduling_agent": 3,
    "execution_agent": 3,
    "biomedical_concept_agent": 3,
    # Wave 4 - Quality
    "postprocessing": 4,
    "reconciliation": 4,
    "validation": 4,
    "enrichment": 4,
    # Wave 5 - Output generation
    "usdm-generator": 5,
    "provenance": 5,
}

# Output file prefix for quality/support agents
# Extraction agents use BaseExtractionAgent._AGENT_FILE_PREFIX (steps 01-14)
# Quality agents: steps 15-18, Support agents: steps 19-20
QUALITY_SUPPORT_FILE_PREFIX = {
    "postprocessing_agent": "15_quality_postprocessing",
    "reconciliation_agent": "16_quality_reconciliation",
    "validation_agent": "17_quality_validation",
    "enrichment_agent": "18_quality_enrichment",
    "usdm-generator": "19_support_usdm_generator",
    "provenance": "20_support_provenance",
}


@dataclass
class PipelineConfig:
    """Configuration for the extraction pipeline."""
    model: str = "gemini-2.5-pro"
    output_dir: str = "output"
    checkpoints_dir: str = "checkpoints"
    max_workers: int = 4
    dpi: int = 100
    enable_vision: bool = True
    enable_enrichment: bool = True
    enable_checkpoints: bool = True
    skip_agents: List[str] = field(default_factory=list)
    fast_model: Optional[str] = None  # Faster model for less-critical agents (narrative, docstructure)
    vision_model: Optional[str] = None  # Model for SoA vision extraction (default: same as model)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "fast_model": self.fast_model,
            "vision_model": self.vision_model,
            "output_dir": self.output_dir,
            "checkpoints_dir": self.checkpoints_dir,
            "max_workers": self.max_workers,
            "dpi": self.dpi,
            "enable_vision": self.enable_vision,
            "enable_enrichment": self.enable_enrichment,
            "enable_checkpoints": self.enable_checkpoints,
            "skip_agents": self.skip_agents,
        }


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""
    execution_id: str = ""
    protocol_id: str = ""
    success: bool = False
    usdm_path: Optional[str] = None
    provenance_path: Optional[str] = None
    entity_count: int = 0
    agent_results: Dict[str, bool] = field(default_factory=dict)
    failed_agents: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    wave_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "protocol_id": self.protocol_id,
            "success": self.success,
            "usdm_path": self.usdm_path,
            "provenance_path": self.provenance_path,
            "entity_count": self.entity_count,
            "agent_results": self.agent_results,
            "failed_agents": self.failed_agents,
            "execution_time_ms": self.execution_time_ms,
            "wave_count": self.wave_count,
        }


def create_all_agents(config: Optional[PipelineConfig] = None) -> List[BaseAgent]:
    """
    Create instances of all agents in the pipeline.

    Returns a list of initialized agent instances ready for registration.
    """
    cfg = config or PipelineConfig()
    agents: List[BaseAgent] = []

    # Support: PDF Parser
    from agents.support.pdf_parser_agent import PDFParserAgent
    agents.append(PDFParserAgent(config={"dpi": cfg.dpi}))

    # Extraction agents
    from agents.extraction.metadata_agent import MetadataAgent
    from agents.extraction.eligibility_agent import EligibilityAgent
    from agents.extraction.objectives_agent import ObjectivesAgent
    from agents.extraction.studydesign_agent import StudyDesignAgent
    from agents.extraction.interventions_agent import InterventionsAgent
    from agents.extraction.procedures_agent import ProceduresAgent
    from agents.extraction.scheduling_agent import SchedulingAgent
    from agents.extraction.execution_agent import ExecutionAgent
    from agents.extraction.narrative_agent import NarrativeAgent
    from agents.extraction.advanced_agent import AdvancedAgent
    from agents.extraction.docstructure_agent import DocStructureAgent
    from agents.extraction.biomedical_concept_agent import BiomedicalConceptAgent

    agent_config = {"model": cfg.model}
    fast_agent_config = {"model": cfg.fast_model} if cfg.fast_model else agent_config
    vision_agent_config = {"model": cfg.vision_model} if cfg.vision_model else agent_config
    agents.extend([
        MetadataAgent(config=fast_agent_config),  # Use fast model - metadata extraction is straightforward
        EligibilityAgent(config=fast_agent_config),  # Use fast model - eligibility criteria extraction
        ObjectivesAgent(config=fast_agent_config),  # Use fast model - objectives and endpoints extraction
        StudyDesignAgent(config=fast_agent_config),  # Use fast model - study design extraction
        InterventionsAgent(config=fast_agent_config),  # Use fast model - interventions extraction
        ProceduresAgent(config=fast_agent_config),  # Use fast model - procedures/devices extraction
        SchedulingAgent(config=agent_config),  # Use main model - complex JSON structure requires reliable parsing
        ExecutionAgent(config=fast_agent_config),  # Use fast model - execution model extraction
        NarrativeAgent(config=fast_agent_config),
        AdvancedAgent(config=fast_agent_config),  # Use fast model - amendments/countries/sites extraction
        DocStructureAgent(config=fast_agent_config),
        BiomedicalConceptAgent(config=fast_agent_config),  # Use fast model - biomedical concepts extraction
    ])

    if cfg.enable_vision:
        from agents.extraction.soa_vision_agent import SoAVisionAgent
        from agents.extraction.soa_text_agent import SoATextAgent
        agents.extend([
            SoAVisionAgent(config=vision_agent_config),
            SoATextAgent(config=fast_agent_config),  # Use fast model - table cell extraction is straightforward once structure is known
        ])

    # Quality agents
    from agents.quality.validation_agent import ValidationAgent
    from agents.quality.reconciliation_agent import ReconciliationAgent
    from agents.quality.postprocessing_agent import SoAPostProcessingAgent
    agents.extend([
        SoAPostProcessingAgent(),
        ValidationAgent(),
        ReconciliationAgent(),
    ])

    if cfg.enable_enrichment:
        from agents.quality.enrichment_agent import EnrichmentAgent
        agents.append(EnrichmentAgent())

    # Support: USDM Generator, Provenance
    from agents.support.usdm_generator_agent import USDMGeneratorAgent
    from agents.support.provenance_agent import ProvenanceAgent
    agents.extend([
        USDMGeneratorAgent(),
        ProvenanceAgent(),
    ])

    # Filter out skipped agents
    if cfg.skip_agents:
        agents = [a for a in agents if a.agent_id not in cfg.skip_agents]

    return agents


class ExtractionPipeline:
    """
    High-level pipeline for running the full extraction workflow.

    Usage:
        pipeline = ExtractionPipeline(config)
        pipeline.initialize()
        result = pipeline.run("path/to/protocol.pdf")
        pipeline.shutdown()
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._orchestrator: Optional[OrchestratorAgent] = None
        self._context_store: Optional[ContextStore] = None
        self._initialized = False

    @property
    def orchestrator(self) -> Optional[OrchestratorAgent]:
        return self._orchestrator

    @property
    def context_store(self) -> Optional[ContextStore]:
        return self._context_store

    def initialize(self) -> Dict[str, bool]:
        """
        Initialize the pipeline: create agents, register with orchestrator.

        Returns dict of agent_id → initialization success.
        """
        self._context_store = ContextStore()
        mq = MessageQueue()

        self._orchestrator = OrchestratorAgent(
            config={
                "max_workers": self.config.max_workers,
                "checkpoints_dir": self.config.checkpoints_dir,
            }
        )
        self._orchestrator.context_store = self._context_store
        self._orchestrator.initialize()

        # Create and register all agents
        agents = create_all_agents(self.config)
        for agent in agents:
            agent.set_context_store(self._context_store)
            agent.set_message_queue(mq)
            self._orchestrator.register_agent(agent)

        # Initialize all agents
        results = self._orchestrator.registry.initialize_all()
        self._initialized = True

        logger.info(f"Pipeline initialized: {len(agents)} agents registered")
        return results

    def run(self, pdf_path: str, protocol_id: str = "") -> PipelineResult:
        """
        Run the full extraction pipeline on a PDF.

        Args:
            pdf_path: Path to the protocol PDF
            protocol_id: Optional protocol identifier

        Returns:
            PipelineResult with USDM and provenance paths
        """
        if not self._initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        if not protocol_id:
            protocol_id = os.path.splitext(os.path.basename(pdf_path))[0]

        start_time = datetime.now()
        result = PipelineResult(protocol_id=protocol_id)

        # Create timestamped output directory
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.config.output_dir, f"{protocol_id}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)

        # Copy protocol PDF to output directory for frontend access
        try:
            import shutil
            pdf_filename = os.path.basename(pdf_path)
            pdf_dest = os.path.join(output_dir, pdf_filename)
            shutil.copy2(pdf_path, pdf_dest)
            logger.info(f"Copied protocol PDF to {pdf_dest}")
        except Exception as e:
            logger.warning(f"Failed to copy protocol PDF to output directory: {e}")

        # Create and execute plan
        plan = self._orchestrator.create_execution_plan(protocol_id=protocol_id)

        # Inject pdf_path and output_dir into all tasks
        for wave in plan.waves:
            for task in wave.tasks:
                task.input_data["pdf_path"] = pdf_path
                task.input_data["output_dir"] = output_dir
                task.input_data["model"] = self.config.model

        status = self._orchestrator.execute_plan(plan)

        # Collect results
        result.execution_id = status.execution_id
        result.wave_count = len(plan.waves)
        for agent_id, agent_result in status.results.items():
            result.agent_results[agent_id] = agent_result.success
            if not agent_result.success:
                result.failed_agents.append(agent_id)

        # Save quality/support agent outputs
        self._save_quality_support_outputs(status, output_dir)

        result.entity_count = self._context_store.entity_count
        result.success = status.state == "completed"

        # Generate USDM output
        usdm_path = os.path.join(output_dir, f"{protocol_id}_usdm.json")
        prov_path = os.path.join(output_dir, f"{protocol_id}_provenance.json")

        usdm_agent = self._orchestrator.registry.get("usdm-generator")
        if usdm_agent:
            usdm_task = AgentTask(
                task_id=f"{protocol_id}_usdm_final",
                agent_id="usdm-generator",
                task_type="usdm_generate",
                input_data={"output_path": usdm_path},
            )
            usdm_result = usdm_agent.execute(usdm_task)
            if usdm_result.success:
                result.usdm_path = usdm_path

        prov_agent = self._orchestrator.registry.get("provenance")
        if prov_agent:
            prov_task = AgentTask(
                task_id=f"{protocol_id}_prov_final",
                agent_id="provenance",
                task_type="provenance_generate",
                input_data={"output_path": prov_path},
            )
            prov_result = prov_agent.execute(prov_task)
            if prov_result.success:
                result.provenance_path = prov_path

        # Run CDISC CORE engine validation on the final USDM JSON
        if result.usdm_path and os.path.exists(result.usdm_path):
            self._run_core_engine_validation(result.usdm_path, output_dir)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result.execution_time_ms = elapsed

        # Generate result.md summary
        self._generate_result_md(result, status, plan, output_dir, pdf_path, start_time)

        logger.info(
            f"Pipeline complete: {protocol_id} - "
            f"{'SUCCESS' if result.success else 'FAILED'} - "
            f"{result.entity_count} entities - "
            f"{elapsed:.0f}ms")

        return result

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get the agent dependency graph."""
        if not self._orchestrator:
            return {}
        graph = self._orchestrator.build_dependency_graph()
        return {k: sorted(v) for k, v in graph.items()}

    def get_agent_count(self) -> int:
        """Get the number of registered agents."""
        if not self._orchestrator:
            return 0
        return self._orchestrator.registry.count

    def shutdown(self) -> None:
        """Shutdown the pipeline and terminate all agents."""
        if self._orchestrator:
            self._orchestrator.registry.terminate_all()
            self._orchestrator.terminate()
        self._initialized = False
        logger.info("Pipeline shutdown complete")

    # --- Output helpers ---

    def _save_quality_support_outputs(
        self, status: ExecutionStatus, output_dir: str
    ) -> None:
        """Save JSON output files for quality and support agents."""
        for agent_id, agent_result in status.results.items():
            prefix = QUALITY_SUPPORT_FILE_PREFIX.get(agent_id)
            if not prefix:
                continue
            filename = f"{prefix}.json"
            output_path = os.path.join(output_dir, filename)
            output = {
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
                "success": agent_result.success,
                "data": agent_result.data or {},
                "error": agent_result.error,
                "confidence": agent_result.confidence_score,
            }
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False, default=str)
                logger.debug(f"Saved quality/support output: {filename}")
            except Exception as e:
                logger.warning(f"Failed to save {filename}: {e}")

    def _run_core_engine_validation(self, usdm_json_path: str, output_dir: str) -> None:
        """Run CDISC CORE engine validation on the final USDM JSON file."""
        from agents.quality.validation_agent import CDISCCOREChecker
        import json
        try:
            checker = CDISCCOREChecker()
            report = checker.run_core_engine(usdm_json_path, output_dir)
            if report:
                issues = checker._parse_core_engine_report(report)
                errors = sum(1 for i in issues if i.severity.value == "error")
                warnings = sum(1 for i in issues if i.severity.value == "warning")
                infos = sum(1 for i in issues if i.severity.value == "info")
                logger.info(
                    f"CDISC CORE engine: {len(issues)} issues "
                    f"({errors} errors, {warnings} warnings, {infos} info)"
                )
                
                # Save conformance report in UI-friendly format
                conformance_report = {
                    "success": True,
                    "engine": "CDISC CORE v0.14.1",
                    "issues": errors,
                    "warnings": warnings,
                    "issues_list": [
                        {
                            "rule_id": i.field_name or "unknown",
                            "severity": i.severity.value.title(),
                            "message": i.message,
                            "dataset": i.entity_type if i.entity_type != "unknown" else None,
                            "variable": i.entity_id if i.entity_id != "unknown" else None,
                        }
                        for i in issues
                    ]
                }
                
                # Save to conformance_report.json
                conformance_path = os.path.join(output_dir, "conformance_report.json")
                with open(conformance_path, 'w', encoding='utf-8') as f:
                    json.dump(conformance_report, f, indent=2)
                logger.info(f"Saved conformance report to {conformance_path}")
            else:
                logger.info("CDISC CORE engine not available or produced no output")
                # Save a report indicating CORE engine not available
                conformance_report = {
                    "success": False,
                    "engine": "CDISC CORE",
                    "error": "CDISC CORE engine not installed",
                    "error_summary": "The CDISC CORE validation engine is not available. Install it to enable conformance checking.",
                }
                conformance_path = os.path.join(output_dir, "conformance_report.json")
                with open(conformance_path, 'w', encoding='utf-8') as f:
                    json.dump(conformance_report, f, indent=2)
        except Exception as e:
            logger.warning(f"CDISC CORE engine validation failed: {e}")
            # Save error report
            conformance_report = {
                "success": False,
                "engine": "CDISC CORE",
                "error": "Validation failed",
                "error_summary": str(e),
                "error_details": str(e)
            }
            conformance_path = os.path.join(output_dir, "conformance_report.json")
            try:
                with open(conformance_path, 'w', encoding='utf-8') as f:
                    json.dump(conformance_report, f, indent=2)
            except:
                pass


    def _generate_result_md(
        self,
        result: PipelineResult,
        status: ExecutionStatus,
        plan: ExecutionPlan,
        output_dir: str,
        pdf_path: str,
        start_time: datetime,
    ) -> None:
        """Generate a result.md summary file in the output directory."""
        from agents.extraction.base_extraction_agent import BaseExtractionAgent

        end_time = datetime.now()
        lines: List[str] = []

        # Build file prefix lookup (extraction + quality/support)
        all_prefixes = dict(BaseExtractionAgent._AGENT_FILE_PREFIX)
        all_prefixes.update(QUALITY_SUPPORT_FILE_PREFIX)

        # Compute totals
        total_tokens = sum(r.tokens_used for r in status.results.values())
        total_api_calls = sum(r.api_calls for r in status.results.values())
        total_agents = len(status.results)
        succeeded = sum(1 for r in status.results.values() if r.success)
        failed = total_agents - succeeded

        # Header
        lines.append(f"# Pipeline Result: {result.protocol_id}")
        lines.append("")
        lines.append(f"**Status:** {'SUCCESS' if result.success else 'FAILED'}")
        lines.append(f"**PDF:** `{os.path.basename(pdf_path)}`")
        lines.append(f"**Model:** {self.config.model}")
        lines.append(f"**Started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Finished:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Duration:** {result.execution_time_ms / 1000:.1f}s")
        lines.append(f"**Entities:** {result.entity_count}")
        lines.append(f"**Waves:** {result.wave_count}")
        lines.append("")

        # Overall statistics
        lines.append("## Statistics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Agents | {total_agents} |")
        lines.append(f"| Succeeded | {succeeded} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Entities | {result.entity_count} |")
        lines.append(f"| Total Tokens | {total_tokens:,} |")
        lines.append(f"| Total API Calls | {total_api_calls} |")
        lines.append(f"| Total Duration | {result.execution_time_ms / 1000:.1f}s |")
        lines.append("")

        # Execution flow diagram
        lines.append("## Execution Flow")
        lines.append("")
        lines.append("```")

        for wave in plan.waves:
            agent_ids = [t.agent_id for t in wave.tasks]
            # Compute wave time (max of parallel agents)
            wave_times = []
            for aid in agent_ids:
                ar = status.results.get(aid)
                if ar:
                    wave_times.append(ar.execution_time_ms)
            wave_time = max(wave_times) if wave_times else 0
            lines.append(f"Wave {wave.wave_number}  ({wave_time / 1000:.1f}s)")
            for aid in sorted(agent_ids):
                ar = status.results.get(aid)
                icon = "OK" if (ar and ar.success) else "FAIL"
                prefix = all_prefixes.get(aid, "")
                out_file = f"{prefix}.json" if prefix else ""
                t = f"{ar.execution_time_ms / 1000:.1f}s" if ar else "?"
                line = f"  [{icon}] {aid} ({t})"
                if out_file:
                    line += f"  ->  {out_file}"
                lines.append(line)
            lines.append("  |")

        # Final outputs
        lines.append("Output")
        if result.usdm_path:
            lines.append(f"  [OK] {os.path.basename(result.usdm_path)}")
        if result.provenance_path:
            lines.append(f"  [OK] {os.path.basename(result.provenance_path)}")
        lines.append("```")
        lines.append("")

        # Build per-agent page sets from context store provenance
        agent_pages: Dict[str, set] = {}
        if self._context_store:
            for entity in self._context_store._entities.values():
                aid_prov = entity.provenance.source_agent_id
                pages = entity.provenance.source_pages
                if aid_prov and pages:
                    if aid_prov not in agent_pages:
                        agent_pages[aid_prov] = set()
                    agent_pages[aid_prov].update(pages)

        def _fmt_pages(aid: str) -> str:
            pages = sorted(agent_pages.get(aid, set()))
            if not pages:
                return ""
            # Compact range notation: 1,2,3,5,6 -> 1-3,5-6
            ranges = []
            start = end = pages[0]
            for p in pages[1:]:
                if p == end + 1:
                    end = p
                else:
                    ranges.append(str(start) if start == end else f"{start}-{end}")
                    start = end = p
            ranges.append(str(start) if start == end else f"{start}-{end}")
            return ",".join(ranges)

        # Agent results table with time and tokens
        lines.append("## Agent Results")
        lines.append("")
        lines.append("| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |")
        lines.append("|------|-------|----------|--------|----------|--------|-----------|-------|-------------|")

        for aid in sorted(all_prefixes.keys(), key=lambda x: all_prefixes.get(x, "")):
            prefix = all_prefixes.get(aid, "")
            step = prefix.split("_")[0] if prefix else ""
            category = prefix.split("_")[1] if prefix and "_" in prefix else ""
            ar = status.results.get(aid)
            if ar is None:
                continue
            stat = "OK" if ar.success else "FAIL"
            t = f"{ar.execution_time_ms / 1000:.1f}"
            tokens = f"{ar.tokens_used:,}" if ar.tokens_used else "0"
            api = str(ar.api_calls) if ar.api_calls else "0"
            pages_str = _fmt_pages(aid)
            out_file = f"`{prefix}.json`" if prefix else ""
            lines.append(f"| {step} | {aid} | {category} | {stat} | {t} | {tokens} | {api} | {pages_str} | {out_file} |")

        # Include pdf-parser if it ran
        pdf_parser_result = status.results.get("pdf-parser")
        if pdf_parser_result:
            stat = "OK" if pdf_parser_result.success else "FAIL"
            t = f"{pdf_parser_result.execution_time_ms / 1000:.1f}"
            lines.append(f"| 00 | pdf-parser | support | {stat} | {t} | 0 | 0 | | |")

        lines.append("")

        # Failed agents
        if result.failed_agents:
            lines.append("## Failed Agents")
            lines.append("")
            for aid in result.failed_agents:
                ar = status.results.get(aid)
                error = ar.error if ar else "unknown"
                lines.append(f"- **{aid}**: {error}")
            lines.append("")

        # Output files
        lines.append("## Output Files")
        lines.append("")
        try:
            for f in sorted(os.listdir(output_dir)):
                if f == "result.md":
                    continue
                lines.append(f"- `{f}`")
        except Exception:
            pass
        lines.append("")

        # Write result.md
        result_path = os.path.join(output_dir, "result.md")
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info(f"Result summary: {result_path}")
        except Exception as e:
            logger.warning(f"Failed to write result.md: {e}")

