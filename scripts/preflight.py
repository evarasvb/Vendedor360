#!/usr/bin/env python3
"""Herramientas de preflight y sanitización para Vendedor360.

Este módulo se encarga de tres tareas principales:

1. Validar que las variables de entorno requeridas estén presentes
   (sin imprimir sus valores).
2. Garantizar que los directorios de runtime (logs, artifacts, etc.)
   existan antes de ejecutar los agentes.
3. Sanitizar el archivo STATUS.md removiendo cualquier rastro de
   credenciales y añadiendo el encabezado base utilizado por el
   orquestador.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from typing import Iterable

BASE_HEADER = """# Vendedor 360 – Estado
Se actualiza automáticamente en cada ejecución del orquestador.

> Las credenciales y tokens se administran mediante GitHub Secrets. Este archivo solo almacena resultados de ejecución y notas operativas.
"""

CREDENTIAL_SECTION_RE = re.compile(r"^##\s+Credenciales.*?(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL)
SENSITIVE_LINE_RE = re.compile(r"^(?:-\s*)?(?:Usuario|Contraseña|Password|Token)[^\n]*$", re.IGNORECASE | re.MULTILINE)


def ensure_runtime_dirs(directories: Iterable[pathlib.Path]) -> None:
    """Crea los directorios necesarios para los agentes."""

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def sanitize_status(status_path: pathlib.Path) -> None:
    """Elimina secciones sensibles de STATUS.md y asegura el encabezado base."""

    if status_path.exists():
        raw = status_path.read_text(encoding="utf-8")
    else:
        raw = ""

    sanitized = CREDENTIAL_SECTION_RE.sub("", raw)
    sanitized = SENSITIVE_LINE_RE.sub("", sanitized)
    sanitized = sanitized.strip()

    # Evitar duplicar encabezados previos.
    base = BASE_HEADER.strip()
    if sanitized.startswith(base):
        sanitized = sanitized[len(base) :].lstrip()
    elif sanitized.startswith("# Vendedor 360 – Estado"):
        sanitized = sanitized.split("\n", 1)[1] if "\n" in sanitized else ""
        sanitized = sanitized.strip()

    if sanitized:
        content = BASE_HEADER + "\n" + sanitized
    else:
        content = BASE_HEADER + "\n## Histórico\n- Aún no hay ejecuciones registradas.\n"

    if "## Gestión de credenciales" not in content:
        content = (
            content.rstrip()
            + "\n\n## Gestión de credenciales\n"
            + "- Las credenciales se administran mediante secretos de GitHub y nunca se registran en STATUS.md.\n"
        )

    content = content.rstrip() + "\n"
    status_path.write_text(content, encoding="utf-8")


def validate_env(required: Iterable[str]) -> None:
    """Verifica que las variables de entorno requeridas existan y no estén vacías."""

    missing: list[str] = []
    for var in required:
        value = os.environ.get(var)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(var)
    if missing:
        joined = ", ".join(sorted(set(missing)))
        raise SystemExit(f"Faltan variables de entorno requeridas: {joined}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight para Vendedor360")
    parser.add_argument("--status", type=pathlib.Path, help="Ruta del STATUS.md a sanitizar")
    parser.add_argument(
        "--runtime-dir",
        action="append",
        type=pathlib.Path,
        default=[],
        help="Directorios que deben existir antes de la ejecución",
    )
    parser.add_argument(
        "--require-env",
        action="append",
        default=[],
        help="Variables de entorno que deben estar presentes",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.status:
        sanitize_status(args.status)

    if args.runtime_dir:
        ensure_runtime_dirs(args.runtime_dir)

    required: list[str] = []
    for item in args.require_env:
        if isinstance(item, str):
            required.extend(part.strip() for part in item.split(",") if part.strip())
    if required:
        validate_env(required)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
