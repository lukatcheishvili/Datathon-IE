"""
fix_visualizations.py
Fixes 5 broken HTML visualisations:
  02a  ev_charging_folium         — blank page (MarkerCluster too heavy: 14 MB)
  06a  ev_registrations_folium    — empty (wrong EV code filter + wrong province format)
  06b  ev_registrations_map_plotly— empty (same root cause as 06a)
  07a  vigo_charging_folium       — Vigo-only → now all-Spain DGT charging sites
  07b  vigo_charging_plotly       — Vigo-only → now all-Spain DGT charging sites

Root causes fixed:
  * 02a:  removed MarkerCluster (11 567 CircleMarkers freeze the browser).
          Replaced with HeatMap + 600-point sample directly on map.
  * 06a/b: DGT MATRABA files encode electric vehicles with '2' at byte 93,
           NOT '3'/'H'/'I'/'K' as the original script assumed.
           Province codes at bytes 152-154 use OLD PLATE prefixes (M, B, V …),
           not INE numeric codes ('28', '08' …).
  * 07a/b: The "Vigo" dataset was a 13-point municipal GeoJSON.
           Replaced with the same DGT Spain-wide XML used for topic 2.
"""
import os, sys, warnings, requests, zipfile, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
import plotly.express as px
import branca.colormap as cm
from pathlib import Path
from lxml import etree

OUT = Path('visualizations')
OUT.mkdir(exist_ok=True)

# ── Spanish province LETTER codes (old matricula plates) → lat / lon / name ──
PROV_LETTER = {
    'M' : (40.417, -3.704, 'Madrid'),
    'B' : (41.582,  2.173, 'Barcelona'),
    'V' : (39.470, -0.376, 'Valencia'),
    'A' : (38.504, -0.324, 'Alicante'),
    'SE': (37.389, -5.984, 'Sevilla'),
    'Z' : (41.649, -0.889, 'Zaragoza'),
    'BI': (43.263, -2.935, 'Bizkaia'),
    'MA': (36.721, -4.421, 'Málaga'),
    'GR': (37.177, -3.599, 'Granada'),
    'MU': (37.992, -1.131, 'Murcia'),
    'CS': (39.986, -0.051, 'Castellón'),
    'T' : (41.119,  1.245, 'Tarragona'),
    'GC': (28.123,-15.436, 'Las Palmas'),
    'TF': (28.464,-16.252, 'S.C. Tenerife'),
    'IB': (39.569,  2.650, 'Illes Balears'),
    'C' : (43.132, -8.414, 'A Coruña'),
    'PO': (42.430, -8.645, 'Pontevedra'),
    'O' : (43.361, -5.859, 'Asturias'),
    'SA': (40.970, -5.664, 'Salamanca'),
    'J' : (37.780, -3.785, 'Jaén'),
    'BU': (42.344, -3.697, 'Burgos'),
    'LE': (42.599, -5.572, 'León'),
    'TO': (39.863, -4.027, 'Toledo'),
    'VA': (41.652, -4.724, 'Valladolid'),
    'AB': (38.996, -1.858, 'Albacete'),
    'CR': (39.003, -3.917, 'Ciudad Real'),
    'CU': (40.070, -2.137, 'Cuenca'),
    'GU': (40.632, -3.167, 'Guadalajara'),
    'AL': (37.004, -2.097, 'Almería'),
    'CA': (36.516, -5.903, 'Cádiz'),
    'CO': (37.885, -4.779, 'Córdoba'),
    'H' : (37.261, -6.945, 'Huelva'),
    'HU': (42.136, -0.409, 'Huesca'),
    'L' : (41.615,  0.627, 'Lleida'),
    'LO': (42.287, -2.540, 'La Rioja'),
    'LU': (43.012, -7.556, 'Lugo'),
    'NA': (42.817, -1.643, 'Navarra'),
    'OR': (42.335, -7.864, 'Ourense'),
    'P' : (41.993, -4.531, 'Palencia'),
    'SG': (40.943, -4.109, 'Segovia'),
    'SO': (41.763, -2.466, 'Soria'),
    'SS': (43.309, -2.003, 'Gipuzkoa'),
    'TE': (40.346, -1.106, 'Teruel'),
    'VI': (42.846, -2.673, 'Araba/Álava'),
    'ZA': (41.500, -5.746, 'Zamora'),
    'AV': (40.656, -4.697, 'Ávila'),
    'BA': (38.879, -6.971, 'Badajoz'),
    'CC': (39.475, -6.372, 'Cáceres'),
    'CE': (35.889, -5.321, 'Ceuta'),
    'ME': (35.292, -2.938, 'Melilla'),
}

