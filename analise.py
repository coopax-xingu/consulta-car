"""Núcleo de análise – Rede COOPAX. Reaproveita bases de /workspace/geo_bases (ou env GEO_BASES)."""
import os,io,re,zipfile,tempfile,requests,warnings
import geopandas as gpd,pandas as pd
warnings.filterwarnings('ignore')
BASE=os.environ.get('GEO_BASES',os.path.join(os.path.dirname(os.path.abspath(__file__)),'data'))
UFS={'11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO','21':'MA','51':'MT'}
SICAR='https://geoserver.car.gov.br/geoserver/sicar/wfs'
import ssl
from requests.adapters import HTTPAdapter
SICAR_MSG='O servidor do SICAR não respondeu. Tente de novo ou envie o KML do imóvel na aba Enviar arquivo.'
class _LegacyTLS(HTTPAdapter):
    # SICAR só aceita TLS1.2 com cifras RSA antigas (ex.: AES256-GCM-SHA384)
    def __init__(self,verify=True,**k): self._v=verify;super().__init__(**k)
    def _ctx(self):
        ctx=ssl.create_default_context()
        try: ctx.set_ciphers('DEFAULT:AES256-GCM-SHA384:AES128-GCM-SHA256:AES256-SHA:AES128-SHA:@SECLEVEL=0')
        except ssl.SSLError: ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        ctx.options|=getattr(ssl,'OP_LEGACY_SERVER_CONNECT',0x4)
        ctx.maximum_version=ssl.TLSVersion.TLSv1_2
        if not self._v: ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
        return ctx
    def init_poolmanager(self,*a,**k): k['ssl_context']=self._ctx();return super().init_poolmanager(*a,**k)
def _sicar_get(params):
    last=None
    for v in (True,False):
        s=requests.Session();s.mount('https://geoserver.car.gov.br',_LegacyTLS(verify=v))
        for _ in range(2):
            try:
                r=s.get(SICAR,params=params,timeout=90,verify=v);r.raise_for_status();return r
            except Exception as e: last=e
    raise RuntimeError(f'{SICAR_MSG} (detalhe: {type(last).__name__})')
def norm_code(c):
    c=c.strip().upper().replace('.','').replace(' ','')
    m=re.match(r'^([A-Z]{2})-(\d{7})-([0-9A-F]{32})$',c);return c if m else None
def fetch_car(code):
    c=norm_code(code)
    if not c: raise ValueError(f'Código inválido: {code}')
    uf=c[:2].lower()
    r=_sicar_get(dict(service='WFS',version='2.0.0',request='GetFeature',typeNames=f'sicar:sicar_imoveis_{uf}',outputFormat='application/json',CQL_FILTER=f"cod_imovel='{c}'"));g=gpd.read_file(io.BytesIO(r.content))
    if g.empty: raise ValueError(f'Não encontrado no SICAR: {code}')
    g=g.set_crs(4674,allow_override=True) if g.crs is None else g.to_crs(4674)
    g['imovel']=c;g['uf']=c[:2]
    return g
def read_upload(name,data):
    d=tempfile.mkdtemp();p=os.path.join(d,name);open(p,'wb').write(data)
    if name.lower().endswith(('.kmz','.zip')):
        zipfile.ZipFile(p).extractall(d)
        c=[os.path.join(r,f) for r,_,fs in os.walk(d) for f in fs if f.lower().endswith(('.kml','.shp','.geojson','.json'))]
        p=c[0]
    g=gpd.read_file(p);g=g[g.geom_type.isin(['Polygon','MultiPolygon'])].copy()
    if g.crs is None: g.set_crs(4326,inplace=True)
    g=g.to_crs(4674)
    nc=next((c for c in ['nome','Name','name','cod_imovel','NOME'] if c in g.columns and g[c].notna().all()),None)
    g['imovel']=g[nc].astype(str) if nc else [f'{name} #{i+1}' for i in range(len(g))]
    return g
def uf_of(geom):
    best=None
    for f in os.listdir(BASE):
        m=re.match(r'^([a-z]{2})_limite\.gpkg$',f)
        if m and gpd.read_file(os.path.join(BASE,f)).intersects(geom).any(): best=m.group(1).upper()
    return best
def layer_paths(uf):
    u=uf.lower();L={'prodes':f'prodes_{u}_yearly.gpkg','acum2007':f'prodes_{u}_acum2007.gpkg','fpb':f'cnfp2025_{u}_tipoB.gpkg',
      'emb_ibama':f'embargos_ibama_{u}.gpkg','emb_est':{'ac':'embargos_imac_ac.gpkg'}.get(u),'uc':f'ucs_{u}_terrabrasilis.gpkg','ti':f'tis_{u}_terrabrasilis.gpkg','pa':f'incra_assentamentos_{u}.gpkg','quil':f'incra_quilombolas_{u}.gpkg','cert':f'incra_certificados_{u}.gpkg'}
    return {k:os.path.join(BASE,v) for k,v in L.items() if v and os.path.exists(os.path.join(BASE,v))}
