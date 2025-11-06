"""Main orchestration entry-point for Vendedor360."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import argparse
import logging
import subprocess
import sys
import time

from agents.common.status import append_status
from credentials_validator import CredentialRequirement, CredentialValidator
from resilience import RetryPolicy, execute_with_retry, ResilienceError


log = logging.getLogger("orchestrator")


@dataclass
class Task:
    """Representation of a runnable task within the orchestrator."""

    name: str
    command: list[str]
    credentials: Iterable[CredentialRequirement]
    retries: int = 2


def load_config(path: Path) -> dict:
    """Load the ``agent_config.yaml`` file without external dependencies."""

    config: dict[str, dict] = {}
    if not path.exists():
        return config
    current_section: str | None = None
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.split("#", 1)[0].rstrip()
            if not line:
                continue
            if not line.startswith(" ") and line.endswith(":"):
                current_section = line[:-1].strip()
                config.setdefault(current_section, {})
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"')
                if current_section:
                    config.setdefault(current_section, {})[key] = _parse_scalar(value)
                else:
                    config[key] = _parse_scalar(value)
    return config


def _parse_scalar(value: str) -> object:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def build_tasks(config: dict, status_path: Path) -> list[Task]:
    """Construct the tasks executed per cycle."""

    cola = str(config.get("paths", {}).get("postulaciones_csv", "queues/postulaciones.csv"))
    since = str(int(config.get("params", {}).get("ventana_horas", 24)))
    python = sys.executable
    tasks: list[Task] = [
        Task(
            name="Mercado Público",
            command=[
                python,
                "agents/mp/run.py",
                "--cola",
                cola,
                "--status",
                str(status_path),
                "--since-hours",
                since,
            ],
            credentials=[
                CredentialRequirement(
                    name="Mercado Público",
                    env_vars=["MP_TICKET", "MP_SESSION_COOKIE"],
                    mode="any",
                    hint="Exporta MP_TICKET o MP_SESSION_COOKIE",
                )
            ],
            retries=3,
        ),
        Task(
            name="Meta/Marketplace",
            command=[python, "agents/meta/run.py", "--status"],
            credentials=[
                CredentialRequirement("Meta Access Token", ["META_ACCESS_TOKEN"], hint="Necesario para la Graph API"),
                CredentialRequirement("Meta App ID", ["META_APP_ID"]),
            ],
            retries=2,
        ),
        Task(
            name="LinkedIn",
            command=[python, "agents/linkedin/run.py", "--status", str(status_path)],
            credentials=[
                CredentialRequirement("LinkedIn Token", ["LINKEDIN_ACCESS_TOKEN"], hint="Genera un token en LinkedIn"),
            ],
            retries=2,
        ),
    ]
    return tasks


def run_command(task: Task, log_dir: Path) -> tuple[str, Path]:
    """Execute a task command with retries and return the resulting state."""

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    slug = task.name.lower().replace("/", "-").replace(" ", "_")
    log_file = log_dir / f"{slug}_{timestamp}.log"

    def _invoke() -> subprocess.CompletedProcess[str]:
        log.info("Running task %s", task.name)
        return subprocess.run(
            task.command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    try:
        completed = execute_with_retry(
            _invoke,
            policy=RetryPolicy(max_attempts=task.retries),
            exceptions=(subprocess.CalledProcessError,),
            logger=log,
        )
        stdout, stderr = completed.stdout, completed.stderr
        state = "ok"
        motivo = "ejecutado"
    except ResilienceError as exc:
        # Last attempt raised a CalledProcessError. Preserve the details.
        stdout = getattr(exc.__cause__, "stdout", "")
        stderr = getattr(exc.__cause__, "stderr", str(exc))
        state = "error"
        motivo = str(exc.__cause__ or exc)
    except Exception as exc:  # pylint: disable=broad-except
        stdout, stderr = "", str(exc)
        state = "error"
        motivo = str(exc)

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file.write_text(
        f"Comando: {' '.join(task.command)}\nEstado: {state}\nMotivo: {motivo}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n",
        encoding="utf-8",
    )
    return state, log_file


def run_cycle(tasks: Iterable[Task], validator: CredentialValidator, status_path: Path, log_dir: Path) -> None:
    resumen: list[dict[str, str]] = []
    for task in tasks:
        report = validator.validate(task.credentials)
        if not report.ok:
            motivo = report.summary() or "faltan_credenciales"
            append_status(status_path, task.name, [{"estado": "skip", "motivo": motivo}])
            resumen.append({"tarea": task.name, "estado": "skip", "motivo": motivo})
            continue
        estado, log_file = run_command(task, log_dir)
        append_status(status_path, task.name, [{"estado": estado, "motivo": str(log_file)}])
        resumen.append({"tarea": task.name, "estado": estado, "log": str(log_file)})
    append_status(status_path, "Orquestador", resumen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orquestador principal de Vendedor360")
    parser.add_argument("--config", default="agent_config.yaml")
    parser.add_argument("--mode", choices=["run_once", "watch"], help="Sobrescribe el modo configurado")
    parser.add_argument("--interval", type=int, help="Intervalo en minutos para modo watch")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    config = load_config(Path(args.config))
    params = config.get("params", {})
    mode = args.mode or params.get("modo", "run_once")
    interval = args.interval or int(params.get("watch_interval_min", 10))
    status_path = Path(config.get("paths", {}).get("status_md", "STATUS.md"))
    log_dir = Path(config.get("paths", {}).get("logs_dir", "logs"))

    validator = CredentialValidator()
    tasks = build_tasks(config, status_path)

    while True:
        run_cycle(tasks, validator, status_path, log_dir)
        if mode != "watch":
            break
        log.info("Esperando %s minutos antes del siguiente ciclo", interval)
        time.sleep(max(1, interval) * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
