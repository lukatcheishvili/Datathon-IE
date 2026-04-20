"""
generate_visualizations.py
Run from the Datathon/ folder:  python generate_visualizations.py
Produces 14 HTML maps in  visualizations/
"""
import os, sys, warnings, requests, zipfile, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster, HeatMap
import plotly.express as px
import plotly.graph_objects as go
import branca.colormap as cm
from pyproj import Transformer
from pathlib import Path
from lxml import etree

# Robust Pathing
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
OUT = BASE_DIR.parent / "visualizations"
OUT.mkdir(exist_ok=True)
print(f'Output folder: {OUT.resolve()}\n')

# ── Shared province centroids ─────────────────────────────────────────────────
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

def utm_to_wgs84(df):
    t = Transformer.from_crs('EPSG:25830','EPSG:4326',always_xy=True)
    valid = df['utm_x'].notna() & df['utm_y'].notna()
    lons, lats = t.transform(df.loc[valid,'utm_x'].values, df.loc[valid,'utm_y'].values)
    df.loc[valid,'longitude'] = lons
    df.loc[valid,'latitude']  = lats
    return df

def util_col(df):
    total = df['capacity_available_mw'].fillna(0) + df['capacity_occupied_mw'].fillna(0)
    df['util']     = np.where(total>0, df['capacity_occupied_mw']/total, 0)
    df['util_pct'] = df['util']*100
    return df

CMAP_RYG = ['#1a9641','#fdae61','#d7191c']
TITLE_CSS = ('position:fixed;top:10px;left:60px;z-index:1000;background:white;'
             'padding:8px 12px;border:2px solid #ccc;border-radius:6px;'
             'font-size:14px;font-weight:bold')

def title_div(title, sub=''):
    sub_html = f'<br><span style="font-size:11px;font-weight:normal">{sub}</span>' if sub else ''
    return folium.Element(f'<div style="{TITLE_CSS}; color: #333; background-color: rgba(255,255,255,0.9);">{title}{sub_html}</div>')

def get_discrete_color(available_mw):
    """
    User logic for 4-charger scenario (D=600kW):
    Sufficient: >= 720 kW | Moderate: 480-719 kW | Congested: < 480 kW
    """
    available_kw = available_mw * 1000
    if available_kw >= 720:
        return '#1a9641', 'Sufficient'  # Green
    elif available_kw >= 480:
        return '#fec200', 'Moderate'    # Yellow
    else:
        return '#d7191c', 'Congested'   # Red

def save_folium(m, name):
    p = OUT / f'{name}.html'
    m.save(str(p))
    print(f'  ✅  {p}')

def save_plotly(fig, name):
    p = OUT / f'{name}.html'
    fig.write_html(str(p))
    print(f'  ✅  {p}')

