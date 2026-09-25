import glob
import html
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# The spend ledger is plain stdlib so the CLI report and this dashboard share
# one costing implementation. Streamlit runs this file as a script, so its own
# directory is importable; the package path is the fallback for pytest.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import token_ledger
except ImportError:  # pragma: no cover - only hit from an unusual import root
    from scripts import token_ledger


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "results"
RUN_SOURCES = ("api_runs", "manual_runs")
SOURCE_LABELS = {"api_runs": "API", "manual_runs": "Manual"}
EXPERIMENT_TRACKS = ("zero_shot", "feedback_driven")
TRACK_LABELS = {
    "zero_shot": "Zero-shot",
    "feedback_driven": "Feedback-driven",
}
STATUS_COLORS = {
    "success": "#16a34a",
    "drc_error": "#f59e0b",
    "schema_error": "#f97316",
    "simulation_error": "#dc2626",
    "parse_error": "#7c3aed",
    "empty_response": "#64748b",
    "client_error": "#be123c",
    "unknown": "#94a3b8",
}
STATUS_LABELS = {
    "success": "Success",
    "drc_error": "DRC error",
    "schema_error": "Schema error",
    "simulation_error": "Simulation error",
    "parse_error": "Parse error",
    "empty_response": "Empty response",
    "client_error": "Client error",
    "unknown": "Unknown",
}
PLOT_COLORS = [
    "#2563eb", "#7c3aed", "#0891b2", "#16a34a", "#ea580c",
    "#db2777", "#4f46e5", "#0f766e", "#ca8a04", "#9333ea",
]
COMPLEX_COLUMNS = {
    "raw_record", "design_json", "metrics_json", "reward_components_json",
    "task_params_json", "weights_json", "prompt_text", "raw_response",
    "requested_params_json", "inference_params_json", "effective_params_json",
    "model_metadata_json", "parameter_adjustments_json",
}


# Missing aggregate values must stay numeric NaN. Python ``None`` in a numeric
# column breaks every downstream formatter and sorter.
NA = float("nan")

# Numeric display formats for the leaderboard and other summary tables. These
# are printf patterns understood by ``st.column_config.NumberColumn``, which
# renders missing values as blanks instead of raising like a pandas Styler does.
TABLE_FORMATS: Dict[str, str] = {
    "Valid design %": "%.1f%%",
    "Requirements met %": "%.1f%%",
    "JSON %": "%.1f%%",
    "Empty response %": "%.1f%%",
    "Client error %": "%.1f%%",
    "Mean score": "%.3f",
    "Median score": "%.3f",
    "Successful score": "%.3f",
    "Best score": "%.3f",
    "Score std": "%.3f",
    "P50 latency (s)": "%.1f",
    "P95 latency (s)": "%.1f",
    "Mean output tokens": "%.0f",
    "Estimated cost ($)": "$%.5f",
    "Estimated total cost": "$%.5f",
    "Mean cost per run": "$%.5f",
    "Mean heat duty (kW)": "%.1f",
    "Mean annual cost ($/y)": "$%.0f",
    "Mean warnings": "%.2f",
}


def _table_column_config(df: pd.DataFrame) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    for column in df.columns:
        fmt = TABLE_FORMATS.get(str(column))
        if fmt is not None:
            config[column] = st.column_config.NumberColumn(str(column), format=fmt)
    return config


def _render_table(
    df: pd.DataFrame,
    column_config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    """Render a summary table with safe numeric formatting and sortable columns."""
    config = _table_column_config(df)
    config.update(column_config or {})
    return st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config=config,
        **kwargs,
    )


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _first_number(mapping: Dict[str, Any], keys: Sequence[str]) -> Optional[float]:
    for key in keys:
        value = _number(mapping.get(key))
        if value is not None:
            return value
    return None


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _estimated_cost(
    prompt_tokens: Optional[float],
    completion_tokens: Optional[float],
    pricing: Dict[str, Any],
) -> Optional[float]:
    prompt_rate = _number(pricing.get("prompt"))
    completion_rate = _number(pricing.get("completion"))
    if (
        prompt_tokens is None
        or completion_tokens is None
        or prompt_rate is None
        or completion_rate is None
    ):
        return None
    return prompt_tokens * prompt_rate + completion_tokens * completion_rate


def _reasoning_label(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return "Not specified"
    return str(value)


def _status_label(value: Any) -> str:
    status = str(value or "unknown")
    return STATUS_LABELS.get(status, status.replace("_", " ").title())


def _track_label(value: Any) -> str:
    track = str(value or "zero_shot")
    return TRACK_LABELS.get(track, track.replace("_", " ").title())


MAX_LABEL_CHARS = 26


def _truncate_label(text: str, limit: int = MAX_LABEL_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip("-_. ") + "…"


def _model_label_map(models: Sequence[str]) -> Dict[str, str]:
    """Build short, unique chart labels for model names.

    Full model names run up to ~40 characters, which squeezes plots and legends
    until they are unreadable. The reasoning variant is kept as a short suffix
    (it is what distinguishes two runs of the same model) and only the base name
    is truncated. The full name always stays in the hover text and in tables.
    """
    unique = sorted({str(model) for model in models})
    labels: Dict[str, str] = {}
    for model in unique:
        base, _, variant = model.partition("__reasoning-")
        suffix = f" ·{variant}" if variant else ""
        labels[model] = _truncate_label(base, MAX_LABEL_CHARS - len(suffix)) + suffix

    # Truncation can make two different models share a label; those fall back
    # to their full names rather than being silently merged in a chart.
    seen: Dict[str, str] = {}
    for model in unique:
        label = labels[model]
        if label in seen:
            labels[model] = model
            labels[seen[label]] = seen[label]
        else:
            seen[label] = model
    return labels


def _with_model_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy carrying a chart-friendly ``model_label`` column."""
    out = df.copy()
    if out.empty:
        out["model_label"] = []
        return out
    labels = _model_label_map(out["model"].astype(str).tolist())
    out["model_label"] = out["model"].astype(str).map(labels)
    return out


def _model_axis_height(count: int, per_row: int = 34, minimum: int = 360) -> int:
    """Charts with one row per model must grow instead of squashing rows."""
    return max(minimum, 120 + per_row * max(count, 1))


def flatten_record(
    record: Dict[str, Any],
    run_type: str,
    prompt: str,
    source_path: str = "",
    line_number: int = 0,
    experiment_track: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize current and legacy benchmark records without hiding raw data."""
    metrics = _as_dict(record.get("metrics"))
    design = _as_dict(record.get("design"))
    rewards = _as_dict(record.get("reward_components"))
    task = _as_dict(record.get("task_params"))
    metadata = _as_dict(record.get("model_metadata"))
    pricing = _as_dict(metadata.get("pricing"))

    heat_w = _first_number(metrics, ("heat_duty_W", "heat_duty"))
    if heat_w is None:
        heat_kw = _first_number(metrics, ("heat_duty_kW",))
        heat_w = heat_kw * 1000.0 if heat_kw is not None else None

    dp_tube_pa = _first_number(metrics, ("dp_tube_Pa",))
    if dp_tube_pa is None:
        dp_tube_kpa = _first_number(metrics, ("dp_tube_kPa",))
        dp_tube_pa = dp_tube_kpa * 1000.0 if dp_tube_kpa is not None else None

    dp_shell_pa = _first_number(metrics, ("dp_shell_Pa",))
    if dp_shell_pa is None:
        dp_shell_kpa = _first_number(metrics, ("dp_shell_kPa",))
        dp_shell_pa = dp_shell_kpa * 1000.0 if dp_shell_kpa is not None else None

    effectiveness = _first_number(metrics, ("effectiveness",))
    prompt_tokens = _number(record.get("prompt_tokens"))
    completion_tokens = _number(record.get("completion_tokens"))
    latency_ms = _number(record.get("latency_ms"))
    target_heat_w = _number(task.get("target_heat_duty"))
    max_dp_tube_pa = _number(task.get("max_dp_tube"))
    max_dp_shell_pa = _number(task.get("max_dp_shell"))

    source_file = Path(source_path).name if source_path else "unknown.jsonl"
    track = experiment_track or str(record.get("evaluation_mode") or "zero_shot")
    run_key = f"{prompt}/{track}/{run_type}/{source_file}:{line_number}"
    timestamp = pd.to_datetime(record.get("timestamp"), utc=True, errors="coerce")
    status = str(record.get("status") or "unknown")
    total_score = _number(record.get("total_score"))
    if total_score is None:
        total_score = _number(record.get("total_reward"))
    if total_score is None:
        total_score = 0.0

    raw_response = record.get("raw_response")
    raw_response_text = "" if raw_response is None else str(raw_response)
    estimated_cost = _estimated_cost(prompt_tokens, completion_tokens, pricing)

    return {
        "run_key": run_key,
        "source": SOURCE_LABELS.get(run_type, run_type),
        "run_type": run_type,
        "prompt": record.get("prompt_slug", prompt),
        "task_id": record.get("task_id", prompt),
        "task_set_version": record.get("task_set_version", "legacy"),
        "experiment_track": track,
        "evaluation_mode": record.get("evaluation_mode", track),
        "score_version": record.get("score_version", "heat_exchanger_score_v1"),
        "simulator_version": record.get("simulator_version", "legacy"),
        "model": record.get("model_name", "Unknown"),
        "model_id": record.get("model_id", record.get("model_name", "Unknown")),
        "provider": record.get("provider") or "Unknown",
        "reasoning": _reasoning_label(record.get("reasoning_mode")),
        "timestamp": timestamp,
        "status": status,
        "status_label": _status_label(status),
        "score": total_score,
        "success": status == "success",
        "has_json": status not in {"client_error", "empty_response", "parse_error"},
        "error": record.get("error") or "",
        "heat_duty_kw": heat_w / 1000.0 if heat_w is not None else None,
        "target_heat_kw": target_heat_w / 1000.0 if target_heat_w is not None else None,
        "dp_tube_kpa": dp_tube_pa / 1000.0 if dp_tube_pa is not None else None,
        "dp_shell_kpa": dp_shell_pa / 1000.0 if dp_shell_pa is not None else None,
        "max_dp_tube_kpa": max_dp_tube_pa / 1000.0 if max_dp_tube_pa is not None else None,
        "max_dp_shell_kpa": max_dp_shell_pa / 1000.0 if max_dp_shell_pa is not None else None,
        "effectiveness_pct": effectiveness * 100.0 if effectiveness is not None else None,
        "annual_cost_usd": _first_number(
            metrics,
            ("cost_annualised_USD_per_yr", "cost_annualized_USD_per_yr"),
        ),
        "warnings": _first_number(metrics, ("num_warnings",)),
        "unmet_requirements": _first_number(rewards, ("num_unmet_requirements",)),
        "area_m2": _first_number(metrics, ("area_m2",)),
        "pump_power_w": _first_number(metrics, ("pump_power_total_W",)),
        "tubes": _first_number(design, ("number_of_tubes",)),
        "length_m": _first_number(design, ("length",)),
        "shell_di_m": _first_number(design, ("outer_shell_di",)),
        "latency_s": latency_ms / 1000.0 if latency_ms and latency_ms > 0 else None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        ),
        "estimated_cost_usd": estimated_cost,
        "heat_reward": _first_number(rewards, ("heat_duty_reward",)),
        "tube_dp_reward": _first_number(rewards, ("pressure_drop_tube_reward",)),
        "shell_dp_reward": _first_number(rewards, ("pressure_drop_shell_reward",)),
        "effectiveness_reward": _first_number(rewards, ("effectiveness_reward",)),
        "cost_reward": _first_number(rewards, ("cost_reward",)),
        "penalty_factor": _first_number(rewards, ("penalty_factor",)),
        "raw_response": raw_response_text,
        "prompt_text": str(record.get("prompt_text") or ""),
        "design_json": _json_text(record.get("design")),
        "metrics_json": _json_text(record.get("metrics") or {}),
        "reward_components_json": _json_text(record.get("reward_components") or {}),
        "task_params_json": _json_text(record.get("task_params") or {}),
        "weights_json": _json_text(record.get("weights") or {}),
        "requested_params_json": _json_text(record.get("requested_params") or {}),
        "inference_params_json": _json_text(record.get("inference_params") or {}),
        "effective_params_json": _json_text(record.get("effective_params") or {}),
        "parameter_adjustments_json": _json_text(record.get("parameter_adjustments") or []),
        "model_metadata_json": _json_text(record.get("model_metadata") or {}),
        "source_path": source_path,
        "line_number": line_number,
        "raw_record": json.dumps(record, ensure_ascii=False),
    }


@st.cache_data(ttl=30, show_spinner=False)
def load_all_runs(results_root: str) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    load_errors: List[Dict[str, Any]] = []
    root = Path(results_root)

    locations: List[Tuple[str, str, str, str]] = []
    discovered = set()

    # Canonical layout: experiment protocol is the top-level boundary, and
    # every protocol owns its own independent set of prompt/task units.
    for track in EXPERIMENT_TRACKS:
        for run_type in RUN_SOURCES:
            pattern = str(root / track / "*" / run_type / "**" / "*.jsonl")
            for path_text in sorted(set(glob.glob(pattern, recursive=True))):
                path = Path(path_text)
                prompt = path.parts[path.parts.index(track) + 1]
                resolved = str(path.resolve())
                discovered.add(resolved)
                locations.append((path_text, prompt, run_type, track))

    # Transitional layout used prompt/<track>/<source>. Keep it readable while
    # making the top-level track layout the only write target.
    for track in EXPERIMENT_TRACKS:
        for run_type in RUN_SOURCES:
            pattern = str(root / "*" / track / run_type / "**" / "*.jsonl")
            for path_text in sorted(set(glob.glob(pattern, recursive=True))):
                path = Path(path_text)
                resolved = str(path.resolve())
                if resolved in discovered:
                    continue
                prompt = path.parts[path.parts.index(track) - 1]
                discovered.add(resolved)
                locations.append((path_text, prompt, run_type, track))

    # Original prompt/<source> layout is also readable and is classified as
    # zero-shot. It is not used for new writes.
    for run_type in RUN_SOURCES:
        pattern = str(root / "*" / run_type / "**" / "*.jsonl")
        for path_text in sorted(set(glob.glob(pattern, recursive=True))):
            path = Path(path_text)
            if str(path.resolve()) in discovered:
                continue
            try:
                prompt = path.parts[path.parts.index(run_type) - 1]
            except (ValueError, IndexError):
                prompt = "unknown"
            locations.append((path_text, prompt, run_type, "zero_shot"))

    for path_text, prompt, run_type, track in locations:
        path = Path(path_text)
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        load_errors.append({
                            "File": str(path),
                            "Line": line_number,
                            "Error": str(exc),
                        })
                        continue
                    rows.append(
                        flatten_record(
                            record,
                            run_type,
                            prompt,
                            source_path=str(path),
                            line_number=line_number,
                            experiment_track=track,
                        )
                    )
        except OSError as exc:
            load_errors.append({"File": str(path), "Line": None, "Error": str(exc)})

    return pd.DataFrame(rows), load_errors


def discover_prompt_units(results_root: str, experiment_track: str) -> List[str]:
    """Return only prompt/task units owned by the selected experiment track."""
    track_root = Path(results_root) / experiment_track
    if not track_root.is_dir():
        return []
    return sorted(
        path.name
        for path in track_root.iterdir()
        if path.is_dir()
        and (path / "prompt.txt").is_file()
        and (path / "task.json").is_file()
    )


def load_task_notes(
    results_root: str,
    experiment_track: str,
    prompt_slug: str,
) -> str:
    """Load the Markdown notes owned by one track-specific task."""
    notes_path = Path(results_root) / experiment_track / prompt_slug / "notes.md"
    try:
        return notes_path.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return ""


# The evaluation contract: every design walks these stages in order and the
# status records the first one it failed. Counting survivors per stage is the
# single most useful view of a benchmark run, because it separates "the model
# cannot produce JSON" from "the model cannot design a heat exchanger".
PIPELINE_STAGES: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    ("Responded", "The model returned any text at all", ("client_error", "empty_response")),
    ("Parsed as JSON", "A design object was recovered from the response", ("parse_error",)),
    ("Schema valid", "The 7-field design contract is satisfied", ("schema_error",)),
    ("DRC passed", "Design rule checks found no geometric violation", ("drc_error",)),
    ("Simulated", "Physics ran end to end and produced finite metrics", ("simulation_error",)),
)


