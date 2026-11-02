import streamlit as st

from src.core import KimnovixAgriOS
from src.tools import (
    POULTRY_FORMULARY,
    SWINE_STATES,
    calculate_crop_agronomy,
    simulate_swine_markov,
)

st.set_page_config(
    page_title="Kimnovix Agri-OS",
    page_icon="🦁",
    layout="wide",
)

engine = KimnovixAgriOS()

st.sidebar.title("🦁 Kimnovix Agri-OS")
st.sidebar.caption("Offline-First Clinical & Agricultural Intelligence")
lang_choice = st.sidebar.selectbox("Language / Lugha", options=["en", "sw"], index=0)
st.sidebar.markdown(f"**Runtime Mode:** `{engine.mode.upper()}`")

st.title("Kimnovix Agri-OS Command Terminal")

tab_cmd, tab_swine, tab_crop, tab_poultry = st.tabs(
    [
        "📡 Command & Telemetry RAG",
        "🐖 Swine Markov Twin",
        "🌱 Crop Agronomy",
        "🐔 Poultry Analytics",
    ]
)

with tab_cmd:
    st.subheader("Unified Deterministic Router & Telemetry RAG")
    user_query = st.text_input(
        "Enter clinical, agronomy, or telemetry query:",
        value="Retrieve breeding section farrowing telemetry logs",
    )
    if st.button("Execute Query", key="btn_cmd"):
        res = engine.process_query(user_query, lang=lang_choice)
        if res["status"] == "BLOCKED" or res["status"] == "ERROR":
            st.error(res["response"])
        else:
            st.markdown(res["response"])
        with st.expander("Raw Telemetry Payload"):
            st.json(res)

with tab_swine:
    st.subheader("Swine Behavioral Digital Twin (Markov Chain)")
    col1, col2, col3 = st.columns(3)
    with col1:
        init_state = st.selectbox("Initial Herd State", options=SWINE_STATES, index=0)
    with col2:
        horizon = st.slider("Simulation Horizon (Steps)", min_value=1, max_value=24, value=6)
    with col3:
        temp_c = st.number_input("Barn Ambient Temp (°C)", min_value=10.0, max_value=45.0, value=24.0, step=0.5)

    if st.button("Run Markov Simulation", key="btn_swine"):
        sim_data = simulate_swine_markov(
            initial_state=init_state, steps=int(horizon), ambient_temp_c=float(temp_c)
        )
        if sim_data["anomaly_detected"]:
            st.warning(f"🚨 Stress Vocalization Anomaly Detected ({sim_data['probabilities']['STRESS_VOCALIZATION']*100:.1f}%)")
        else:
            st.success(f"🟢 Herd State Nominal — Dominant State: {sim_data['dominant_state']}")
        st.bar_chart(sim_data["probabilities"])
        with st.expander("Raw Markov State Vector"):
            st.json(sim_data)

with tab_crop:
    st.subheader("Crop Irrigation & Compost Deficit Calculator")
    c1, c2, c3 = st.columns(3)
    with c1:
        crop_name = st.text_input("Crop Type", value="Maize")
    with c2:
        area_ha = st.number_input("Field Area (Hectares)", min_value=0.1, max_value=1000.0, value=2.0, step=0.5)
    with c3:
        soil_moist = st.number_input("Current Soil Moisture (%)", min_value=5.0, max_value=100.0, value=45.0, step=1.0)

    if st.button("Calculate Agronomy Deficit", key="btn_crop"):
        agro_res = calculate_crop_agronomy(
            crop=crop_name, area_ha=float(area_ha), current_moisture_pct=float(soil_moist)
        )
        st.info(
            f"**Irrigation Required:** {agro_res['irrigation_required_m3']} m³ "
            f"({agro_res['irrigation_required_liters']:,.0f} L) | "
            f"**Organic Compost:** {agro_res['compost_required_tons']} tons"
        )
        with st.expander("Raw Agronomy Payload"):
            st.json(agro_res)

with tab_poultry:
    st.subheader("Poultry Flock Antibiotic & Soluble Powder Dosing")
    p1, p2, p3 = st.columns(3)
    with p1:
        compound = st.selectbox("Select Compound", options=list(POULTRY_FORMULARY.keys()), index=0)
    with p2:
        flock_count = st.number_input("Flock Size (Birds)", min_value=1, max_value=100000, value=100, step=10)
    with p3:
        bird_wt = st.number_input("Avg Bird Weight (kg)", min_value=0.05, max_value=10.0, value=1.5, step=0.1)

    if st.button("Compute Flock Dosage", key="btn_poultry"):
        constructed_query = f"poultry {compound} {int(flock_count)} {float(bird_wt)}"
        poultry_out = engine.process_query(constructed_query, lang=lang_choice)
        if poultry_out["status"] in ("BLOCKED", "ERROR"):
            st.error(poultry_out["response"])
        else:
            st.markdown(poultry_out["response"])
            with st.expander("Raw Payload"):
                st.json(poultry_out)
