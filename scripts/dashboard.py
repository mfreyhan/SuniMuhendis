import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px
import plotly.graph_objects as go

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="LLM Benchmark Dashboard", layout="wide")
st.title("🔥 Heat Exchanger LLM Benchmark Dashboard")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RESULTS_ROOT = os.path.join(REPO_ROOT, 'results')

def flatten_record(d: dict, run_type: str, prompt: str) -> dict:
    m = d.get("metrics", {}) or {}
    design = d.get("design", {}) or {}
    return {
        "Run Type": run_type,
        "Prompt": prompt,
        "Task ID": d.get("task_id", prompt),
        "Score Version": d.get("score_version", "heat_exchanger_score_v1"),
        "Model": d.get("model_name", "Unknown"),
        "Total Score": d.get("total_score", d.get("total_reward", 0.0)),
        "Status": d.get("status", "unknown"),
        "Heat Duty (kW)": m.get("heat_duty_W", 0.0) / 1000.0,
        "Cost ($/y)": m.get("cost_annualised_USD_per_yr", 0.0),
        "Effectiveness (%)": m.get("effectiveness", 0.0) * 100,
        "DP Tube (kPa)": m.get("dp_tube_Pa", 0.0) / 1000.0,
        "DP Shell (kPa)": m.get("dp_shell_Pa", 0.0) / 1000.0,
        "Warnings": m.get("num_warnings", 0.0),
        "Tubes": design.get("number_of_tubes", 0),
        "Area (m2)": m.get("area_m2", 0.0),
    }

def load_jsonl_runs(run_type: str) -> pd.DataFrame:
    rows = []
    # run_type = "api_runs" or "manual_runs"
    # Old pattern: results/<prompt>/api_runs/<model>.jsonl
    # New pattern: results/<prompt>/api_runs/<task_id>/<model>.jsonl
    pattern_old = os.path.join(RESULTS_ROOT, "*", run_type, "*.jsonl")
    pattern_new = os.path.join(RESULTS_ROOT, "*", run_type, "*", "*.jsonl")
    
    paths = glob.glob(pattern_old) + glob.glob(pattern_new)
    for path in set(paths):
        # Infer prompt from path structure depending on depth
        parts = path.split(os.sep)
        try:
            run_type_idx = parts.index(run_type)
            prompt = parts[run_type_idx - 1]
        except ValueError:
            prompt = "unknown"
            
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    d = json.loads(line)
                    rows.append(flatten_record(d, run_type, prompt))
                except json.JSONDecodeError:
                    pass
    return pd.DataFrame(rows)

def aggregate_runs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    out = []
    for model, g in df.groupby("Model"):
        n_total = len(g)
        valid_runs = g[g["Status"] != "client_error"]
        n_valid = len(valid_runs)
        succ = g[g["Status"] == "success"]
        
        row = {
            "Model": model,
            "Valid Runs": n_valid,
            "Success %": 100.0 * len(succ) / n_valid if n_valid > 0 else 0.0,
            "Flawless %": 100.0 * len(succ[succ["Warnings"] == 0]) / len(succ) if len(succ) else 0.0,
            "Mean Score": succ["Total Score"].mean() if len(succ) else 0.0,
            "Min Score": succ["Total Score"].min() if len(succ) else 0.0,
            "Max Score": succ["Total Score"].max() if len(succ) else 0.0,
            "Std Dev": succ["Total Score"].std() if len(succ) > 1 else 0.0,
        }
        eng_cols = ["Heat Duty (kW)", "Cost ($/y)", "Effectiveness (%)",
                    "DP Tube (kPa)", "DP Shell (kPa)", "Warnings", "Area (m2)"]
        for c in eng_cols:
            row[c] = succ[c].mean() if len(succ) else 0.0
        out.append(row)
    
    cols = ["Model", "Valid Runs", "Success %", "Flawless %", "Mean Score", "Min Score", "Max Score", "Std Dev",
            "Heat Duty (kW)", "Cost ($/y)", "Effectiveness (%)",
            "DP Tube (kPa)", "DP Shell (kPa)", "Warnings", "Area (m2)"]
    return pd.DataFrame(out)[cols]

