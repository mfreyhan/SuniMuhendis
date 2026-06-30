import streamlit as st
import pandas as pd
import json
import os
import glob
import plotly.express as px

# .env (HF_TOKEN vb.) tutarlilik icin; dashboard icin sart degil.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="LLM Benchmark Dashboard", layout="wide")
st.title("🔥 Heat Exchanger LLM Benchmark Dashboard")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MANUAL_DB = os.path.join(REPO_ROOT, 'reports', 'benchmark_results.json')
RESULTS_ROOT = os.path.join(REPO_ROOT, 'results')


# ──────────────────────────────────────────────────────────────────────────
#  Ortak: tek bir kaydi (run/record) duz bir satira cevirir
# ──────────────────────────────────────────────────────────────────────────
def flatten_record(d: dict) -> dict:
    m = d.get("metrics", {}) or {}
    design = d.get("design", {}) or {}
    return {
        "Model": d.get("model_name", "Unknown"),
        "Total Score": d.get("total_reward", 0.0),
        "Heat Duty (kW)": m.get("heat_duty_W", 0.0) / 1000.0,
        "Cost ($/y)": m.get("cost_annualised_USD_per_yr", 0.0),
        "Effectiveness (%)": m.get("effectiveness", 0.0) * 100,
        "DP Tube (kPa)": m.get("dp_tube_Pa", 0.0) / 1000.0,
        "DP Shell (kPa)": m.get("dp_shell_Pa", 0.0) / 1000.0,
        "Warnings": m.get("num_warnings", 0.0),
        "Tubes": design.get("number_of_tubes", 0),
        "Area (m2)": m.get("area_m2", 0.0),
    }


# ──────────────────────────────────────────────────────────────────────────
#  Kaynak 1: HF Benchmark — results/<slug>/benchmark/<model>/*.json
#  Her (prompt, model) altindaki ~N run ORTALANIR.
# ──────────────────────────────────────────────────────────────────────────
def load_results_runs() -> pd.DataFrame:
    rows = []
    pattern = os.path.join(RESULTS_ROOT, "*", "benchmark", "*", "*.json")
    for path in glob.glob(pattern):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        row = flatten_record(d)
        # prompt slug = results/<slug>/benchmark/<model>/file.json
        row["Prompt"] = d.get("prompt_slug") or os.path.basename(
            os.path.dirname(os.path.dirname(os.path.dirname(path)))
        )
        row["Status"] = d.get("status", "unknown")
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_runs(df: pd.DataFrame) -> pd.DataFrame:
    """Model basina ortalama: score TUM run'lar uzerinden; muhendislik metrikleri
    yalniz BASARILI run'lar uzerinden (basarisiz run'larin 0'lari metrikleri bozmasin)."""
    eng_cols = ["Heat Duty (kW)", "Cost ($/y)", "Effectiveness (%)",
                "DP Tube (kPa)", "DP Shell (kPa)", "Warnings", "Area (m2)"]
    out = []
    for model, g in df.groupby("Model"):
        n = len(g)
        succ = g[g["Status"] == "success"]
        row = {
            "Model": model,
            "Runs": n,
            "Success %": 100.0 * len(succ) / n if n else 0.0,
            "Total Score": g["Total Score"].mean(),
        }
        for c in eng_cols:
            row[c] = succ[c].mean() if len(succ) else 0.0
        out.append(row)
    cols = ["Model", "Runs", "Success %", "Total Score",
            "Heat Duty (kW)", "Cost ($/y)", "Effectiveness (%)",
            "DP Tube (kPa)", "DP Shell (kPa)", "Warnings", "Area (m2)"]
    return pd.DataFrame(out)[cols] if out else pd.DataFrame(columns=cols)


