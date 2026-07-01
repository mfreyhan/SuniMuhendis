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
    pattern = os.path.join(RESULTS_ROOT, "*", run_type, "*.jsonl")
    for path in glob.glob(pattern):
        # Extract prompt folder name
        prompt = os.path.basename(os.path.dirname(os.path.dirname(path)))
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
        
        # Skor ve diger metrikler SADECE basarili run'lar uzerinden hesaplanir
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
    st.subheader("📈 Görsel Karşılaştırma")
    col1, col2 = st.columns(2)
    with col1:
        # Boxplot for Score distribution (Sadece basarililar gosterilsin)
        df_succ = df_raw[df_raw["Status"] == "success"]
        fig_score = px.box(df_succ, x="Model", y="Total Score", color="Model", 
                           title="Skor Dağılımı (Sadece Başarılı)", points="all")
        st.plotly_chart(fig_score, use_container_width=True)
        
        fig_heat = px.bar(df_agg, x="Model", y="Heat Duty (kW)", color="Model",
                          title="Ortalama Isı Transferi (kW)")
        fig_heat.add_hline(y=150, line_dash="dash", line_color="red",
                           annotation_text="Örnek Hedef (150kW)")
        st.plotly_chart(fig_heat, use_container_width=True)
    with col2:
        st.plotly_chart(px.bar(df_agg, x="Model", y="Cost ($/y)", color="Model",
                               title="Ortalama Yıllık Maliyet ($/y)"),
                        use_container_width=True)
        st.plotly_chart(px.bar(df_agg, x="Model", y="Warnings", color="Model",
                               title="Ort. Mekanik Uyarı (Sadece Başarılılarda)"),
                        use_container_width=True)

# UI
st.sidebar.header("Veri Kaynağı")
source = st.sidebar.radio(
    "Kaynak seçin",
    ["Tüm Çalıştırmalar (Birlikte)", "API Çalıştırmaları (api_runs/)", "Manuel Çalıştırmalar (manual_runs/)"],
)

if st.sidebar.button("Yenile (Refresh)"):
    st.rerun()
st.sidebar.markdown("---")

if source.startswith("Tüm"):
    df_api = load_jsonl_runs("api_runs")
    df_man = load_jsonl_runs("manual_runs")
    if not df_api.empty and not df_man.empty:
        runs_df = pd.concat([df_api, df_man], ignore_index=True)
    elif not df_api.empty:
        runs_df = df_api
    else:
        runs_df = df_man
        
    if not runs_df.empty:
        # Modellerin karismamasi icin ismin yanina kaynagi yazalim
        runs_df["Model"] = runs_df.apply(lambda r: f"{r['Model']} [{'API' if r['Run Type'] == 'api_runs' else 'Manual'}]", axis=1)
    run_type_name = "tümü"
    run_type = "tümü"
else:
    run_type = "api_runs" if source.startswith("API") else "manual_runs"
    run_type_name = run_type
    runs_df = load_jsonl_runs(run_type)

if runs_df.empty:
    st.warning(f"Henüz `{run_type_name}` kaydı bulunamadı. Lütfen önce test scriptlerini çalıştırın.")
    st.stop()

st.sidebar.header("Filtreler")
prompts = sorted(runs_df["Prompt"].unique().tolist())
selected_prompt = st.sidebar.selectbox("Görev (Prompt)", prompts)

sub_df = runs_df[runs_df["Prompt"] == selected_prompt]
agg_df = aggregate_runs(sub_df).sort_values("Mean Score", ascending=False)

st.subheader(f"📊 Ortalama Sonuçlar — Görev: `{selected_prompt}`")
st.caption("Score istatistikleri tüm koşuları (başarısızlar dahil) kapsarken, mühendislik metrikleri sadece 'success' (başarılı) koşuların ortalamasıdır.")
st.dataframe(
    agg_df.style
       .highlight_max(subset=["Mean Score", "Heat Duty (kW)", "Success %"], color="lightgreen")
       .highlight_min(subset=["Cost ($/y)", "Warnings"], color="lightgreen")
       .format(precision=3),
    use_container_width=True,
)

render_charts(sub_df, agg_df)

csv = agg_df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("CSV Olarak İndir (ortalama)", data=csv,
                           file_name=f"benchmark_{selected_prompt}_{run_type}_avg.csv", mime="text/csv")
