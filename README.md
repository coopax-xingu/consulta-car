---
title: Rede COOPAX - Consulta CAR
emoji: 🌳
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 8501
pinned: false
short_description: Triagem socioambiental inicial do CAR (RO, AC, AM e MT)
---

# Rede COOPAX – Consulta Socioambiental do CAR
Triagem inicial do CAR antes de fechar com o cliente (indicativa; não substitui a análise do banco/BASA).
Cruza o imóvel (código CAR via SICAR WFS público, ou KML/KMZ/SHP-zip/GeoJSON) com PRODES 2008–2025 e máscara até 2007 (INPE),
Floresta Pública Tipo B (SFB CNFP 2025), embargos IBAMA (24/10/2026) e IMAC-AC (2023–mar/2026), UC e TI (TerraBrasilis),
Assentamentos, Quilombolas e parcelas SIGEF/SNCI (INCRA, 23–24/10/2026). Bases em `data/` para **RO, AC, AM e MT** (gpkg simplificados, sem Git LFS; nenhum arquivo > 100 MB). O polígono do imóvel vem sempre do SICAR WFS (`sicar_imoveis_<uf>`), então qualquer UF resolve o código; as camadas de cruzamento só existem para as 4 UFs acima.

- Página inteira: `https://<usuario>-consulta-car.hf.space/` · Embutida: `.../?embed=true`
- Rodar local: `pip install -r requirements.txt && streamlit run app.py` (ou `docker build -t consulta-car . && docker run -p 8501:8501 consulta-car`)

## Atualizar bases (fora do Space, no computador/box com as bases completas)
1. `GEO_BASES=/workspace/geo_bases tools/atualizar_bases.sh ibama` (diário/semanal), `prodes` (anual, após divulgação INPE ~nov/dez), `imac`, `incra` (mensal), ou `tudo`. Os scripts `dl_wfs.py`, `dl_arcgis.py`, `incra_build.py` precisam estar na pasta GEO_BASES (cópias em tools/).
2. `python tools/slim_data.py` – regrava `data/` enxuto.
3. `git add data && git commit -m "bases AAAA-MM-DD" && git push`.

## Estados AM e MT (adicionados em 11/11/2026)
| Camada | Fonte / data | AM | MT |
|---|---|---|---|
| PRODES anual 2008–2025 | INPE TerraBrasilis WFS `prodes-legal-amz:yearly_deforestation` (pub. 16/10/2026) | 88.685 pol. | 91.287 pol. |
| PRODES Cerrado e Pantanal (fora do bioma Amazônia) | TerraBrasilis `prodes-cerrado-nb` / `prodes-pantanal-nb` yearly_deforestation, ano ≥ 2008 | – | `prodes_mt_yearly_cerrado.gpkg`, `prodes_mt_yearly_pantanal.gpkg` |
| Máscara até 2007 | `accumulated_deforestation_2007` (só bioma Amazônia) | 45.223 | 26.581 |
| Floresta Pública Tipo B | SFB CNFP 2025 (FeatureServer) | 326 | 388 |
| Embargos IBAMA | pamgia.ibama.gov.br (11/11/2026) | 9.430 | 7.793 |
| UC federal/estadual/municipal | MMA CNUC, shapefile 2025_08 (03/09/2025) – também usado para RO e AC (`ucs_<uf>_cnuc.gpkg`) | 116 | 114 |
| Terras Indígenas | TerraBrasilis `indigenous_area_legal_amazon` | 151 | 77 |
| Quilombolas | INCRA (24/10/2026) | 2 | 5 |

Não carregados para AM/MT: Assentamentos INCRA, parcelas SIGEF/SNCI (certificacao.incra.gov.br estava fora do ar a partir da box em 11/11) e embargos estaduais (IPAAM/SEMA-MT). O app avisa no parecer quando uma base não está carregada.
Reconstruir: baixar as fontes (ver `tools/`) e rodar `GEO_NEW=<pasta> python tools/build_estados.py AM MT RO AC`.
