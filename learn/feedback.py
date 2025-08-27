#!/usr/bin/env python3
import json, pathlib, re
from collections import Counter
from agents.common.status import append_status

def safe_json_load(p):
    try: return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except: return []

def main():
    status = "STATUS.md"
    logs = {
        "lici": safe_json_load("logs/lici.json"),
        "wherex": safe_json_load("logs/wherex.json"),
        "senegocia": safe_json_load("logs/senegocia.json"),
        "mp": safe_json_load("logs/mp.json"),
        "meta": safe_json_load("logs/meta_campaigns.json")
    }
    palabras_no_match = [r.get("palabra") for r in logs.get("lici", []) if r.get("estado")=="no_match"]
    excl = Counter()
    for r in logs.get("lici", []):
        motivo = (r.get("motivo") or "")
        if "exclusion" in motivo: excl.update([motivo])
    insights = {
        "palabras_sin_match": [p for p in palabras_no_match if p][:10],
        "exclusiones_mas_frecuentes": excl.most_common(5)
    }
    pathlib.Path("learn").mkdir(exist_ok=True, parents=True)
    pathlib.Path("reports").mkdir(exist_ok=True, parents=True)
    pathlib.Path("learn/state.json").write_text(json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8")
    pathlib.Path("reports/daily_insights.md").write_text(
        "# Daily Insights\n\n- Palabras sin match (top 10):\n" +
        "".join(f"  - {p}\n" for p in insights["palabras_sin_match"]) +
        "\n- Exclusiones frecuentes:\n" +
        "".join(f"  - {k}: {v}\n" for k,v in insights["exclusiones_mas_frecuentes"]), encoding="utf-8")
    append_status(status, "Learn/Feedback", [{"estado": "ok", "palabras_no_match": len(palabras_no_match)}])
    return 0

if __name__ == "__main__":
    import sys; sys.exit(main())