# ──────────────────────────────────────────────────────────────────────────
#  Kaynak 2: Manuel — reports/benchmark_results.json (her kayit ayri satir)
# ──────────────────────────────────────────────────────────────────────────
def load_manual_data() -> pd.DataFrame:
    if not os.path.exists(MANUAL_DB):
        return pd.DataFrame()
    try:
        with open(MANUAL_DB, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return pd.DataFrame()
    except json.JSONDecodeError:
        return pd.DataFrame()

    rows = []
    for d in data:
        row = flatten_record(d)
        w = d.get("weights", {}) or {}
        row["Config Signature"] = (
            f"Heat:{w.get('w_heat', 0):.2f} | Cost:{w.get('w_cost', 0):.2f} | "
            f"Eff:{w.get('w_eff', 0):.2f} | Tube:{w.get('w_drop_tube', 0):.2f} | "
            f"Shell:{w.get('w_drop_shell', 0):.2f}"
        )
        rows.append(row)
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────
#  Ortak grafikler
# ──────────────────────────────────────────────────────────────────────────
def render_charts(df: pd.DataFrame):
    st.subheader("📈 Görsel Karşılaştırma")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.bar(df, x="Model", y="Total Score", color="Model",
                               title="Toplam Ödül Skoru (Total Score)"),
                        use_container_width=True)
        fig_heat = px.bar(df, x="Model", y="Heat Duty (kW)", color="Model",
                          title="Isı Transferi (kW)")
        fig_heat.add_hline(y=150, line_dash="dash", line_color="red",
                           annotation_text="Hedef (150kW)")
        st.plotly_chart(fig_heat, use_container_width=True)
    with col2:
        st.plotly_chart(px.bar(df, x="Model", y="Cost ($/y)", color="Model",
                               title="Yıllık Maliyet ($/y)"),
                        use_container_width=True)
        st.plotly_chart(px.bar(df, x="Model", y="Warnings", color="Model",
                               title="Mekanik Uyarı Sayısı (Warnings)"),
                        use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════════════════════════════════
st.sidebar.header("Veri Kaynağı")
source = st.sidebar.radio(
    "Kaynak seçin",
    ["HF Benchmark (results/)", "Manuel (reports/)"],
)

if st.sidebar.button("Yenile (Refresh)"):
    st.rerun()
st.sidebar.markdown("---")

if source == "HF Benchmark (results/)":
    runs = load_results_runs()
    if runs.empty:
        st.warning(
            "Henüz HF benchmark sonucu yok. Önce çalıştırın:\n\n"
            "`python3 scripts/run_hf_benchmark.py --prompt heat_exchanger_v1 --repeats 5`"
        )
        st.stop()

    st.sidebar.header("Filtreler")
    prompts = sorted(runs["Prompt"].unique().tolist())
    selected_prompt = st.sidebar.selectbox("Prompt", prompts)

    sub = runs[runs["Prompt"] == selected_prompt]
    agg = aggregate_runs(sub)
    agg = agg.sort_values("Total Score", ascending=False)

    st.subheader(f"📊 Ortalama Sonuçlar — Prompt: `{selected_prompt}`")
    st.caption("Her satır, o model klasöründeki tüm testlerin ortalamasıdır "
               "(score tüm run'lar; mühendislik metrikleri yalnız başarılı run'lar).")
    st.dataframe(
        agg.style
           .highlight_max(subset=["Total Score", "Heat Duty (kW)", "Success %"], color="lightgreen")
           .highlight_min(subset=["Cost ($/y)", "Warnings"], color="lightgreen")
           .format(precision=2),
        use_container_width=True,
    )
    render_charts(agg)

    csv = agg.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("CSV Olarak İndir (ortalama)", data=csv,
                               file_name=f"benchmark_{selected_prompt}_avg.csv", mime="text/csv")

else:
    df = load_manual_data()
    if df.empty:
        st.warning("Henüz manuel test sonucu yok. `python3 scripts/run_llm_eval.py` ile test edin.")
        st.stop()

    st.sidebar.header("Filtreler")
    configs = ["All"] + df["Config Signature"].unique().tolist()
    selected_config = st.sidebar.selectbox("Görev Ağırlığı Konfigürasyonu", configs)
    if selected_config != "All":
        df = df[df["Config Signature"] == selected_config]

    st.subheader("📊 Manuel Değerlendirme Sonuçları (her kayıt ayrı)")
    st.dataframe(
        df.style
          .highlight_max(subset=["Total Score", "Heat Duty (kW)"], color="lightgreen")
          .highlight_min(subset=["Cost ($/y)", "Warnings"], color="lightgreen")
          .format(precision=2),
        use_container_width=True,
    )
    render_charts(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("CSV Olarak İndir", data=csv,
                               file_name="manual_benchmark_results.csv", mime="text/csv")
