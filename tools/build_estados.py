"""Gera data/ enxuto para AM, MT (novos) e UCs CNUC para RO/AC/AM/MT. Uso: GEO_NEW=/workspace/geo_bases_new python tools/build_estados.py [AM MT ...]
Fontes: ver README. Tudo EPSG:4674."""
import geopandas as g,pandas as pd,os,sys,re
N=os.environ.get('GEO_NEW','/workspace/geo_bases_new');OLD=os.environ.get('GEO_BASES','/workspace/geo_bases')
O=os.environ.get('OUT','/workspace/consulta_car_hf/data')+'/'
TOL=0.00005
def clean(d):
    d=d[d.geometry.notna()&~d.geometry.is_empty].copy();d['geometry']=d.geometry.make_valid();return d
def save(d,name):
    d.to_file(O+name+'.gpkg',driver='GPKG',SPATIAL_INDEX='YES');print(name,len(d),round(os.path.getsize(O+name+'.gpkg')/1e6,1),'MB',flush=True)
def fix(s):
    if not isinstance(s,str): return s
    try: return s.encode('latin1').decode('utf-8')
    except Exception: return s
def lim(u):
    u=u.lower();p=f'{N}/{u}_limite_tb.gpkg' if os.path.exists(f'{N}/{u}_limite_tb.gpkg') else f'{OLD}/{u}_limite.gpkg'
    return g.read_file(p).to_crs(4674)
cn=g.read_file(f'{N}/cnuc/cnuc_2025_08.shp',encoding='latin1')
for c in ['nome_uc','categoria','esfera','grupo','situacao','uf']: cn[c]=cn[c].map(fix)
cn=clean(cn).to_crs(4674)
ti=g.read_file(f'{OLD}/_indigenous_area_legal_amazon.gpkg').to_crs(4674)
qb=g.read_file(f'{OLD}/incra/quilombolas/dados.shp',encoding='latin1');qb=qb.set_crs(4674,allow_override=True) if qb.crs is None else qb.to_crs(4674)
for u in (sys.argv[1:] or ['AM','MT']):
    l=u.lower();L=lim(u);LG=L.union_all()
    if u in('RO','AC','AM','MT'):
        c=cn[cn.intersects(LG)].copy()
        c=c[c.geometry.intersection(LG).area>0]
        c=c.rename(columns={'nome_uc':'nome'});c['esfera']=c.esfera.str.lower()
        save(c[['nome','categoria','esfera','geometry']],f'ucs_{l}_cnuc')
    if u not in('AM','MT'): continue
    save(L[['sigla','geometry']],f'{l}_limite')
    t=clean(ti[ti.intersects(LG)])[['terrai_nom','fase_ti','geometry']];save(t,f'tis_{l}_terrabrasilis')
    q=clean(qb[qb.intersects(LG)])[['nm_comunid','geometry']]
    if len(q): save(q,f'incra_quilombolas_{l}')
    f=g.read_file(f'{N}/cnfp2025_{l}_todas.gpkg');f=clean(f[f.tipo=='TIPO B'])[['nome','orgao','categoria','geometry']];f['geometry']=f.geometry.simplify(TOL,preserve_topology=True);save(f,f'cnfp2025_{l}_tipoB')
    e=clean(g.read_file(f'{N}/embargos_ibama_{l}.gpkg'))[['num_tad','serie_tad','num_auto_infracao','dat_embargo','nome_embargado','geometry']];save(e,f'embargos_ibama_{l}')
    a=clean(g.read_file(f'{N}/prodes_{l}_acum2007.gpkg'))[['geometry']];a['geometry']=a.geometry.simplify(TOL,preserve_topology=True);save(clean(a),f'prodes_{l}_acum2007')
    def prod(src,name,tol=TOL):
        y=g.read_file(src)[['year','geometry']];y=y[y.year>=2008];y=clean(y)
        y['geometry']=y.geometry.simplify(tol,preserve_topology=True);save(clean(y),name)
    prod(f'{N}/prodes_{l}_yearly.gpkg',f'prodes_{l}_yearly')
    if u=='MT':  # fora do bioma Amazônia: PRODES Cerrado e Pantanal (arquivos separados < 100 MB p/ GitHub)
        prod(f'{N}/prodes_mt_cerrado.gpkg','prodes_mt_yearly_cerrado',0.0001)
        prod(f'{N}/prodes_mt_pantanal.gpkg','prodes_mt_yearly_pantanal',0.0001)