# ══════════════════════════════════════════════════════════════
# 1. ROAD ROUTES
# ══════════════════════════════════════════════════════════════
print('\n[1/7] Road Routes ...')
od_file = DATA_DIR / 'road_routes/od_rutas/20240331_OD_rutas.csv'
if od_file.exists():
    df_od = pd.read_csv(od_file, nrows=500_000)   # sample for speed
    df_od['origin_prov'] = df_od['origin_zone'].astype(str).str[:2]
    df_od['dest_prov']   = df_od['destination_zone'].astype(str).str[:2]
    
    # FILTER: Focus on Inter-Province / Inter-CCAA flows (Interurban)
    # We drop intra-provincial trips to highlight the long-distance arteries
    df_od = df_od[df_od['origin_prov'] != df_od['dest_prov']]
    
    prov_od  = df_od.groupby(['origin_prov','dest_prov'])['trips'].sum().reset_index()
    prov_out = (df_od.groupby('origin_prov')['trips'].sum()
                .reset_index().rename(columns={'origin_prov':'code','trips':'total_trips'}))
    prov_out = prov_out[prov_out['code'].isin(PC)].copy()
    prov_out['lat']  = prov_out['code'].map(lambda c: PC[c][0])
    prov_out['lon']  = prov_out['code'].map(lambda c: PC[c][1])
    prov_out['name'] = prov_out['code'].map(lambda c: PC[c][2])
    top_flows = prov_od[prov_od['origin_prov']!=prov_od['dest_prov']].nlargest(40,'trips')
    max_trips = prov_out['total_trips'].max()
    max_flow  = top_flows['trips'].max()

    # Folium
    m = folium.Map(location=[40.2,-3.5], zoom_start=6, tiles='CartoDB Positron')
    for _, r in prov_out.iterrows():
        ratio = r['total_trips']/max_trips
        folium.CircleMarker([r['lat'],r['lon']], radius=5+27*ratio,
            color='#08306b', weight=1, fill=True, fill_color='#4292c6', fill_opacity=0.75,
            popup=folium.Popup(f"<b>{r['name']}</b><br>Trips: {r['total_trips']:,.0f}",max_width=200),
            tooltip=f"{r['name']} — {r['total_trips']:,.0f} trips").add_to(m)
    for _, r in top_flows.iterrows():
        o,d = r['origin_prov'],r['dest_prov']
        if o in PC and d in PC:
            folium.PolyLine([[PC[o][0],PC[o][1]],[PC[d][0],PC[d][1]]], color='#d94801',
                weight=1.5+5*(r['trips']/max_flow), opacity=0.3+0.5*(r['trips']/max_flow),
                tooltip=f"{PC[o][2]} → {PC[d][2]}: {r['trips']:,.0f}").add_to(m)
    m.get_root().html.add_child(title_div('🛣️ Road OD Flows — Spain (2024-03-31) [Folium]',
                                          'Circles = total trips | Lines = top 40 inter-province flows'))
    save_folium(m, 'road_od_flows_spain')

else:
    print('  ⚠️  OD routes CSV not found — skipping Road Routes')

# ══════════════════════════════════════════════════════════════
# 2. EV CHARGING POINTS (DGT)
# ══════════════════════════════════════════════════════════════
print('\n[2/7] EV Charging Points (DGT) ...')
try:
    XML_URL = 'https://infocar.dgt.es/datex2/v3/miterd/EnergyInfrastructureTablePublication/electrolineras.xml'
    print('  Downloading DGT XML (~80 MB) ...')
    r = requests.get(XML_URL, timeout=180)
    root = etree.fromstring(r.content)
    def ftext(el, name):
        res = el.xpath(f'.//*[local-name()="{name}"]/text()')
        return res[0].strip() if res else None
    sites = root.xpath('.//*[local-name()="energyInfrastructureSite"]')
    records = []
    for site in sites:
        lat = ftext(site,'latitude'); lon = ftext(site,'longitude')
        if not lat or not lon: continue
        name_vals = site.xpath('.//*[local-name()="name"]//*[local-name()="value"]/text()')
        connectors = site.xpath('.//*[local-name()="energyInfrastructureConnector"]')
        records.append({'site_id': site.get('id',''),
            'name': name_vals[0].strip() if name_vals else '',
            'latitude': float(lat), 'longitude': float(lon),
            'n_connectors': len(connectors),
            'operator': ftext(site,'operatorName')})
    df_ch = pd.DataFrame(records)
    
    # FILTER: Drop stations within major city centers (Interurban/Entrance only)
    major_cities = ['MADRID', 'BARCELONA', 'VALENCIA', 'SEVILLA', 'ZARAGOZA', 'BILBAO', 'MALAGA']
    df_ch = df_ch[~df_ch['name'].str.upper().str.contains('|'.join(major_cities))]
    
    df_ch = df_ch[df_ch['latitude'].between(35,44.5) & df_ch['longitude'].between(-9.5,5)].reset_index(drop=True)
    print(f'  {len(df_ch):,} interurban charging sites parsed')

    # Plotly
    fig1 = px.density_mapbox(df_ch, lat='latitude', lon='longitude', radius=10,
        center=dict(lat=40.2,lon=-3.5), zoom=5, mapbox_style='carto-positron',
        title=f'EV Charging Density — Spain DGT ({len(df_ch):,} sites) [Plotly / OSM]',
        color_continuous_scale='YlOrRd')
    fig1.update_layout(height=580, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig1, 'ev_charging_density_spain')

    fig2 = px.scatter_mapbox(df_ch, lat='latitude', lon='longitude',
        hover_name='name', hover_data={'operator':True,'site_id':False,'latitude':False,'longitude':False},
        color_discrete_sequence=['#2ca25f'], zoom=5, center=dict(lat=40.2,lon=-3.5),
        mapbox_style='carto-positron', opacity=0.55,
        title='EV Charging Sites — individual points [Plotly / OSM]')
    fig2.update_traces(marker_size=5)
    fig2.update_layout(height=580, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig2, 'ev_charging_stations_spain')
