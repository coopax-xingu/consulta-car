---
title: Rede COOPAX - Consulta CAR
emoji: 🌳
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 8501
pinned: false
short_description: Triagem socioambiental inicial do CAR (AC e RO)
---

# Rede COOPAX – Consulta Socioambiental do CAR
Triagem inicial do CAR antes de fechar com o cliente (indicativa; não substitui a análise do banco/BASA).
Cruza o imóvel (código CAR via SICAR WFS público, ou KML/KMZ/SHP-zip/GeoJSON) com PRODES 2008–2025 e máscara até 2007 (INPE),
Floresta Pública Tipo B (SFB CNFP 2025), embargos IBAMA (24/10/2026) e IMAC-AC (2023–mar/2026), UC e TI (TerraBrasilis),
Assentamentos, Quilombolas e parcelas SIGEF/SNCI (INCRA, 23–24/10/2026). Bases só para **AC e RO** em `data/` (~251 MB, Git LFS).

- Página inteira: `https://<usuario>-consulta-car.hf.space/` · Embutida: `.../?embed=true`
- Rodar local: `pip install -r requirements.txt && streamlit run app.py` (ou `docker build -t consulta-car . && docker run -p 8501:8501 consulta-car`)

## Atualizar bases (fora do Space, no computador/box com as bases completas)
1. `GEO_BASES=/workspace/geo_bases tools/atualizar_bases.sh ibama` (diário/semanal), `prodes` (anual, após divulgação INPE ~nov/dez), `imac`, `incra` (mensal), ou `tudo`. Os scripts `dl_wfs.py`, `dl_arcgis.py`, `incra_build.py` precisam estar na pasta GEO_BASES (cópias em tools/).
2. `python tools/slim_data.py` – regrava `data/` enxuto.
3. `git add data && git commit -m "bases AAAA-MM-DD" && git push`.
