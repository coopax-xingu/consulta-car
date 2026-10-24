import streamlit as st,folium,pandas as pd,re
from streamlit_folium import st_folium
import analise as A
st.set_page_config(page_title='Rede COOPAX – Consulta Socioambiental do CAR',page_icon='🌳',layout='wide')
import base64,os
_logo=base64.b64encode(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_c.png'),'rb').read()).decode()
st.markdown(f"""<style>
:root{{--g:#1f5a2b;--gd:#173a1e;--gl:#e8f0e2;--t:#8a5a2b;--tl:#f5ede2;--ink:#2b2a25}}
html,body,[class*="css"]{{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.block-container{{padding-top:1rem;max-width:1140px}}
.cx-top{{background:#fff;border-bottom:4px solid var(--t);display:flex;align-items:center;gap:10px;padding:10px 4px;margin-bottom:12px}}
.cx-top img{{height:48px}}.cx-top b{{color:var(--gd);font-size:20px}}.cx-top small{{display:block;font-size:12px;color:var(--t)}}
.cx-lead{{background:var(--tl);border-left:4px solid var(--t);padding:10px 14px;border-radius:6px;font-size:15px}}
h2,h3{{color:var(--gd)!important}}
.stDownloadButton button{{background:var(--t)!important;color:#fff!important;border:0!important}}
</style>
<div class="cx-top"><img src="data:image/png;base64,{_logo}"><span><b>Rede COOPAX – Consulta Socioambiental do CAR</b><small>Cooperativas de Produção Agroecológica</small></span></div>
<div class="cx-lead"><b>Triagem inicial</b> do CAR antes de fechar com o cliente. Cruza o imóvel com PRODES (INPE), Floresta Pública Tipo B (SFB), embargos IBAMA/IMAC, Unidades de Conservação, Terras Indígenas, Assentamentos e Quilombolas (INCRA) e parcelas SIGEF/SNCI. <i>Indicativo – não substitui a análise socioambiental do banco (BASA).</i></div>""",unsafe_allow_html=True)
t1,t2=st.tabs(['📋 Códigos do CAR','📁 Enviar arquivo'])
with t1: codes=st.text_area('Cole um ou mais códigos do CAR (com ou sem pontos), um por linha',height=120,placeholder='AC-1200203-DA98.CA29.FB26.4AB5.9AE1.226F.40EF.AFEF')
with t2: ups=st.file_uploader('KML, KMZ, SHP (zip) ou GeoJSON',type=['kml','kmz','zip','geojson','json'],accept_multiple_files=True)
if st.button('🔎 Consultar',type='primary',use_container_width=True):
    gs,errs=[],[]
    with st.spinner('Buscando polígonos e cruzando bases...'):
        for c in [x for x in re.split(r'[\s,;]+',codes or '') if x]:
            try: gs.append(A.fetch_car(c))
            except Exception as e: errs.append(str(e))
        for f in ups or []:
            try: gs.append(A.read_upload(f.name,f.getvalue()))
            except Exception as e: errs.append(f'{f.name}: {e}')
        st.session_state.res=[x for g in gs for x in A.analyze(g)];st.session_state.errs=errs
for e in st.session_state.get('errs',[]): st.error(e)
res=st.session_state.get('res')
if res:
    st.download_button('⬇️ Baixar planilha (xlsx) de todos',A.to_xlsx(res),'consulta_car_coopax.xlsx',use_container_width=True)
    CORES={2008:'#fff176',2012:'#ffb74d',2016:'#ff7043',2020:'#e53935',2023:'#880e4f'}
    def cor_ano(y): return [c for a,c in CORES.items() if y>=a][-1] if y else '#e53935'
    for i,(r,lay,det) in enumerate(res):
        st.markdown('---');st.subheader(r['Imóvel'])
        p=r.get('Parecer','');(st.error if '🔴' in p else st.warning if '🟡' in p else st.success)(p)
        if not lay: continue
        c=lay['CAR'].geometry.iloc[0].centroid
        m=folium.Map(location=[c.y,c.x],zoom_start=14,tiles=None)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',attr='Esri',name='Satélite').add_to(m)
        def add(k,nome,style,tip=None):
            g=lay.get(k)
            if g is None or g.empty: return
            g=g[[x for x in (tip or []) if x in g.columns]+['geometry']].copy()
            for x in g.columns:
                if x!='geometry': g[x]=g[x].astype(str)
            folium.GeoJson(g.to_json(),name=nome,style_function=style,tooltip=folium.GeoJsonTooltip(fields=[x for x in g.columns if x!='geometry']) if len(g.columns)>1 else None).add_to(m)
        add('acum2007','Desmate até 2007',lambda f:{'color':'#9e9e9e','fillOpacity':.35,'weight':.5})
        add('fpb','Floresta Pública B',lambda f:{'color':'#2e7d32','fillOpacity':.35,'weight':1},['nome','orgao'])
        add('uc','Unid. Conservação',lambda f:{'color':'#00bcd4','fillOpacity':.25,'weight':1},['nome','categoria'])
        add('ti','Terra Indígena',lambda f:{'color':'#ff9800','fillOpacity':.25,'weight':1},['terrai_nom'])
        add('pa','Assentamento INCRA',lambda f:{'color':'#fdd835','fillOpacity':.15,'weight':2,'dashArray':'5'},['nome_proje','cd_sipra'])
        add('quil','Território Quilombola',lambda f:{'color':'#795548','fillOpacity':.35,'weight':2},['nm_comunid'])
        add('cert','Parcelas SIGEF/SNCI',lambda f:{'color':'#3949ab','fill':False,'weight':1},['fonte','nome_area','nome_imove'])
        add('prodes','PRODES (por ano)',lambda f:{'color':cor_ano(int(float(f['properties']['year']))),'fillColor':cor_ano(int(float(f['properties']['year']))),'fillOpacity':.55,'weight':.5},['year'])
        add('emb_ibama','Embargo IBAMA',lambda f:{'color':'#6a1b9a','fillOpacity':.5,'weight':2},['num_tad','nome_embargado'])
        add('emb_est','Embargo estadual',lambda f:{'color':'#ff00ff','fillOpacity':.5,'weight':2},['NUM_AI','AUTUADO'])
        add('CAR','Imóvel (CAR)',lambda f:{'color':'yellow','fill':False,'weight':3})
        m.fit_bounds([[b[1],b[0]],[b[3],b[2]]] if (b:=lay['CAR'].total_bounds) is not None else None)
        folium.LayerControl(collapsed=True).add_to(m)
        leg="<div style='position:fixed;bottom:20px;left:10px;z-index:9999;background:white;padding:6px;font-size:11px;border-radius:4px'>PRODES: "+' '.join(f"<span style='background:{c}'>&nbsp;&nbsp;&nbsp;</span> {a}+" for a,c in CORES.items())+"</div>"
        m.get_root().html.add_child(folium.Element(leg))
        st_folium(m,height=430,use_container_width=True,key=f'map{i}',returned_objects=[])
        cols=st.columns(4)
        cols[0].metric('Área (ha)',r['Área (ha)']);cols[1].metric('PRODES pós-2008 (ha)',r['PRODES pós-22/07/2008 (ha)']);cols[2].metric('PRODES pós-2019 (ha)',r['PRODES pós-2019 (ha)']);cols[3].metric('Desmate até 2007 (ha)',r['Desmate até 2007 (ha)'])
        st.dataframe(pd.DataFrame([(k,str(v)) for k,v in r.items()],columns=['Item','Resultado']),hide_index=True,use_container_width=True)
        st.download_button('📄 Baixar laudo (PDF)',A.laudo_pdf(r,lay),f"laudo_{re.sub(r'\W','_',r['Imóvel'])[:40]}.pdf",key=f'pdf{i}',use_container_width=True)
st.caption('Fontes: INPE/PRODES 2008–2025 · SFB CNFP 2025 · IBAMA embargos (atualização diária) · IMAC-AC 2023–2026 · TerraBrasilis UC/TI · INCRA acervo fundiário (PA, quilombolas, SIGEF/SNCI) · SICAR WFS. Indicativo; não substitui análise oficial.')
