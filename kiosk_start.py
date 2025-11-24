#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import requests
from datetime import datetime, time as dtime
import json
import logging

# ===============================
#     CONFIGURATION GÉNÉRALE
# ===============================

CONFIG_FILE = "/home/kioskuser/kiosk_server/kiosk_server/config.json"

DEFAULT_ACTIVE_START = dtime(8, 0)   # 08:00
DEFAULT_ACTIVE_END = dtime(20, 0)    # 20:00
CHECK_INTERVAL = 60                  # secondes entre vérifications

NODE_SERVER_DIR = "/home/kioskuser/kiosk_server/kiosk_server"
NODE_EXEC = "/usr/bin/node"
SERVER_FILE = "server.js"
SERVER_URL = "http://localhost:8080"
MAX_WAIT = 10
PING_INTERVAL = 0.5

CHROMIUM_CMD = [
    "chromium",
    "--kiosk",
    "--noerrdialogs",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-session-crashed-bubble",
    "--disable-translate",
    "--disable-features=TranslateUI",
    "--disable-plugins",
    "--disable-extensions",
    "--disable-component-update",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-sync",
    "--disable-default-apps",
    "--disable-first-run-ui",
    "--no-first-run",
    "--lang=en-US",
    "--start-fullscreen",
    "--check-for-update-interval=31536000",
    "--user-data-dir=/tmp/kiosk-profile",
    SERVER_URL
]


logging.basicConfig(
    filename="/var/log/kiosk.log",
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)

# ===============================
#           UTILITAIRES
# ===============================

# Forcer DISPLAY=:0 si non défini (test en distanciel)
if "DISPLAY" not in os.environ or not os.environ["DISPLAY"]:
    os.environ["DISPLAY"] = ":0"



def log(msg):
    logging.info(msg)
    
def load_active_hours(prev_hours=None):
    """Charge les heures d'activité depuis le fichier config.json"""
    start = DEFAULT_ACTIVE_START
    end = DEFAULT_ACTIVE_END
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            if "active_hours" in cfg:
                s = cfg["active_hours"].get("start", "08:00")
                e = cfg["active_hours"].get("end", "20:00")
                h1, m1 = map(int, s.split(":"))
                h2, m2 = map(int, e.split(":"))
                start = dtime(h1, m1)
                end = dtime(h2, m2)
    except Exception as err:
        log(f" Impossible de charger la config horaire : {err}")

    if prev_hours != (start, end):
        log(f" Heures actives : {start.strftime('%H:%M')} → {end.strftime('%H:%M')}")
    return start, end

def within_active_hours(start, end):
    now = datetime.now().time()
    if start < end:
        return start <= now < end
    else:
        # Cas où la plage passe minuit
        return now >= start or now < end

def wait_until_start(start, end):
    log("  En dehors des heures d’activité, attente du créneau...")
    while not within_active_hours(start, end):
        time.sleep(CHECK_INTERVAL)
    log(" Créneau horaire actif — démarrage du kiosk")

def stop_chromium_and_server(server_process, chromium_process):
    """Arrête Chromium et le serveur Node proprement"""
    log(" Fin du créneau horaire — arrêt du kiosk")
    
    # Chromium
    subprocess.run(["pkill", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if chromium_process and chromium_process.poll() is None:
        chromium_process.terminate()
        try:
            chromium_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chromium_process.kill()
    
    # Node.js
    if server_process and server_process.poll() is None:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

    # Écran off
    try:
        subprocess.run(["xset", "dpms", "force", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass

# ===============================
#       BOUCLE PRINCIPALE
# ===============================

prev_hours = None

while True:
    ACTIVE_START, ACTIVE_END = load_active_hours(prev_hours)
    prev_hours = (ACTIVE_START, ACTIVE_END)

    if not within_active_hours(ACTIVE_START, ACTIVE_END):
        wait_until_start(ACTIVE_START, ACTIVE_END)

    # --- Lancer serveur Node.js ---
    server_process = subprocess.Popen([NODE_EXEC, SERVER_FILE], cwd=NODE_SERVER_DIR)
    log(" Serveur Node.js lancé, attente de disponibilité...")

    start_time = time.time()
    server_ready = False
    while time.time() - start_time < MAX_WAIT:
        try:
            r = requests.get(SERVER_URL, timeout=1)
            if r.status_code == 200:
                server_ready = True
                break
        except requests.RequestException:
            pass
        time.sleep(PING_INTERVAL)

    if not server_ready:
        log(" Serveur Node.js non disponible, arrêt.")
        stop_chromium_and_server(server_process, None)
        time.sleep(CHECK_INTERVAL)
        continue

    log(" Serveur prêt, lancement de Chromium...")
    chromium_process = subprocess.Popen(CHROMIUM_CMD)

    time.sleep(5)
    # Réactiver écran
    for cmd in [["xset", "s", "off"], ["xset", "-dpms"], ["xset", "s", "noblank"], ["xset", "dpms", "force", "on"]]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        except FileNotFoundError:
            pass

    # Masquer curseur (si unclutter existe)
    try:
        subprocess.run(["pgrep", "unclutter"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # unclutter non trouvé → lancement
        try:
            subprocess.Popen(["unclutter"])
        except FileNotFoundError:
            log(" unclutter non installé — curseur visible")

    # --- Boucle de surveillance horaire ---
    try:
        while within_active_hours(ACTIVE_START, ACTIVE_END):
            time.sleep(CHECK_INTERVAL)
            # Recharge la config si modifiée
            ACTIVE_START, ACTIVE_END = load_active_hours(prev_hours)
            prev_hours = (ACTIVE_START, ACTIVE_END)
        stop_chromium_and_server(server_process, chromium_process)
    except KeyboardInterrupt:
        stop_chromium_and_server(server_process, chromium_process)
        break
