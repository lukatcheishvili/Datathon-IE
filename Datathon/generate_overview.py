"""
generate_overview.py
Creates a single unified overview map combining all EV infrastructure layers.
Run from the Datathon/ folder:  python generate_overview.py
"""
import sys, warnings, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from pyproj import Transformer
from pathlib import Path
from lxml import etree

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
OUT      = BASE_DIR / "visualizations"
OUT.mkdir(exist_ok=True)

# ── Province centroids ──────────────────────────────────────────────────────────
PC = {
    '01':(42.846,-2.673,'Araba/Álava'),    '02':(38.996,-1.858,'Albacete'),
    '03':(38.504,-0.324,'Alicante'),        '04':(37.004,-2.097,'Almería'),
    '05':(40.656,-4.697,'Ávila'),           '06':(38.879,-6.971,'Badajoz'),
    '07':(39.569, 2.650,'Illes Balears'),   '08':(41.582, 2.173,'Barcelona'),
    '09':(42.344,-3.697,'Burgos'),          '10':(39.475,-6.372,'Cáceres'),
    '11':(36.516,-5.903,'Cádiz'),           '12':(39.986,-0.051,'Castellón'),
    '13':(39.003,-3.917,'Ciudad Real'),     '14':(37.885,-4.779,'Córdoba'),
    '15':(43.132,-8.414,'A Coruña'),        '16':(40.070,-2.137,'Cuenca'),
    '17':(41.980, 2.821,'Girona'),          '18':(37.177,-3.599,'Granada'),
    '19':(40.632,-3.167,'Guadalajara'),     '20':(43.309,-2.003,'Gipuzkoa'),
    '21':(37.261,-6.945,'Huelva'),          '22':(42.136,-0.409,'Huesca'),
    '23':(37.780,-3.785,'Jaén'),            '24':(42.599,-5.572,'León'),
    '25':(41.615, 0.627,'Lleida'),          '26':(42.287,-2.540,'La Rioja'),
    '27':(43.012,-7.556,'Lugo'),            '28':(40.417,-3.704,'Madrid'),
    '29':(36.721,-4.421,'Málaga'),          '30':(37.992,-1.131,'Murcia'),
    '31':(42.817,-1.643,'Navarra'),         '32':(42.335,-7.864,'Ourense'),
    '33':(43.361,-5.859,'Asturias'),        '34':(41.993,-4.531,'Palencia'),
    '35':(28.123,-15.436,'Las Palmas'),     '36':(42.430,-8.645,'Pontevedra'),
    '37':(40.970,-5.664,'Salamanca'),       '38':(28.464,-16.252,'S.C. Tenerife'),
    '39':(43.183,-3.988,'Cantabria'),       '40':(40.943,-4.109,'Segovia'),
    '41':(37.389,-5.984,'Sevilla'),         '42':(41.763,-2.466,'Soria'),
    '43':(41.119, 1.245,'Tarragona'),       '44':(40.346,-1.106,'Teruel'),
    '45':(39.863,-4.027,'Toledo'),          '46':(39.470,-0.376,'Valencia'),
    '47':(41.652,-4.724,'Valladolid'),      '48':(43.263,-2.935,'Bizkaia'),
    '49':(41.500,-5.746,'Zamora'),          '50':(41.649,-0.889,'Zaragoza'),
    '51':(35.889,-5.321,'Ceuta'),           '52':(35.292,-2.938,'Melilla'),
}

# ── Color palette — one distinct base color per data source ─────────────────────
# Operator base colors (readiness shown via opacity + radius)
C = {
    'iberdrola': '#1565C0',   # Electric blue
    'endesa':    '#E65100',   # Deep orange
    'viesgo':    '#6A1B9A',   # Rich purple
    'ev_dgt':    '#00897B',   # Teal
    'road_node': '#0D47A1',   # Dark navy
    'road_arc':  '#B71C1C',   # Dark red
    'vigo':      '#558B2F',   # Lime green
}

READINESS = {
    'Sufficient': (0.90, 9),   # (fill_opacity, radius)
    'Moderate':   (0.55, 6),
    'Congested':  (0.20, 4),
}