TITLE_CSS = ('position:fixed;top:10px;left:60px;z-index:1000;background:white;'
             'padding:8px 12px;border:2px solid #ccc;border-radius:6px;'
             'font-size:14px;font-weight:bold')

def title_div(title, sub=''):
    sub_html = (f'<br><span style="font-size:11px;font-weight:normal">{sub}</span>'
                if sub else '')
    return folium.Element(f'<div style="{TITLE_CSS}">{title}{sub_html}</div>')

def save_folium(m, name):
    p = OUT / f'{name}.html'
    m.save(str(p))
    sz = p.stat().st_size / 1024
    print(f'  OK  {p.name}  ({sz:.0f} KB)')

def save_plotly(fig, name):
    p = OUT / f'{name}.html'
    fig.write_html(str(p))
    sz = p.stat().st_size / 1024
    print(f'  OK  {p.name}  ({sz:.0f} KB)')

# ── DGT XML parser (reused for sections 02a and 07a/07b) ─────────────────────
def ftext(el, tag):
    res = el.xpath(f'.//*[local-name()="{tag}"]/text()')
    return res[0].strip() if res else None

def download_dgt_charging():
    XML_URL = ('https://infocar.dgt.es/datex2/v3/miterd/'
               'EnergyInfrastructureTablePublication/electrolineras.xml')
    print('  Downloading DGT XML (~80 MB) ...')
    resp = requests.get(XML_URL, timeout=240)
    resp.raise_for_status()
    root = etree.fromstring(resp.content)
    sites = root.xpath('.//*[local-name()="energyInfrastructureSite"]')
    records = []
    for site in sites:
        lat = ftext(site, 'latitude')
        lon = ftext(site, 'longitude')
        if not lat or not lon:
            continue
        name_vals = site.xpath(
            './/*[local-name()="name"]//*[local-name()="value"]/text()')
        connectors = site.xpath(
            './/*[local-name()="energyInfrastructureConnector"]')
        records.append({
            'site_id'    : site.get('id', ''),
            'name'       : name_vals[0].strip() if name_vals else '',
            'latitude'   : float(lat),
            'longitude'  : float(lon),
            'n_connectors': len(connectors),
            'operator'   : ftext(site, 'operatorName'),
        })
    df = pd.DataFrame(records)
    df = df[df['latitude'].between(35, 44.5) &
            df['longitude'].between(-9.5, 5)].reset_index(drop=True)
    print(f'  {len(df):,} charging sites parsed')
    return df

# ══════════════════════════════════════════════════════════════════════════════
# FIX 02a  EV Charging Folium — lightweight: HeatMap + 600-point sample
# ══════════════════════════════════════════════════════════════════════════════
print('\n[FIX 02a] EV Charging Folium — removing heavy MarkerCluster ...')
df_ch = None
try:
    df_ch = download_dgt_charging()

    m = folium.Map(location=[40.2, -3.5], zoom_start=6, tiles='OpenStreetMap')

    # All-sites heat layer
    HeatMap(df_ch[['latitude', 'longitude']].values.tolist(),
            radius=12, blur=18, min_opacity=0.35, name='Heat Density').add_to(m)

    # Random 600-point sample — NO MarkerCluster (that was crashing the browser)
    sample = df_ch.sample(min(600, len(df_ch)), random_state=42)
    fg = folium.FeatureGroup(name='Sample markers (600)', show=True).add_to(m)
    for _, row in sample.iterrows():
        label = row['name'] or 'EV Charger'
        folium.CircleMarker(
            [row['latitude'], row['longitude']], radius=4,
            color='#2ca25f', fill=True, fill_color='#66c2a4',
            fill_opacity=0.8, weight=0.8,
            popup=folium.Popup(
                f"<b>{label}</b><br>Connectors: {row['n_connectors']}"
                f"<br>Operator: {row['operator'] or 'N/A'}",
                max_width=220),
            tooltip=label,
        ).add_to(fg)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div(
        'EV Charging Points — Spain DGT [Folium]',
        f'{len(df_ch):,} sites · HeatMap = all | Markers = 600 random sample'))
    save_folium(m, '02a_ev_charging_folium')