def _ov(P,L,ea):
    if L is None or L.empty: return L.iloc[0:0] if L is not None else gpd.GeoDataFrame()
    c=L[L.intersects(P)].copy()
    if c.empty: return c
    c['geometry']=c.geometry.intersection(P);c['ha']=c.to_crs(ea).area/1e4
    return c[c.ha>0.0001]
def _dt(v):
    try: return pd.to_datetime(float(v),unit='ms').date().isoformat()
    except Exception: return str(v)[:10]
ESF=('Federal','Estadual','Municipal')
def pct(h,area): return round(100*h/area,2) if area else 0.0
def analyze_one(row,uf):
    P=row.geometry.buffer(0);ea=gpd.GeoSeries([P],crs=4674).estimate_utm_crs()
    Pe=gpd.GeoSeries([P],crs=4674).to_crs(ea).iloc[0];area=Pe.area/1e4
    win=gpd.GeoSeries([P],crs=4674).to_crs(ea).buffer(5000).to_crs(4674);bb=tuple(win.total_bounds);W=win.iloc[0]
    big=gpd.GeoSeries([P],crs=4674).to_crs(ea).buffer(60000).to_crs(4674).total_bounds
    D={}
    for k,p in layer_paths(uf).items():
        g=gpd.read_file(p,bbox=tuple(big) if k in('uc','ti','emb_ibama','emb_est','pa','quil') else bb).to_crs(4674)
        if k!='emb_ibama': g['geometry']=g.geometry.buffer(0)
        D[k]=g
    pr=_ov(P,D.get('prodes'),ea);ac=_ov(P,D.get('acum2007'),ea);fb=_ov(P,D.get('fpb'),ea)
    ei=_ov(P,D.get('emb_ibama'),ea);ee=_ov(P,D.get('emb_est'),ea);uc=_ov(P,D.get('uc'),ea);ti=_ov(P,D.get('ti'),ea);pa=_ov(P,D.get('pa'),ea);qu=_ov(P,D.get('quil'),ea);ce=_ov(P,D.get('cert'),ea)
    if len(ce):
        nm=ce.apply(lambda x:str(x.nome_area if x.fonte=='SIGEF' else x.nome_imove).upper(),axis=1)
        pub=nm.str.contains(r'GLEBA|PER[IÍ]METRO|^PA |^PDS |^PAE |PROJETO|ASSENTAMENTO|RESERVA',regex=True)
        gl=ce[pub];ce=ce[~pub]
    else: gl=ce
    def near(k,campo):
        L=D.get(k)
        if L is None or L.empty: return '> 60 km'
        d=L.to_crs(ea).distance(Pe)/1000;i=d.idxmin();return f"{L.loc[i,campo]} ({d[i]:.1f} km)"
    s=lambda d:round(float(d.ha.sum()),2) if len(d) else 0.0
    anos=pr.groupby('year').ha.sum().round(2).to_dict() if len(pr) else {}
    r={'Imóvel':row.imovel,'UF':uf,'Status SICAR':(f"{'Ativo' if row.get('status_imovel')=='AT' else row.get('status_imovel')} / {row.get('condicao')}" if 'condicao' in row and pd.notna(row.get('condicao')) else 'arquivo enviado'),
       'Município':row.get('municipio',''),'Área (ha)':round(area,2),'Desmate até 2007 (ha)':s(ac),
       'PRODES pós-22/07/2008 (ha)':round(sum(v for y,v in anos.items() if y>=2009),2),'PRODES pós-2019 (ha)':round(sum(v for y,v in anos.items() if y>=2020),2),
       'PRODES por ano':'; '.join(f'{int(y)}: {v:.2f}' for y,v in sorted(anos.items())) or '—',
       'Floresta Pública B (ha)':s(fb),'Floresta Pública B':'; '.join(fb.nome.astype(str).unique()) if len(fb) else '—',
       'Embargo IBAMA (ha)':s(ei),'Embargo IBAMA':'; '.join(f"TEI {t}-{se} AI {a} ({_dt(d)}) {n} – {h:.4f} ha" for t,se,a,d,n,h in ei[['num_tad','serie_tad','num_auto_infracao','dat_embargo','nome_embargado','ha']].values) if len(ei) else '—',
       'Embargo IBAMA mais próximo':near('emb_ibama','num_tad'),
       'Embargo estadual (ha)':s(ee),'Embargo estadual':'; '.join(f"AI {a} ({d}) {n} – {h:.2f} ha" for a,d,n,h in ee[['NUM_AI','DT_EMB','AUTUADO','ha']].values) if len(ee) else ('—' if 'emb_est' in D else 'base estadual indisponível'),
       'Embargo estadual mais próximo':near('emb_est','NUM_AI') if 'emb_est' in D else 'n/d',
       'UC (ha)':s(uc),'UC':'; '.join(uc.nome.unique()) if len(uc) else '—','UC mais próxima':near('uc','nome'),
       **{f'UC {e} (ha)':s(uc[uc.esfera.astype(str).str.lower()==e.lower()]) if len(uc) and 'esfera' in uc else 0.0 for e in ESF},
       **{f'UC {e}':('; '.join(f"{x.nome} ({x.categoria}) – {x.ha:.2f} ha" for x in uc[uc.esfera.astype(str).str.lower()==e.lower()].itertuples()) or '—') if len(uc) and 'esfera' in uc else '—' for e in ESF},
       'TI (ha)':s(ti),'TI':'; '.join(ti.terrai_nom.unique()) if len(ti) else '—','TI mais próxima':near('ti','terrai_nom'),
       'Assentamento INCRA (ha)':s(pa),'Assentamento INCRA':'; '.join(f"{n} (SIPRA {c}, {fa})" for n,c,fa in pa[['nome_proje','cd_sipra','fase']].drop_duplicates().values) if len(pa) else '—','Assentamento mais próximo':near('pa','nome_proje'),
       'Quilombola (ha)':s(qu),'Território Quilombola':'; '.join(qu.nm_comunid.unique()) if len(qu) else '—','Quilombola mais próximo':near('quil','nm_comunid'),
       'Gleba pública/perímetro de PA certificado':'; '.join(f"{x.fonte} {(x.nome_area if x.fonte=='SIGEF' else x.nome_imove)} {x.ha:.2f} ha" for x in gl.itertuples()) if len(gl) else '—',
       'Parcelas certificadas SIGEF/SNCI sobrepostas (ha)':s(ce),'Parcelas certificadas':'; '.join(f"{x.fonte} {(x.nome_area if x.fonte=='SIGEF' else x.nome_imove)} [{x.parcela_co if x.fonte=='SIGEF' else x.num_certif}] {x.ha:.2f} ha" for x in ce.sort_values('ha',ascending=False).head(10).itertuples()) if len(ce) else '—'}
    r['Floresta Pública B (%)']=pct(r['Floresta Pública B (ha)'],area);r['Embargo IBAMA (%)']=pct(r['Embargo IBAMA (ha)'],area);r['UC (%)']=pct(r['UC (ha)'],area)
    for e in ESF: r[f'UC {e} (%)']=pct(r[f'UC {e} (ha)'],area)
    r['Floresta Pública B']='; '.join(f"{x.nome} ({x.orgao}, {x.categoria}) – {x.ha:.2f} ha" for x in fb.itertuples()) if len(fb) else '—'
    imp,att=[],[]
    if r['Embargo IBAMA (ha)']>=0.05 or r['Embargo estadual (ha)']>=0.05: imp.append('sobreposição com área embargada')
    elif r['Embargo IBAMA']!='—' or str(r['Embargo estadual']).startswith('AI'): att.append('embargo encostando na divisa (verificar titular)')
    if r['UC (ha)']>0.05: imp.append('sobreposição com UC')
    if r['TI (ha)']>0.05: imp.append('sobreposição com Terra Indígena')
    if r['Quilombola (ha)']>0.05: imp.append('sobreposição com Território Quilombola')
    if r['Assentamento INCRA (ha)']>0.05: att.append('imóvel em PA do INCRA, verificar beneficiário/CCU')
    if r['Parcelas certificadas SIGEF/SNCI sobrepostas (ha)']>0.5: att.append('sobreposição com parcela certificada de terceiros (SIGEF/SNCI) – conferir titularidade')
    if r['Gleba pública/perímetro de PA certificado']!='—' and r['Assentamento INCRA (ha)']<=0.05: att.append('imóvel dentro de gleba pública certificada – verificar titulação/regularização fundiária')
    if r['Floresta Pública B (ha)']>0.05: imp.append('sobreposição com Floresta Pública Tipo B')
    if r['PRODES pós-2019 (ha)']>=1: imp.append(f"desmatamento PRODES pós-2019 ({r['PRODES pós-2019 (ha)']} ha)")
    elif r['PRODES pós-22/07/2008 (ha)']>0: att.append(f"desmatamento PRODES pós-2008 ({r['PRODES pós-22/07/2008 (ha)']} ha)")
    if imp: v='🔴 Impedimento provável para crédito: '+'; '.join(imp+att)
    elif att: v='🟡 Atenção: '+'; '.join(att)
    else: v='🟢 Sem restrição nas bases consultadas'
    r['Parecer']=v+' (triagem inicial indicativa – não substitui a análise socioambiental do banco/BASA nem do órgão ambiental; PRODES ≥ ~6 ha, ano PRODES = ago–jul).'
    lay={'CAR':gpd.GeoDataFrame(geometry=[P],crs=4674)}
    for k in D: lay[k]=D[k][D[k].intersects(W)] if k not in('uc','ti','pa','quil') else D[k][D[k].intersects(gpd.GeoSeries([W],crs=4674).iloc[0].buffer(0.05))]
    return r,lay,{'PRODES':pr,'Floresta B':fb,'Embargo IBAMA':ei,'Embargo estadual':ee,'UC':uc,'TI':ti,'Assentamento':pa,'Quilombola':qu,'Certificadas (terceiros)':ce,'Gleba/PA certificado':gl}