except Exception as e:
    print(f'  ⚠️  EV Charging skipped: {e}')

# ══════════════════════════════════════════════════════════════
# 3. IBERDROLA
# ══════════════════════════════════════════════════════════════
print('\n[3/7] Iberdrola ...')
ib_path = DATA_DIR / 'Iberdrola Historical Map of Electricity Consumption Capacity/2026_03_05_R1-001_Demanda.csv'
if ib_path.exists():
    df_ib = pd.read_csv(ib_path, sep=';', encoding='utf-8-sig', decimal=',', thousands='.', on_bad_lines='skip')
    df_ib.columns = df_ib.columns.str.strip()
    rename = {'Gestor de red':'grid_operator','Provincia':'province','Municipio':'municipality',
               'Coordenada UTM X':'utm_x','Coordenada UTM Y':'utm_y','Subestación':'substation_id',
               'Nivel de Tensión (kV)':'voltage_kv','Capacidad firme disponible (MW)':'capacity_available_mw',
               'Capacidad de acceso firme de demanda ocupada (MW)':'capacity_occupied_mw'}
    df_ib = df_ib.rename(columns={k:v for k,v in rename.items() if k in df_ib.columns})
    df_ib = utm_to_wgs84(df_ib)
    df_ib = df_ib[df_ib['latitude'].between(35,44.5) & df_ib['longitude'].between(-9.5,5)].reset_index(drop=True)
    df_ib = util_col(df_ib)

    # Folium
    m = folium.Map(location=[40.4,-3.7], zoom_start=6, tiles='CartoDB Positron')
    
    for _, r in df_ib.iterrows():
        col, status = get_discrete_color(r['capacity_available_mw'])
        folium.CircleMarker([r['latitude'],r['longitude']],
            radius=6,
            color=col, fill=True, fill_color=col, fill_opacity=0.8, weight=1,
            popup=folium.Popup(
                f"<div style='color:#333; min-width:150px; font-family:sans-serif;'>"
                f"<h4 style='margin:0; color:{col};'>{status}</h4><hr>"
                f"<b>Substation:</b> {r['substation_id']}<br>"
                f"<b>Available:</b> {r['capacity_available_mw']:.2f} MW<br>"
                f"<b>Readiness:</b> 4-Charger Site (600kW)"
                f"</div>", max_width=250),
            tooltip=f"{r['substation_id']} | {status}").add_to(m)
    
    # Legend overlay
    legend_html = f"""
    <div style="position:fixed; bottom: 50px; left: 50px; width: 220px; height: 110px; 
                background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                padding: 10px; border-radius: 8px; color: #333; line-height: 1.6;">
        <b>Grid Readiness (600kW)</b><br>
        <i style="background: #1a9641; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Sufficient (≥ 720 kW)<br>
        <i style="background: #fec200; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Moderate (480-719 kW)<br>
        <i style="background: #d7191c; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Congested (< 480 kW)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    m.get_root().html.add_child(title_div('🔌 Iberdrola i-DE — Expansion Readiness',
                                          "Scenario: 4 x 150kW Chargers (Total Demand: 600kW)"))
    save_folium(m, 'iberdrola_ide_expansion_readiness')

else:
    print('  ⚠️  Iberdrola CSV not found')

# ══════════════════════════════════════════════════════════════
# 4. ENDESA
# ══════════════════════════════════════════════════════════════
print('\n[4/7] ENDESA ...')
endesa_dir = DATA_DIR / 'ENDESA - e-distribucion'
csv_files  = sorted(endesa_dir.glob('*.csv')) if endesa_dir.exists() else []
if csv_files:
    dfs = []
    for fp in csv_files:
        df = pd.read_csv(fp, sep=';', encoding='utf-8-sig', decimal=',', thousands='.', on_bad_lines='skip')
        df['source_file'] = fp.name; dfs.append(df)
    df_en = pd.concat(dfs, ignore_index=True)
    df_en.columns = df_en.columns.str.strip()
    # deduplicate repeated column names
    seen = {}; deduped = []
    for c in df_en.columns:
        seen[c] = seen.get(c,0); deduped.append(c if seen[c]==0 else f'{c}_{seen[c]}'); seen[c]+=1
    df_en.columns = deduped
    rename = {'Gestor de red':'grid_operator','Coordenada UTM X':'utm_x','Coordenada UTM Y':'utm_y',
               'Nivel de Tensión (kV)':'voltage_kv','Capacidad disponible (MW)':'capacity_available_mw',
               'Capacidad ocupada (MW)':'capacity_occupied_mw','Nombre Subestación':'substation_name',
               'Comunidad Autónoma':'autonomous_community','Provincia_1':'province_name'}
    df_en = df_en.rename(columns={k:v for k,v in rename.items() if k in df_en.columns})
    df_en = utm_to_wgs84(df_en)
    df_en = df_en[df_en['latitude'].between(35,44.5) & df_en['longitude'].between(-9.5,5)].reset_index(drop=True)
    df_en = util_col(df_en)
    if 'substation_name' not in df_en.columns:
        df_en['substation_name'] = df_en.get('substation_id','N/A')

    # Folium
    m = folium.Map(location=[38.5,-2.0], zoom_start=6, tiles='CartoDB Positron')
    operators = df_en['grid_operator'].dropna().unique()
    fg = {op: folium.FeatureGroup(name=f'ENDESA {op}').add_to(m) for op in operators}
    for _, r in df_en.iterrows():
        col, status = get_discrete_color(r['capacity_available_mw'])
        name = r.get('substation_name','N/A')
        folium.CircleMarker([r['latitude'],r['longitude']],
            radius=6,
            color=col, fill=True, fill_color=col, fill_opacity=0.8, weight=1,
            popup=folium.Popup(
                f"<div style='color:#333; min-width:150px; font-family:sans-serif;'>"
                f"<h4 style='margin:0; color:{col};'>{status}</h4><hr>"
                f"<b>Node:</b> {name}<br>"
                f"<b>Available:</b> {r['capacity_available_mw']:.2f} MW<br>"
                f"<b>Provider:</b> {r['grid_operator']}"
                f"</div>", max_width=260),
            tooltip=f"{name} | {status}").add_to(fg.get(r['grid_operator'],m))
    
    legend_html = f"""
    <div style="position:fixed; bottom: 50px; left: 50px; width: 180px; height: 110px; 
                background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                padding: 10px; border-radius: 8px; color: #333;">
        <b>Readiness (600kW Demand)</b><br>
        <i style="background: #1a9641; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Sufficient (≥ 720 kW)<br>
        <i style="background: #fec200; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Moderate (480-719 kW)<br>
        <i style="background: #d7191c; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Congested (< 480 kW)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div('⚡ ENDESA e-distribución — Generation Capacity',
                                          'Discrete Readiness segments for 600kW deployments'))
    save_folium(m, 'endesa_edistribucion_expansion_readiness')

