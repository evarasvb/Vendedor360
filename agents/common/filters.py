import json, pathlib
EXCLUS_DEFAULT = ["logo","logotipo","impreso","impresión","impresas","personalizado",
                  "personalizada","serigrafía","serigrafiado","bordado","esval"]
def load_exclusions(base: pathlib.Path) -> list[str]:
    p = base / "exclusiones.json"
    if p.exists():
        try: return [w.lower() for w in json.loads(p.read_text(encoding="utf-8"))]
        except Exception: return EXCLUS_DEFAULT
    return EXCLUS_DEFAULT
def contains_exclusion(txt: str, exclus: list[str]) -> bool:
    t = (txt or "").lower()
    return any(w in t for w in exclus)
