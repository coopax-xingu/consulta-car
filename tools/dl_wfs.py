import sys,requests,geopandas as gpd,pandas as pd,io
base,layer,cql,out=sys.argv[1:5]
frames=[];start=0;N=20000
while True:
    p=dict(service='WFS',version='2.0.0',request='GetFeature',typeNames=layer,outputFormat='application/json',count=N,startIndex=start)
    if len(sys.argv)>5: p['sortBy']=sys.argv[5]
    if cql!='-': p['CQL_FILTER']=cql
    for t in range(4):
        try:
            r=requests.get(base,params=p,timeout=600);r.raise_for_status();g=gpd.read_file(io.BytesIO(r.content));break
        except Exception as e: print('retry',e,flush=True)
    else: sys.exit(1)
    print(layer,start,len(g),flush=True)
    if len(g)==0:break
    frames.append(g);start+=N
    if len(g)<N:break
g=pd.concat(frames,ignore_index=True)
g=gpd.GeoDataFrame(g,geometry='geometry',crs=frames[0].crs)
for c in g.columns:
    if c!='geometry' and not pd.api.types.is_numeric_dtype(g[c]): g[c]=g[c].astype(str)
g.to_file(out,driver='GPKG');print('DONE',out,len(g),g.crs)