def render_charts(df_raw: pd.DataFrame, df_agg: pd.DataFrame):
    st.subheader("📈 Visual Comparison")
    col1, col2 = st.columns(2)
    with col1:
        df_succ = df_raw[df_raw["Status"] == "success"]
        fig_score = px.box(df_succ, x="Model", y="Total Score", color="Model", 
                           title="Score Distribution (Success Only)", points="all")
        st.plotly_chart(fig_score, width='stretch')
        
        fig_heat = px.bar(df_agg, x="Model", y="Heat Duty (kW)", color="Model",
                          title="Average Heat Duty (kW)")
        fig_heat.add_hline(y=150, line_dash="dash", line_color="red",
                           annotation_text="Target Example (150kW)")
        st.plotly_chart(fig_heat, width='stretch')
    with col2:
        st.plotly_chart(px.bar(df_agg, x="Model", y="Cost ($/y)", color="Model",
                               title="Average Annual Cost ($/y)"),
                        width='stretch')
        st.plotly_chart(px.bar(df_agg, x="Model", y="Warnings", color="Model",
                               title="Avg. Mechanical Warnings (Success Only)"),
                        width='stretch')

# UI
st.sidebar.header("Data Source")
source = st.sidebar.radio(
    "Select Source",
    ["All Runs (Combined)", "API Runs (api_runs/)", "Manual Runs (manual_runs/)"],
    key="source_selector"
)

if st.sidebar.button("Refresh"):
    st.rerun()
st.sidebar.markdown("---")

if source.startswith("All"):
    df_api = load_jsonl_runs("api_runs")
    df_man = load_jsonl_runs("manual_runs")
    if not df_api.empty and not df_man.empty:
        runs_df = pd.concat([df_api, df_man], ignore_index=True)
    elif not df_api.empty:
        runs_df = df_api
    else:
        runs_df = df_man
        
    if not runs_df.empty:
        runs_df["Model"] = runs_df.apply(lambda r: f"{r['Model']} [{'API' if r['Run Type'] == 'api_runs' else 'Manual'}]", axis=1)
    run_type_name = "all"
    run_type = "all"
else:
    run_type = "api_runs" if source.startswith("API") else "manual_runs"
    run_type_name = run_type
    runs_df = load_jsonl_runs(run_type)

if runs_df.empty:
    st.warning(f"No `{run_type_name}` records found yet. Please run the test scripts first.")
    st.stop()

st.sidebar.header("Filters")

# Prompt filter
prompts = sorted(runs_df["Prompt"].unique().tolist())
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = prompts[0] if prompts else None
selected_prompt = st.sidebar.selectbox("Prompt", prompts, index=prompts.index(st.session_state.current_prompt) if st.session_state.current_prompt in prompts else 0)
st.session_state.current_prompt = selected_prompt

filtered_by_prompt = runs_df[runs_df["Prompt"] == selected_prompt]

# Task ID filter
tasks = sorted(filtered_by_prompt["Task ID"].unique().tolist())
if "current_task" not in st.session_state:
    st.session_state.current_task = tasks[0] if tasks else None
selected_task = st.sidebar.selectbox("Task ID", tasks, index=tasks.index(st.session_state.current_task) if st.session_state.current_task in tasks else 0)
st.session_state.current_task = selected_task

filtered_by_task = filtered_by_prompt[filtered_by_prompt["Task ID"] == selected_task]

# Score version filter
score_versions = sorted(filtered_by_task["Score Version"].unique().tolist())
if "current_score_version" not in st.session_state:
    st.session_state.current_score_version = score_versions[-1] if score_versions else None
selected_score = st.sidebar.selectbox("Score Version", score_versions, index=score_versions.index(st.session_state.current_score_version) if st.session_state.current_score_version in score_versions else 0)
st.session_state.current_score_version = selected_score

sub_df = filtered_by_task[filtered_by_task["Score Version"] == selected_score]
agg_df = aggregate_runs(sub_df).sort_values("Mean Score", ascending=False)

st.subheader(f"📊 Average Results")
st.markdown(f"**Task ID**: `{selected_task}` | **Prompt**: `{selected_prompt}` | **Score Version**: `{selected_score}`")
st.caption("Score statistics cover all runs (including failures), whereas engineering metrics are the average of 'success' runs only.")
st.dataframe(
    agg_df.style
       .highlight_max(subset=["Mean Score", "Heat Duty (kW)", "Success %"], color="lightgreen")
       .highlight_min(subset=["Cost ($/y)", "Warnings"], color="lightgreen")
       .format(precision=3),
    width='stretch',
)

render_charts(sub_df, agg_df)

csv = agg_df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Download as CSV (average)", data=csv,
                           file_name=f"benchmark_{selected_task}_{selected_prompt}_{run_type}_avg.csv", mime="text/csv")