def analyze(g):
    out=[]
    for _,row in g.iterrows():
        uf=row.get('uf') if isinstance(row.get('uf'),str) and len(row.get('uf'))==2 else uf_of(row.geometry)
        if not uf or not layer_paths(uf): out.append(({'Imóvel':row.imovel,'Parecer':f'UF {uf} sem bases carregadas'},None,None));continue
        out.append(analyze_one(row,uf))
    return out
def to_xlsx(results):
    b=io.BytesIO();rows=[r for r,_,_ in results];det=[]
    for r,_,d in results:
        for k,v in (d or {}).items():
            if v is not None and len(v):
                for _,x in v.drop(columns='geometry',errors='ignore').iterrows(): det.append({'Imóvel':r['Imóvel'],'Camada':k,**{c:str(y) for c,y in x.items()}})
    with pd.ExcelWriter(b) as w:
        pd.DataFrame(rows).to_excel(w,sheet_name='Resumo',index=False);pd.DataFrame(det).to_excel(w,sheet_name='Detalhe',index=False)
        pd.DataFrame({'Fonte':['PRODES/INPE TerraBrasilis (2008–2025)','CNFP 2025 – SFB (Tipo B)','Embargos IBAMA (pamgia, diário)','Embargos IMAC-AC 2023–2026','UC e TI – TerraBrasilis','INCRA acervo fundiário (certificacao.incra.gov.br/csv_shp): Assentamentos, Quilombolas, SIGEF, SNCI','Polígonos – SICAR WFS público']}).to_excel(w,sheet_name='Fontes',index=False)
    return b.getvalue()
