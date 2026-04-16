"""
Build grid_viability_map.html from real Iberdrola (i-DE) capacity data.
Source: 2026_01_02_R1-001_Generación.xlsx
"""

import os
import pandas as pd
import numpy as np
import folium
from pyproj import Transformer

# ── Paths ─────────────────────────────────────────────────────────────────────
XLSX      = '2026_01_02_R1-001_Generación.xlsx'
OUT_MAP   = 'outputs/grid_viability_map.html'

# ── Grid thresholds (unchanged from notebook) ─────────────────────────────────
GRID_THRESHOLDS = {'Sufficient': 2.0, 'Moderate': 0.5, 'Congested': 0.0}
GRID_COLORS     = {'Sufficient': '#5cb85c', 'Moderate': '#f0ad4e', 'Congested': '#d9534f'}
STATUS_ORDER    = ['Congested', 'Moderate', 'Sufficient']

def classify_grid(mw):
    if mw is None or (isinstance(mw, float) and np.isnan(mw)):
        return 'Unknown'
    if mw >= GRID_THRESHOLDS['Sufficient']:
        return 'Sufficient'
    if mw >= GRID_THRESHOLDS['Moderate']:
        return 'Moderate'
    return 'Congested'

# ── 1. Load & clean Excel ─────────────────────────────────────────────────────
print('Loading Excel...')
df = pd.read_excel(XLSX, header=0)
print(f'  Raw rows: {len(df):,}')

# Parse UTM coordinates (comma = decimal separator in Spanish locale)
df['utm_x'] = df['Coordenada UTM X'].astype(str).str.replace(',', '.').astype(float)
df['utm_y'] = df['Coordenada UTM Y'].astype(str).str.replace(',', '.').astype(float)

# Parse available capacity (comma = decimal separator)
df['cap_mw'] = (
    pd.to_numeric(
        df['Capacidad disponible (MW)'].astype(str).str.replace(',', '.'),
        errors='coerce'
    ).fillna(0.0)
)

# Drop the 4 rows with clearly wrong UTM coordinates (negative or out of range)
df = df[(df['utm_x'] > 10_000) & (df['utm_x'] < 900_000)].copy()
print(f'  After filtering bad UTM: {len(df):,} rows')

# ── 2. Aggregate per physical substation ─────────────────────────────────────
# Multiple connection points share the same substation ID + UTM coords.
# Sum available capacity across all positions → total headroom at the node.
print('Aggregating by substation...')
agg = (
    df.groupby(
        ['Subestación', 'utm_x', 'utm_y', 'Provincia', 'Municipio'],
        as_index=False
    )
    .agg(
        total_cap_mw  = ('cap_mw', 'sum'),
        n_positions   = ('cap_mw', 'count'),
        voltage_kv    = ('Nivel de Tensión (kV)', lambda s: ', '.join(
                            sorted(set(s.astype(str)), key=lambda v: float(v.replace(',', '.')) if v.replace(',', '.').replace('.', '').isdigit() else 9999)
                        )),
        occupied_mw   = ('Capacidad ocupada (MW)', lambda s:
                            pd.to_numeric(s.astype(str).str.replace(',', '.'), errors='coerce').fillna(0).sum()
                        ),
    )
)
print(f'  Unique substations: {len(agg):,}')

# ── 3. Convert UTM (ETRS89 Zone 30N / EPSG:25830) → WGS84 lat/lon ────────────
print('Converting UTM -> lat/lon (EPSG:25830 -> EPSG:4326)...')
transformer = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
lons, lats = transformer.transform(agg['utm_x'].values, agg['utm_y'].values)
agg['longitude'] = lons
agg['latitude']  = lats

# Sanity check: drop any points outside Spain's bbox
spain_mask = (
    agg['latitude'].between(27.0, 44.5) &
    agg['longitude'].between(-18.5, 5.0)
)
n_dropped = (~spain_mask).sum()
if n_dropped:
    print(f'  Dropping {n_dropped} points outside Spain bbox after conversion')
agg = agg[spain_mask].reset_index(drop=True)
print(f'  Final substations on map: {len(agg):,}')

