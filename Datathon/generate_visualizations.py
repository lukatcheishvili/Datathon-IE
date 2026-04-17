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

OUT = Path('visualizations')
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
    return folium.Element(f'<div style="{TITLE_CSS}">{title}{sub_html}</div>')

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
od_file = Path('data/road_routes/od_rutas/20240331_OD_rutas.csv')
if od_file.exists():
    df_od = pd.read_csv(od_file, nrows=500_000)   # sample for speed
    df_od['origin_prov'] = df_od['origin_zone'].astype(str).str[:2]
    df_od['dest_prov']   = df_od['destination_zone'].astype(str).str[:2]
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
    m = folium.Map(location=[40.2,-3.5], zoom_start=6, tiles='OpenStreetMap')
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
    save_folium(m, '01a_road_routes_folium')

    # Plotly
    fig = go.Figure()
    for _, r in top_flows.iterrows():
        o,d = r['origin_prov'],r['dest_prov']
        if o in PC and d in PC:
            a = 0.25+0.60*(r['trips']/max_flow)
            fig.add_trace(go.Scattermapbox(lat=[PC[o][0],PC[d][0],None],lon=[PC[o][1],PC[d][1],None],
                mode='lines',line=dict(color=f'rgba(217,72,1,{a:.2f})',width=0.8+4*(r['trips']/max_flow)),
                hoverinfo='skip',showlegend=False))
    fig.add_trace(go.Scattermapbox(
        lat=prov_out['lat'], lon=prov_out['lon'], mode='markers',
        marker=dict(size=prov_out['total_trips']/max_trips*36+6, color=prov_out['total_trips'],
                    colorscale='Blues', showscale=True,
                    colorbar=dict(title='Trips'), opacity=0.85),
        text=prov_out['name'], customdata=prov_out[['total_trips']],
        hovertemplate='<b>%{text}</b><br>Trips: %{customdata[0]:,.0f}<extra></extra>'))
    fig.update_layout(mapbox_style='open-street-map', mapbox=dict(center=dict(lat=40.2,lon=-3.5),zoom=5),
        title='Road OD Flows — Total Trips by Province [Plotly / OSM]',
        height=620, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig, '01b_road_routes_plotly')
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
    df_ch = df_ch[df_ch['latitude'].between(35,44.5) & df_ch['longitude'].between(-9.5,5)].reset_index(drop=True)
    print(f'  {len(df_ch):,} charging sites parsed')

    # Folium
    m = folium.Map(location=[40.2,-3.5], zoom_start=6, tiles='OpenStreetMap')
    HeatMap(df_ch[['latitude','longitude']].values.tolist(), radius=12, blur=18,
            min_opacity=0.35, name='Heat Density').add_to(m)
    mc = MarkerCluster(name='Charging Sites (cluster)', show=False).add_to(m)
    for _, r in df_ch.iterrows():
        folium.CircleMarker([r['latitude'],r['longitude']], radius=4,
            color='#2ca25f', fill=True, fill_color='#66c2a4', fill_opacity=0.8, weight=0.8,
            popup=folium.Popup(f"<b>{r['name'] or 'EV Charger'}</b><br>Operator: {r['operator'] or 'N/A'}",max_width=220),
            tooltip=r['name'] or 'EV Charger').add_to(mc)
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div('⚡ EV Charging Points — Spain DGT [Folium]',
                                          f'{len(df_ch):,} sites · Toggle: HeatMap | Cluster markers'))
    save_folium(m, '02a_ev_charging_folium')

    # Plotly
    fig1 = px.density_mapbox(df_ch, lat='latitude', lon='longitude', radius=10,
        center=dict(lat=40.2,lon=-3.5), zoom=5, mapbox_style='open-street-map',
        title=f'EV Charging Density — Spain DGT ({len(df_ch):,} sites) [Plotly / OSM]',
        color_continuous_scale='YlOrRd')
    fig1.update_layout(height=580, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig1, '02b_ev_charging_density_plotly')

    fig2 = px.scatter_mapbox(df_ch, lat='latitude', lon='longitude',
        hover_name='name', hover_data={'operator':True,'site_id':False,'latitude':False,'longitude':False},
        color_discrete_sequence=['#2ca25f'], zoom=5, center=dict(lat=40.2,lon=-3.5),
        mapbox_style='open-street-map', opacity=0.55,
        title='EV Charging Sites — individual points [Plotly / OSM]')
    fig2.update_traces(marker_size=5)
    fig2.update_layout(height=580, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig2, '02c_ev_charging_scatter_plotly')
