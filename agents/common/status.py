from datetime import datetime
import pathlib, json
def append_status(status_path: str, section: str, resultados: list[dict]):
    p = pathlib.Path(status_path)
    prev = p.read_text(encoding="utf-8") if p.exists() else ""
    lines = [prev, "\n" if prev and not prev.endswith("\n") else "", f"## {section}\n",
             f"- Fecha: {datetime.now().isoformat()}\n"]
    for r in resultados:
        detalle = ", ".join(f"{k}:{v}" for k,v in r.items())
        lines.append(f"- {detalle}\n")
    p.write_text("".join(lines), encoding="utf-8")
def write_json_log(path: str, data: list[dict]):
    p = pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
