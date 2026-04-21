"""
dashboard.py  —  IE Datathon · EV Infrastructure Spain
Run:  streamlit run dashboard.py
"""
import streamlit as st
from pathlib import Path
import subprocess, sys
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
/* ── Hide Streamlit chrome ── */
#MainMenu, footer,
[data-testid="stStatusWidget"],
[data-testid="stToolbar"]       { visibility: hidden; height: 0; }
header[data-testid="stHeader"]  { background: transparent; height: 0; }
[data-testid="stSidebar"]       { display: none; }
.block-container                { padding: 0 !important; max-width: 100vw !important; }
.stApp                          { background: #0d1117; }

/* ── Banner ── */
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
                font-family: 'Segoe UI', Arial, sans-serif; }
.banner-sub   { font-size: 11px; color: #8aa0c0; margin-top: 2px;
                font-family: 'Segoe UI', Arial, sans-serif; }

/* ── Nav strip background ── */
.nav-strip {
    background: #161b27;
    padding: 8px 16px;
    border-bottom: 1px solid #1e2d45;
}

/* ── Radio → pill buttons ──
   Hide the outer label (the "Select dashboard" text) */
div[data-testid="stRadio"] > label { display: none !important; }

/* Row of pills */
div[data-testid="stRadio"] > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    background: transparent !important;
}

/* Each pill wrapper */
div[data-testid="stRadio"] > div > label {
    background: #1c2333 !important;
    border: 1px solid #2a3f5f !important;
    border-radius: 6px !important;
    padding: 5px 14px 5px 10px !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    display: flex !important;
    align-items: center !important;
}

/* Text inside pill — keep visible */
div[data-testid="stRadio"] > div > label p,
div[data-testid="stRadio"] > div > label span,
div[data-testid="stRadio"] > div > label div[data-testid="stMarkdownContainer"] {
    color: #8aa0c0 !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    font-family: 'Segoe UI', Arial, sans-serif !important;
    display: block !important;
    visibility: visible !important;
}

/* Hover state */
div[data-testid="stRadio"] > div > label:hover {
    background: #0f3460 !important;
    border-color: #4a7fc1 !important;
}
div[data-testid="stRadio"] > div > label:hover p,
div[data-testid="stRadio"] > div > label:hover span {
    color: #dce8ff !important;
}

/* Active/selected pill */
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: #0f3460 !important;
    border-color: #4a90d9 !important;
    box-shadow: 0 0 0 2px rgba(74,144,217,0.3) !important;
}
div[data-testid="stRadio"] > div > label:has(input:checked) p,
div[data-testid="stRadio"] > div > label:has(input:checked) span {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Overview pill always accented */
div[data-testid="stRadio"] > div > label:first-child {
    border-color: #4a90d9 !important;
    background: #0d2341 !important;
}
div[data-testid="stRadio"] > div > label:first-child p,
div[data-testid="stRadio"] > div > label:first-child span { color: #90c8ff !important; }

/* Hide only the radio circle dot, not the text */
div[data-testid="stRadio"] input[type="radio"] {
    position: absolute !important;
    opacity: 0 !important;
    width: 0 !important;
    height: 0 !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* ── iframe ── */
iframe { border: none !important; display: block; }
</style>
""", unsafe_allow_html=True)

# ── Charts registry ─────────────────────────────────────────────────────────────
CHARTS_DIR = Path(__file__).parent / "visualizations"

CHARTS = [
    {"id": "overview",   "name": "🗺️  All Data Overview",              "file": "overview_all_data.html"},
    {"id": "iberdrola",  "name": "🔌  Iberdrola i-DE — Readiness",      "file": "iberdrola_ide_expansion_readiness.html"},
    {"id": "endesa",     "name": "⚡  ENDESA e-distribución — Readiness","file": "endesa_edistribucion_expansion_readiness.html"},
    {"id": "viesgo",     "name": "🌐  VIESGO — Readiness",              "file": "viesgo_distribution_expansion_readiness.html"},
    {"id": "road",       "name": "🛣️  Road OD Flows",                   "file": "road_od_flows_spain.html"},
    {"id": "ev_density", "name": "🌡️  EV Charging Density",             "file": "ev_charging_density_spain.html"},
    {"id": "ev_scatter", "name": "📍  EV Charging Stations",            "file": "ev_charging_stations_spain.html"},
    {"id": "vigo",       "name": "🗺️  Vigo Charging Points",            "file": "vigo_ev_charging_points.html"},
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

# ── Zero Heroes KPI Scorecard ────────────────────────────────────────────────────
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Grid Readiness", "24.1%", delta="Substations with >0.72MW")
with kpi2:
    st.metric("Coverage Needs", "181 Sites", delta="Proposed for 2027", delta_color="inverse")
with kpi3:
    st.metric("Estimated ROI", "€1.2M", delta="Avg. Annual Revenue/Site")
with kpi4:
    st.metric("Forecasted Fleet", "139k", delta="+12% YoY EV Adoption")

st.markdown("<hr style='margin: 0; border: 0.5px solid #1e2d45;'>", unsafe_allow_html=True)

# ── Navigation ──────────────────────────────────────────────────────────────────
st.markdown('<div class="nav-strip">', unsafe_allow_html=True)

selected = st.radio(
    label="Select dashboard",
    options=[c["name"] for c in CHARTS],
    index=0,
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown('</div>', unsafe_allow_html=True)

# ── Resolve active chart ─────────────────────────────────────────────────────────
active     = next(c for c in CHARTS if c["name"] == selected)
chart_path = CHARTS_DIR / active["file"]

# ── Auto-generate overview if missing ───────────────────────────────────────────
if active["id"] == "overview" and not chart_path.exists():
    st.info("⏳ Generating the All Data Overview map for the first time — this may take ~60 seconds (downloads live data)...")
    gen_script = Path(__file__).parent / "generate_overview.py"
    if gen_script.exists():
        with st.spinner("Building combined overview map..."):
            result = subprocess.run(
                [sys.executable, str(gen_script)],
                capture_output=True, text=True,
                cwd=str(Path(__file__).parent)
            )
        if chart_path.exists():
            st.success("✅ Overview map generated! Loading...")
            st.rerun()
        else:
            st.error("❌ Generation failed. Output:")
            st.code(result.stderr or result.stdout)
    else:
        st.error("generate_overview.py not found next to dashboard.py")

# ── Embed chart ─────────────────────────────────────────────────────────────────
elif chart_path.exists():
    with st.spinner(f"Loading {active['name'].strip()} ..."):
        html_content = chart_path.read_text(encoding="utf-8", errors="replace")
    components.html(html_content, height=870, scrolling=False)

else:
    st.error(f"Chart file not found: `{active['file']}`")
    st.info("Run `python generate_visualizations.py` from the Datathon folder to generate all charts.")
