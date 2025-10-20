# Vendedor 360
Automatiza postulaciones (Wherex, Senegocia, MP, Lici) y publicaciones (Meta/Marketplace, LinkedIn).
- Orquestador horario (GitHub Actions).
- Filtro anti-logo global.
- Colas CSV para controlar qué postular/publicar.
- STATUS.md y artifacts con evidencia.

## Secrets requeridos
WHEREX_USER, WHEREX_PASS
SENEGOCIA_USER, SENEGOCIA_PASS
MP_TICKET (y opcional MP_SESSION_COOKIE)
LICI_USER, LICI_PASS
META_PAGE_ACCESS_TOKEN, META_PAGE_ID
LINKEDIN_ACCESS_TOKEN

## Automatización Lici
- Módulo: `agents/lici/run.py`
- Cola sugerida: `queues/postulaciones.csv` (se usa para priorizar empresas y umbrales de match).
- Ejecución manual: `python -m agents.lici.run --cola queues/postulaciones.csv --status STATUS.md`
- Evidencia: archivos `artifacts/lici_*.csv` y bitácora JSON en `logs/lici.json`.