else:
    print('  ⚠️  ENDESA CSV files not found')

# ══════════════════════════════════════════════════════════════
# 5. VIESGO
# ══════════════════════════════════════════════════════════════
print('\n[5/7] VIESGO ...')
viesgo_dir = DATA_DIR / 'VIESGO'

def load_viesgo(fname):
    df = pd.read_csv(viesgo_dir/fname, sep=';', encoding='latin-1', skip_blank_lines=True)
    df.columns = df.columns.str.strip().str.replace('\n',' ',regex=False)
    rename = {'Gestor de red':'grid_operator','Provincia':'province','Municipio':'municipality',
               'Coordenada UTM X':'utm_x_raw','Coordenada UTM Y':'utm_y_raw',
               'Subestación ':'substation_id','Subestación':'substation_id','Nombre subestación':'substation_name',
               'Nombre Subestación':'substation_name','Nivel de tensión (kV)':'voltage_kv',
               'Nivel de Tensión (kV)':'voltage_kv',
               'Capacidad firme disponible (MW)':'capacity_available_mw',
               'Capacidad disponible (MW)':'capacity_available_mw',
               'Capacidad de acceso firme de demanda ocupada (MW)':'capacity_occupied_mw',
               'Capacidad ocupada (MW)':'capacity_occupied_mw'}
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    def parse_utm(s):
        return pd.to_numeric(s.astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),errors='coerce')
    df['utm_x'] = parse_utm(df['utm_x_raw'])
    df['utm_y'] = parse_utm(df['utm_y_raw'])
    for col in ['voltage_kv','capacity_available_mw','capacity_occupied_mw']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',','.').str.strip(),errors='coerce')
    df = utm_to_wgs84(df)
    return df.dropna(subset=['substation_id']).reset_index(drop=True)