def utm_to_wgs84(df):
    t = Transformer.from_crs('EPSG:25830', 'EPSG:4326', always_xy=True)
    valid = df['utm_x'].notna() & df['utm_y'].notna()
    lons, lats = t.transform(df.loc[valid,'utm_x'].values, df.loc[valid,'utm_y'].values)
    df.loc[valid,'longitude'] = lons
    df.loc[valid,'latitude']  = lats
    return df

def readiness_status(available_mw):
    kw = available_mw * 1000
    if kw >= 720:   return 'Sufficient'
    elif kw >= 480: return 'Moderate'
    else:           return 'Congested'

def add_grid_layer(m, df, operator_key, operator_label, id_col, prov_col=None):
    """Add a grid operator's substations as a FeatureGroup."""
    fg = folium.FeatureGroup(name=f'⚡ {operator_label}', show=True)
    color = C[operator_key]
    for _, r in df.dropna(subset=['latitude','longitude']).iterrows():
        status = readiness_status(r['capacity_available_mw'])
        fill_op, radius = READINESS[status]
        sub_id = r.get(id_col, 'N/A')
        prov   = r.get(prov_col, '') if prov_col else ''
        folium.CircleMarker(
            [r['latitude'], r['longitude']],
            radius=radius,
            color=color,
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=fill_op,
            popup=folium.Popup(
                f"<div style='font-family:sans-serif;color:#333;min-width:160px'>"
                f"<b style='color:{color}'>{operator_label}</b><br>"
                f"<hr style='margin:4px 0'>"
                f"<b>Substation:</b> {sub_id}<br>"
                f"<b>Status:</b> {status}<br>"
                f"<b>Available:</b> {r['capacity_available_mw']:.2f} MW<br>"
                + (f"<b>Province:</b> {prov}<br>" if prov else "")
                + f"</div>", max_width=240),
            tooltip=f"{operator_label} · {sub_id} · {status}"
        ).add_to(fg)
    fg.add_to(m)
    print(f'  ✅  {operator_label}: {len(df)} substations')

# ── Build base map ──────────────────────────────────────────────────────────────
print('\n🗺️  Building unified overview map...\n')
m = folium.Map(location=[40.2, -3.5], zoom_start=6, tiles='CartoDB Positron')

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Road OD Flows
# ══════════════════════════════════════════════════════════════════════════════
print('[1/5] Road OD Flows...')
od_file = DATA_DIR / 'road_routes/od_rutas/20240331_OD_rutas.csv'
if od_file.exists():
    df_od = pd.read_csv(od_file, nrows=500_000)
    df_od['origin_prov'] = df_od['origin_zone'].astype(str).str[:2]
    df_od['dest_prov']   = df_od['destination_zone'].astype(str).str[:2]
    df_od = df_od[df_od['origin_prov'] != df_od['dest_prov']]

    prov_out = (df_od.groupby('origin_prov')['trips'].sum()
                .reset_index().rename(columns={'origin_prov':'code','trips':'total_trips'}))
    prov_out = prov_out[prov_out['code'].isin(PC)].copy()
    prov_out['lat']  = prov_out['code'].map(lambda c: PC[c][0])
    prov_out['lon']  = prov_out['code'].map(lambda c: PC[c][1])
    prov_out['name'] = prov_out['code'].map(lambda c: PC[c][2])

    top_flows  = df_od.groupby(['origin_prov','dest_prov'])['trips'].sum().reset_index().nlargest(40,'trips')
    max_trips  = prov_out['total_trips'].max()
    max_flow   = top_flows['trips'].max()

    fg_road = folium.FeatureGroup(name='🛣️ Road OD Flows', show=True)
    # Flow arcs
    for _, r in top_flows.iterrows():
        o, d = r['origin_prov'], r['dest_prov']
        if o in PC and d in PC:
            weight = 1.2 + 5 * (r['trips'] / max_flow)
            opacity = 0.25 + 0.55 * (r['trips'] / max_flow)
            folium.PolyLine(
                [[PC[o][0], PC[o][1]], [PC[d][0], PC[d][1]]],
                color=C['road_arc'], weight=weight, opacity=opacity,
                tooltip=f"{PC[o][2]} → {PC[d][2]}: {r['trips']:,.0f} trips"
            ).add_to(fg_road)
    # Province nodes
    for _, r in prov_out.iterrows():
        ratio = r['total_trips'] / max_trips
        folium.CircleMarker(
            [r['lat'], r['lon']], radius=5 + 24 * ratio,
            color=C['road_node'], weight=1,
            fill=True, fill_color=C['road_node'], fill_opacity=0.75,
            popup=folium.Popup(
                f"<div style='font-family:sans-serif;color:#333'>"
                f"<b style='color:{C['road_node']}'>{r['name']}</b><br>"
                f"Outbound trips: <b>{r['total_trips']:,.0f}</b></div>", max_width=200),
            tooltip=f"{r['name']} — {r['total_trips']:,.0f} trips"
        ).add_to(fg_road)
    fg_road.add_to(m)
    print(f'  ✅  Road flows: {len(top_flows)} arcs, {len(prov_out)} province nodes')