except Exception as e:
    print(f'  ⚠️  EV Charging skipped: {e}')

# ══════════════════════════════════════════════════════════════
# 3. IBERDROLA
# ══════════════════════════════════════════════════════════════
print('\n[3/7] Iberdrola ...')
ib_path = Path('data/Iberdrola Historical Map of Electricity Consumption Capacity/2026_03_05_R1-001_Demanda.csv')
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

    colormap = cm.LinearColormap(CMAP_RYG, vmin=0, vmax=1, caption='Capacity Utilisation')

    # Folium
    m = folium.Map(location=[40.4,-3.7], zoom_start=6, tiles='OpenStreetMap')
    colormap.add_to(m)
    for _, r in df_ib.iterrows():
        col = colormap(r['util'])
        folium.CircleMarker([r['latitude'],r['longitude']],
            radius=max(3,min(11, r['capacity_occupied_mw']/20+3)),
            color=col, fill=True, fill_color=col, fill_opacity=0.75, weight=0.5,
            popup=folium.Popup(
                f"<b>{r['substation_id']}</b><br>Province: {r['province']}<br>"
                f"Voltage: {r['voltage_kv']} kV<br>Available: {r['capacity_available_mw']:.2f} MW<br>"
                f"Occupied: {r['capacity_occupied_mw']:.2f} MW<br>Utilisation: {r['util_pct']:.1f}%",max_width=250),
            tooltip=f"{r['substation_id']} | {r['util_pct']:.0f}% used").add_to(m)
    m.get_root().html.add_child(title_div('🔌 Iberdrola i-DE — Consumption Capacity [Folium]',
                                          f"{len(df_ib):,} substations · Size=occupied MW · Colour: green=free → red=full"))
    save_folium(m, '03a_iberdrola_folium')

    # Plotly
    df_ib['size_col'] = df_ib['capacity_occupied_mw'].clip(upper=200).fillna(1)+2
    fig = px.scatter_mapbox(df_ib, lat='latitude', lon='longitude',
        color='util_pct', size='size_col', hover_name='substation_id',
        hover_data={'province':True,'voltage_kv':True,'capacity_available_mw':':.2f',
                    'capacity_occupied_mw':':.2f','util_pct':':.1f','latitude':False,'longitude':False,'size_col':False},
        color_continuous_scale='RdYlGn_r', range_color=[0,100], size_max=18,
        zoom=5, center=dict(lat=40.4,lon=-3.7), mapbox_style='open-street-map',
        title='Iberdrola i-DE — Substation Consumption Capacity Utilisation (%) [Plotly / OSM]',
        labels={'util_pct':'Utilisation (%)'})
    fig.update_layout(height=650, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig, '03b_iberdrola_plotly')
else:
    print('  ⚠️  Iberdrola CSV not found')

# ══════════════════════════════════════════════════════════════
# 4. ENDESA
# ══════════════════════════════════════════════════════════════
print('\n[4/7] ENDESA ...')
endesa_dir = Path('data/ENDESA - e-distribucion')
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

    colormap = cm.LinearColormap(CMAP_RYG, vmin=0, vmax=1, caption='Capacity Utilisation')
    operators = df_en['grid_operator'].dropna().unique()

    # Folium
    m = folium.Map(location=[38.5,-2.0], zoom_start=6, tiles='OpenStreetMap')
    colormap.add_to(m)
    fg = {op: folium.FeatureGroup(name=f'ENDESA {op}').add_to(m) for op in operators}
    for _, r in df_en.iterrows():
        col = colormap(r['util']); name = r.get('substation_name','N/A')
        folium.CircleMarker([r['latitude'],r['longitude']],
            radius=max(3,min(11,r['capacity_occupied_mw']/15+3)),
            color=col, fill=True, fill_color=col, fill_opacity=0.75, weight=0.5,
            popup=folium.Popup(
                f"<b>{name}</b><br>Operator: {r['grid_operator']}<br>"
                f"Voltage: {r['voltage_kv']} kV<br>Available: {r['capacity_available_mw']:.2f} MW<br>"
                f"Occupied: {r['capacity_occupied_mw']:.2f} MW<br>Utilisation: {r['util_pct']:.1f}%",max_width=260),
            tooltip=f"{name} | {r['util_pct']:.0f}%").add_to(fg.get(r['grid_operator'],m))
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div('⚡ ENDESA e-distribución — Generation Capacity [Folium]',
                                          'R1-026: Aragón | R1-299: Andalucía | Colour = utilisation %'))
    save_folium(m, '04a_endesa_folium')

    # Plotly
    df_en['size_col'] = df_en['capacity_occupied_mw'].clip(upper=500).fillna(1)+2
    fig = px.scatter_mapbox(df_en, lat='latitude', lon='longitude',
        color='util_pct', size='size_col', hover_name='substation_name',
        hover_data={'autonomous_community':True,'voltage_kv':True,'capacity_available_mw':':.2f',
                    'capacity_occupied_mw':':.2f','util_pct':':.1f','grid_operator':True,
                    'latitude':False,'longitude':False,'size_col':False},
        color_continuous_scale='RdYlGn_r', range_color=[0,100], size_max=18,
        zoom=5, center=dict(lat=38.5,lon=-2.0), mapbox_style='open-street-map',
        title='ENDESA e-distribucion - Generation Node Capacity Utilisation (%) [Plotly / OSM]',
        labels={'util_pct':'Utilisation (%)','grid_operator':'Grid Operator'})
    fig.update_layout(height=650, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig, '04b_endesa_plotly')
