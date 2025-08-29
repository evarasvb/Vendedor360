# MetaOps – Robot de Automatización para Meta (FB/IG/WA)

Servicio FastAPI para operar Catálogo, Contenidos, Inbox y Reportes usando APIs oficiales de Meta y Google Sheets.

## Stack
- Python 3.11, FastAPI, APScheduler
- SQLAlchemy + Alembic (SQLite/Postgres)
- Google Sheets (gspread)
- Docker, docker-compose, Makefile
- Tests con pytest, lint con ruff

## Requisitos
- Docker y Docker Compose instalados
- Cuenta Google con acceso a Google Cloud
- App de Meta (Graph/Marketing/WhatsApp Cloud)

## Configuración
1. Crea `.env` desde `.env.example` y completa valores.
2. Crea una Service Account en Google Cloud y descarga `service_account.json`.
3. Copia `service_account.json` a `creds/service_account.json` (o define otra ruta en `.env`).
4. Comparte los Google Sheets INVENTARIO y REPORTES con el correo de la Service Account.
5. En Meta Developers, configura tu App, genera tokens long-lived y configura Webhooks apuntando a `/webhooks/fb-ig` y `/webhooks/wa`.

## Levantar con Docker
```bash
make up
```
Accede a `http://localhost:8000/docs`.

## Probar rápidamente
- Health:
```bash
curl -s http://localhost:8000/health
```
- Seed catálogo (requiere Sheets):
```bash
curl -X POST http://localhost:8000/catalog/sync
```
- Programar post en 2 minutos:
```bash
NOW=$(date -u -d "+2 minutes" +%Y-%m-%dT%H:%M:%SZ)
curl -X POST http://localhost:8000/content/schedule \
  -H 'Content-Type: application/json' \
  -d '{"text":"Oferta {{sku}} a ${{precio}}","destination":"fb","scheduled_at":"'"$NOW"'"}'
```
- Reglas de inbox:
```bash
curl -X POST http://localhost:8000/inbox/rules \
  -H 'Content-Type: application/json' \
  -d '{"keyword":"precio","response_text":"¡Gracias! Te contactamos.","escalate_to_human":false}'
```

## Desarrollo local
```bash
make install
make run
```

## Migraciones (opcional)
```bash
make alembic-init
make migrate
make head
```

## CI
Incluye workflow mínimo de lint + tests (agregar en GitHub).

## Licencia
MIT
