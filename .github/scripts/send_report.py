#!/usr/bin/env python3
import os, sys, smtplib, mimetypes, pathlib
from email.message import EmailMessage

def need_env():
    req = ["SMTP_SERVER","SMTP_PORT","SMTP_USER","SMTP_PASS","SMTP_FROM","REPORT_TO"]
    missing = [k for k in req if not os.getenv(k)]
    return (len(missing)==0), missing

def attach_file(msg: EmailMessage, path: str):
    p = pathlib.Path(path)
    if not p.exists():
        return
    ctype, encoding = mimetypes.guess_type(p.name)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(p, "rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=p.name)

def main():
    ok, missing = need_env()
    if not ok:
        print("[send_report] skip: faltan variables:", ",".join(missing))
        return 0
    status_md = pathlib.Path("STATUS.md").read_text(encoding="utf-8") if pathlib.Path("STATUS.md").exists() else "(sin contenido)"
    msg = EmailMessage()
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = os.environ["REPORT_TO"]
    msg["Subject"] = "Vendedor360 – Reporte de ejecución"
    msg.set_content("Adjunto STATUS.md y logs/artifacts si están presentes.\n\nResumen:\n\n" + status_md[:2000])
    # Adjuntos básicos
    attach_file(msg, "STATUS.md")
    # Opcional: adjuntar logs zip si existe
    for path in ["logs/lici.json","logs/wherex.json","logs/senegocia.json","logs/mp.json","logs/meta_campaigns.json"]:
        attach_file(msg, path)
    with smtplib.SMTP_SSL(os.environ["SMTP_SERVER"], int(os.environ["SMTP_PORT"])) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)
    print("[send_report] enviado a", os.environ["REPORT_TO"])
    return 0

if __name__ == "__main__":
    sys.exit(main())

