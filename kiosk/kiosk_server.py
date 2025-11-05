#!/usr/bin/env python3
from flask import Flask, send_from_directory, request, send_file
import os
print("...... start server .....")
app = Flask(__name__)

@app.route('/')
def index():
    return send_file('/home/kioskuser/kiosk_page.html')
    
@app.route('/kiosk_config.txt')
def config():
    return send_from_directory('.', 'kiosk_config.txt')
    
@app.route('/log', methods=['POST'])
def log():
    data = request.get_json()
    print("[JS LOG]:", data.get('message'))
    return "", 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)