# Vendedor 360
Automatiza postulaciones (Wherex, Senegocia, MP) y publicaciones (Meta/Marketplace, LinkedIn).
- Orquestador horario (GitHub Actions).
- Filtro anti-logo global.
- Colas CSV para controlar qué postular/publicar.
- STATUS.md y artifacts con evidencia.

## Secrets requeridos
WHEREX_USER, WHEREX_PASS
SENEGOCIA_USER, SENEGOCIA_PASS
MP_TICKET (y opcional MP_SESSION_COOKIE)
META_PAGE_ACCESS_TOKEN, META_PAGE_ID
LINKEDIN_ACCESS_TOKEN
 LICI_USER, LICI_PASS
 CM_USER, CM_PASS
 META_AD_ACCOUNT_ID, META_PIXEL_ID

## Colas y configuración
- queues/postulaciones.csv: ahora incluye columnas `match_min`, `prioridad`, `nota`.
- queues/cm_agregar.csv: insumos Convenio Marco (Barrilito, Kensington, Rexel).
- queues/publicaciones.csv: añade `imagen`, `categoria`, `stock`.
- config/meta_segments.json: segmentos y creatividades para campañas “Liquidadora”.

## Reports
- reports/daily_insights.md: resumen diario de palabras sin match y exclusiones frecuentes.

Recordatorio: agregar imágenes reales a `assets/...` cuando estén disponibles.