if viesgo_dir.exists():
    df_vd = util_col(load_viesgo('2026_04_01_R1005_demanda_Consumption capacity in the network.csv'))
    df_vg = util_col(load_viesgo('2026_04_01_R1005_generacion_Generation capacity in the network.csv'))

    colormap = cm.LinearColormap(CMAP_RYG, vmin=0, vmax=1, caption='Capacity Utilisation')

    # Folium
    m = folium.Map(location=[43.2,-4.5], zoom_start=7, tiles='CartoDB Positron')
    fg_d = folium.FeatureGroup(name='⬇ Demand').add_to(m)
    fg_g = folium.FeatureGroup(name='⬆ Generation').add_to(m)
    for fg, df, tag in [(fg_d,df_vd,'DEMAND'),(fg_g,df_vg,'GENERATION')]:
        for _, r in df.dropna(subset=['latitude','longitude']).iterrows():
            col, status = get_discrete_color(r['capacity_available_mw'])
            name = r.get('substation_name', r.get('substation_id','N/A'))
            folium.CircleMarker([r['latitude'],r['longitude']],
                radius=6,
                color=col, fill=True, fill_color=col, fill_opacity=0.8, weight=1,
                popup=folium.Popup(
                    f"<div style='color:#333; min-width:150px; font-family:sans-serif;'>"
                    f"<h4 style='margin:0; color:{col};'>{status}</h4><hr>"
                    f"<b>Substation:</b> {name} [{tag}]<br>"
                    f"<b>Available:</b> {r['capacity_available_mw']:.2f} MW<br>"
                    f"<b>Deployment:</b> 600kW Scenario"
                    f"</div>", max_width=250),
                tooltip=f"{name} [{tag[0]}] | {status}").add_to(fg)
    
    legend_html = f"""
    <div style="position:fixed; bottom: 50px; left: 50px; width: 180px; height: 110px; 
                background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                padding: 10px; border-radius: 8px; color: #333;">
        <b>Readiness (600kW Demand)</b><br>
        <i style="background: #1a9641; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Sufficient (≥ 720 kW)<br>
        <i style="background: #fec200; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Moderate (480-719 kW)<br>
        <i style="background: #d7191c; width: 12px; height: 12px; display: inline-block; border-radius:50%;"></i> Congested (< 480 kW)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div('🌐 VIESGO Distribution — Expansion Readiness',
                                          'Scenario: 4 x 150kW Chargers (Total Demand: 600kW)'))
    save_folium(m, 'viesgo_distribution_expansion_readiness')

else:
    print('  ⚠️  VIESGO data folder not found')

# ══════════════════════════════════════════════════════════════
# 6. VEHICLE REGISTRATIONS (EV subset, 2025 only for speed)
# ══════════════════════════════════════════════════════════════
print('\n[6/7] Vehicle Registrations (fetching EV records for 2025) ...')
EV_CODES = ['3','H','I','K']
PROP_LBL = {'3':'Pure Electric','H':'PHEV Gasoline','I':'PHEV Diesel','K':'PHEV Other'}
_COLS = [(0,8,'reg_date'),(93,94,'prop_code'),(152,154,'prov_code')]

def fetch_ev_month(year, month):
    url = (f'https://www.dgt.es/microdatos/salida/{year}/{month}'
           f'/vehiculos/matriculaciones/export_mensual_mat_{year}{month:02d}.zip')
    try:
        r = requests.get(url, timeout=60, headers={'User-Agent':'Mozilla/5.0'})
        if r.status_code != 200: return pd.DataFrame()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            content = z.open(z.namelist()[0]).read().decode('latin-1')
        rows = [
            {name: line[s:e].strip() for s,e,name in _COLS}
            for line in content.splitlines()
            if len(line)>=200 and line[93:94].strip() in EV_CODES
        ]
        df = pd.DataFrame(rows)
        df['year']=year; df['month']=month
        return df
    except Exception as e:
        print(f'    skip {year}-{month:02d}: {e}')
        return pd.DataFrame()

mini = []
for mo in range(1,13):
    print(f'  2025-{mo:02d}... ', end='', flush=True)
    tmp = fetch_ev_month(2025, mo)
    if len(tmp): print(f'{len(tmp):,} EVs'); mini.append(tmp)
    else: print('skip')

if mini:
    df_ev = pd.concat(mini, ignore_index=True)
    df_ev['propulsion_label'] = df_ev['prop_code'].map(PROP_LBL).fillna('Other EV')
    prov_ev = (df_ev.groupby('prov_code')
               .agg(total_ev=('prop_code','count'),
                    pure_bev=('prop_code', lambda x:(x=='3').sum()),
                    phev    =('prop_code', lambda x: x.isin(['H','I','K']).sum()))
               .reset_index().rename(columns={'prov_code':'code'}))
    prov_ev = prov_ev[prov_ev['code'].isin(PC)].copy()
    prov_ev['lat']  = prov_ev['code'].map(lambda c: PC[c][0])
    prov_ev['lon']  = prov_ev['code'].map(lambda c: PC[c][1])
    prov_ev['name'] = prov_ev['code'].map(lambda c: PC[c][2])
    max_ev = prov_ev['total_ev'].max()

else:
    print('  ⚠️  No EV registration data fetched')

# ══════════════════════════════════════════════════════════════
# 7. VIGO CHARGING POINTS
# ══════════════════════════════════════════════════════════════
print('\n[7/7] Vigo Charging Points ...')
try:
    import geopandas as gpd
    VIGO_URL = 'https://datos.vigo.org/data/trafico/ptos_recarga.geojson'
    gdf = gpd.read_file(VIGO_URL)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf['longitude'] = gdf.geometry.x
    gdf['latitude']  = gdf.geometry.y
    print(f'  {len(gdf)} charging points loaded')

    # Folium
    m = folium.Map(location=[42.225,-8.720], zoom_start=13, tiles='CartoDB Positron')
    for _, r in gdf.iterrows():
        web_html = (f'<br>🌐 <a href="{r["web"]}" target="_blank">Website</a>'
                    if r.get('web') and pd.notna(r['web']) else '')
        tel_html = f'<br>📞 {r["telefono"]}' if r.get('telefono') and pd.notna(r['telefono']) else ''
        barrio   = f', {r["barrio"]}' if r.get('barrio') and pd.notna(r['barrio']) else ''
        folium.Marker([r['latitude'],r['longitude']],
            popup=folium.Popup(
                f"<b>{r['nombre']}</b><br>📍 {r['calle']}{barrio}<br>📮 {r['codigo_postal']}"
                +tel_html+web_html, max_width=270),
            tooltip=r['nombre'],
            icon=folium.Icon(color='green',icon='bolt',prefix='fa')).add_to(m)
    folium.Circle([42.225,-8.720], radius=4000, color='#2ca25f',
        fill=True, fill_opacity=0.05, weight=2, dash_array='8').add_to(m)
    m.get_root().html.add_child(title_div('⚡ Vigo EV Charging Points — Municipal Dataset [Folium]',
                                          f'{len(gdf)} public charging locations · Click for details'))
    save_folium(m, 'vigo_ev_charging_points')

except Exception as e:
    print(f'  ⚠️  Vigo skipped: {e}')

# ══════════════════════════════════════════════════════════════
print(f'\n{"="*60}')
print(f'Done! All files saved to: {OUT.resolve()}')
files = sorted(OUT.glob('*.html'))
print(f'{len(files)} HTML files:')
for f in files:
    print(f'  {f.name}')