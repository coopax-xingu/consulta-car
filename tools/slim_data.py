# Gera ./data (versão enxuta) a partir de GEO_BASES completo (/workspace/geo_bases). Uso: python tools/slim_data.py
import geopandas as g,os,sys
B=os.environ.get('GEO_BASES','/workspace/geo_bases');O=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data/')
keep={'prodes':['year'],'acum2007':[],'fpb':['nome','orgao','categoria'],'emb_ibama':['num_tad','serie_tad','num_auto_infracao','dat_embargo','nome_embargado'],
'emb_est':['NUM_AI','DT_EMB','AUTUADO'],'uc':['nome','categoria','esfera'],'ti':['terrai_nom','fase_ti'],'pa':['nome_proje','cd_sipra','fase'],'quil':['nm_comunid'],
'cert':['fonte','nome_area','nome_imove','parcela_co','num_certif'],'lim':['sigla']}
for u in ['ac','ro']:
    L={'prodes':f'prodes_{u}_yearly','acum2007':f'prodes_{u}_acum2007','fpb':f'cnfp2025_{u}_tipoB','emb_ibama':f'embargos_ibama_{u}','emb_est':{'ac':'embargos_imac_ac'}.get(u),
       'uc':f'ucs_{u}_terrabrasilis','ti':f'tis_{u}_terrabrasilis','pa':f'incra_assentamentos_{u}','quil':f'incra_quilombolas_{u}','cert':f'incra_certificados_{u}','lim':f'{u}_limite'}
    for k,f in L.items():
        if not f: continue
        d=g.read_file(f'{B}/{f}.gpkg');d=d[[c for c in keep[k] if c in d.columns]+['geometry']];d=d[d.geometry.notna()&~d.geometry.is_empty]
        if k in('prodes','acum2007'): d['geometry']=d.geometry.simplify(0.00002,preserve_topology=True)
        d.to_file(O+f+'.gpkg',driver='GPKG',SPATIAL_INDEX='YES');print(f,len(d))