def pipeline_funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Survivors after each evaluation stage, plus what dropped out where."""
    if df.empty:
        return pd.DataFrame()
    rows: List[Dict[str, Any]] = []
    remaining = len(df)
    blocked: set = set()
    for stage, description, statuses in PIPELINE_STAGES:
        blocked = blocked.union(statuses)
        survivors = int((~df["status"].isin(blocked)).sum())
        rows.append({
            "Stage": stage,
            "Description": description,
            "Runs": survivors,
            "Lost here": remaining - survivors,
            "Share %": 100.0 * survivors / len(df),
        })
        remaining = survivors
    return pd.DataFrame(rows)


def _requirement_flags(df: pd.DataFrame, task: Dict[str, Any]) -> pd.DataFrame:
    """Flag which task requirements each simulated design actually meets.

    A design that simulates is not automatically a *useful* design: it still has
    to hit the duty target and stay inside the pressure-drop budget. These flags
    are what turns "it ran" into "it would be accepted".
    """
    out = df.copy()
    target_heat = _number(task.get("target_heat_duty"))
    max_tube = _number(task.get("max_dp_tube"))
    max_shell = _number(task.get("max_dp_shell"))

    target_kw = out["target_heat_kw"] if "target_heat_kw" in out else None
    if target_heat is not None:
        target_kw = (
            target_kw.fillna(target_heat / 1000.0)
            if target_kw is not None else target_heat / 1000.0
        )
    tube_limit = out["max_dp_tube_kpa"] if "max_dp_tube_kpa" in out else None
    if max_tube is not None and tube_limit is not None:
        tube_limit = tube_limit.fillna(max_tube / 1000.0)
    shell_limit = out["max_dp_shell_kpa"] if "max_dp_shell_kpa" in out else None
    if max_shell is not None and shell_limit is not None:
        shell_limit = shell_limit.fillna(max_shell / 1000.0)

    out["meets_heat"] = (
        out["heat_duty_kw"] >= target_kw if target_kw is not None else pd.NA
    )
    out["meets_dp_tube"] = (
        out["dp_tube_kpa"] <= tube_limit if tube_limit is not None else pd.NA
    )
    out["meets_dp_shell"] = (
        out["dp_shell_kpa"] <= shell_limit if shell_limit is not None else pd.NA
    )
    out["no_warnings"] = out["warnings"].fillna(0) == 0
    checks = ["meets_heat", "meets_dp_tube", "meets_dp_shell"]
    available = [
        column for column in checks
        if column in out and out[column].dtype != object
    ]
    out["meets_all"] = (
        out[available].fillna(False).all(axis=1) if available else False
    )
    return out


def _requirement_rate(df: pd.DataFrame, task: Dict[str, Any]) -> Optional[float]:
    """Share of all attempts that ended in a design meeting every requirement."""
    if df.empty:
        return None
    successful = df[df["status"] == "success"]
    if successful.empty:
        return 0.0
    flagged = _requirement_flags(successful, task)
    return 100.0 * float(flagged["meets_all"].sum()) / len(df)


_NUMERIC_TOKEN = re.compile(r"[-+]?\d[\d_.,]*(?:[eE][-+]?\d+)?")


def _error_pattern(message: str) -> str:
    """Collapse run-specific numbers so failure reasons cluster properly.

    Raw DRC messages embed the offending diameters, so every run produces a
    unique string and the failure table degenerates into a list of singletons.
    """
    text = str(message or "").strip()
    if not text:
        return "No details recorded"
    collapsed = " ".join(_NUMERIC_TOKEN.sub("#", text).split())
    return collapsed[:160]


def aggregate_runs(df: pd.DataFrame, task: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    task = task or {}

    rows: List[Dict[str, Any]] = []
    # One row per model. Source stays visible as a column so a model that was
    # run both through the API and manually is still a single leaderboard entry.
    for model, group in df.groupby("model", dropna=False):
        attempts = len(group)
        non_client = group[group["status"] != "client_error"]
        successes = group[group["status"] == "success"]
        costs = group["estimated_cost_usd"].dropna()
        latencies = group["latency_s"].dropna()
        completions = group["completion_tokens"].dropna()
        reasons = sorted(set(group["reasoning"].dropna().astype(str)))
        sources = sorted(set(group["source"].dropna().astype(str)))
        accepted = (
            int(_requirement_flags(successes, task)["meets_all"].sum())
            if len(successes) else 0
        )
        # Distinct design payloads expose mode collapse: a model that emits the
        # same geometry every time cannot be improved by sampling more.
        distinct_designs = (
            int(successes["design_json"].nunique()) if len(successes) else 0
        )

        rows.append({
            "Model": model,
            "Source": ", ".join(sources),
            "Reasoning": ", ".join(reasons),
            "Runs": attempts,
            "Non-client runs": len(non_client),
            "Valid design %": 100.0 * len(successes) / attempts if attempts else NA,
            "Requirements met %": 100.0 * accepted / attempts if attempts else NA,
            "Distinct designs": distinct_designs,
            "JSON %": 100.0 * int(group["has_json"].sum()) / attempts if attempts else NA,
            "Empty response %": 100.0 * int((group["status"] == "empty_response").sum()) / attempts,
            "Client error %": 100.0 * int((group["status"] == "client_error").sum()) / attempts,
            "Mean score": non_client["score"].mean() if len(non_client) else NA,
            "Median score": non_client["score"].median() if len(non_client) else NA,
            "Successful score": successes["score"].mean() if len(successes) else NA,
            "Best score": group["score"].max() if attempts else NA,
            "Score std": non_client["score"].std(ddof=0) if len(non_client) else NA,
            "P50 latency (s)": latencies.median() if len(latencies) else NA,
            "P95 latency (s)": latencies.quantile(0.95) if len(latencies) else NA,
            "Mean output tokens": completions.mean() if len(completions) else NA,
            "Estimated cost ($)": costs.sum() if len(costs) else NA,
            "Mean heat duty (kW)": successes["heat_duty_kw"].mean() if len(successes) else NA,
            "Mean annual cost ($/y)": successes["annual_cost_usd"].mean() if len(successes) else NA,
            "Mean warnings": successes["warnings"].mean() if len(successes) else NA,
        })

    return pd.DataFrame(rows).sort_values(
        ["Mean score", "Valid design %", "Best score"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def _style_figure(
    fig: go.Figure,
    height: int = 410,
    legend: str = "auto",
) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=24, r=24, t=68, b=34),
        legend_title_text="",
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        hoverlabel=dict(
            bgcolor="#0b1220",
            bordercolor="#253453",
            font=dict(color="#f8fafc", size=12),
        ),
        font=dict(family="Inter, Segoe UI, sans-serif", color="#26334d"),
        title=dict(font=dict(size=17, color="#101828"), x=0.01, xanchor="left"),
        legend=dict(
            bgcolor="rgba(255,255,255,.82)",
            bordercolor="#e3e9f2",
            borderwidth=1,
            font=dict(size=11),
        ),
    )
    if legend == "bottom":
        # Long model names in a right-hand legend steal most of the plotting
        # width, so wide-label charts hang their legend under the axes instead.
        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.16,
                x=0,
                xanchor="left",
                bgcolor="rgba(255,255,255,0)",
                bordercolor="rgba(0,0,0,0)",
            ),
            margin=dict(l=24, r=24, t=68, b=96),
        )
    # ``automargin`` keeps long categorical tick labels from being clipped.
    fig.update_xaxes(
        gridcolor="#edf1f7",
        linecolor="#dbe3ee",
        zerolinecolor="#dbe3ee",
        automargin=True,
        title_font=dict(color="#526078", size=12),
        tickfont=dict(color="#667085", size=11),
    )
    fig.update_yaxes(
        gridcolor="#edf1f7",
        linecolor="#dbe3ee",
        zerolinecolor="#dbe3ee",
        automargin=True,
        title_font=dict(color="#526078", size=12),
        tickfont=dict(color="#667085", size=11),
    )
    return fig


def _show_figure(fig: go.Figure, height: int = 410, legend: str = "auto") -> None:
    st.plotly_chart(
        _style_figure(fig, height, legend),
        width="stretch",
        config={
            "displayModeBar": False,
            "displaylogo": False,
            "scrollZoom": False,
            "responsive": True,
        },
    )


def _fmt_number(value: Any, digits: int = 2, suffix: str = "") -> str:
    parsed = _number(value)
    if parsed is None:
        return "—"
    return f"{parsed:,.{digits}f}{suffix}"


def _parse_json_text(value: Any) -> Any:
    try:
        return json.loads(str(value))
    except (TypeError, ValueError):
        return value


def _visible_export(df: pd.DataFrame) -> pd.DataFrame:
    return df[[column for column in df.columns if column not in COMPLEX_COLUMNS]].copy()


def _render_header(experiment_track: str) -> None:
    track_tag = html.escape(_track_label(experiment_track).upper())
    trace_tag = (
        "EPISODE-LEVEL TRACEABILITY"
        if experiment_track == "feedback_driven" else "RUN-LEVEL TRACEABILITY"
    )
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-glow"></div>
          <div class="hero-main">
            <div class="eyebrow"><span></span>SM-BENCH / BENCHMARK INTELLIGENCE</div>
            <h1>Heat Exchanger <em>Evaluation Lab</em></h1>
          </div>
          <div class="hero-tags">
            <span>PHYSICS-GROUNDED</span><span>{track_tag}</span><span>{trace_tag}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(df: pd.DataFrame, leaderboard: pd.DataFrame, task: Dict[str, Any]) -> None:
    """Headline numbers answering: did this benchmark produce usable designs?"""
    attempts = len(df)
    successful = df[df["status"] == "success"]
    flagged = _requirement_flags(successful, task) if not successful.empty else successful
    accepted = int(flagged["meets_all"].sum()) if not successful.empty else 0
    best_score = df["score"].max() if attempts else None
    median_valid = successful["score"].median() if not successful.empty else None

    cols = st.columns(5)
    cols[0].metric("RUNS", f"{attempts:,}", f"{df['model'].nunique():,} models")
    cols[1].metric(
        "VALID DESIGNS",
        f"{100.0 * len(successful) / attempts:.1f}%" if attempts else "—",
        f"{len(successful):,} simulated",
    )
    cols[2].metric(
        "REQUIREMENTS MET",
        f"{100.0 * accepted / attempts:.1f}%" if attempts else "—",
        f"{accepted:,} would be accepted",
    )
    cols[3].metric("BEST SCORE", _fmt_number(best_score, 3), "benchmark ceiling")
    cols[4].metric("MEDIAN VALID SCORE", _fmt_number(median_valid, 3), "typical valid design")

    verdict, detail = _benchmark_verdict(df, leaderboard, accepted, attempts)
    best_model = str(leaderboard.iloc[0]["Model"]) if not leaderboard.empty else "—"
    best_mean = leaderboard.iloc[0]["Mean score"] if not leaderboard.empty else None
    st.markdown(
        f"""
        <div class="summary-strip">
          <div><span>LEADING MODEL</span><strong>{html.escape(best_model)}</strong>
            <small>Mean benchmark score · {_fmt_number(best_mean, 3)}</small></div>
          <div><span>TASK VERDICT</span><strong>{html.escape(verdict)}</strong>
            <small>{html.escape(detail)}</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _benchmark_verdict(
    df: pd.DataFrame,
    leaderboard: pd.DataFrame,
    accepted: int,
    attempts: int,
) -> Tuple[str, str]:
    """Judge the task itself, not the models.

    A benchmark is only useful while it separates models. If everyone fails or
    everyone maxes out, the task needs recalibration before any of the model
    numbers mean anything.
    """
    if attempts == 0:
        return "No data", "Nothing to judge under the current filters."
    if len(leaderboard) < 2:
        return "Single model", "Add more models before reading the task difficulty."

    means = leaderboard["Mean score"].dropna()
    if means.empty:
        return "No scored runs", "Every run failed before producing a score."
    spread = float(means.max() - means.min())
    accepted_rate = 100.0 * accepted / attempts

    if accepted_rate == 0.0:
        return (
            "Too hard",
            f"No design met every requirement across {attempts:,} runs.",
        )
    if accepted_rate > 90.0 and spread < 0.05:
        return (
            "Too easy",
            f"{accepted_rate:.0f}% of runs are accepted and models differ by only {spread:.3f}.",
        )
    if spread < 0.05:
        return (
            "Not discriminative",
            f"Best and worst model are within {spread:.3f} mean score.",
        )
    return (
        "Discriminative",
        f"{spread:.3f} mean-score spread between best and worst model · "
        f"{accepted_rate:.0f}% of runs accepted.",
    )


