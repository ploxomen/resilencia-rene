#!/usr/bin/env python3
"""
backup-agent/backup.py
Realiza backups incrementales de la DB principal y los envía a la DB espejo en la nube.
Intervalo por defecto: cada 120 segundos (2 minutos).
"""

import os
import time
import subprocess
import datetime
import logging
import requests
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BACKUP] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/backup.log"),
    ],
)
log = logging.getLogger("backup-agent")

# ── Config desde variables de entorno ────────────────────────
DB_HOST          = os.environ["DB_HOST"]
DB_PORT          = os.environ.get("DB_PORT", "5432")
DB_USER          = os.environ["DB_USER"]
DB_PASSWORD      = os.environ["DB_PASSWORD"]
DB_NAME          = os.environ["DB_NAME"]
MIRROR_HOST      = os.environ["MIRROR_HOST"]
MIRROR_PORT      = os.environ.get("MIRROR_PORT", "5433")
MIRROR_USER      = os.environ["MIRROR_USER"]
MIRROR_PASSWORD  = os.environ["MIRROR_PASSWORD"]
INTERVAL         = int(os.environ.get("BACKUP_INTERVAL_SECONDS", "120"))
DASHBOARD_URL    = os.environ.get("DASHBOARD_API_URL", "http://dashboard:3001")
BACKUP_DIR       = "/backups"

os.makedirs(BACKUP_DIR, exist_ok=True)

env = {
    **os.environ,
    "PGPASSWORD": DB_PASSWORD,
}

def notify_dashboard(event: dict):
    try:
        requests.post(f"{DASHBOARD_URL}/api/event", json=event, timeout=3)
    except Exception:
        pass  # Dashboard puede no estar disponible, no bloquear backup

def do_backup() -> bool:
    ts        = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename  = f"{BACKUP_DIR}/backup_{ts}.sql"
    t_start   = time.time()

    log.info(f"Iniciando backup incremental → {filename}")
    notify_dashboard({"type": "backup_start", "timestamp": ts})

    # ── Dump de la DB principal ──────────────────────────────
    dump_cmd = [
        "pg_dump",
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-d", DB_NAME,
        "--no-password",
        "-F", "p",          # plain SQL para poder ejecutar en espejo
        "-f", filename,
    ]
    result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"pg_dump falló: {result.stderr}")
        notify_dashboard({"type": "backup_error", "timestamp": ts, "error": result.stderr})
        return False

    # ── Restaurar en DB espejo ───────────────────────────────
    mirror_env = {**os.environ, "PGPASSWORD": MIRROR_PASSWORD}

    restore_cmd = [
        "psql",
        "-h", MIRROR_HOST,
        "-p", MIRROR_PORT,
        "-U", MIRROR_USER,
        "-d", DB_NAME,
        "--no-password",
        "-f", filename,
    ]
    result2 = subprocess.run(restore_cmd, env=mirror_env, capture_output=True, text=True)

    elapsed = round(time.time() - t_start, 2)

    if result2.returncode != 0:
        log.warning(f"Restauración con advertencias (puede ser normal): {result2.stderr[:300]}")

    size_kb = round(os.path.getsize(filename) / 1024, 1)
    log.info(f"Backup completado en {elapsed}s — {size_kb} KB")

    notify_dashboard({
        "type":     "backup_done",
        "timestamp": ts,
        "filename": os.path.basename(filename),
        "elapsed":  elapsed,
        "size_kb":  size_kb,
    })
    return True


def main():
    log.info(f"Backup agent iniciado — intervalo: {INTERVAL}s")
    while True:
        try:
            do_backup()
        except Exception as exc:
            log.exception(f"Error inesperado en ciclo de backup: {exc}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
