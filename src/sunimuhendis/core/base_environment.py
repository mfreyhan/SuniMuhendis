import re
import statistics
from abc import ABC, abstractmethod
from collections import Counter
from typing import Dict, Any, List, Optional, Sequence
from .types import AuditReport, EvaluationResult, Requirement, ScoreResult
from .base_simulator import BaseSimulator
from .base_score import BaseScoreFunction

class BaseEnvironment(ABC):
    """
    Main environment class combining the simulator, reward function, and DRC validation.
    """
    
    def __init__(self, simulator: BaseSimulator, score_function: BaseScoreFunction):
        self.simulator = simulator
        self.score_function = score_function
        
    @abstractmethod
    def validate_schema(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Checks the structural/schema validity of the incoming design.
        E.g., validation via Pydantic model.
        """
        pass
        
    @abstractmethod
    def run_drc(self, design_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Design Rule Check (DRC). Checks physical/logical constraints.
        """
        pass

    def get_score_function(self, task_params: Dict[str, Any]) -> BaseScoreFunction:
        """
        Returns the score function to be used for the current task.
        By default, returns the environment's default score function.
        Subclasses can override this to support dynamic score functions based on task_params.
        """
        return self.score_function

    # ─────────────────────────────────────────────────────────────────
    #  Task feasibility audit — hooks each environment fills
    # ─────────────────────────────────────────────────────────────────
    #
    # ``audit_task`` below is the shared algorithm; the four hooks here are
    # the environment-specific parts. An environment that implements
    # ``sample_designs`` and ``get_requirements`` gets the whole audit. The
    # other two hooks sharpen it but are optional.
    #
    # These are deliberately NOT abstract: existing environments (and the
    # dummy ones in tests and scripts) keep working, and ``audit_task``
    # fails with a message naming exactly what is missing.

    def sample_designs(self, num_samples: int, seed: int = 0) -> List[Dict[str, Any]]:
        """
        Produce ``num_samples`` candidate designs spanning this environment's
        design space. Must be deterministic for a given ``seed``.

        The sampler should cover the space broadly rather than aim for good
        designs: the audit asks what the task makes *possible*, so a biased
        sampler hides exactly the walls it is meant to find.
        """
        raise NotImplementedError(
            "{} does not implement sample_designs(); it cannot be audited. "
            "Implement it to return a deterministic list of candidate designs."
            .format(type(self).__name__)
        )

    def get_requirements(self, task_params: Dict[str, Any]) -> List[Requirement]:
        """
        The hard requirements this task imposes — what a design must meet to
        count as solving the task, as opposed to merely scoring well.
        """
        raise NotImplementedError(
            "{} does not implement get_requirements(); it cannot be audited. "
            "Implement it to translate task_params into a list of Requirement."
            .format(type(self).__name__)
        )

    def list_design_checks(self) -> Sequence[str]:
        """
        Every design check this environment is capable of raising, as stable
        labels. Optional: supplying it lets the audit report *dead* checks —
        rules that can never fire and so silently protect nothing.
        """
        return ()

    def analyse_physics(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Environment-specific closed-form analysis of the task, for limits that
        sampling cannot prove. A heat exchanger reports its ε-NTU ceiling here;
        an airframe environment would report something else entirely.

        Anything returned lands in ``AuditReport.physics``. Keys whose name
        starts with ``CRITICAL`` or ``WARNING`` are also promoted into
        ``AuditReport.findings``.
        """
        return {}

    @staticmethod
    def normalise_warning(warning: str) -> str:
        """
        Collapse a warning into a stable label so occurrences can be counted.
        By default strips embedded numbers, so 'Tube velocity 0.13 m/s < min
        0.5 m/s' and 'Tube velocity 0.31 m/s < min 0.5 m/s' become one label.
        """
        return re.sub(r"[-+]?\d*\.?\d+", "#", warning).strip()

    def extract_warnings(self, metrics: Dict[str, Any], raw_output: Dict[str, Any]) -> List[str]:
        """
        Pull the design warnings out of one simulation result. The default
        reads ``raw_output['warnings']``; override if a simulator reports them
        elsewhere.
        """
        warnings = raw_output.get("warnings", [])
        if not isinstance(warnings, (list, tuple)):
            return []
        return [str(w) for w in warnings]

    # ─────────────────────────────────────────────────────────────────
    #  Task feasibility audit — the shared algorithm
    # ─────────────────────────────────────────────────────────────────

    def audit_task(
        self,
        task_params: Dict[str, Any],
        num_samples: int = 20000,
        seed: int = 0,
    ) -> AuditReport:
        """
        Audit a task configuration for feasibility before spending any model
        calls on it.

        Answers four questions a task must survive to measure anything:

        1. Is the task reachable at all — does any design meet every requirement?
        2. Is any penalty unavoidable — does every feasible design carry the
           same warning? Such a penalty is a constant tax, not feedback.
        3. Where does the reward actually live — is producing *some* valid
           design worth more than producing a good one?
        4. Do the declared design checks ever fire, or are some of them dead?

        Requires ``sample_designs`` and ``get_requirements``.
        """
        task_id = str(task_params.get("task_id", "audit"))
        designs = self.sample_designs(num_samples, seed)
        requirements = self.get_requirements(task_params)

        best_score = None
        feasible_scores: List[float] = []
        feasible_warning_sets: List[frozenset] = []
        feasible_warning_counts: List[int] = []
        warning_counter: Counter = Counter()
        requirement_hits: Counter = Counter()
        simulated = 0

        for index, design in enumerate(designs):
            result = self.evaluate(task_id, task_params, "audit-{}".format(index), design)
            score = result.score.normalized_total
            if best_score is None or score > best_score:
                best_score = score
            if result.status != "success":
                continue

            simulated += 1
            labels = {self.normalise_warning(w)
                      for w in self.extract_warnings(result.metrics, result.raw_simulation_output)}
            for label in labels:
                warning_counter[label] += 1

            met_all = True
            for requirement in requirements:
                if requirement.satisfied_by(result.metrics):
                    requirement_hits[requirement.name] += 1
                else:
                    met_all = False
            if met_all:
                feasible_scores.append(score)
                feasible_warning_sets.append(frozenset(labels))
                feasible_warning_counts.append(len(labels))

        report = AuditReport(
            environment=type(self).__name__,
            task_id=task_id,
            samples_requested=len(designs),
            samples_simulated=simulated,
            feasible_count=len(feasible_scores),
            requirements=requirements,
            score_ceiling=best_score,
        )

        if simulated:
            report.requirement_satisfaction = {
                r.name: requirement_hits[r.name] / simulated for r in requirements
            }
            report.warning_frequency = {
                label: count / simulated for label, count in warning_counter.most_common()
            }
            declared = list(self.list_design_checks())
            if declared:
                fired = set(warning_counter)
                report.dead_checks = [
                    check for check in declared
                    if not any(check.lower() in label.lower() for label in fired)
                ]

        if feasible_scores:
            report.feasible_score_floor = min(feasible_scores)
            report.feasible_score_median = statistics.median(feasible_scores)
            report.min_warning_count = min(feasible_warning_counts)
            forced = frozenset.intersection(*feasible_warning_sets)
            report.forced_warnings = sorted(forced)
            report.entry_reward = report.feasible_score_floor
            if best_score is not None:
                report.craft_reward = best_score - report.feasible_score_floor

        report.physics = self.analyse_physics(task_params)
        report.findings = self._derive_findings(report)
        return report

    @staticmethod
    def _derive_findings(report: AuditReport) -> List[str]:
        """Turn the measured audit numbers into ranked, readable findings."""
        findings: List[str] = []

        if report.samples_simulated == 0:
            findings.append(
                "CRITICAL: no sampled design simulated successfully — the sampler and the "
                "environment disagree about the design space."
            )
            return findings

        if report.feasible_count == 0:
            unmet = sorted(report.requirement_satisfaction.items(), key=lambda kv: kv[1])
            findings.append(
                "CRITICAL: no sampled design meets every requirement — the task may be "
                "unreachable. Hardest requirement: '{}' met by {:.2%} of designs.".format(
                    unmet[0][0], unmet[0][1]) if unmet else
                "CRITICAL: no sampled design meets every requirement."
            )

        if report.forced_warnings:
            findings.append(
                "CRITICAL: {} warning(s) fire for EVERY feasible design ({}). This is a constant "
                "penalty no design can avoid, so it carries no information and only shrinks the "
                "usable score range.".format(
                    len(report.forced_warnings), "; ".join(report.forced_warnings))
            )

        if report.entry_reward is not None and report.craft_reward is not None:
            if report.craft_reward <= 0:
                findings.append(
                    "CRITICAL: the best design observed scores no better than the worst feasible "
                    "one — the score cannot rank designs that solve the task."
                )
            elif report.entry_reward > report.craft_reward:
                findings.append(
                    "WARNING: reward budget favours showing up over engineering — reaching any "
                    "feasible design is worth +{:.3f} while perfecting it is worth only +{:.3f}. "
                    "Iterative improvement has little room to show.".format(
                        report.entry_reward, report.craft_reward)
                )

        if report.min_warning_count:
            findings.append(
                "INFO: the fewest warnings any feasible design achieved is {} — a warning-free "
                "design may be out of reach.".format(report.min_warning_count)
            )

        if report.dead_checks:
            findings.append(
                "INFO: {} declared design check(s) never fired across the sample ({}). They "
                "protect nothing as configured.".format(
                    len(report.dead_checks), "; ".join(report.dead_checks))
            )

        for key, value in report.physics.items():
            if key.startswith("CRITICAL") or key.startswith("WARNING"):
                findings.append("{}: {}".format(key, value))

        severities = ("CRITICAL", "WARNING", "INFO")

        def rank(finding: str) -> int:
            for level, prefix in enumerate(severities):
                if finding.startswith(prefix):
                    return level
            return len(severities)

        findings.sort(key=rank)
        return findings
        
    def evaluate(self, task_id: str, task_params: Dict[str, Any], design_id: str, design_params: Dict[str, Any]) -> EvaluationResult:
        """
        Main evaluation loop.
        """
        score_fn = self.get_score_function(task_params)
        
        # 1. Schema Validation
        schema_valid, schema_err = self.validate_schema(design_params)
        if not schema_valid:
            score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=schema_err)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="schema_error",
                score=score,
                error_message=schema_err
            )
            
        # 2. DRC Validation
        drc_valid, drc_err = self.run_drc(design_params)
        if not drc_valid:
            score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=drc_err)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="drc_error",
                score=score,
                error_message=drc_err
            )
            
        # 3. Simulation
        try:
            success, metrics, raw_data, sim_err = self.simulator.simulate(design_params)
            
            if not success:
                score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=sim_err)
                return EvaluationResult(
                    task_id=task_id,
                    design_id=design_id,
                    status="simulation_error",
                    score=score,
                    error_message=sim_err
                )
                
            # 4. Score Calculation (Success case)
            score = score_fn.calculate_score(task_params, metrics, is_valid=True)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="success",
                score=score,
                metrics=metrics,
                raw_simulation_output=raw_data
            )
            
        except Exception as e:
            # Catch unexpected simulator crashes
            error_msg = f"Unexpected simulation crash: {str(e)}"
            score = score_fn.calculate_score(task_params, {}, is_valid=False, error_message=error_msg)
            return EvaluationResult(
                task_id=task_id,
                design_id=design_id,
                status="simulation_error",
                score=score,
                error_message=error_msg
            )