else:
    print('  ⚠️  ENDESA CSV files not found')

# ══════════════════════════════════════════════════════════════
# 5. VIESGO
# ══════════════════════════════════════════════════════════════
print('\n[5/7] VIESGO ...')
viesgo_dir = Path('data/VIESGO')

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
    m = folium.Map(location=[43.2,-4.5], zoom_start=7, tiles='OpenStreetMap')
    colormap.add_to(m)
    fg_d = folium.FeatureGroup(name='⬇ Demand').add_to(m)
    fg_g = folium.FeatureGroup(name='⬆ Generation').add_to(m)
    for fg, df, tag in [(fg_d,df_vd,'DEMAND'),(fg_g,df_vg,'GENERATION')]:
        for _, r in df.dropna(subset=['latitude','longitude']).iterrows():
            col = colormap(r['util'])
            name = r.get('substation_name', r.get('substation_id','N/A'))
            folium.CircleMarker([r['latitude'],r['longitude']],
                radius=max(4,min(14,r['capacity_occupied_mw']/10+4)),
                color=col, fill=True, fill_color=col, fill_opacity=0.8, weight=0.5,
                popup=folium.Popup(
                    f"<b>{name}</b> [{tag}]<br>Province: {r['province']}<br>"
                    f"Voltage: {r['voltage_kv']} kV<br>Available: {r['capacity_available_mw']:.2f} MW<br>"
                    f"Occupied: {r['capacity_occupied_mw']:.2f} MW<br>Utilisation: {r['util_pct']:.1f}%",max_width=250),
                tooltip=f"{name} [{tag[0]}] | {r['util_pct']:.0f}%").add_to(fg)
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(title_div('🌐 VIESGO Distribution — Northern Spain [Folium]',
                                          '177 substations · Toggle: ⬇ Demand | ⬆ Generation · Colour = utilisation %'))
    save_folium(m, '05a_viesgo_folium')

    # Plotly
    df_vd2 = df_vd.dropna(subset=['latitude','longitude']).copy(); df_vd2['type']='Demand'
    df_vg2 = df_vg.dropna(subset=['latitude','longitude']).copy(); df_vg2['type']='Generation'
    for df in [df_vd2,df_vg2]:
        df['size_col'] = df['capacity_occupied_mw'].clip(upper=200).fillna(1)+3
        if 'substation_name' not in df.columns: df['substation_name'] = df.get('substation_id','N/A')
    cols = ['latitude','longitude','province','voltage_kv','capacity_available_mw',
            'capacity_occupied_mw','util_pct','size_col','type','substation_name']
    comb = pd.concat([df_vd2[[c for c in cols if c in df_vd2.columns]],
                      df_vg2[[c for c in cols if c in df_vg2.columns]]], ignore_index=True)
    fig = px.scatter_mapbox(comb, lat='latitude', lon='longitude',
        color='util_pct', size='size_col', hover_name='substation_name',
        hover_data={'province':True,'voltage_kv':True,'capacity_available_mw':':.2f',
                    'capacity_occupied_mw':':.2f','util_pct':':.1f','type':True,
                    'latitude':False,'longitude':False,'size_col':False},
        color_continuous_scale='RdYlGn_r', range_color=[0,100], size_max=20,
        zoom=6, center=dict(lat=43.2,lon=-4.5), mapbox_style='open-street-map',
        title='VIESGO Distribution - Demand & Generation Capacity - Northern Spain [Plotly / OSM]',
        labels={'util_pct':'Utilisation (%)','type':'Capacity Type'})
    fig.update_layout(height=650, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig, '05b_viesgo_plotly')
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

    # Folium
    m = folium.Map(location=[40.2,-3.5], zoom_start=6, tiles='OpenStreetMap')
    for _, r in prov_ev.iterrows():
        ratio = r['total_ev']/max_ev; bev_pct = 100*r['pure_bev']/max(r['total_ev'],1)
        folium.CircleMarker([r['lat'],r['lon']], radius=5+28*ratio,
            color='#08306b', weight=1, fill=True, fill_color='#4292c6', fill_opacity=0.75,
            popup=folium.Popup(
                f"<b>{r['name']}</b><br>Total EVs: {r['total_ev']:,}<br>"
                f"Pure BEV: {r['pure_bev']:,} ({bev_pct:.1f}%)<br>PHEV: {r['phev']:,}",max_width=230),
            tooltip=f"{r['name']} — {r['total_ev']:,} EVs").add_to(m)
    heat = [[r['lat'],r['lon'],r['total_ev']] for _,r in prov_ev.iterrows()]
    HeatMap(heat, radius=30, blur=25, min_opacity=0.3,
            gradient={'0.4':'blue','0.65':'lime','1':'red'}).add_to(m)
    m.get_root().html.add_child(title_div('🚗⚡ EV Registrations — Spain by Province (2025) [Folium]',
                                          'Circles = total EV count | Heat = density distribution'))
    save_folium(m, '06a_ev_registrations_folium')

    # Plotly — map
    prov_ev['size_col'] = prov_ev['total_ev']/max_ev*36+5
    prov_ev['bev_pct']  = 100*prov_ev['pure_bev']/prov_ev['total_ev'].clip(lower=1)
    fig1 = px.scatter_mapbox(prov_ev, lat='lat', lon='lon',
        color='total_ev', size='size_col', hover_name='name',
        hover_data={'total_ev':':,','pure_bev':':,','phev':':,','bev_pct':':.1f',
                    'lat':False,'lon':False,'size_col':False},
        color_continuous_scale='Blues', size_max=40,
        zoom=5, center=dict(lat=40.2,lon=-3.5), mapbox_style='open-street-map',
        title='EV Vehicle Registrations by Province — Spain 2025 [Plotly / OSM]',
        labels={'total_ev':'Total EVs','bev_pct':'BEV share (%)'})
    fig1.update_layout(height=650, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig1, '06b_ev_registrations_map_plotly')

    # Plotly — monthly trend
    df_ev['month_dt'] = pd.to_datetime(df_ev[['year','month']].assign(day=1))
    monthly = df_ev.groupby(['month_dt','propulsion_label']).size().reset_index(name='count')
    fig2 = px.area(monthly, x='month_dt', y='count', color='propulsion_label',
        title='Monthly EV Registrations Trend — Spain 2025 [Plotly]',
        labels={'count':'Registrations','month_dt':'Month','propulsion_label':'Type'},
        color_discrete_map={'Pure Electric':'#2171b5','PHEV Gasoline':'#fd8d3c',
                            'PHEV Diesel':'#e6550d','PHEV Other':'#a63603'})
    fig2.update_layout(height=400, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig2, '06c_ev_registrations_trend_plotly')
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
    m = folium.Map(location=[42.225,-8.720], zoom_start=13, tiles='OpenStreetMap')
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
    save_folium(m, '07a_vigo_charging_folium')

    # Plotly
    fig = px.scatter_mapbox(gdf, lat='latitude', lon='longitude', hover_name='nombre',
        hover_data={'calle':True,'barrio':True,'codigo_postal':True,'telefono':True,
                    'web':True,'latitude':False,'longitude':False},
        color_discrete_sequence=['#2ca25f'], zoom=13, center=dict(lat=42.225,lon=-8.720),
        mapbox_style='open-street-map',
        title='Vigo EV Charging Points — Municipal Open Data [Plotly / OSM]')
    fig.update_traces(marker=dict(size=15, opacity=0.9))
    fig.update_layout(height=600, margin=dict(l=0,r=0,t=50,b=0))
    save_plotly(fig, '07b_vigo_charging_plotly')
except Exception as e:
    print(f'  ⚠️  Vigo skipped: {e}')

# ══════════════════════════════════════════════════════════════
print(f'\n{"="*60}')
print(f'Done! All files saved to: {OUT.resolve()}')
files = sorted(OUT.glob('*.html'))
print(f'{len(files)} HTML files:')
for f in files:
    print(f'  {f.name}')