else:
    print('  ⚠️  OD routes CSV not found — skipping')

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — EV Charging Stations (DGT)
# ══════════════════════════════════════════════════════════════════════════════
print('\n[2/5] EV Charging Stations (DGT)...')
try:
    XML_URL = 'https://infocar.dgt.es/datex2/v3/miterd/EnergyInfrastructureTablePublication/electrolineras.xml'
    print('  Downloading DGT XML...')
    resp = requests.get(XML_URL, timeout=180)
    root = etree.fromstring(resp.content)
    def ftext(el, name):
        res = el.xpath(f'.//*[local-name()="{name}"]/text()')
        return res[0].strip() if res else None
    sites   = root.xpath('.//*[local-name()="energyInfrastructureSite"]')
    records = []
    for site in sites:
        lat = ftext(site,'latitude'); lon = ftext(site,'longitude')
        if not lat or not lon: continue
        name_vals = site.xpath('.//*[local-name()="name"]//*[local-name()="value"]/text()')
        records.append({
            'name':      name_vals[0].strip() if name_vals else '',
            'latitude':  float(lat),
            'longitude': float(lon),
            'operator':  ftext(site,'operatorName') or 'N/A',
        })
    df_ch = pd.DataFrame(records)
    major = ['MADRID','BARCELONA','VALENCIA','SEVILLA','ZARAGOZA','BILBAO','MALAGA']
    df_ch = df_ch[~df_ch['name'].str.upper().str.contains('|'.join(major))]
    df_ch = df_ch[df_ch['latitude'].between(35,44.5) & df_ch['longitude'].between(-9.5,5)].reset_index(drop=True)

    fg_ev = folium.FeatureGroup(name='⚡ EV Charging Stations (DGT — interurban)', show=True)
    cluster = MarkerCluster(name='EV Charger Cluster').add_to(fg_ev)
    for _, r in df_ch.iterrows():
        folium.CircleMarker(
            [r['latitude'], r['longitude']], radius=4,
            color=C['ev_dgt'], weight=0.8,
            fill=True, fill_color=C['ev_dgt'], fill_opacity=0.75,
            popup=folium.Popup(
                f"<div style='font-family:sans-serif;color:#333'>"
                f"<b style='color:{C['ev_dgt']}'>{r['name'] or 'EV Charger'}</b><br>"
                f"Operator: {r['operator']}</div>", max_width=220),
            tooltip=r['name'] or 'EV Charger'
        ).add_to(cluster)
    fg_ev.add_to(m)
    print(f'  ✅  DGT charging stations: {len(df_ch):,} sites')
except Exception as e:
    print(f'  ⚠️  EV Charging skipped: {e}')

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — Iberdrola i-DE
# ══════════════════════════════════════════════════════════════════════════════
print('\n[3/5] Iberdrola i-DE...')
ib_path = DATA_DIR / 'Iberdrola Historical Map of Electricity Consumption Capacity/2026_03_05_R1-001_Demanda.csv'
if ib_path.exists():
    df_ib = pd.read_csv(ib_path, sep=';', encoding='utf-8-sig', decimal=',', thousands='.', on_bad_lines='skip')
    df_ib.columns = df_ib.columns.str.strip()
    df_ib = df_ib.rename(columns={
        'Subestación':'substation_id', 'Provincia':'province',
        'Coordenada UTM X':'utm_x', 'Coordenada UTM Y':'utm_y',
        'Capacidad firme disponible (MW)':'capacity_available_mw'
    })
    df_ib = utm_to_wgs84(df_ib)
    df_ib = df_ib[df_ib['latitude'].between(35,44.5) & df_ib['longitude'].between(-9.5,5)].reset_index(drop=True)
    add_grid_layer(m, df_ib, 'iberdrola', 'Iberdrola i-DE', 'substation_id', 'province')