def laudo_pdf(r,lay):
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt;from matplotlib.backends.backend_pdf import PdfPages;import textwrap
    b=io.BytesIO()
    with PdfPages(b) as pdf:
        fig=plt.figure(figsize=(8.27,11.69));fig.text(.06,.96,'Rede COOPAX – Consulta Socioambiental do CAR',fontsize=15,weight='bold',color='#1b5e20')
        fig.text(.06,.935,f"Laudo indicativo – {pd.Timestamp.now(tz='America/Boa_Vista'):%d/%m/%Y %H:%M} (horário de Boa Vista)",fontsize=9)
        ax=fig.add_axes([.06,.52,.88,.4]);cor={'acum2007':'#9e9e9e','fpb':'#2e7d32','uc':'#00bcd4','ti':'#ff9800','prodes':'#e53935','emb_ibama':'#6a1b9a','emb_est':'#ff00ff','pa':'#fdd835','quil':'#795548','cert':'#3949ab'}
        if lay:
            for k,c in cor.items():
                if k in lay and len(lay[k]): lay[k].to_crs(3857).plot(ax=ax,color=c,alpha=.45)
            g=lay['CAR'].to_crs(3857);g.boundary.plot(ax=ax,color='yellow',lw=2);x0,y0,x1,y1=g.buffer(max(400,(r['Área (ha)']*1e4)**.5*.6)).total_bounds;ax.set_xlim(x0,x1);ax.set_ylim(y0,y1)
            try:
                import contextily as cx;cx.add_basemap(ax,source=cx.providers.Esri.WorldImagery,attribution_size=4)
            except Exception: pass
        ax.set_axis_off()
        y=.49
        for k,v in r.items():
            for i,l in enumerate(textwrap.wrap(f"{k}: {v}",105) or ['']):
                fig.text(.06,y,l,fontsize=8,weight='bold' if k=='Parecer' else 'normal',color='#b71c1c' if k=='Parecer' else 'black');y-=.016
        pdf.savefig(fig);plt.close(fig)
    return b.getvalue()
