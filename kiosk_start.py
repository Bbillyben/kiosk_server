#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import requests



# désactiver économiseur d'écran / DPMS
subprocess.run(["xset", "s", "off"])
subprocess.run(["xset", "-dpms"])
subprocess.run(["xset", "s", "noblank"])

# Lancer unclutter pour masquer le curseur
subprocess.Popen(["unclutter"])

# --- 1️⃣ Configuration ---
NODE_SERVER_DIR = "/home/kioskuser/kiosk_server/kiosk_server"
NODE_EXEC = "/usr/bin/node"
SERVER_FILE = "server.js"
SERVER_URL = "http://localhost:8080"   # URL à tester avant de lancer Chromium
MAX_WAIT = 10                           # secondes à attendre pour le serveur
CHECK_INTERVAL = 0.5                     # intervalle entre chaque ping serveur

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
    "--force-ui-language=en-US",
    "--start-fullscreen",
    "--check-for-update-interval=31536000",
    "--user-data-dir=/tmp/kiosk-profile",
    SERVER_URL
]

# --- 2️⃣ Lancer le serveur Node.js ---
server_process = subprocess.Popen([NODE_EXEC, SERVER_FILE], cwd=NODE_SERVER_DIR)
print("➡️ Serveur Node.js lancé, attente de disponibilité...")

# --- 3️⃣ Attendre que le serveur réponde ---
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
    time.sleep(CHECK_INTERVAL)

if not server_ready:
    print("❌ Serveur Node.js non disponible après attente. Arrêt du script.")
    server_process.terminate()
    server_process.wait()
    exit(1)

print("✅ Serveur Node.js prêt, lancement de Chromium...")

# --- 4️⃣ Lancer Chromium ---
try:
    subprocess.run(CHROMIUM_CMD)
finally:
    # --- 5️⃣ Arrêter le serveur Node.js si Chromium se ferme ---
    if server_process.poll() is None:
        print("🛑 Fermeture du serveur Node.js")
        server_process.send_signal(signal.SIGTERM)
        server_process.wait()