def _render_pipeline(df: pd.DataFrame) -> None:
    """Where designs die in the four-stage evaluation contract."""
    funnel = pipeline_funnel(df)
    if funnel.empty:
        return

    left, right = st.columns((1.15, 1.0))
    with left:
        fig = go.Figure(go.Funnel(
            y=funnel["Stage"],
            x=funnel["Runs"],
            textinfo="value+percent initial",
            marker=dict(color=["#93b4ff", "#6d93f7", "#4b78ee", "#2f6bff", "#16a34a"]),
            hovertemplate=(
                "<b>%{y}</b><br>%{x} runs survived<br>"
                "%{customdata[0]} lost at this stage<extra></extra>"
            ),
            customdata=funnel[["Lost here"]].values,
        ))
        fig.update_layout(title="Evaluation pipeline · where designs drop out")
        _show_figure(fig, 400)

    with right:
        losses = funnel[funnel["Lost here"] > 0]
        if losses.empty:
            st.success("Every model output survived all four evaluation stages.")
        else:
            fig = px.bar(
                losses.sort_values("Lost here"),
                x="Lost here",
                y="Stage",
                orientation="h",
                text="Lost here",
                color_discrete_sequence=["#dc2626"],
                labels={"Lost here": "Runs lost", "Stage": ""},
                title="Runs lost per stage",
            )
            fig.update_traces(
                hovertemplate="<b>%{y}</b><br>%{x} runs lost here<extra></extra>",
            )
            fig.update_layout(showlegend=False)
            _show_figure(fig, 400)

    _render_table(funnel[["Stage", "Description", "Runs", "Lost here", "Share %"]])


def _render_failure_reasons(df: pd.DataFrame) -> None:
    """The actual engineering reasons behind the failures, not raw messages."""
    failures = df[(df["status"] != "success") & (df["status"] != "client_error")].copy()
    if failures.empty:
        return
    failures["Reason"] = failures["error"].map(_error_pattern)
    summary = (
        failures.groupby(["status_label", "Reason"])
        .agg(Runs=("run_key", "count"), Models=("model", "nunique"))
        .reset_index()
        .rename(columns={"status_label": "Stage"})
        .sort_values("Runs", ascending=False)
    )
    st.markdown("#### Why designs are rejected")
    st.caption(
        "Run-specific numbers are collapsed to `#` so the same engineering "
        "mistake groups into one row."
    )
    _render_table(summary.head(25))


def _render_overview(df: pd.DataFrame, leaderboard: pd.DataFrame, task: Dict[str, Any]) -> None:
    st.subheader("Executive overview")
    _render_kpis(df, leaderboard, task)
    st.caption(
        "Mean score includes every model output except client-side failures. "
        "Parse, DRC, and simulation failures remain zero-score outcomes."
    )

    _render_pipeline(df)

    score_df = _with_model_labels(df[df["status"] != "client_error"])
    if score_df.empty:
        st.info("No model outputs are available for the score distribution.")
    else:
        order = (
            score_df.groupby("model_label")["score"].median()
            .sort_values().index.tolist()
        )
        fig = px.box(
            score_df,
            x="score",
            y="model_label",
            color="model_label",
            orientation="h",
            points="all",
            category_orders={"model_label": order},
            color_discrete_sequence=PLOT_COLORS,
            labels={"model_label": "", "score": "Score"},
            title="Score distribution · every model output, failures included as 0",
            custom_data=["model", "status_label"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Score %{x:.3f}<br>"
                "%{customdata[1]}<extra></extra>"
            ),
        )
        fig.update_layout(showlegend=False)
        fig.update_xaxes(range=[-0.02, 1.02])
        _show_figure(fig, _model_axis_height(score_df["model_label"].nunique()))

    _render_failure_reasons(df)


def _render_leaderboard(df: pd.DataFrame, leaderboard: pd.DataFrame) -> None:
    st.subheader("Model leaderboard")
    st.caption(
        "**Valid design %** is the share of attempts that simulated at all; "
        "**Requirements met %** is the share that also hit the duty target and stayed "
        "inside both pressure-drop limits — that is the number that says whether a "
        "model is engineering-useful. Mean score includes model-side failures as zero."
    )
    if leaderboard.empty:
        st.info("No leaderboard can be generated for the current filters.")
        return

    max_runs = int(leaderboard["Runs"].max())
    controls = st.columns((1.0, 1.0, 1.4))
    min_runs = controls[0].number_input(
        "Minimum runs per model",
        min_value=1,
        max_value=max(1, max_runs),
        value=1,
        step=1,
        help="Hide models that were sampled too few times to compare fairly.",
    )
    sort_column = controls[1].selectbox(
        "Rank by",
        ["Mean score", "Requirements met %", "Successful score", "Best score",
         "Valid design %", "JSON %", "P50 latency (s)", "Estimated cost ($)", "Runs"],
        key="leaderboard_sort",
    )
    ascending = sort_column in {"P50 latency (s)", "Estimated cost ($)"}
    controls[2].caption(
        "Latency and cost rank ascending (cheaper and faster first); "
        "every other column ranks descending."
    )

    ranked = leaderboard[leaderboard["Runs"] >= int(min_runs)].copy()
    if ranked.empty:
        st.info(f"No model has at least {int(min_runs)} runs under the current filters.")
        return
    ranked = ranked.sort_values(
        sort_column, ascending=ascending, na_position="last"
    ).reset_index(drop=True)
    ranked.insert(0, "#", range(1, len(ranked) + 1))

    _render_table(ranked)

    chart_df = ranked.head(20).sort_values("Mean score", ascending=True).copy()
    chart_df["Label"] = chart_df["Model"].map(
        _model_label_map(chart_df["Model"].astype(str).tolist())
    )
    fig = px.bar(
        chart_df,
        x="Mean score",
        y="Label",
        orientation="h",
        color="Requirements met %",
        color_continuous_scale=[[0, "#dce7ff"], [1, "#16a34a"]],
        range_x=[0, 1],
        text="Mean score",
        title="Quality vs. requirement compliance",
        labels={"Label": ""},
        custom_data=["Requirements met %", "Runs", "Model", "Valid design %"],
    )
    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{customdata[2]}</b><br>Mean score %{x:.3f}<br>"
            "Requirements met %{customdata[0]:.1f}% · valid %{customdata[3]:.1f}%<br>"
            "%{customdata[1]} runs<extra></extra>"
        ),
    )
    _show_figure(fig, _model_axis_height(len(chart_df), per_row=40))

    csv = ranked.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download leaderboard CSV",
        data=csv,
        file_name="benchmark_leaderboard.csv",
        mime="text/csv",
    )


