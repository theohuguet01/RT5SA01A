#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Machine à café Lunar White - MODE DÉMO
Version sans carte à puce pour tester l'interface
"""

from flask import Flask, render_template, jsonify, request
import datetime
import os
import time

app = Flask(__name__)

# Configuration
PRIX_BOISSON = 20  # 0.20€ en centimes
BOISSONS = {
    1: {"nom": "Café", "emoji": "☕"},
    2: {"nom": "Thé", "emoji": "🍵"},
    3: {"nom": "Chocolat chaud", "emoji": "🍫"}
}

# Fichier de log
LOG_FILE = "log_demo.txt"

# Simulation de carte (en mémoire)
demo_card = {
    "solde": 150,  # 1.50€
    "pin": "1234",
    "compteur": 0,
    "connected": False,
    "last_check": time.time()
}


def log_transaction(message):
    """Enregistre une transaction dans le fichier log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


@app.route('/')
def index():
    """Page d'accueil de la machine à café"""
    return render_template('index.html', boissons=BOISSONS)


@app.route('/api/check_card', methods=['POST'])
def check_card():
    """Simule la détection de la carte"""
    # Simuler la présence de la carte
    if not demo_card["connected"]:
        demo_card["connected"] = True
        demo_card["last_check"] = time.time()
        log_transaction("DEMO: Carte détectée")
    else:
        demo_card["last_check"] = time.time()
    
    return jsonify({
        "success": True, 
        "message": "Carte détectée (MODE DÉMO)",
        "connected": True
    })


@app.route('/api/card_status', methods=['GET'])
def card_status():
    """Vérifie si la carte est toujours connectée"""
    # Simuler une déconnexion après 30 secondes d'inactivité (pour test)
    # En vrai, la carte reste connectée
    current_time = time.time()
    if current_time - demo_card["last_check"] > 30:
        demo_card["connected"] = False
        log_transaction("DEMO: Carte déconnectée (timeout)")
    
    return jsonify({
        "connected": demo_card["connected"]
    })


@app.route('/api/verify_pin', methods=['POST'])
def verify_pin():
    """Simule la vérification du PIN"""
    data = request.get_json()
    pin_str = data.get('pin', '')
    
    if len(pin_str) != 4 or not pin_str.isdigit():
        return jsonify({"success": False, "error": "PIN invalide (4 chiffres requis)"})
    
    demo_card["last_check"] = time.time()
    
    # Vérifier le PIN
    if pin_str == demo_card["pin"]:
        solde_euros = demo_card["solde"] / 100.0
        log_transaction(f"DEMO: PIN vérifié - Solde: {solde_euros:.2f}€")
        
        return jsonify({
            "success": True,
            "solde": demo_card["solde"],
            "solde_euros": f"{solde_euros:.2f}"
        })
    else:
        log_transaction(f"DEMO: PIN incorrect")
        return jsonify({"success": False, "error": "PIN incorrect (essayez 1234)"})


@app.route('/api/acheter_boisson', methods=['POST'])
def acheter_boisson():
    """Simule l'achat d'une boisson"""
    data = request.get_json()
    boisson_id = data.get('boisson_id')
    pin_str = data.get('pin', '')
    
    # Convertir l'ID en entier si c'est une chaîne
    try:
        boisson_id = int(boisson_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "ID de boisson invalide"})
    
    if boisson_id not in BOISSONS:
        return jsonify({"success": False, "error": f"Boisson invalide (ID: {boisson_id})"})
    
    if pin_str != demo_card["pin"]:
        return jsonify({"success": False, "error": "PIN incorrect"})
    
    demo_card["last_check"] = time.time()
    
    boisson = BOISSONS[boisson_id]
    
    # Vérifier le solde
    if demo_card["solde"] < PRIX_BOISSON:
        log_transaction(f"DEMO: Solde insuffisant: {demo_card['solde']/100:.2f}€ < 0.20€")
        return jsonify({
            "success": False,
            "error": f"Solde insuffisant ({demo_card['solde']/100:.2f}€)"
        })
    
    # Débiter
    demo_card["solde"] -= PRIX_BOISSON
    demo_card["compteur"] += 1
    
    nouveau_solde_euros = demo_card["solde"] / 100.0
    
    log_transaction(
        f"DEMO ACHAT: {boisson['nom']} - 0.20€ débités - "
        f"Nouveau solde: {nouveau_solde_euros:.2f}€"
    )
    
    return jsonify({
        "success": True,
        "message": f"{boisson['nom']} servi(e) !",
        "boisson": boisson['nom'],
        "nouveau_solde": demo_card["solde"],
        "nouveau_solde_euros": f"{nouveau_solde_euros:.2f}"
    })


@app.route('/api/get_logs', methods=['GET'])
def get_logs():
    """Récupère les dernières transactions"""
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    return jsonify({"logs": lines[-20:]})


@app.route('/api/reset_demo', methods=['POST'])
def reset_demo():
    """Réinitialise la carte démo"""
    demo_card["solde"] = 150
    demo_card["compteur"] = 0
    demo_card["connected"] = False
    log_transaction("DEMO: Carte réinitialisée à 1.50€")
    return jsonify({"success": True, "message": "Carte réinitialisée"})


if __name__ == '__main__':
    # Créer le fichier de log s'il n'existe pas
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== Machine à café Lunar White - MODE DÉMO ===\n")
    
    print("=" * 60)
    print("  🎭 Machine à café Lunar White - MODE DÉMO")
    print("  (Sans carte à puce - Interface de test)")
    print("=" * 60)
    print("  Serveur Flask démarré sur http://127.0.0.1:5000")
    print("  PIN de démonstration: 1234")
    print("  Solde initial: 1.50€")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
