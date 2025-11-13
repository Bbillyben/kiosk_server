#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import requests
from datetime import datetime, time as dtime
import json

# ===============================
# 🔧 CONFIGURATION GÉNÉRALE
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

# ===============================
# ⚙️  PRÉPARATION DE L’ENVIRONNEMENT
# ===============================

# Forcer DISPLAY=:0 si non défini
if "DISPLAY" not in os.environ or not os.environ["DISPLAY"]:
    os.environ["DISPLAY"] = ":0"

# ===============================
# ⚙️  FONCTIONS UTILITAIRES
# ===============================

def load_active_hours():
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
        print(f"⚠️ Impossible de charger la config horaire : {err}")
    print(f"🕒 Heures actives chargées : début = {start.strftime('%H:%M')} / fin = {end.strftime('%H:%M')}")

    return start, end

def within_active_hours(start, end):
    """Retourne True si l'heure actuelle est dans la plage autorisée"""
    now = datetime.now().time()
    if start < end:
        return start <= now < end
    else:
        # Cas où la plage passe minuit (ex: 22h → 06h)
        return now >= start or now < end

def wait_until_start(start, end):
    """Attend la prochaine heure d'ouverture"""
    print("⏸️  En dehors des heures d’activité, attente du créneau...")
    while not within_active_hours(start, end):
        time.sleep(CHECK_INTERVAL)
    print("✅ Créneau horaire actif — démarrage du kiosk")

def stop_chromium_and_server(server_process):
    """Arrête proprement Chromium et le serveur Node"""
    print("🛑 Fin du créneau horaire — arrêt du kiosk")
    subprocess.run(["pkill", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if server_process and server_process.poll() is None:
        server_process.send_signal(signal.SIGTERM)
        server_process.wait()
    # Tente d’éteindre l’écran si X est disponible
    try:
        subprocess.run(["xset", "dpms", "force", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    time.sleep(2)

# ===============================
# 🚀 BOUCLE PRINCIPALE
# ===============================

while True:
    ACTIVE_START, ACTIVE_END = load_active_hours()

    if not within_active_hours(ACTIVE_START, ACTIVE_END):
        wait_until_start(ACTIVE_START, ACTIVE_END)

    # Réactivation écran
    for cmd in [["xset", "s", "off"], ["xset", "-dpms"], ["xset", "s", "noblank"], ["xset", "dpms", "force", "on"]]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass

    # Masquer curseur (si unclutter existe)
    try:
        subprocess.Popen(["unclutter"])
    except FileNotFoundError:
        print("⚠️ unclutter non installé — curseur visible")

    # --- Démarrer le serveur Node.js ---
    server_process = subprocess.Popen([NODE_EXEC, SERVER_FILE], cwd=NODE_SERVER_DIR)
    print("➡️ Serveur Node.js lancé, attente de disponibilité...")

    # Attendre que le serveur soit prêt
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
        print("❌ Serveur Node.js non disponible, arrêt.")
        server_process.terminate()
        server_process.wait()
        time.sleep(CHECK_INTERVAL)
        continue

    print("✅ Serveur prêt, lancement de Chromium...")
    chromium_proc = subprocess.Popen(CHROMIUM_CMD)

    # --- Boucle de surveillance horaire ---
    try:
        while within_active_hours(ACTIVE_START, ACTIVE_END):
            time.sleep(CHECK_INTERVAL)
            ACTIVE_START, ACTIVE_END = load_active_hours()  # Recharger si modifié
        stop_chromium_and_server(server_process)
        chromium_proc.terminate()
    except KeyboardInterrupt:
        stop_chromium_and_server(server_process)
        chromium_proc.terminate()
        break