def _add_target_lines(fig: go.Figure, task: Dict[str, Any], kind: str) -> None:
    if kind == "heat":
        target = _number(task.get("target_heat_duty"))
        if target is not None:
            fig.add_hline(
                y=target / 1000.0,
                line_dash="dash",
                line_color="#ef476f",
                annotation_text=f"Target {target / 1000.0:g} kW",
            )
    elif kind == "pressure":
        tube = _number(task.get("max_dp_tube"))
        shell = _number(task.get("max_dp_shell"))
        if tube is not None:
            fig.add_vline(
                x=tube / 1000.0,
                line_dash="dash",
                line_color="#ef476f",
                annotation_text="Tube limit",
            )
        if shell is not None:
            fig.add_hline(
                y=shell / 1000.0,
                line_dash="dash",
                line_color="#ef476f",
                annotation_text="Shell limit",
            )


REQUIREMENT_CHECKS = (
    ("meets_heat", "Heat duty target"),
    ("meets_dp_tube", "Tube ΔP limit"),
    ("meets_dp_shell", "Shell ΔP limit"),
    ("no_warnings", "No mechanical warning"),
    ("meets_all", "All requirements"),
)


def _render_requirement_compliance(successful: pd.DataFrame, task: Dict[str, Any]) -> None:
    """Which task requirement each model actually satisfies.

    A simulated design is not a usable one. This is the chart that says whether
    a model merely produced runnable geometry or an exchanger an engineer would
    sign off on, and which single constraint is blocking it.
    """
    flagged = _requirement_flags(successful, task)
    rows: List[Dict[str, Any]] = []
    for label, group in flagged.groupby("model_label"):
        for column, name in REQUIREMENT_CHECKS:
            if column not in group:
                continue
            values = group[column]
            if values.dtype == object:
                continue
            rows.append({
                "model_label": label,
                "Requirement": name,
                "Share": 100.0 * float(values.fillna(False).sum()) / len(group),
                "Designs": len(group),
            })
    if not rows:
        st.info("This task defines no numeric requirement to check against.")
        return

    compliance = pd.DataFrame(rows)
    order = (
        compliance[compliance["Requirement"] == "All requirements"]
        .set_index("model_label")["Share"].sort_values().index.tolist()
    )
    fig = px.bar(
        compliance,
        x="Share",
        y="model_label",
        color="Requirement",
        orientation="h",
        barmode="group",
        category_orders={"model_label": order or sorted(compliance["model_label"].unique())},
        color_discrete_sequence=["#2f6bff", "#0891b2", "#7c3aed", "#ca8a04", "#16a34a"],
        labels={"model_label": "", "Share": "Share of valid designs (%)"},
        title="Requirement compliance · share of simulated designs that pass",
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:.0f}%<extra></extra>",
    )
    fig.update_xaxes(range=[0, 100])
    _show_figure(
        fig,
        _model_axis_height(compliance["model_label"].nunique(), per_row=96, minimum=420),
        legend="bottom",
    )


def _render_design_diversity(successful: pd.DataFrame) -> None:
    """Are models exploring the design space or repeating one answer?

    Repeated identical geometry means extra sampling buys nothing, which
    matters directly for building a training dataset out of these runs.
    """
    diversity = (
        successful.groupby("model_label")
        .agg(
            Designs=("design_json", "count"),
            Distinct=("design_json", "nunique"),
        )
        .reset_index()
        .rename(columns={"model_label": "Model"})
    )
    diversity["Distinct %"] = 100.0 * diversity["Distinct"] / diversity["Designs"]
    repeated = int((successful["design_json"].duplicated()).sum())
    st.markdown("#### Design diversity")
    st.caption(
        f"{successful['design_json'].nunique():,} distinct geometries across "
        f"{len(successful):,} valid designs · {repeated:,} repeats. "
        "Low diversity means resampling the same model will not find a better design."
    )
    _render_table(
        diversity.sort_values("Distinct %", ascending=False),
        column_config={
            "Distinct %": st.column_config.ProgressColumn(
                "Distinct %", min_value=0.0, max_value=100.0, format="%.0f%%",
            ),
        },
    )


def _render_best_design(successful: pd.DataFrame, task: Dict[str, Any]) -> None:
    """The best design any model produced, against the task requirements.

    This is the artifact the project is actually after: the current frontier of
    what an LLM can design for this task, and how far it still is from spec.
    """
    best = successful.sort_values("score", ascending=False).iloc[0]
    flags = _requirement_flags(successful, task).sort_values("score", ascending=False).iloc[0]
    target_heat = _number(task.get("target_heat_duty"))
    target_kw = target_heat / 1000.0 if target_heat is not None else None
    gap = (
        best["heat_duty_kw"] - target_kw
        if _number(best["heat_duty_kw"]) is not None and target_kw is not None
        else None
    )
    verdict = "meets every requirement" if bool(flags["meets_all"]) else "still off spec"

    with st.expander(
        f"Best design in view · {best['model']} · score {_fmt_number(best['score'], 3)}"
        f" · {verdict}",
        expanded=False,
    ):
        cols = st.columns(4)
        cols[0].metric(
            "HEAT DUTY",
            _fmt_number(best["heat_duty_kw"], 1, " kW"),
            _fmt_number(gap, 1, " kW vs target") if gap is not None else None,
        )
        cols[1].metric("TUBE ΔP", _fmt_number(best["dp_tube_kpa"], 2, " kPa"))
        cols[2].metric("SHELL ΔP", _fmt_number(best["dp_shell_kpa"], 2, " kPa"))
        cols[3].metric("ANNUAL COST", _fmt_number(best["annual_cost_usd"], 0, " $/y"))
        st.json(_parse_json_text(best["design_json"]), expanded=True)
        st.caption(
            "Open the Runs tab and sort by *Highest score* for the full evidence "
            "trail behind this design."
        )


def _render_engineering(df: pd.DataFrame, task: Dict[str, Any]) -> None:
    st.subheader("Engineering analysis")
    successful = _with_model_labels(df[df["status"] == "success"])
    if successful.empty:
        st.info("No successful simulations are available for engineering analysis.")
        return

    target_heat = _number(task.get("target_heat_duty"))
    max_tube = _number(task.get("max_dp_tube"))
    max_shell = _number(task.get("max_dp_shell"))
    flagged = _requirement_flags(successful, task)
    accepted = int(flagged["meets_all"].sum())
    target_cols = st.columns(4)
    target_cols[0].metric("HEAT TARGET", _fmt_number(target_heat / 1000.0 if target_heat else None, 1, " kW"))
    target_cols[1].metric("TUBE ΔP LIMIT", _fmt_number(max_tube / 1000.0 if max_tube else None, 2, " kPa"))
    target_cols[2].metric("SHELL ΔP LIMIT", _fmt_number(max_shell / 1000.0 if max_shell else None, 2, " kPa"))
    target_cols[3].metric(
        "ACCEPTED DESIGNS",
        f"{accepted:,}",
        f"of {len(successful):,} valid",
    )

    _render_best_design(successful, task)
    _render_requirement_compliance(successful, task)

    left, right = st.columns(2)
    with left:
        pressure = successful.dropna(subset=["dp_tube_kpa", "dp_shell_kpa"])
        if not pressure.empty:
            fig = px.scatter(
                pressure,
                x="dp_tube_kpa",
                y="dp_shell_kpa",
                color="model_label",
                size="score",
                size_max=20,
                color_discrete_sequence=PLOT_COLORS,
                labels={
                    "dp_tube_kpa": "Tube ΔP (kPa)",
                    "dp_shell_kpa": "Shell ΔP (kPa)",
                    "model_label": "Model",
                },
                title="Hydraulic operating envelope",
                custom_data=["score", "model"],
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>Tube ΔP %{x:.3f} kPa<br>"
                    "Shell ΔP %{y:.3f} kPa<br>Score %{customdata[0]:.3f}<extra></extra>"
                )
            )
            _add_target_lines(fig, task, "pressure")
            _show_figure(fig, 440, legend="bottom")
        else:
            st.info("Pressure-drop metrics are not available.")

    with right:
        thermo = successful.dropna(subset=["annual_cost_usd", "heat_duty_kw"])
        if not thermo.empty:
            fig = px.scatter(
                thermo,
                x="annual_cost_usd",
                y="heat_duty_kw",
                color="model_label",
                size="score",
                size_max=20,
                color_discrete_sequence=PLOT_COLORS,
                labels={
                    "annual_cost_usd": "Annualized cost ($/y)",
                    "heat_duty_kw": "Heat duty (kW)",
                    "model_label": "Model",
                },
                title="Thermal performance vs. cost",
                custom_data=["score", "model"],
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>Cost $%{x:,.0f}/y<br>"
                    "Heat %{y:.1f} kW<br>Score %{customdata[0]:.3f}<extra></extra>"
                )
            )
            _add_target_lines(fig, task, "heat")
            _show_figure(fig, 440, legend="bottom")
        else:
            st.info("Heat-duty and cost metrics are not jointly available.")

    reward_columns = {
        "heat_reward": "Heat duty",
        "tube_dp_reward": "Tube ΔP",
        "shell_dp_reward": "Shell ΔP",
        "effectiveness_reward": "Effectiveness",
        "cost_reward": "Cost",
        "penalty_factor": "Penalty factor",
    }
    reward_means = successful.groupby("model_label")[list(reward_columns)].mean()
    reward_means = reward_means.dropna(how="all")
    if not reward_means.empty:
        fig = go.Figure(data=go.Heatmap(
            z=reward_means.values,
            x=[reward_columns[column] for column in reward_means.columns],
            y=reward_means.index.tolist(),
            zmin=0,
            zmax=1,
            colorscale=[[0, "#eef3ff"], [0.5, "#82a8ff"], [1, "#245cff"]],
            text=reward_means.round(3).values,
            texttemplate="%{text}",
            hovertemplate="Model: %{y}<br>Component: %{x}<br>Mean: %{z:.3f}<extra></extra>",
        ))
        fig.update_layout(title="Mean reward components")
        _show_figure(fig, _model_axis_height(len(reward_means), per_row=44))

    metric_options = {
        "Heat duty (kW)": "heat_duty_kw",
        "Annual cost ($/y)": "annual_cost_usd",
        "Effectiveness (%)": "effectiveness_pct",
        "Tube ΔP (kPa)": "dp_tube_kpa",
        "Shell ΔP (kPa)": "dp_shell_kpa",
        "Area (m²)": "area_m2",
        "Pump power (W)": "pump_power_w",
        "Warnings": "warnings",
    }
    selected_label = st.selectbox("Distribution metric", list(metric_options))
    selected_metric = metric_options[selected_label]
    metric_df = successful.dropna(subset=[selected_metric])
    if not metric_df.empty:
        order = (
            metric_df.groupby("model_label")[selected_metric].median()
            .sort_values().index.tolist()
        )
        fig = px.violin(
            metric_df,
            x=selected_metric,
            y="model_label",
            color="model_label",
            orientation="h",
            box=True,
            points="all",
            category_orders={"model_label": order},
            color_discrete_sequence=PLOT_COLORS,
            labels={"model_label": "", selected_metric: selected_label},
            title=f"{selected_label} distribution",
            custom_data=["model"],
        )
        fig.update_traces(
            hovertemplate=(
                f"<b>%{{customdata[0]}}</b><br>{selected_label} %{{x:.3f}}<extra></extra>"
            ),
        )
        fig.update_layout(showlegend=False)
        _show_figure(fig, _model_axis_height(metric_df["model_label"].nunique(), per_row=46))

    _render_design_diversity(successful)


