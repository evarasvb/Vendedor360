#!/usr/bin/env bash
set -euo pipefail

# ===== PRE-CHEQUEOS =====
if [[ -z "${MP_TICKET:-}" && -z "${MP_SESSION_COOKIE:-}" ]]; then
  echo "[ERROR] Debes exportar MP_TICKET o MP_SESSION_COOKIE antes de ejecutar." >&2
  exit 1
fi

# Variables opcionales
export VENTANA_HORAS="${VENTANA_HORAS:-24}"
export MAX_RESULTADOS="${MAX_RESULTADOS:-200}"
export MODO="${MODO:-run_once}"          # run_once | watch
export WATCH_INTERVAL_MIN="${WATCH_INTERVAL_MIN:-10}"

# Estructura de carpetas
mkdir -p logs

# Ejecutar el agente (usa vendedor360.py ya creado)
python3 vendedor360.py
