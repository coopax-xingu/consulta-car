import geopandas as g,pandas as pd,glob,os
def rd(pat):
    f=sorted(glob.glob(f'incra/{pat}/*.shp'))[0];d=g.read_file(f,encoding='latin1') if True else None
    if d.crs is None: d.set_crs(4674,inplace=True)
    d=d.to_crs(4674);d['geometry']=d.geometry.make_valid()
    for c in d.columns:
        if c!='geometry' and not pd.api.types.is_numeric_dtype(d[c]): d[c]=d[c].astype(str)
    return d
q=rd('quilombolas')
for uf in ['AC','RO']:
    u=uf.lower();lim=g.read_file(f'{u}_limite.gpkg').union_all()
    a=rd(f'Assentamento_Brasil_{uf}');a.to_file(f'incra_assentamentos_{u}.gpkg');print('PA',uf,len(a),list(a.columns))
    s=pd.concat([rd(f'Sigef_Brasil_{uf}').assign(fonte='SIGEF'),rd(f'snci_{uf}').assign(fonte='SNCI')],ignore_index=True)
    g.GeoDataFrame(s,crs=4674).to_file(f'incra_certificados_{u}.gpkg');print('cert',uf,len(s),list(s.columns))
    qq=q[q.intersects(lim)];qq.to_file(f'incra_quilombolas_{u}.gpkg');print('quil',uf,len(qq),list(q.columns))