else:
    print('  ⚠️  Iberdrola CSV not found')

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — ENDESA e-distribución
# ══════════════════════════════════════════════════════════════════════════════
print('\n[4/5] ENDESA e-distribución...')
endesa_dir = DATA_DIR / 'ENDESA - e-distribucion'
if endesa_dir.exists():
    dfs = []
    for fp in sorted(endesa_dir.glob('*.csv')):
        df = pd.read_csv(fp, sep=';', encoding='utf-8-sig', decimal=',', thousands='.', on_bad_lines='skip')
        df['source_file'] = fp.name
        dfs.append(df)
    df_en = pd.concat(dfs, ignore_index=True)
    df_en.columns = df_en.columns.str.strip()
    seen = {}; deduped = []
    for c in df_en.columns:
        seen[c] = seen.get(c,0); deduped.append(c if seen[c]==0 else f'{c}_{seen[c]}'); seen[c]+=1
    df_en.columns = deduped
    df_en = df_en.rename(columns={
        'Nombre Subestación':'substation_id',
        'Coordenada UTM X':'utm_x', 'Coordenada UTM Y':'utm_y',
        'Capacidad disponible (MW)':'capacity_available_mw',
        'Comunidad Autónoma':'province'
    })
    df_en = utm_to_wgs84(df_en)
    df_en = df_en[df_en['latitude'].between(35,44.5) & df_en['longitude'].between(-9.5,5)].reset_index(drop=True)
    add_grid_layer(m, df_en, 'endesa', 'ENDESA e-distribución', 'substation_id', 'province')
else:
    print('  ⚠️  ENDESA folder not found')

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 5 — VIESGO
# ══════════════════════════════════════════════════════════════════════════════
print('\n[5/5] VIESGO...')
viesgo_dir = DATA_DIR / 'VIESGO'
if viesgo_dir.exists():
    def load_viesgo(fname):
        df = pd.read_csv(viesgo_dir/fname, sep=';', encoding='latin-1', skip_blank_lines=True)
        df.columns = df.columns.str.strip().str.replace('\n',' ',regex=False)
        # Deduplicate column names before anything else
        seen = {}; deduped = []
        for c in df.columns:
            seen[c] = seen.get(c, 0)
            deduped.append(c if seen[c] == 0 else f'{c}_{seen[c]}')
            seen[c] += 1
        df.columns = deduped
        df = df.rename(columns={
            'Subestación ':'substation_id','Subestación':'substation_id',
            'Nombre subestación':'substation_id','Nombre Subestación':'substation_id',
            'Provincia':'province',
            'Coordenada UTM X':'utm_x_raw','Coordenada UTM Y':'utm_y_raw',
            'Capacidad firme disponible (MW)':'capacity_available_mw',
            'Capacidad disponible (MW)':'capacity_available_mw',
        })
        def parse_utm(s):
            return pd.to_numeric(s.astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),errors='coerce')
        df['utm_x'] = parse_utm(df['utm_x_raw'])
        df['utm_y'] = parse_utm(df['utm_y_raw'])
        if 'capacity_available_mw' in df.columns:
            df['capacity_available_mw'] = pd.to_numeric(
                df['capacity_available_mw'].astype(str).str.replace(',','.').str.strip(), errors='coerce')
        return utm_to_wgs84(df).dropna(subset=['substation_id']).reset_index(drop=True)

    KEEP = ['substation_id', 'province', 'capacity_available_mw', 'latitude', 'longitude']

    def trim(df):
        cols = [c for c in KEEP if c in df.columns]
        return df[cols].copy()

    df_vd = trim(load_viesgo('2026_04_01_R1005_demanda_Consumption capacity in the network.csv'))
    df_vg = trim(load_viesgo('2026_04_01_R1005_generacion_Generation capacity in the network.csv'))
    df_vi = pd.concat([df_vd, df_vg], ignore_index=True)
    df_vi = df_vi[df_vi['latitude'].between(35,44.5) & df_vi['longitude'].between(-9.5,5)].reset_index(drop=True)
    add_grid_layer(m, df_vi, 'viesgo', 'VIESGO Distribution', 'substation_id', 'province')