def _render_efficiency(df: pd.DataFrame) -> None:
    st.subheader("Reliability and inference efficiency")
    labelled = _with_model_labels(df)
    chart_height = _model_axis_height(labelled["model_label"].nunique())
    left, right = st.columns(2)
    with left:
        status_table = (
            labelled.groupby(["model_label", "status_label"])
            .size().rename("count").reset_index()
        )
        status_table["share"] = status_table["count"] / status_table.groupby(
            "model_label")["count"].transform("sum")
        success_order = (
            status_table[status_table["status_label"] == "Success"]
            .set_index("model_label")["share"]
        )
        order = sorted(
            status_table["model_label"].unique().tolist(),
            key=lambda label: success_order.get(label, 0.0),
        )
        fig = px.bar(
            status_table,
            x="share",
            y="model_label",
            orientation="h",
            color="status_label",
            category_orders={"model_label": order},
            color_discrete_map={
                label: STATUS_COLORS[key] for key, label in STATUS_LABELS.items()
            },
            labels={"model_label": "", "share": "Run share", "status_label": "Outcome"},
            title="Outcome composition by model",
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:.1%}<extra></extra>",
        )
        fig.update_xaxes(tickformat=".0%")
        _show_figure(fig, chart_height)

    with right:
        latency = labelled.dropna(subset=["latency_s"])
        if not latency.empty:
            order = (
                latency.groupby("model_label")["latency_s"].median()
                .sort_values(ascending=False).index.tolist()
            )
            fig = px.box(
                latency,
                x="latency_s",
                y="model_label",
                color="model_label",
                orientation="h",
                points="all",
                category_orders={"model_label": order},
                color_discrete_sequence=PLOT_COLORS,
                labels={"model_label": "", "latency_s": "Latency (s)"},
                title="Response latency distribution",
                custom_data=["model"],
            )
            fig.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>Latency %{x:.1f} s<extra></extra>",
            )
            fig.update_layout(showlegend=False)
            _show_figure(fig, chart_height)
        else:
            st.info("Latency data is not available.")

    _render_effort_return(labelled)

    costs = labelled.dropna(subset=["estimated_cost_usd"])
    if not costs.empty:
        cost_summary = costs.groupby("model").agg(
            runs=("run_key", "count"),
            total_cost=("estimated_cost_usd", "sum"),
            mean_cost=("estimated_cost_usd", "mean"),
        ).reset_index()
        scores = labelled[labelled["status"] != "client_error"].groupby("model")["score"].mean()
        cost_summary["cost_per_score"] = cost_summary.apply(
            lambda row: (
                row["mean_cost"] / scores.get(row["model"])
                if _number(scores.get(row["model"])) not in (None, 0.0) else NA
            ),
            axis=1,
        )
        cost_summary = cost_summary.rename(columns={
            "model": "Model",
            "runs": "Runs",
            "total_cost": "Estimated total cost",
            "mean_cost": "Mean cost per run",
            "cost_per_score": "Cost per score point",
        }).sort_values("Estimated total cost", ascending=False)
        st.markdown("#### What a benchmark point costs")
        st.caption(
            "Estimated from provider token rates; discounts, caching, and provider "
            "overrides are not reflected. *Cost per score point* is the number to "
            "compare when choosing which model to spend a sampling budget on."
        )
        _render_table(cost_summary)


def _render_effort_return(labelled: pd.DataFrame) -> None:
    """Does spending more inference effort buy a better design?

    Two questions decide how to sample this benchmark: does a longer response
    help, and does raising a model's reasoning effort help? Both are answered
    per model, not per run, because single runs are too noisy to read.
    """
    scored = labelled[labelled["status"] != "client_error"]
    if scored.empty:
        return

    st.markdown("#### Does more effort pay off?")
    left, right = st.columns(2)

    with left:
        effort = (
            scored.dropna(subset=["completion_tokens"])
            .groupby(["model_label", "model"])
            .agg(
                tokens=("completion_tokens", "mean"),
                score=("score", "mean"),
                runs=("run_key", "count"),
            )
            .reset_index()
        )
        if effort.empty:
            st.info("No token accounting is available for these runs.")
        else:
            fig = px.scatter(
                effort,
                x="tokens",
                y="score",
                text="model_label",
                size="runs",
                size_max=26,
                color_discrete_sequence=["#2f6bff"],
                labels={"tokens": "Mean output tokens", "score": "Mean score"},
                title="Output length vs. quality · one point per model",
                custom_data=["model", "runs"],
            )
            fig.update_traces(
                textposition="top center",
                textfont=dict(size=10, color="#667085"),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{x:,.0f} mean output tokens<br>"
                    "Mean score %{y:.3f} · %{customdata[1]} runs<extra></extra>"
                ),
            )
            fig.update_yaxes(range=[-0.02, 1.02])
            _show_figure(fig, 420)

    with right:
        variants = scored.copy()
        variants["base_model"] = variants["model"].astype(str).str.split("__reasoning-").str[0]
        counts = variants.groupby("base_model")["reasoning"].nunique()
        comparable = counts[counts > 1].index.tolist()
        variants = variants[variants["base_model"].isin(comparable)]
        if variants.empty:
            st.info(
                "No model in this view was run at more than one reasoning effort, "
                "so the effect of reasoning cannot be isolated here."
            )
        else:
            summary = (
                variants.groupby(["base_model", "reasoning"])
                .agg(score=("score", "mean"), runs=("run_key", "count"))
                .reset_index()
            )
            fig = px.bar(
                summary,
                x="score",
                y="base_model",
                color="reasoning",
                orientation="h",
                barmode="group",
                color_discrete_sequence=PLOT_COLORS,
                labels={"base_model": "", "score": "Mean score", "reasoning": "Reasoning"},
                title="Reasoning effort vs. quality",
                custom_data=["runs"],
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{y}</b> · %{fullData.name}<br>"
                    "Mean score %{x:.3f} · %{customdata[0]} runs<extra></extra>"
                ),
            )
            fig.update_xaxes(range=[0, 1])
            _show_figure(fig, 420, legend="bottom")


def _render_run_explorer(df: pd.DataFrame) -> None:
    st.subheader("Run explorer")
    st.caption(
        "Select any row to inspect the model response, design payload, simulation output, "
        "score breakdown, and request metadata."
    )
    search_col, sort_col = st.columns((1.6, 1.0))
    with search_col:
        search = st.text_input(
            "Search runs",
            placeholder="Model, outcome, error, or raw response…",
        ).strip().lower()
    with sort_col:
        sort_choice = st.selectbox(
            "Sort by",
            ["Newest", "Highest score", "Lowest score", "Slowest", "Most output tokens"],
        )

    view = df.copy()
    if search:
        haystack = (
            view["model"].fillna("").astype(str)
            + " " + view["status"].fillna("").astype(str)
            + " " + view["status_label"].fillna("").astype(str)
            + " " + view["error"].fillna("").astype(str)
            + " " + view["raw_response"].fillna("").astype(str)
        ).str.lower()
        view = view[haystack.str.contains(search, regex=False)]

    if view.empty:
        st.info("No runs match your search.")
        return

    sort_rules = {
        "Newest": (["timestamp", "model"], [False, True]),
        "Highest score": (["score", "timestamp"], [False, False]),
        "Lowest score": (["score", "timestamp"], [True, False]),
        "Slowest": (["latency_s", "timestamp"], [False, False]),
        "Most output tokens": (["completion_tokens", "timestamp"], [False, False]),
    }
    sort_columns, ascending = sort_rules[sort_choice]
    view = view.sort_values(
        sort_columns,
        ascending=ascending,
        na_position="last",
    ).reset_index(drop=True)

    display = view[[
        "line_number", "timestamp", "model", "source", "reasoning", "status_label",
        "score", "latency_s", "completion_tokens", "heat_duty_kw",
        "dp_tube_kpa", "dp_shell_kpa", "annual_cost_usd", "warnings",
    ]].rename(columns={
            "line_number": "#", "timestamp": "Time", "model": "Model", "source": "Source",
            "reasoning": "Reasoning", "status_label": "Outcome", "score": "Score",
            "latency_s": "Latency (s)", "completion_tokens": "Output tokens",
            "heat_duty_kw": "Heat duty (kW)", "dp_tube_kpa": "Tube ΔP (kPa)",
            "dp_shell_kpa": "Shell ΔP (kPa)", "annual_cost_usd": "Annual cost ($/y)",
            "warnings": "Warnings",
        })
    selection = st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=430,
        on_select="rerun",
        selection_mode="single-row",
        key="run_explorer_table",
        column_config={
            "#": st.column_config.NumberColumn("Run", format="#%d", width="small"),
            "Time": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss", width="medium"),
            "Model": st.column_config.TextColumn(width="large"),
            "Source": st.column_config.TextColumn(width="small"),
            "Reasoning": st.column_config.TextColumn(width="small"),
            "Outcome": st.column_config.TextColumn(width="medium"),
            "Score": st.column_config.ProgressColumn(
                min_value=0.0,
                max_value=1.0,
                format="%.3f",
            ),
            "Latency (s)": st.column_config.NumberColumn(format="%.1f"),
            "Output tokens": st.column_config.NumberColumn(format="%d"),
            "Heat duty (kW)": st.column_config.NumberColumn(format="%.1f"),
            "Tube ΔP (kPa)": st.column_config.NumberColumn(format="%.3f"),
            "Shell ΔP (kPa)": st.column_config.NumberColumn(format="%.3f"),
            "Annual cost ($/y)": st.column_config.NumberColumn(format="$%.0f"),
            "Warnings": st.column_config.NumberColumn(format="%d"),
        },
    )

    selected_rows = list(selection.selection.rows)
    selected_position = selected_rows[0] if selected_rows and selected_rows[0] < len(view) else 0
    row = view.iloc[selected_position]
    if not selected_rows:
        st.caption("No row selected yet; showing the first run in the current view.")

    status_color = STATUS_COLORS.get(row["status"], STATUS_COLORS["unknown"])
    status_text = html.escape(str(row["status_label"]))
    model_name = html.escape(str(row["model"]))
    model_id = html.escape(str(row["model_id"]))
    source_ref = html.escape(
        f"{Path(row['source_path']).name} · line {int(row['line_number'])}"
    )
    st.markdown(
        f"<div class='run-title'><span style='background:{status_color}'>{status_text}</span>"
        f"<div><strong>{model_name}</strong><small>{model_id}<br>{source_ref}</small></div></div>",
        unsafe_allow_html=True,
    )
    primary_metrics = st.columns(3)
    primary_metrics[0].metric("SCORE", _fmt_number(row["score"], 3))
    primary_metrics[1].metric("LATENCY", _fmt_number(row["latency_s"], 1, " s"))
    primary_metrics[2].metric(
        "ESTIMATED API COST",
        _fmt_number(row["estimated_cost_usd"], 5, " $"),
    )
    token_metrics = st.columns(3)
    token_metrics[0].metric("PROMPT TOKENS", _fmt_number(row["prompt_tokens"], 0))
    token_metrics[1].metric("OUTPUT TOKENS", _fmt_number(row["completion_tokens"], 0))
    token_metrics[2].metric("REASONING", row["reasoning"])

    if row["status"] == "success":
        st.markdown("#### Engineering snapshot")
        engineering_top = st.columns(3)
        engineering_top[0].metric("HEAT DUTY", _fmt_number(row["heat_duty_kw"], 1, " kW"))
        engineering_top[1].metric("EFFECTIVENESS", _fmt_number(row["effectiveness_pct"], 1, "%"))
        engineering_top[2].metric("ANNUAL COST", _fmt_number(row["annual_cost_usd"], 0, " $/y"))
        engineering_bottom = st.columns(3)
        engineering_bottom[0].metric("TUBE ΔP", _fmt_number(row["dp_tube_kpa"], 3, " kPa"))
        engineering_bottom[1].metric("SHELL ΔP", _fmt_number(row["dp_shell_kpa"], 3, " kPa"))
        engineering_bottom[2].metric("WARNINGS", _fmt_number(row["warnings"], 0))

    if row["error"]:
        st.error(row["error"])

    raw_tab, design_tab, metrics_tab, score_tab, request_tab, provenance_tab = st.tabs([
        "Raw response", "Design", "Metrics", "Score breakdown", "Request", "Provenance",
    ])
    with raw_tab:
        if row["raw_response"].strip():
            st.code(row["raw_response"], language="json", wrap_lines=True)
        else:
            st.warning("The model returned an empty response, or no raw response was recorded.")
    with design_tab:
        st.json(_parse_json_text(row["design_json"]), expanded=True)
    with metrics_tab:
        st.json(_parse_json_text(row["metrics_json"]), expanded=False)
    with score_tab:
        st.json(_parse_json_text(row["reward_components_json"]), expanded=True)
    with request_tab:
        req_left, req_right = st.columns(2)
        with req_left:
            st.markdown("**Effective parameters**")
            st.json(_parse_json_text(row["effective_params_json"]), expanded=True)
            st.markdown("**Requested parameters**")
            st.json(_parse_json_text(row["requested_params_json"]), expanded=False)
        with req_right:
            st.markdown("**Model metadata**")
            st.json(_parse_json_text(row["model_metadata_json"]), expanded=False)
            st.markdown("**Preflight adjustments**")
            st.json(_parse_json_text(row["parameter_adjustments_json"]), expanded=True)
    with provenance_tab:
        st.write({
            "Source file": row["source_path"],
            "Line": int(row["line_number"]),
            "Experiment track": _track_label(row["experiment_track"]),
            "Task ID": row["task_id"],
            "Task set": row["task_set_version"],
            "Score": row["score_version"],
            "Simulator": row["simulator_version"],
            "Evaluation mode": row["evaluation_mode"],
            "Provider": row["provider"],
        })

    with st.expander("Prompt and task parameters for this run"):
        st.code(row["prompt_text"] or "Prompt text is not available in this legacy record.", wrap_lines=True)
        st.json(_parse_json_text(row["task_params_json"]), expanded=False)

    st.download_button(
        "Download this run as JSON",
        data=json.dumps(_parse_json_text(row["raw_record"]), ensure_ascii=False, indent=2),
        file_name=f"{row['model']}_{int(row['line_number'])}.json",
        mime="application/json",
    )