except Exception as e:
    print(f'  FAILED: {e}')

# ══════════════════════════════════════════════════════════════════════════════
# FIX 06a + 06b  EV Registrations — correct code '2', letter province codes
# ══════════════════════════════════════════════════════════════════════════════
print('\n[FIX 06a+06b] EV Registrations (propulsion code=\'2\', letter province codes) ...')

_COLS = [(0, 8, 'reg_date'), (93, 94, 'prop_code'), (152, 154, 'prov_code')]

def fetch_ev_month(year, month):
    url = (f'https://www.dgt.es/microdatos/salida/{year}/{month}'
           f'/vehiculos/matriculaciones/export_mensual_mat_{year}{month:02d}.zip')
    try:
        resp = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return pd.DataFrame()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            content = z.open(z.namelist()[0]).read().decode('latin-1')
        rows = [
            {name: line[s:e].strip() for s, e, name in _COLS}
            for line in content.splitlines()
            # KEY FIX: code '2' at byte 93 = electric vehicle in DGT MATRABA format
            if len(line) >= 200 and line[93:94] == '2'
        ]
        df = pd.DataFrame(rows)
        df['year'] = year
        df['month'] = month
        return df
    except Exception as exc:
        print(f'    skip {year}-{month:02d}: {exc}')
        return pd.DataFrame()

batches = []
for mo in range(1, 13):
    print(f'  2025-{mo:02d}... ', end='', flush=True)
    tmp = fetch_ev_month(2025, mo)
    if len(tmp):
        print(f'{len(tmp):,} EVs')
        batches.append(tmp)
    else:
        print('skip')

if batches:
    df_ev = pd.concat(batches, ignore_index=True)
    print(f'  Total 2025 EV registrations: {len(df_ev):,}')

    # Aggregate by LETTER province code, keep only known codes
    prov_ev = (df_ev.groupby('prov_code')
               .agg(total_ev=('prop_code', 'count'))
               .reset_index()
               .rename(columns={'prov_code': 'code'}))
    prov_ev = prov_ev[prov_ev['code'].isin(PROV_LETTER)].copy()
    prov_ev['lat']  = prov_ev['code'].map(lambda c: PROV_LETTER[c][0])
    prov_ev['lon']  = prov_ev['code'].map(lambda c: PROV_LETTER[c][1])
    prov_ev['name'] = prov_ev['code'].map(lambda c: PROV_LETTER[c][2])
    max_ev = prov_ev['total_ev'].max()
    print(f'  {len(prov_ev)} provinces with EV registrations')

    # ── 06a  Folium ──────────────────────────────────────────────────────────
    m = folium.Map(location=[40.2, -3.5], zoom_start=6, tiles='OpenStreetMap')

    for _, r in prov_ev.iterrows():
        ratio = r['total_ev'] / max_ev
        folium.CircleMarker(
            [r['lat'], r['lon']], radius=5 + 28 * ratio,
            color='#08306b', weight=1, fill=True,
            fill_color='#4292c6', fill_opacity=0.75,
            popup=folium.Popup(
                f"<b>{r['name']}</b><br>EV Registrations 2025: {r['total_ev']:,}",
                max_width=230),
            tooltip=f"{r['name']} — {r['total_ev']:,} EVs",
        ).add_to(m)

    heat_data = [[r['lat'], r['lon'], r['total_ev']]
                 for _, r in prov_ev.iterrows()]
    HeatMap(heat_data, radius=35, blur=25, min_opacity=0.3,
            gradient={'0.4': 'blue', '0.65': 'lime', '1': 'red'}).add_to(m)

    m.get_root().html.add_child(title_div(
        'EV Registrations — Spain by Province (2025) [Folium]',
        'Circles = EV count · Heat = density distribution'))
    save_folium(m, '06a_ev_registrations_folium')

    # ── 06b  Plotly ──────────────────────────────────────────────────────────
    prov_ev['size_col'] = prov_ev['total_ev'] / max_ev * 36 + 5
    fig = px.scatter_mapbox(
        prov_ev, lat='lat', lon='lon',
        color='total_ev', size='size_col', hover_name='name',
        hover_data={'total_ev': ':,', 'lat': False, 'lon': False, 'size_col': False},
        color_continuous_scale='Blues', size_max=40,
        zoom=5, center=dict(lat=40.2, lon=-3.5),
        mapbox_style='open-street-map',
        title='EV Vehicle Registrations by Province — Spain 2025 [Plotly / OSM]',
        labels={'total_ev': 'Total EVs'})
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=50, b=0))
    save_plotly(fig, '06b_ev_registrations_map_plotly')

