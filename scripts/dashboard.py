import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="LLM Benchmark Dashboard", layout="wide")

st.title("🔥 Heat Exchanger LLM Benchmark Dashboard")

# 1. Load Data
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../reports/benchmark_results.json'))


def load_data():
    if not os.path.exists(db_path):
        return pd.DataFrame()
    with open(db_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if not data: return pd.DataFrame()
        except json.JSONDecodeError:
            return pd.DataFrame()
            
    # Flatten the data for pandas
    flat_data = []
    for d in data:
        row = {
            "Model": d.get("model_name", "Unknown"),
            "Total Reward": d.get("total_reward", 0.0),
            "Heat Duty (kW)": d.get("metrics", {}).get("heat_duty_W", 0.0) / 1000.0,
            "Cost ($/y)": d.get("metrics", {}).get("cost_annualised_USD_per_yr", 0.0),
            "Effectiveness (%)": d.get("metrics", {}).get("effectiveness", 0.0) * 100,
            "DP Tube (kPa)": d.get("metrics", {}).get("dp_tube_Pa", 0.0) / 1000.0,
            "DP Shell (kPa)": d.get("metrics", {}).get("dp_shell_Pa", 0.0) / 1000.0,
            "Warnings": d.get("metrics", {}).get("num_warnings", 0.0),
            "Weight (Heat)": d.get("weights", {}).get("w_heat", 0.0),
            "Weight (Cost)": d.get("weights", {}).get("w_cost", 0.0),
            "Weight (DP Tube)": d.get("weights", {}).get("w_drop_tube", 0.0),
            "Weight (DP Shell)": d.get("weights", {}).get("w_drop_shell", 0.0),
            "Weight (Eff)": d.get("weights", {}).get("w_eff", 0.0),
            "Tubes": d.get("design", {}).get("number_of_tubes", 0),
            "Area (m2)": d.get("metrics", {}).get("area_m2", 0.0)
        }
        flat_data.append(row)
    return pd.DataFrame(flat_data)

df = load_data()

if df.empty:
    st.warning("Henüz hiç test sonucu kaydedilmemiş. Lütfen 'python scripts/run_llm_eval.py' ile bir model test edin.")
    st.stop()

# 2. Sidebar Filters
st.sidebar.header("Filtreler")

# Unique task configurations based on weights
df['Config Signature'] = df.apply(lambda r: f"Heat:{r['Weight (Heat)']:.2f} | Cost:{r['Weight (Cost)']:.2f} | Eff:{r['Weight (Eff)']:.2f} | Tube:{r['Weight (DP Tube)']:.2f} | Shell:{r['Weight (DP Shell)']:.2f}", axis=1)
configs = df['Config Signature'].unique().tolist()
configs.insert(0, "All")

selected_config = st.sidebar.selectbox("Görev Ağırlığı Konfigürasyonu", configs)

if selected_config != "All":
    df = df[df['Config Signature'] == selected_config]

# 3. Main Data Table
st.subheader("📊 Değerlendirme Sonuçları (Tablo)")
st.dataframe(df.style.highlight_max(subset=['Total Reward', 'Heat Duty (kW)'], color='lightgreen')
                     .highlight_min(subset=['Cost ($/y)', 'Warnings'], color='lightgreen')
                     .format(precision=2))

# 4. Charts
st.subheader("📈 Görsel Karşılaştırma")

col1, col2 = st.columns(2)

with col1:
    fig_reward = px.bar(df, x="Model", y="Total Reward", color="Model", title="Toplam Ödül Skoru (Total Reward)")
    st.plotly_chart(fig_reward, use_container_width=True)
    
    fig_heat = px.bar(df, x="Model", y="Heat Duty (kW)", color="Model", title="Isı Transferi (kW)")
    # Add target line
    fig_heat.add_hline(y=150, line_dash="dash", line_color="red", annotation_text="Hedef (150kW)")
    st.plotly_chart(fig_heat, use_container_width=True)

with col2:
    fig_cost = px.bar(df, x="Model", y="Cost ($/y)", color="Model", title="Yıllık Maliyet ($/y)")
    st.plotly_chart(fig_cost, use_container_width=True)
    
    fig_warn = px.bar(df, x="Model", y="Warnings", color="Model", title="Mekanik Uyarı Sayısı (Warnings)")
    st.plotly_chart(fig_warn, use_container_width=True)

# 5. Raw Export
st.sidebar.markdown("---")
if st.sidebar.button("Yenile (Refresh)"):
    st.rerun()

csv = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="CSV Olarak İndir",
    data=csv,
    file_name='llm_benchmark_results.csv',
    mime='text/csv',
)
