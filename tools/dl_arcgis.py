import sys,requests,geopandas as gpd,pandas as pd,io
url,where,out=sys.argv[1:4]; step=int(sys.argv[4]) if len(sys.argv)>4 else 1000
ids=requests.get(url+'/query',params=dict(where=where,returnIdsOnly='true',f='json'),timeout=300).json()['objectIds'];ids.sort()
print('ids',len(ids),flush=True);fr=[]
for i in range(0,len(ids),step):
    ch=ids[i:i+step]
    for t in range(5):
        try:
            r=requests.post(url+'/query',data=dict(objectIds=','.join(map(str,ch)),outFields='*',outSR=4674,f='geojson'),timeout=600);r.raise_for_status()
            g=gpd.read_file(io.BytesIO(r.content));break
        except Exception as e: print('retry',e,flush=True)
    else: sys.exit(1)
    fr.append(g);print(i,len(g),flush=True)
g=gpd.GeoDataFrame(pd.concat(fr,ignore_index=True),geometry='geometry',crs='EPSG:4674')
for c in g.columns:
    if c!='geometry' and not pd.api.types.is_numeric_dtype(g[c]): g[c]=g[c].astype(str)
g.to_file(out,driver='GPKG');print('DONE',out,len(g))