def _load_task_and_prompt(
    experiment_track: str,
    prompt_slug: str,
    df: pd.DataFrame,
) -> Tuple[Dict[str, Any], str]:
    prompt_unit = RESULTS_ROOT / experiment_track / prompt_slug
    task_path = prompt_unit / "task.json"
    prompt_path = prompt_unit / "prompt.txt"
    task: Dict[str, Any] = {}
    prompt_text = ""
    try:
        task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        if not df.empty:
            parsed = _parse_json_text(df.iloc[0]["task_params_json"])
            task = parsed if isinstance(parsed, dict) else {}
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8-sig")
    except OSError:
        if not df.empty:
            prompt_text = str(df.iloc[0]["prompt_text"] or "")
    return task, prompt_text


def _render_task(task: Dict[str, Any], prompt_text: str, df: pd.DataFrame) -> None:
    st.subheader("Task and experiment definition")
    left, right = st.columns((0.9, 1.1))
    with left:
        st.markdown("#### Task parameters")
        st.json(task, expanded=True)
        weights = {
            key: value for key, value in task.items()
            if key.startswith("w_") and _number(value) is not None
        }
        if weights:
            weight_df = pd.DataFrame({"Component": list(weights), "Weight": list(weights.values())})
            fig = px.bar(
                weight_df,
                x="Weight",
                y="Component",
                orientation="h",
                title="Score weights",
                color="Weight",
                color_continuous_scale=[[0, "#dce7ff"], [1, "#2f6bff"]],
            )
            fig.update_traces(
                hovertemplate="<b>%{y}</b><br>Weight %{x:.3f}<extra></extra>",
            )
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            _show_figure(fig, 330)
    with right:
        st.markdown("#### Prompt sent to the model")
        st.code(prompt_text or "Prompt text is not available.", wrap_lines=True)

    versions = df[[
        "experiment_track", "evaluation_mode", "task_set_version",
        "score_version", "simulator_version",
    ]].drop_duplicates()
    st.markdown("#### Versions represented in the selected runs")
    st.dataframe(versions, width="stretch", hide_index=True)


@st.cache_data(ttl=300, show_spinner="Reading live prices…")
def _load_ledger(
    results_root: str,
    price_mode: str,
) -> Tuple[pd.DataFrame, Optional[str], str]:
    """Build the ledger against a price list; live prices are read per refresh."""
    fallback: Dict[str, Any] = {}
    book = token_ledger.resolve_price_book(
        price_mode,
        on_fallback=lambda exc: fallback.update({"error": f"{type(exc).__name__}: {exc}"}),
    )
    rows = token_ledger.build_ledger(results_root, book)
    source = str(book.get("source") or book.get("path") or "unknown")
    if fallback:
        source = f"{source} — live prices unavailable ({fallback['error']})"
    return pd.DataFrame(rows), book.get("synced_at"), source


def _render_spend() -> None:
    """All-time token and cost ledger, priced both then and now.

    Deliberately ignores the task filters: this answers "what has this research
    consumed so far", which is a question about the whole programme, not about
    whichever task is on screen.
    """
    st.subheader("Token and spend ledger")
    st.caption(
        "Every run ever recorded, across all tasks and tracks — the filters "
        "above do not apply here. Each run is priced twice: at the rate frozen "
        "into the run itself, and at the rate of the selected price list."
    )

    snapshots = token_ledger.available_price_snapshots()
    options = ["Live OpenRouter prices", "Local registry (models.json)"] + [
        Path(path).stem for path in snapshots
    ]
    choice = st.selectbox(
        "Reprice against",
        options,
        key="spend_price_book",
        help=(
            "Live reads openrouter.ai/api/v1/models right now. The dated books "
            "are the price lists archived by past benchmark runs."
        ),
    )
    if choice == options[0]:
        price_mode = "live"
    elif choice == options[1]:
        price_mode = "local"
    else:
        price_mode = str(snapshots[options.index(choice) - 2])

    ledger, priced_at, price_source = _load_ledger(str(RESULTS_ROOT), price_mode)
    if ledger.empty:
        st.info("No benchmark runs have been recorded yet.")
        return

    totals = token_ledger.summarize(ledger.to_dict("records"))
    cols = st.columns(5)
    cols[0].metric("RUNS RECORDED", f"{totals['runs']:,}")
    cols[1].metric(
        "TOTAL TOKENS",
        f"{totals['total_tokens']:,.0f}",
        f"{totals['completion_tokens']:,.0f} generated",
    )
    cols[2].metric(
        "COST AT THE TIME",
        _fmt_number(totals["cost_then_usd"], 4, " $"),
        f"{totals['runs_priced_then']:,} of {totals['runs']:,} runs priced",
    )
    cols[3].metric(
        "COST AT SELECTED PRICES",
        _fmt_number(totals["cost_now_usd"], 4, " $"),
        str(priced_at or price_source),
    )
    change = totals["price_change_pct"]
    cols[4].metric(
        "LIKE-FOR-LIKE CHANGE",
        f"{change:+.1f}%" if change is not None else "—",
        f"{totals['comparable_runs']:,} comparable runs",
    )

    if totals["reasoning_tokens"]:
        st.caption(
            f"{totals['reasoning_tokens']:,.0f} of the generated tokens are hidden "
            "reasoning tokens — billed as output, absent from the response text."
        )

    monthly = (
        ledger[ledger["month"] != "unknown"]
        .groupby("month")
        .agg(
            Runs=("model", "count"),
            Tokens=("total_tokens", "sum"),
            **{
                "Cost then ($)": ("cost_then_usd", "sum"),
                "Cost now ($)": ("cost_now_usd", "sum"),
            },
        )
        .reset_index()
        .rename(columns={"month": "Month"})
        .sort_values("Month")
    )
    if not monthly.empty:
        monthly["Cumulative tokens"] = monthly["Tokens"].cumsum()
        fig = go.Figure()
        fig.add_bar(
            x=monthly["Month"],
            y=monthly["Tokens"],
            name="Tokens in month",
            marker_color="#2f6bff",
            hovertemplate="<b>%{x}</b><br>%{y:,.0f} tokens<extra></extra>",
        )
        fig.add_scatter(
            x=monthly["Month"],
            y=monthly["Cumulative tokens"],
            name="Cumulative",
            mode="lines+markers",
            line=dict(color="#16a34a", width=2),
            hovertemplate="<b>%{x}</b><br>%{y:,.0f} tokens to date<extra></extra>",
        )
        fig.update_layout(title="Token consumption over time")
        _show_figure(fig, 400, legend="bottom")

    by_model = (
        ledger.groupby("model")
        .agg(
            Runs=("model", "count"),
            Tokens=("total_tokens", "sum"),
            **{
                "Prompt tokens": ("prompt_tokens", "sum"),
                "Output tokens": ("completion_tokens", "sum"),
                "Cost then ($)": ("cost_then_usd", "sum"),
                "Cost now ($)": ("cost_now_usd", "sum"),
            },
        )
        .reset_index()
        .rename(columns={"model": "Model"})
        .sort_values("Cost now ($)", ascending=False)
    )
    st.markdown("#### Spend by model")
    _render_table(by_model)

    st.download_button(
        "Download the full per-run ledger (CSV)",
        data=ledger[list(token_ledger.LEDGER_EXPORT_COLUMNS)]
        .to_csv(index=False)
        .encode("utf-8-sig"),
        file_name="token_ledger.csv",
        mime="text/csv",
    )
    st.caption(f"Price source · {price_source}")
    st.caption(
        "Runs recorded before token accounting existed contribute no tokens, and "
        "runs without a frozen price contribute no historical cost — both are "
        "visible in the *priced* counts rather than being silently zeroed. "
        "`python scripts/token_report.py` prints the same ledger on the command line."
    )


