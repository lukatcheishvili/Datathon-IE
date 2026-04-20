"""
dashboard.py  —  IE Datathon · EV Infrastructure Spain
Run:  streamlit run dashboard.py
"""
import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IE Datathon — EV Infrastructure Spain",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit default chrome */
#MainMenu, footer,
[data-testid="stStatusWidget"],
[data-testid="stToolbar"]              { visibility: hidden; height: 0; }
header[data-testid="stHeader"]         { background: transparent; height: 0; }
[data-testid="stSidebar"]              { display: none; }

/* Remove all default padding */
.block-container {
    padding: 0 !important;
    max-width: 100vw !important;
}
.stApp { background: #f0f2f5; }

/* ── Top banner ── */
.app-banner {
    background: linear-gradient(90deg, #1a1a2e 0%, #0f3460 100%);
    padding: 12px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    border-bottom: 3px solid #0a2444;
}
.banner-icon  { font-size: 26px; }
.banner-title { font-size: 19px; font-weight: 700; color: #e8eaf0;
                font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.3; }
.banner-sub   { font-size: 11px; color: #8aa0c0; margin-top: 2px;
                font-family: 'Segoe UI', Arial, sans-serif; }

/* ── Nav strip ── */
.nav-strip {
    background: #1a1a2e;
    padding: 8px 20px;
    border-bottom: 1px solid #0f3460;
}

/* ── Streamlit radio styled as pill buttons ── */
div[data-testid="stRadio"] > label { display: none; }
div[data-testid="stRadio"] > div {
    display: flex !important;
    flex-wrap: wrap;
    gap: 6px !important;
}
div[data-testid="stRadio"] > div > label {
    background: #16213e !important;
    color: #8aa0c0 !important;
    border: 1px solid #2a3a5c !important;
    border-radius: 6px !important;
    padding: 6px 14px !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.18s !important;
    font-family: 'Segoe UI', Arial, sans-serif !important;
}
div[data-testid="stRadio"] > div > label:hover {
    background: #0f3460 !important;
    color: #dce8ff !important;
    border-color: #4a7fc1 !important;
}
/* Active/selected pill */
div[data-testid="stRadio"] > div > label[data-baseweb="radio"]:has(input:checked),
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: #0f3460 !important;
    color: #ffffff !important;
    border-color: #4a90d9 !important;
    box-shadow: 0 0 0 2px rgba(74,144,217,0.25) !important;
}
/* Hide the radio circle */
div[data-testid="stRadio"] input[type="radio"],
div[data-testid="stRadio"] span[data-testid="stMarkdownContainer"] > p { display: none !important; }
div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] { display: none !important; }

/* ── iframe wrapper ── */
iframe { border: none !important; display: block; }

/* ── Loading state ── */
.stSpinner { padding: 40px; }
</style>
""", unsafe_allow_html=True)

# ── Charts registry ─────────────────────────────────────────────────────────────
CHARTS_DIR = Path(__file__).parent / "visualizations"

CHARTS = [
    {
        "id":   "iberdrola",
        "name": "Iberdrola i-DE — Readiness",
        "icon": "🔌",
        "file": "iberdrola_ide_expansion_readiness.html",
    },
    {
        "id":   "endesa",
        "name": "ENDESA e-distribución — Readiness",
        "icon": "⚡",
        "file": "endesa_edistribucion_expansion_readiness.html",
    },
    {
        "id":   "viesgo",
        "name": "VIESGO — Readiness",
        "icon": "🌐",
        "file": "viesgo_distribution_expansion_readiness.html",
    },
    {
        "id":   "road",
        "name": "Road OD Flows",
        "icon": "🛣️",
        "file": "road_od_flows_spain.html",
    },
    {
        "id":   "ev_density",
        "name": "EV Charging Density",
        "icon": "🌡️",
        "file": "ev_charging_density_spain.html",
    },
    {
        "id":   "ev_scatter",
        "name": "EV Charging Stations",
        "icon": "📍",
        "file": "ev_charging_stations_spain.html",
    },
    {
        "id":   "vigo",
        "name": "Vigo Charging Points",
        "icon": "🗺️",
        "file": "vigo_ev_charging_points.html",
    },
]

# ── Banner ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-banner">
  <div class="banner-icon">⚡</div>
  <div>
    <div class="banner-title">IE Datathon — EV Infrastructure Spain</div>
    <div class="banner-sub">
      Electricity grid capacity &nbsp;×&nbsp; EV charging infrastructure &nbsp;×&nbsp; Road traffic flows
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Navigation ──────────────────────────────────────────────────────────────────
st.markdown('<div class="nav-strip">', unsafe_allow_html=True)

chart_labels = [f"{c['icon']}  {c['name']}" for c in CHARTS]
chart_ids    = [c["id"] for c in CHARTS]

selected_label = st.radio(
    label="Select dashboard",
    options=chart_labels,
    index=0,
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown('</div>', unsafe_allow_html=True)

# ── Resolve selected chart ──────────────────────────────────────────────────────
selected_idx   = chart_labels.index(selected_label)
active_chart   = CHARTS[selected_idx]
chart_path     = CHARTS_DIR / active_chart["file"]

# ── Embed chart ─────────────────────────────────────────────────────────────────
if chart_path.exists():
    with st.spinner(f"Loading {active_chart['name']} …"):
        html_content = chart_path.read_text(encoding="utf-8", errors="replace")
    # Height: fills most of a typical 1080p screen minus banner (~80px) + nav (~50px)
    components.html(html_content, height=870, scrolling=False)
else:
    st.error(f"⚠️  Chart file not found: {chart_path}")
    st.info("Run `python generate_visualizations.py` from the Datathon folder to generate the charts.")