# ── 4. Classify grid status ───────────────────────────────────────────────────
agg['grid_status'] = agg['total_cap_mw'].apply(classify_grid)
status_counts = agg['grid_status'].value_counts()
print('\nGrid status summary:')
for s in STATUS_ORDER:
    print(f'  {s:12s}: {status_counts.get(s, 0):,}')

# ── 5. Build Folium map ───────────────────────────────────────────────────────
print('\nBuilding map...')
SPAIN_CENTER = [40.4, -3.7]

m = folium.Map(
    location=SPAIN_CENTER,
    zoom_start=6,
    tiles='CartoDB dark_matter',
    prefer_canvas=True
)

# One feature group per status (easiest to toggle)
feature_groups = {}
for status in STATUS_ORDER:
    fg = folium.FeatureGroup(
        name=f'{["🔴","🟡","🟢"][STATUS_ORDER.index(status)]} {status} Grid ({status_counts.get(status, 0):,} substations)',
        show=True
    )
    feature_groups[status] = fg

for _, row in agg.iterrows():
    status  = row['grid_status']
    color   = GRID_COLORS.get(status, 'gray')
    cap     = row['total_cap_mw']
    fg      = feature_groups.get(status, feature_groups['Congested'])

    # Radius: log scale so 0 MW → 4px, 500 MW → 18px
    radius = 4 if cap == 0 else max(4, min(18, 4 + 5 * np.log1p(cap)))

    popup_html = (
        f"<b>Subestación {int(row['Subestación'])}</b><br>"
        f"<b>{row['Municipio']}</b>, {row['Provincia']}<br>"
        f"<hr style='margin:4px 0; border-color:#555'>"
        f"Available: <b>{cap:.1f} MW</b><br>"
        f"Occupied: {row['occupied_mw']:.1f} MW<br>"
        f"Voltage(s): {row['voltage_kv']} kV<br>"
        f"Connection points: {int(row['n_positions'])}<br>"
        f"Status: <b style='color:{color}'>{status}</b>"
    )

    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.75,
        weight=0.5,
        popup=folium.Popup(popup_html, max_width=240),
        tooltip=f"{row['Municipio']} | {cap:.1f} MW | {status}"
    ).add_to(fg)

for fg in feature_groups.values():
    fg.add_to(m)

# ── Legend ────────────────────────────────────────────────────────────────────
legend_html = f"""
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
            background:rgba(0,0,0,0.85);color:#fff;
            padding:14px 18px;border-radius:8px;font-family:Arial;font-size:12px;line-height:1.9">
  <b>⚡ Iberdrola (i-DE) Grid Capacity</b><br>
  <small style="color:#aaa">Source: R1-001 Generación (Jan 2026)<br>
  {len(agg):,} substations · Real data</small><br>
  <hr style="border-color:#555;margin:6px 0">
  <span style="color:{GRID_COLORS['Sufficient']}">●</span>
  <b>Sufficient</b> (&ge;{GRID_THRESHOLDS['Sufficient']:.0f} MW) &nbsp; {status_counts.get('Sufficient', 0):,}<br>
  <span style="color:{GRID_COLORS['Moderate']}">●</span>
  <b>Moderate</b> ({GRID_THRESHOLDS['Moderate']:.1f}–{GRID_THRESHOLDS['Sufficient']:.0f} MW) &nbsp; {status_counts.get('Moderate', 0):,}<br>
  <span style="color:{GRID_COLORS['Congested']}">●</span>
  <b>Congested</b> (&lt;{GRID_THRESHOLDS['Moderate']:.1f} MW) &nbsp; {status_counts.get('Congested', 0):,}<br>
  <hr style="border-color:#555;margin:6px 0">
  <small style="color:#aaa">Circle size ∝ available MW (log scale)<br>
  Thresholds: ≥2 MW = can support ≥13 chargers @ 150 kW</small>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl(collapsed=False).add_to(m)

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs('outputs', exist_ok=True)
m.save(OUT_MAP)
print(f'\nDone. Saved -> {OUT_MAP}')
print(f'   Sufficient : {status_counts.get("Sufficient", 0):,}')
print(f'   Moderate   : {status_counts.get("Moderate", 0):,}')
print(f'   Congested  : {status_counts.get("Congested", 0):,}')