else:
    print('  ⚠️  VIESGO folder not found')

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 6 — Vigo Charging Points
# ══════════════════════════════════════════════════════════════════════════════
print('\n[6/6] Vigo Charging Points...')
try:
    import geopandas as gpd
    gdf = gpd.read_file('https://datos.vigo.org/data/trafico/ptos_recarga.geojson')
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf['longitude'] = gdf.geometry.x
    gdf['latitude']  = gdf.geometry.y
    fg_vigo = folium.FeatureGroup(name='📍 Vigo EV Charging Points', show=True)
    for _, r in gdf.iterrows():
        folium.CircleMarker(
            [r['latitude'], r['longitude']], radius=7,
            color=C['vigo'], weight=2,
            fill=True, fill_color=C['vigo'], fill_opacity=0.85,
            popup=folium.Popup(
                f"<div style='font-family:sans-serif;color:#333'>"
                f"<b style='color:{C['vigo']}'>{r['nombre']}</b><br>"
                f"📍 {r['calle']}</div>", max_width=240),
            tooltip=r['nombre']
        ).add_to(fg_vigo)
    fg_vigo.add_to(m)
    print(f'  ✅  Vigo: {len(gdf)} charging points')
except Exception as e:
    print(f'  ⚠️  Vigo skipped: {e}')

# ── Layer control ───────────────────────────────────────────────────────────────
folium.LayerControl(collapsed=False, position='topright').add_to(m)

# ── Dashboard layout CSS + structure (fixed-position overlay) ───────────────────
LAYOUT_CSS = """
<style>
/* Let Folium map fill the full viewport as normal */
html, body { margin:0; padding:0; height:100%; overflow:hidden;
             font-family:'Segoe UI',Arial,sans-serif; }

/* ── Fixed overlay: header ── */
.db-header {
    position:fixed; top:0; left:0; right:0; height:50px;
    background:linear-gradient(90deg,#1a1a2e 0%,#0f3460 100%);
    color:white; display:flex; align-items:center; gap:14px;
    padding:0 20px; border-bottom:3px solid #0a2444; z-index:3000;
    box-sizing:border-box;
}
.db-header-icon { font-size:22px; }
.db-header-title { font-size:16px; font-weight:700; }
.db-header-subtitle { font-size:11px; color:#aab4c8; margin-top:2px; }

/* ── Fixed overlay: sidebar ── */
.db-sidebar {
    position:fixed; top:53px; left:0; bottom:26px; width:258px;
    background:white; border-right:1px solid #dde1e7;
    overflow-y:auto; z-index:2000; box-sizing:border-box;
}
.db-sidebar-section { padding:12px 14px; border-bottom:1px solid #eef0f3; }
.db-sidebar-section h4 {
    margin:0 0 8px 0; font-size:10px; font-weight:700;
    text-transform:uppercase; letter-spacing:.9px; color:#1a1a2e;
}
.legend-row { display:flex; align-items:center; font-size:12px; color:#444; margin-bottom:5px; gap:8px; }
.leg-dot { width:12px; height:12px; border-radius:50%; flex-shrink:0; border:1.5px solid rgba(0,0,0,0.15); }
.leg-line { width:22px; height:3px; border-radius:2px; flex-shrink:0; }
.op-header { font-size:11px; font-weight:700; color:#1a1a2e; margin:6px 0 4px 0; }
.readiness-guide {
    display:flex; gap:6px; margin:6px 0 4px 0; align-items:center;
    font-size:10px; color:#777;
}

/* ── Fixed overlay: source bar ── */
.db-source {
    position:fixed; bottom:0; left:0; right:0; height:26px;
    background:white; border-top:1px solid #dde1e7;
    display:flex; align-items:center; padding:0 16px;
    font-size:11px; color:#888; z-index:2000; box-sizing:border-box;
}

/* ── Push the Folium map behind the overlays ── */
.folium-map {
    position:fixed !important;
    top:53px !important; left:258px !important;
    right:0 !important; bottom:26px !important;
    width:auto !important; height:auto !important;
}
[id^="map_"] {
    position:fixed !important;
    top:53px !important; left:258px !important;
    right:0 !important; bottom:26px !important;
    width:auto !important; height:auto !important;
}

/* Hide any default Folium full-screen / attribution overlays */
.leaflet-control-attribution { display:none !important; }
</style>
<script>
/* After page loads, tell Leaflet to recalculate its size */
window.addEventListener('load', function() {
    setTimeout(function() {
        for (var id in window) {
            if (id.startsWith('map_') && window[id] && window[id].invalidateSize) {
                window[id].invalidateSize();
            }
        }
    }, 300);
});
</script>
"""

