# app/main.py
import streamlit as st
from utils.telemetry import setup_cache, load_session
from utils.plotting import plot_telemetry, plot_delta_time, plot_heatmap
from utils.sector_times import calculate_sector_times, format_sector_dataframe
from utils.styling import load_custom_css
import fastf1
from fastf1.plotting import get_team_color
import pandas as pd
import io
from matplotlib.backends.backend_pdf import PdfPages

# Setup cache and FastF1
setup_cache()

# Page configuration
st.set_page_config(page_title="F1 Telemetry Hub", layout="wide")
load_custom_css()

# HTML Navigation Bar with anchor links
st.markdown("""
    <div class="nav-bar">
        <a href="#home">Home</a>
        <a href="#telemetry">Telemetry</a>
        <a href="#delta">Delta Time</a>
        <a href="#sectors">Sectors</a>
        <a href="#download">Download</a>
    </div>
""", unsafe_allow_html=True)

# Load session sidebar
with st.sidebar:
    st.header("Session Configuration")
    year = st.selectbox("Select Year", list(range(2018, 2026))[::-1], key="year_select")
    event_schedule = fastf1.get_event_schedule(year, include_testing=True)
    event_options = {idx: name for idx, name in enumerate(event_schedule['EventName'])}
    event_idx = st.selectbox("Select Event", list(event_options.keys()), 
                            format_func=lambda x: event_options[x], key="event_select")
    session_type = st.selectbox("Session Type", ['FP1', 'FP2', 'FP3', 'Q', 'R'], key="session_type_select")

    if st.button("Load Session", key="load_session_button"):
        session = load_session(year, event_schedule, event_idx, session_type)
        if session:
            st.session_state['loaded_session'] = session
            st.session_state['loaded_event_name'] = event_options[event_idx]
            st.session_state['loaded_session_type'] = session_type

if 'loaded_session' not in st.session_state:
    st.warning("Please load a session to continue.")
    st.stop()

session = st.session_state['loaded_session']

# Lap comparison config
# Get unique driver codes
driver_codes = sorted(session.laps['Driver'].unique())

# Build a mapping of code → full name (e.g. "VER" → "Max Verstappen")
driver_names = {code: f"{session.get_driver(code)['FullName']} ({code})" for code in driver_codes}

# Create columns for selection
col1, col2 = st.columns(2)

with col1:
    driver1 = st.selectbox(
        "Driver 1",
        driver_codes,
        format_func=lambda code: driver_names[code],
        key="driver1_select"
    )
    laps1 = session.laps.pick_drivers(driver1)
    lap_num1 = st.selectbox(
        f"{driver_names[driver1]} Lap",
        laps1['LapNumber'].tolist(),
        key="lap1_select"
    )

with col2:
    driver2 = st.selectbox(
        "Driver 2",
        driver_codes,
        index=1 if len(driver_codes) > 1 else 0,
        format_func=lambda code: driver_names[code],
        key="driver2_select"
    )
    laps2 = session.laps.pick_drivers(driver2)
    lap_num2 = st.selectbox(
        f"{driver_names[driver2]} Lap",
        laps2['LapNumber'].tolist(),
        key="lap2_select"
    )

lap1 = laps1[laps1['LapNumber'] == lap_num1].iloc[0]
lap2 = laps2[laps2['LapNumber'] == lap_num2].iloc[0]
telemetry1 = lap1.get_car_data().add_distance()
telemetry2 = lap2.get_car_data().add_distance()
team1_color = get_team_color(session.get_driver(driver1)['TeamName'], session)
team2_color = get_team_color(session.get_driver(driver2)['TeamName'], session)

figs = []

# Telemetry Section
st.markdown("<h2 id='telemetry'>Telemetry Comparison</h2>", unsafe_allow_html=True)
metrics = {"Speed": "Speed (km/h)", "Throttle": "Throttle (%)", "Brake": "Brake", "nGear": "Gear"}
for metric, label in metrics.items():
    fig = plot_telemetry(telemetry1, telemetry2, metric, label, driver1, driver2, team1_color, team2_color)
    st.pyplot(fig)
    figs.append(fig)

# Delta Time Section
st.markdown("<h2 id='delta'>Delta Time</h2>", unsafe_allow_html=True)
delta_fig = plot_delta_time(lap1, lap2, driver1, driver2)
st.pyplot(delta_fig)
figs.append(delta_fig)

# Sector Times Section
st.markdown("<h2 id='sectors'>Sector Times</h2>", unsafe_allow_html=True)
sector_df = calculate_sector_times(session, driver1, driver2, lap_num1, lap_num2)
st.dataframe(format_sector_dataframe(sector_df))

# Download Report Section
st.markdown("<h2 id='download'>Download Report</h2>", unsafe_allow_html=True)
pdf_buffer = io.BytesIO()
with PdfPages(pdf_buffer) as pdf:
    for fig in figs:
        pdf.savefig(fig)
st.download_button(
    label="Download PDF Report",
    data=pdf_buffer.getvalue(),
    file_name=f"F1_Telemetry_{driver1}_vs_{driver2}.pdf",
    mime="application/pdf"
)

st.caption("Powered by FastF1 & Streamlit | © 2025")
