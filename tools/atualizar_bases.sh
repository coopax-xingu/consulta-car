#!/bin/bash
# Atualiza bases em $GEO_BASES (padrão /workspace/geo_bases). Uso: ./atualizar_bases.sh [ibama|prodes|imac|tudo]
# Sugestão cron: IBAMA diário 05:00; PRODES/CNFP anual (dez, após divulgação INPE/SFB).
set -e; B=${GEO_BASES:-/workspace/geo_bases}; cd $B; . venv/bin/activate
TB=https://terrabrasilis.dpi.inpe.br/geoserver/prodes-legal-amz/ows
IB=https://pamgia.ibama.gov.br/server/rest/services/01_Publicacoes_Bases/adm_embargos_ibama_a/FeatureServer/0
W=${1:-tudo}
for uf in RO AC; do u=${uf,,}
 if [[ $W == ibama || $W == tudo ]]; then python dl_arcgis.py $IB "uf='$uf'" tmp_$u.gpkg 500 && mv tmp_$u.gpkg embargos_ibama_$u.gpkg; fi
 if [[ $W == prodes || $W == tudo ]]; then python dl_wfs.py $TB prodes-legal-amz:yearly_deforestation "state='$uf'" tmp_p_$u.gpkg fid && mv tmp_p_$u.gpkg prodes_${u}_yearly.gpkg; fi
done
if [[ $W == imac || $W == tudo ]]; then mkdir -p imac; for y in 2023 2024 2025 2026; do curl -sfL -o imac/$y.zip https://imac.ac.gov.br/wp-content/uploads/2026/10/Embargos_ADM_IMAC_$y.zip && unzip -oq imac/$y.zip -d imac/$y; done
python - <<'P'
import geopandas as g,pandas as pd,glob
a=g.GeoDataFrame(pd.concat([g.read_file(f).to_crs(4674).assign(arquivo=f) for f in glob.glob('imac/*/*/*.shp')],ignore_index=True),crs=4674)
for c in a.columns:
    if c!='geometry' and not pd.api.types.is_numeric_dtype(a[c]): a[c]=a[c].astype(str)
a.to_file('embargos_imac_ac.gpkg');print('IMAC',len(a))
P
fi

# INCRA acervo fundiário (Assentamentos, Quilombolas, SIGEF, SNCI) – sugestão: mensal. Uso: ./atualizar_bases.sh incra
if [[ $W == incra || $W == tudo ]]; then
 mkdir -p incra; cd incra
 get(){ curl -sfk -m 900 -o "$2.zip" "https://certificacao.incra.gov.br/csv_shp/zip/$1.zip" && rm -rf "$2" && mkdir "$2" && unzip -oq "$2.zip" -d "$2" && (cd "$2"; for f in *; do mv -- "$f" "dados.${f##*.}"; done); }
 get "Assentamento%20Brasil_AC" Assentamento_Brasil_AC; get "Assentamento%20Brasil_RO" Assentamento_Brasil_RO
 get "Sigef%20Brasil_AC" Sigef_Brasil_AC; get "Sigef%20Brasil_RO" Sigef_Brasil_RO
 get "Im%C3%B3vel%20certificado%20SNCI%20Brasil_AC" snci_AC; get "Im%C3%B3vel%20certificado%20SNCI%20Brasil_RO" snci_RO
 get "%C3%81reas%20de%20Quilombolas" quilombolas
 cd ..; python incra_build.py; date > ultima_atualizacao_incra.txt
fi
date > ultima_atualizacao_$W.txt; echo OK