def _render_task_notes(
    notes: str,
    experiment_track: str,
    prompt_slug: str,
) -> None:
    with st.container(border=True):
        heading, provenance = st.columns((0.72, 0.28))
        heading.markdown("#### Task notes")
        provenance.caption(f"{_track_label(experiment_track)} · {prompt_slug}")
        if notes:
            st.markdown(notes)
        else:
            st.caption("No task-specific notes have been recorded yet.")


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #101828;
            --muted: #667085;
            --line: #e3e9f2;
            --panel: rgba(255,255,255,.92);
            --blue: #2f6bff;
            --blue-deep: #1746d1;
            --navy: #09111f;
        }
        .stApp {
            background:
              radial-gradient(circle at 78% -8%, rgba(78,134,255,.12), transparent 27rem),
              linear-gradient(180deg, #f8faff 0%, #f3f6fb 48%, #f7f9fc 100%);
            color: var(--ink);
        }
        .block-container { max-width: 1540px; padding-top: .9rem; padding-bottom: 4rem; }
        h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.025em; }
        h2 { font-weight: 760; margin-top: 1.15rem; }
        h4 { font-weight: 720; }
        .hero {
            position: relative; overflow: hidden;
            display:flex; align-items:center; justify-content:space-between;
            flex-wrap:wrap; gap:1rem;
            padding: 1.1rem 1.6rem; margin-bottom: .9rem; border-radius: 18px;
            color: white;
            background:
              linear-gradient(110deg, rgba(47,107,255,.12), transparent 48%),
              linear-gradient(130deg, #09111f 0%, #101d36 58%, #123a75 100%);
            border: 1px solid rgba(255,255,255,.08);
            box-shadow: 0 26px 70px rgba(20,41,89,.22), inset 0 1px 0 rgba(255,255,255,.08);
        }
        .hero::after {
            content:""; position:absolute; inset:0; opacity:.22; pointer-events:none;
            background-image: linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
            background-size: 38px 38px;
            mask-image: linear-gradient(90deg, transparent 42%, black);
        }
        .hero-glow {
            position:absolute; width:330px; height:330px; right:-55px; top:-170px;
            border-radius:50%; background:#2f6bff; filter:blur(70px); opacity:.42;
        }
        .hero-main { position:relative; z-index:1; min-width:0; }
        .hero h1 {
            position:relative; z-index:1; color:white; margin:.25rem 0 0;
            font-size:clamp(1.3rem, 2.3vw, 1.85rem); line-height:1.05; letter-spacing:-.04em;
        }
        .hero h1 em { color:#86aaff; font-style:normal; font-weight:650; }
        .hero p { position:relative; z-index:1; color:#cbd7eb; margin:0; font-size:1.02rem; max-width:720px; }
        .eyebrow {
            position:relative; z-index:1; display:flex; align-items:center; gap:.55rem;
            color:#a8c2ff; font-size:.7rem; font-weight:800; letter-spacing:.16em;
        }
        .eyebrow span { width:7px; height:7px; border-radius:50%; background:#5eead4; box-shadow:0 0 14px #5eead4; }
        .hero-tags { position:relative; z-index:1; display:flex; flex-wrap:wrap; gap:.45rem; }
        .hero-tags span {
            color:#dce7ff; font-size:.64rem; font-weight:750; letter-spacing:.1em;
            padding:.34rem .62rem; border:1px solid rgba(168,194,255,.26); border-radius:999px;
            background:rgba(255,255,255,.055); backdrop-filter:blur(8px);
        }
        [data-testid="stMetric"] {
            position:relative; overflow:hidden; min-height:112px;
            background:linear-gradient(145deg, rgba(255,255,255,.98), rgba(248,250,255,.92));
            border:1px solid var(--line); border-radius:16px; padding:1rem 1.1rem;
            box-shadow:0 8px 28px rgba(16,24,40,.055), inset 0 1px 0 white;
        }
        [data-testid="stMetric"]::before {
            content:""; position:absolute; left:0; top:0; width:100%; height:3px;
            background:linear-gradient(90deg, var(--blue), #68a0ff 65%, transparent);
        }
        [data-testid="stMetricLabel"] { color:#738096; font-size:.72rem; font-weight:760; letter-spacing:.075em; }
        [data-testid="stMetricValue"] { color:var(--ink); font-size:1.78rem; font-weight:720; letter-spacing:-.035em; }
        [data-testid="stMetricDelta"] { color:#526078; }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap:.35rem; padding:.34rem; background:rgba(227,233,242,.66); border-radius:14px;
            width:max-content; max-width:100%; overflow-x:auto;
        }
        button[data-baseweb="tab"] {
            height:2.35rem; border-radius:10px; color:#65728a; border:0;
            font-size:.85rem; font-weight:680; padding:0 .92rem;
        }
        button[data-baseweb="tab"]:hover { color:var(--ink); background:rgba(255,255,255,.55); }
        button[data-baseweb="tab"][aria-selected="true"] {
            color:var(--blue-deep); background:white; box-shadow:0 3px 12px rgba(16,24,40,.09);
        }
        button[data-baseweb="tab"] [data-testid="stMarkdownContainer"] p { font-size:inherit; }
        div[data-testid="stDataFrame"] {
            border:1px solid var(--line); border-radius:15px; overflow:hidden;
            box-shadow:0 8px 26px rgba(16,24,40,.045); background:white;
        }
        [data-testid="stPlotlyChart"] {
            background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:17px;
            box-shadow:0 8px 28px rgba(16,24,40,.045); overflow:hidden;
        }
        [data-testid="stCaptionContainer"] { color:#748197; }
        .summary-strip {
            display:grid; grid-template-columns: 1.4fr 1fr; gap:1rem; margin:.85rem 0 1rem;
        }
        .summary-strip > div {
            position:relative; display:flex; flex-direction:column; min-width:0; padding:1.05rem 1.2rem;
            background:linear-gradient(135deg, rgba(255,255,255,.98), rgba(244,248,255,.9));
            border:1px solid var(--line); border-radius:16px;
            box-shadow:0 8px 25px rgba(16,24,40,.045);
        }
        .summary-strip span { color:#748197; font-size:.67rem; font-weight:800; letter-spacing:.11em; }
        .summary-strip strong { color:var(--ink); font-size:1.18rem; margin:.28rem 0 .12rem; overflow-wrap:anywhere; }
        .summary-strip small { color:#718096; }
        .run-title {
            display:flex; align-items:center; gap:.85rem; padding:1.08rem 1.2rem;
            background:linear-gradient(145deg, #fff, #f8faff); border:1px solid var(--line);
            border-radius:16px; margin:.8rem 0 1rem; box-shadow:0 8px 26px rgba(16,24,40,.05);
        }
        .run-title span { color:white; padding:.3rem .62rem; border-radius:999px; font-size:.72rem; font-weight:760; letter-spacing:.03em; }
        .run-title > div { display:flex; flex-direction:column; min-width:0; }
        .run-title strong { color:var(--ink); font-size:1.08rem; }
        .run-title small { display:block; color:#748197; overflow-wrap:anywhere; margin-top:.2rem; }
        .sidebar-brand {
            display:flex; align-items:center; gap:.72rem; padding:.25rem 0 1.1rem;
            border-bottom:1px solid rgba(255,255,255,.1); margin-bottom:1.15rem;
        }
        .sidebar-brand > span {
            display:grid; place-items:center; width:38px; height:38px; border-radius:11px;
            color:white; font-size:.76rem; font-weight:850; letter-spacing:.04em;
            background:linear-gradient(145deg, #3b75ff, #1649cc); box-shadow:0 8px 24px rgba(47,107,255,.35);
        }
        .sidebar-brand > div { display:flex; flex-direction:column; }
        .sidebar-brand strong { color:#f8fafc; font-size:.78rem; letter-spacing:.105em; }
        .sidebar-brand small { color:#92a4bf; font-size:.72rem; margin-top:.08rem; }
        [data-testid="stSidebar"] {
            background:linear-gradient(180deg, #0a1221 0%, #101a2d 58%, #0d1727 100%);
            border-right:1px solid #1d2a41;
        }
        [data-testid="stSidebar"] h3 { color:#8ea8d3; font-size:.69rem; letter-spacing:.13em; margin-top:.45rem; }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#c8d3e5; }
        [data-testid="stSidebar"] [role="radiogroup"] label * {
            color:#c8d3e5 !important; font-size:.84rem;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            min-height:0; background:rgba(255,255,255,.065); border-color:rgba(255,255,255,.1);
            box-shadow:none; padding:.6rem .7rem;
        }
        [data-testid="stSidebar"] [data-testid="stMetric"]::before { display:none; }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"],
        [data-testid="stSidebar"] [data-testid="stMetricValue"] { color:#e8eef8; }
        [data-testid="stSidebar"] .stButton button,
        [data-testid="stSidebar"] .stDownloadButton button {
            border-radius:10px; border:1px solid rgba(142,168,211,.26); color:#e7eef9;
            background:rgba(255,255,255,.055); font-weight:650;
        }
        [data-testid="stSidebar"] .stButton button:hover,
        [data-testid="stSidebar"] .stDownloadButton button:hover {
            border-color:#6490ff; color:white; background:rgba(47,107,255,.2);
        }
        .track-banner {
            display:flex; align-items:flex-start; justify-content:space-between; gap:2rem;
            padding:1.55rem 1.7rem; margin:.5rem 0 1.1rem; border-radius:18px;
            background:linear-gradient(135deg, #0e1a31, #14356e); color:white;
            border:1px solid rgba(255,255,255,.08); box-shadow:0 18px 45px rgba(20,41,89,.16);
        }
        .track-banner span, .contract-card span {
            color:#89adff; font-size:.67rem; font-weight:820; letter-spacing:.12em;
        }
        .track-banner .track-title {
            color:white; margin:.25rem 0 .35rem; font-size:1.55rem;
            font-weight:720; letter-spacing:-.025em;
        }
        .track-banner p { color:#c5d2e8; margin:0; max-width:760px; }
        .track-banner > strong {
            flex:0 0 auto; color:#b9f8e9; background:rgba(45,212,191,.1);
            border:1px solid rgba(94,234,212,.22); border-radius:999px;
            padding:.42rem .7rem; font-size:.66rem; letter-spacing:.08em;
        }
        .feedback-flow {
            display:grid; grid-template-columns:repeat(4, 1fr); gap:.85rem; margin-bottom:1rem;
        }
        .feedback-flow > div, .contract-card {
            background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:16px;
            padding:1.05rem 1.1rem; box-shadow:0 8px 26px rgba(16,24,40,.045);
        }
        .feedback-flow span {
            display:block; color:var(--blue); font-size:.7rem; font-weight:850; letter-spacing:.1em; margin-bottom:.45rem;
        }
        .feedback-flow strong { display:block; color:var(--ink); font-size:.98rem; margin-bottom:.25rem; }
        .feedback-flow p, .contract-card p { color:#718096; font-size:.84rem; line-height:1.5; margin:0; }
        .contract-card { margin-bottom:1rem; }
        .contract-card strong { display:block; color:var(--ink); margin:.35rem 0 .28rem; font-size:1rem; overflow-wrap:anywhere; }
        .stTextInput input, div[data-baseweb="select"] > div { border-radius:11px; }
        .stDownloadButton button, .stButton button { border-radius:10px; font-weight:650; }
        @media (max-width: 900px) {
            .hero { padding:1.1rem 1.15rem; border-radius:15px; }
            .summary-strip { grid-template-columns: 1fr; }
            .track-banner { flex-direction:column; gap:1rem; }
            .feedback-flow { grid-template-columns:1fr 1fr; }
        }
        @media (max-width: 600px) { .feedback-flow { grid-template-columns:1fr; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _select_experiment_track(runs: pd.DataFrame) -> str:
    st.sidebar.markdown("### EXPERIMENT TRACK")
    labels = [TRACK_LABELS[track] for track in EXPERIMENT_TRACKS]
    selected_label = st.sidebar.selectbox("Track", labels, key="experiment_track")
    selected_track = next(
        track for track, label in TRACK_LABELS.items() if label == selected_label
    )
    count = 0
    if not runs.empty and "experiment_track" in runs:
        count = int((runs["experiment_track"] == selected_track).sum())
    if selected_track == "feedback_driven" and count == 0:
        st.sidebar.caption("Workspace ready · execution planned")
    else:
        st.sidebar.caption(f"{count:,} recorded runs")
    return selected_track


def _render_feedback_preparation(prompt_slug: Optional[str] = None) -> None:
    safe_prompt = html.escape(prompt_slug or "<future-task-slug>")
    st.markdown(
        f"""
        <div class="track-banner">
          <div><span>PLANNED TRACK</span><div class="track-title">Feedback-driven evaluation</div>
          <p>The workspace is reserved and isolated from zero-shot results. Execution logic is intentionally not enabled yet.</p></div>
          <strong>READY FOR DESIGN</strong>
        </div>
        <div class="feedback-flow">
          <div><span>01</span><strong>Baseline</strong><p>Generate and score one independent initial design.</p></div>
          <div><span>02</span><strong>Feedback</strong><p>Package simulator metrics, violations, and score signals.</p></div>
          <div><span>03</span><strong>Refinement</strong><p>Run bounded improvement rounds with explicit stopping rules.</p></div>
          <div><span>04</span><strong>Audit</strong><p>Compare score gain against total calls, tokens, latency, and cost.</p></div>
        </div>
        <div class="contract-card">
          <span>RESERVED WORKSPACE</span><strong>results/feedback_driven/{safe_prompt}/</strong>
          <p>This track owns a separate task catalog. Future records will be stored as complete episodes so every feedback round remains traceable.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        st.markdown("#### Episode-level metrics")
        st.markdown(
            "- Initial, final, and best score\n"
            "- Absolute and relative score gain\n"
            "- Successful refinement rate\n"
            "- Stop reason and completed rounds"
        )
    with right:
        st.markdown("#### Full-budget accounting")
        st.markdown(
            "- Total model calls and simulator evaluations\n"
            "- Prompt, output, and aggregate tokens\n"
            "- End-to-end latency and estimated cost\n"
            "- Complete prompt, feedback, and design lineage"
        )
    st.info(
        "This screen is a structural placeholder only. No feedback loop, model call, "
        "or iterative runner has been implemented."
    )


def _values(df: pd.DataFrame, column: str) -> List[str]:
    if df.empty or column not in df:
        return []
    return sorted(df[column].dropna().astype(str).unique().tolist())


def _seed_state(key: str, value: Any) -> None:
    """Seed a widget's state once, then leave the user's choice alone."""
    if key not in st.session_state:
        st.session_state[key] = value


def _prune_state(key: str, options: Sequence[Any]) -> None:
    """Drop stored selections that no longer exist in the current options."""
    stored = st.session_state.get(key)
    if isinstance(stored, list):
        kept = [value for value in stored if value in options]
        if kept != stored:
            st.session_state[key] = kept


def _select_task(runs: pd.DataFrame, experiment_track: str) -> str:
    """Pick the task unit. Every other filter operates inside this scope."""
    st.sidebar.markdown("### TASK")
    counts = (
        runs["prompt"].astype(str).value_counts().to_dict()
        if not runs.empty else {}
    )
    on_disk = discover_prompt_units(str(RESULTS_ROOT), experiment_track)
    options = sorted(set(counts) | set(on_disk))
    if not options:
        return ""

    default_slug = options[-1]
    if not runs.empty and runs["timestamp"].notna().any():
        latest = runs.dropna(subset=["timestamp"]).sort_values("timestamp")
        default_slug = str(latest.iloc[-1]["prompt"])
    key = f"task_{experiment_track}"
    _seed_state(key, default_slug if default_slug in options else options[-1])
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[-1]

    selected = st.sidebar.selectbox(
        "Task",
        options,
        key=key,
        format_func=lambda slug: f"{slug} · {counts.get(slug, 0)} runs",
        help="Each task owns its own prompt, scoring config, and results.",
    )
    if counts.get(selected, 0) == 0:
        st.sidebar.caption("This task has a definition on disk but no recorded runs yet.")
    return selected


def _filter_summary(scoped: pd.DataFrame, total: int) -> None:
    models = scoped["model"].nunique() if not scoped.empty else 0
    success = int((scoped["status"] == "success").sum()) if not scoped.empty else 0
    st.caption(
        f"**{len(scoped):,} / {total:,} runs** in view · {models:,} models · "
        f"{success:,} successful simulations"
    )


def _render_filter_bar(runs: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Flat, non-cascading filters.

    Every option list is derived from the full task scope, so choosing one
    filter never removes options from another one. That is what makes a
    selection survive while the rest of the view is being narrowed down.
    """
    models = _values(runs, "model")
    statuses = _values(runs, "status")
    sources = _values(runs, "source")
    reasonings = _values(runs, "reasoning")
    versions = _values(runs, "score_version")

    model_key = f"f_models_{scope}"
    status_key = f"f_status_{scope}"
    source_key = f"f_source_{scope}"
    reasoning_key = f"f_reasoning_{scope}"
    version_key = f"f_version_{scope}"
    score_key = f"f_score_{scope}"
    keys = [
        model_key, status_key, source_key, reasoning_key,
        version_key, score_key, f"f_taskid_{scope}",
    ]

    status_labels = [_status_label(status) for status in statuses]
    _seed_state(model_key, list(models))
    _seed_state(status_key, list(status_labels))
    _seed_state(source_key, list(sources))
    _seed_state(reasoning_key, list(reasonings))
    # Mixing score versions in one leaderboard compares incomparable numbers,
    # so only the newest version is on by default.
    _seed_state(version_key, versions[-1:] if versions else [])
    for key, options in (
        (model_key, models),
        (status_key, status_labels),
        (source_key, sources),
        (reasoning_key, reasonings),
        (version_key, versions),
    ):
        _prune_state(key, options)

    run_counts = runs["model"].astype(str).value_counts().to_dict()
    success_counts = (
        runs[runs["status"] == "success"]["model"].astype(str).value_counts().to_dict()
    )
    mean_scores = (
        runs[runs["status"] != "client_error"]
        .groupby("model")["score"].mean().to_dict()
    )

    def _set_models(values: Sequence[str]) -> None:
        st.session_state[model_key] = list(values)

    def _reset_all() -> None:
        for key in keys:
            st.session_state.pop(key, None)

    with st.container(border=True):
        head, reset = st.columns((4.0, 1.0))
        head.markdown("#### Filters")
        reset.button(
            "Reset filters",
            width="stretch",
            on_click=_reset_all,
            key=f"reset_{scope}",
        )

        st.multiselect(
            "Models",
            models,
            key=model_key,
            format_func=lambda model: (
                f"{model} · {run_counts.get(model, 0)} runs"
                f" · {success_counts.get(model, 0)} ok"
            ),
            placeholder="Search a model…",
            help="Type to search. Use the shortcuts below to switch cohorts quickly.",
        )
        shortcuts = st.columns(4)
        shortcuts[0].button(
            "All models", width="stretch", key=f"m_all_{scope}",
            on_click=_set_models, args=(models,),
        )
        shortcuts[1].button(
            "Clear", width="stretch", key=f"m_none_{scope}",
            on_click=_set_models, args=([],),
        )
        shortcuts[2].button(
            "Only models that succeeded", width="stretch", key=f"m_ok_{scope}",
            on_click=_set_models,
            args=([model for model in models if success_counts.get(model, 0) > 0],),
        )
        def _rank_value(model: str) -> float:
            score = _number(mean_scores.get(model))
            return score if score is not None else -1.0

        top_models = sorted(models, key=_rank_value, reverse=True)[:5]
        shortcuts[3].button(
            "Top 5 by mean score", width="stretch", key=f"m_top_{scope}",
            on_click=_set_models, args=(top_models,),
        )

        row = st.columns((1.25, 1.0, 1.0))
        with row[0]:
            st.pills(
                "Outcome",
                status_labels,
                selection_mode="multi",
                key=status_key,
            )
        with row[1]:
            st.pills("Source", sources, selection_mode="multi", key=source_key)
        with row[2]:
            st.pills("Reasoning", reasonings, selection_mode="multi", key=reasoning_key)

        task_ids = _values(runs, "task_id")
        task_id_key = f"f_taskid_{scope}"
        if len(task_ids) > 1:
            _seed_state(task_id_key, list(task_ids))
            _prune_state(task_id_key, task_ids)
            st.pills("Task ID", task_ids, selection_mode="multi", key=task_id_key)

        bottom = st.columns((1.2, 1.0))
        with bottom[0]:
            score_range = st.slider(
                "Score range",
                min_value=0.0,
                max_value=1.0,
                value=(0.0, 1.0),
                step=0.01,
                key=score_key,
            )
        with bottom[1]:
            if len(versions) > 1:
                st.pills(
                    "Score version",
                    versions,
                    selection_mode="multi",
                    key=version_key,
                    help="Older versions scored the same designs differently.",
                )
            else:
                st.caption(f"Score version · {versions[0] if versions else 'unknown'}")

        selected_models = st.session_state.get(model_key, [])
        selected_statuses = st.session_state.get(status_key, [])
        selected_sources = st.session_state.get(source_key, [])
        selected_reasonings = st.session_state.get(reasoning_key, [])
        selected_versions = st.session_state.get(version_key, versions)

        scoped = runs
        if selected_models:
            scoped = scoped[scoped["model"].isin(selected_models)]
        else:
            scoped = scoped.iloc[0:0]
        if selected_statuses:
            scoped = scoped[scoped["status_label"].isin(selected_statuses)]
        if selected_sources:
            scoped = scoped[scoped["source"].isin(selected_sources)]
        if selected_reasonings:
            scoped = scoped[scoped["reasoning"].isin(selected_reasonings)]
        if selected_versions and len(versions) > 1:
            scoped = scoped[scoped["score_version"].isin(selected_versions)]
        selected_task_ids = st.session_state.get(task_id_key, [])
        if selected_task_ids and len(task_ids) > 1:
            scoped = scoped[scoped["task_id"].astype(str).isin(selected_task_ids)]
        low, high = score_range
        if (low, high) != (0.0, 1.0):
            scoped = scoped[scoped["score"].between(low, high)]

        _filter_summary(scoped, len(runs))
        if not selected_models:
            st.caption("No model is selected — pick at least one, or press *All models*.")

    return scoped.copy()


def main() -> None:
    st.set_page_config(
        page_title="SM-Bench Lab",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
          <span>SM</span><div><strong>SM-BENCH</strong><small>Evaluation console</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    runs, load_errors = load_all_runs(str(RESULTS_ROOT))
    selected_track = _select_experiment_track(runs)
    track_runs = (
        runs[runs["experiment_track"] == selected_track].copy()
        if not runs.empty else runs
    )

    refresh_col, health_col = st.sidebar.columns((1, 1))
    if refresh_col.button("Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    health_col.metric("TRACK RUNS", f"{len(track_runs):,}")
    _render_header(selected_track)

    if selected_track == "feedback_driven" and track_runs.empty:
        prompt_units = discover_prompt_units(str(RESULTS_ROOT), selected_track)
        if prompt_units:
            preferred = (
                "heat_exchanger_hard_v2"
                if "heat_exchanger_hard_v2" in prompt_units else prompt_units[-1]
            )
            selected_prompt = st.sidebar.selectbox(
                "Prompt set",
                prompt_units,
                index=prompt_units.index(preferred),
                key="feedback_prompt_preview",
            )
        else:
            selected_prompt = None
        _render_feedback_preparation(selected_prompt)
        return

    if track_runs.empty:
        st.warning("No benchmark runs have been recorded for this experiment track yet.")
        st.code("python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model MODEL")
        st.stop()

    selected_prompt = _select_task(track_runs, selected_track)
    task_runs = track_runs[track_runs["prompt"].astype(str) == selected_prompt].copy()

    task, prompt_text = _load_task_and_prompt(selected_track, selected_prompt, task_runs)
    task_notes = load_task_notes(str(RESULTS_ROOT), selected_track, selected_prompt)

    if task_runs.empty:
        st.warning(f"No runs have been recorded for `{selected_prompt}` yet.")
        st.code(
            "python scripts/run_api_benchmark.py "
            f"--prompt {selected_prompt} --model MODEL"
        )
        st.stop()

    filtered = _render_filter_bar(task_runs, f"{selected_track}::{selected_prompt}")
    leaderboard = aggregate_runs(filtered, task)

    if load_errors:
        with st.sidebar.expander(f"{len(load_errors)} load warnings"):
            st.dataframe(pd.DataFrame(load_errors), hide_index=True, width="stretch")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### EXPORT")
    export = _visible_export(filtered)
    st.sidebar.download_button(
        "Download filtered CSV",
        data=export.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{selected_prompt}_runs.csv",
        mime="text/csv",
        width="stretch",
    )
    st.sidebar.download_button(
        "Download filtered JSONL",
        data="\n".join(filtered["raw_record"].tolist()) + "\n",
        file_name=f"{selected_prompt}_runs.jsonl",
        mime="application/x-ndjson",
        width="stretch",
    )

    if filtered.empty:
        st.warning(
            "No run matches the current filters. Press **Reset filters** above, "
            "or widen the outcome and model selection."
        )
        st.stop()

    (
        overview_tab, explorer_tab, leaderboard_tab, engineering_tab,
        efficiency_tab, spend_tab, task_tab,
    ) = st.tabs([
        "Overview",
        "Runs",
        "Leaderboard",
        "Engineering",
        "Reliability",
        "Spend",
        "Task",
    ])
    with overview_tab:
        _render_overview(filtered, leaderboard, task)
    with explorer_tab:
        _render_run_explorer(filtered)
    with leaderboard_tab:
        _render_leaderboard(filtered, leaderboard)
    with engineering_tab:
        _render_engineering(filtered, task)
    with efficiency_tab:
        _render_efficiency(filtered)
    with spend_tab:
        _render_spend()
    with task_tab:
        _render_task_notes(task_notes, selected_track, selected_prompt)
        _render_task(task, prompt_text, filtered)


if __name__ == "__main__":
    main()