SIDEBAR = f"""
<div class="db-header">
  <div class="db-header-icon">🗺️</div>
  <div>
    <div class="db-header-title">All Data Overview — EV Infrastructure Spain</div>
    <div class="db-header-subtitle">Grid readiness × EV charging coverage × Road traffic flows · Toggle layers top-right</div>
  </div>
</div>

<div class="db-sidebar">

  <div class="db-sidebar-section">
    <h4>Grid Operators</h4>

    <div class="op-header" style="color:{C['iberdrola']}">● Iberdrola i-DE</div>
    <div class="readiness-guide">
      <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{C['iberdrola']};opacity:.9;"></span> Sufficient
      <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{C['iberdrola']};opacity:.55;"></span> Moderate
      <span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:{C['iberdrola']};opacity:.25;"></span> Congested
    </div>

    <div class="op-header" style="color:{C['endesa']}">● ENDESA e-distribución</div>
    <div class="readiness-guide">
      <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{C['endesa']};opacity:.9;"></span> Sufficient
      <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{C['endesa']};opacity:.55;"></span> Moderate
      <span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:{C['endesa']};opacity:.25;"></span> Congested
    </div>

    <div class="op-header" style="color:{C['viesgo']}">● VIESGO Distribution</div>
    <div class="readiness-guide">
      <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{C['viesgo']};opacity:.9;"></span> Sufficient
      <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{C['viesgo']};opacity:.55;"></span> Moderate
      <span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:{C['viesgo']};opacity:.25;"></span> Congested
    </div>

    <p style="font-size:10px;color:#999;margin:8px 0 0 0;">
      Scenario: 4 × 150kW chargers = 600kW per site.<br>
      Dot size + opacity = readiness level.
    </p>
  </div>

  <div class="db-sidebar-section">
    <h4>EV Charging</h4>
    <div class="legend-row">
      <span class="leg-dot" style="background:{C['ev_dgt']};"></span>
      DGT national charging stations
    </div>
    <div class="legend-row">
      <span class="leg-dot" style="background:{C['vigo']};width:10px;height:10px;"></span>
      Vigo municipal charging points
    </div>
  </div>

  <div class="db-sidebar-section">
    <h4>Road Traffic</h4>
    <div class="legend-row">
      <span class="leg-dot" style="background:{C['road_node']};"></span>
      Province node (size = outbound trips)
    </div>
    <div class="legend-row">
      <span class="leg-line" style="background:{C['road_arc']};"></span>
      Top 40 inter-province flow arcs
    </div>
  </div>

  <div class="db-sidebar-section">
    <h4>Readiness Thresholds</h4>
    <p style="font-size:11px;color:#555;margin:0;line-height:1.6;">
      ✅ <b>Sufficient</b> ≥ 720 kW<br>
      🟡 <b>Moderate</b> 480–719 kW<br>
      🔴 <b>Congested</b> &lt; 480 kW
    </p>
  </div>

</div>

<div class="db-source">📊 Sources: Iberdrola i-DE · ENDESA e-distribución · VIESGO · DGT electrolineras.xml · Concello de Vigo · MITMA OD Matrix</div>
"""

SOURCE_BAR = ""  # source bar is now part of SIDEBAR overlay

# ── Inject layout into Folium HTML ──────────────────────────────────────────────
import re
html_str = m.get_root().render()
html_str = html_str.replace('</head>', LAYOUT_CSS + '\n</head>', 1)
html_str = re.sub(r'<body>\s*', '<body>\n' + SIDEBAR + '\n', html_str, count=1)
# SOURCE_BAR is empty — no </body> injection needed

out_path = OUT / 'overview_all_data.html'
out_path.write_text(html_str, encoding='utf-8')
print(f'\n✅  Overview map saved → {out_path}')
print(f'   File size: {out_path.stat().st_size // 1024} KB')