else:
    print('  FAILED: no EV registration data fetched')

# ══════════════════════════════════════════════════════════════════════════════
# FIX 07a + 07b  All-Spain DGT Charging (replace Vigo 13-point dataset)
# ══════════════════════════════════════════════════════════════════════════════
print('\n[FIX 07a+07b] All-Spain EV Charging — DGT national data ...')

if df_ch is None:
    # 02a failed, need fresh download
    try:
        df_ch = download_dgt_charging()
    except Exception as e:
        print(f'  FAILED to download DGT data: {e}')
        df_ch = pd.DataFrame()

if len(df_ch):
    df = df_ch

    # ── 07a  Folium (all Spain) ───────────────────────────────────────────────
    m = folium.Map(location=[40.2, -3.5], zoom_start=6, tiles='OpenStreetMap')

    HeatMap(df[['latitude', 'longitude']].values.tolist(),
            radius=12, blur=18, min_opacity=0.35, name='Heat Density').add_to(m)

    sample = df.sample(min(600, len(df)), random_state=99)
    fg = folium.FeatureGroup(name='Sample markers (600)', show=True).add_to(m)
    for _, row in sample.iterrows():
        label = row['name'] or 'EV Charger'
        folium.CircleMarker(
            [row['latitude'], row['longitude']], radius=4,
            color='#2ca25f', fill=True, fill_color='#66c2a4',
            fill_opacity=0.8, weight=0.8,
            popup=folium.Popup(
                f"<b>{label}</b><br>Connectors: {row['n_connectors']}"
                f"<br>Operator: {row['operator'] or 'N/A'}",
                max_width=220),
            tooltip=label,
        ).add_to(fg)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div(
        'EV Charging Points — All Spain DGT [Folium]',
        f'{len(df):,} charging sites across Spain · HeatMap = all | Markers = 600 sample'))
    save_folium(m, '07a_vigo_charging_folium')

    # ── 07b  Plotly (all Spain) ───────────────────────────────────────────────
    fig = px.scatter_mapbox(
        df, lat='latitude', lon='longitude', hover_name='name',
        hover_data={
            'operator'    : True,
            'n_connectors': True,
            'site_id'     : False,
            'latitude'    : False,
            'longitude'   : False,
        },
        color_discrete_sequence=['#2ca25f'],
        zoom=5, center=dict(lat=40.2, lon=-3.5),
        mapbox_style='open-street-map', opacity=0.55,
        title=f'EV Charging Sites — All Spain DGT ({len(df):,} sites) [Plotly / OSM]')
    fig.update_traces(marker_size=5)
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=50, b=0))
    save_plotly(fig, '07b_vigo_charging_plotly')

else:
    print('  FAILED: no DGT charging data available')

print('\n' + '='*60)
print('Done!  Fixed files in:  visualizations/')
fixed = ['02a_ev_charging_folium.html',
         '06a_ev_registrations_folium.html',
         '06b_ev_registrations_map_plotly.html',
         '07a_vigo_charging_folium.html',
         '07b_vigo_charging_plotly.html']
for f in fixed:
    p = OUT / f
    if p.exists():
        print(f'  {f}  ({p.stat().st_size/1024:.0f} KB)')
    else:
        print(f'  {f}  [MISSING]')
