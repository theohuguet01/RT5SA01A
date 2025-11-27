#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Machine à café Lunar White - Application Flask
Gestion d'une machine à café avec carte à puce
"""

from flask import Flask, render_template, jsonify, request
from smartcard.System import readers
from smartcard.util import toHexString, toBytes
import datetime
import os

app = Flask(__name__)

# Configuration
PRIX_BOISSON = 20  # 0.20€ en centimes
BOISSONS = {
    1: {"nom": "Café", "emoji": "☕"},
    2: {"nom": "Thé", "emoji": "🍵"},
    3: {"nom": "Chocolat chaud", "emoji": "🍫"},
    4: {"nom": "Cappuccino", "emoji": "🥤"},
}

# Fichier de log
LOG_FILE = "log.txt"


def log_transaction(message):
    """Enregistre une transaction dans le fichier log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def get_card_connection():
    """Établit la connexion avec la carte à puce"""
    try:
        r = readers()
        if len(r) < 1:
            return None, "Aucun lecteur de carte détecté"
        
        reader = r[0]
        connection = reader.createConnection()
        connection.connect()
        return connection, None
    except Exception as e:
        error_msg = str(e)
        # Détecter si la carte est déconnectée/non alimentée
        if "unpowered" in error_msg.lower() or "0x80100067" in error_msg:
            return None, "CARD_DISCONNECTED"
        return None, f"Erreur de connexion: {error_msg}"


def lire_compteur(conn):
    """Lit le compteur anti-rejoue de la carte"""
    try:
        apdu = [0x82, 0x07, 0x00, 0x00, 0x02]
        data, sw1, sw2 = conn.transmit(apdu)
        if sw1 == 0x90 and sw2 == 0x00:
            # Compteur en little endian
            ctr = data[0] | (data[1] << 8)
            return ctr, None
        else:
            return None, f"Erreur lecture compteur: SW1={sw1:02X} SW2={sw2:02X}"
    except Exception as e:
        error_msg = str(e)
        if "unpowered" in error_msg.lower() or "0x80100067" in error_msg:
            return None, "CARD_DISCONNECTED"
        return None, f"Exception: {error_msg}"


def verifier_pin(conn, pin):
    """Vérifie le PIN de la carte (4 octets)"""
    try:
        apdu = [0x82, 0x04, 0x00, 0x00, 0x04] + pin
        data, sw1, sw2 = conn.transmit(apdu)
        if sw1 == 0x90 and sw2 == 0x00:
            return True, None
        elif sw1 == 0x69 and sw2 == 0x83:
            return False, "PIN bloqué"
        elif sw1 == 0x63:
            return False, f"PIN incorrect - {sw2} essai(s) restant(s)"
        else:
            return False, f"Erreur PIN: SW1={sw1:02X} SW2={sw2:02X}"
    except Exception as e:
        error_msg = str(e)
        if "unpowered" in error_msg.lower() or "0x80100067" in error_msg:
            return False, "CARD_DISCONNECTED"
        return False, f"Exception: {error_msg}"


def lire_solde(conn):
    """Lit le solde de la carte"""
    try:
        apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
        data, sw1, sw2 = conn.transmit(apdu)
        if sw1 == 0x90 and sw2 == 0x00:
            # Solde en little endian (centimes)
            solde = data[0] | (data[1] << 8)
            return solde, None
        elif sw1 == 0x69 and sw2 == 0x82:
            return None, "PIN non vérifié"
        else:
            return None, f"Erreur lecture solde: SW1={sw1:02X} SW2={sw2:02X}"
    except Exception as e:
        error_msg = str(e)
        if "unpowered" in error_msg.lower() or "0x80100067" in error_msg:
            return None, "CARD_DISCONNECTED"
        return None, f"Exception: {error_msg}"


def debiter_carte(conn, montant, ctr):
    """Débite un montant de la carte avec anti-rejoue"""
    try:
        p1 = ctr & 0xFF
        p2 = (ctr >> 8) & 0xFF
        m_lsb = montant & 0xFF
        m_msb = (montant >> 8) & 0xFF
        
        apdu = [0x82, 0x03, p1, p2, 0x02, m_lsb, m_msb]
        data, sw1, sw2 = conn.transmit(apdu)
        
        if sw1 == 0x90 and sw2 == 0x00:
            return True, None
        elif sw1 == 0x61:
            return False, "Solde insuffisant"
        elif sw1 == 0x69 and sw2 == 0x82:
            return False, "PIN non vérifié"
        elif sw1 == 0x69 and sw2 == 0x84:
            return False, "Erreur anti-rejoue"
        else:
            return False, f"Erreur débit: SW1={sw1:02X} SW2={sw2:02X}"
    except Exception as e:
        error_msg = str(e)
        if "unpowered" in error_msg.lower() or "0x80100067" in error_msg:
            return False, "CARD_DISCONNECTED"
        return False, f"Exception: {error_msg}"


@app.route('/')
def index():
    """Page d'accueil de la machine à café"""
    return render_template('index.html', boissons=BOISSONS)


@app.route('/api/check_card', methods=['POST'])
def check_card():
    """Vérifie la présence de la carte et demande le PIN"""
    conn, error = get_card_connection()
    if error:
        if error == "CARD_DISCONNECTED":
            log_transaction("Carte déconnectée (unpowered)")
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        log_transaction(f"ERREUR: {error}")
        return jsonify({"success": False, "error": error})
    
    log_transaction("Carte détectée")
    return jsonify({"success": True, "message": "Carte détectée"})


@app.route('/api/verify_pin', methods=['POST'])
def verify_pin():
    """Vérifie le PIN et retourne le solde"""
    data = request.get_json()
    pin_str = data.get('pin', '')
    
    if len(pin_str) != 4 or not pin_str.isdigit():
        return jsonify({"success": False, "error": "PIN invalide (4 chiffres requis)"})
    
    pin = [int(c) for c in pin_str]
    
    conn, error = get_card_connection()
    if error:
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    # Vérifier le PIN
    success, error = verifier_pin(conn, pin)
    if not success:
        log_transaction(f"Échec vérification PIN: {error}")
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    # Lire le solde
    solde, error = lire_solde(conn)
    if error:
        log_transaction(f"Erreur lecture solde: {error}")
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    solde_euros = solde / 100.0
    log_transaction(f"PIN vérifié - Solde: {solde_euros:.2f}€")
    
    return jsonify({
        "success": True,
        "solde": solde,
        "solde_euros": f"{solde_euros:.2f}"
    })


@app.route('/api/acheter_boisson', methods=['POST'])
def acheter_boisson():
    """Achète une boisson en débitant la carte"""
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
    
    if len(pin_str) != 4 or not pin_str.isdigit():
        return jsonify({"success": False, "error": "PIN invalide"})
    
    pin = [int(c) for c in pin_str]
    boisson = BOISSONS[boisson_id]
    
    conn, error = get_card_connection()
    if error:
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    # 1. Lire le compteur anti-rejoue
    ctr, error = lire_compteur(conn)
    if error:
        log_transaction(f"Erreur lecture compteur: {error}")
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    # 2. Vérifier le PIN
    success, error = verifier_pin(conn, pin)
    if not success:
        log_transaction(f"Échec vérification PIN: {error}")
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    # 3. Vérifier le solde
    solde, error = lire_solde(conn)
    if error:
        log_transaction(f"Erreur lecture solde: {error}")
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    if solde < PRIX_BOISSON:
        log_transaction(f"Solde insuffisant: {solde/100:.2f}€ < 0.20€")
        return jsonify({
            "success": False,
            "error": f"Solde insuffisant ({solde/100:.2f}€)"
        })
    
    # 4. Vérifier à nouveau le PIN pour le débit
    success, error = verifier_pin(conn, pin)
    if not success:
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    # 5. Débiter la carte
    success, error = debiter_carte(conn, PRIX_BOISSON, ctr)
    if not success:
        log_transaction(f"Erreur débit: {error}")
        if error == "CARD_DISCONNECTED":
            return jsonify({"success": False, "error": "Carte déconnectée", "disconnected": True})
        return jsonify({"success": False, "error": error})
    
    nouveau_solde = solde - PRIX_BOISSON
    nouveau_solde_euros = nouveau_solde / 100.0
    
    log_transaction(
        f"ACHAT: {boisson['nom']} - 0.20€ débités - "
        f"Nouveau solde: {nouveau_solde_euros:.2f}€"
    )
    
    return jsonify({
        "success": True,
        "message": f"{boisson['nom']} servi(e) !",
        "boisson": boisson['nom'],
        "nouveau_solde": nouveau_solde,
        "nouveau_solde_euros": f"{nouveau_solde_euros:.2f}"
    })


@app.route('/api/get_logs', methods=['GET'])
def get_logs():
    """Récupère les dernières transactions"""
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Retourner les 20 dernières lignes
    return jsonify({"logs": lines[-20:]})


if __name__ == '__main__':
    # Créer le fichier de log s'il n'existe pas
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== Machine à café Lunar White - Log démarré ===\n")
    
    print("=" * 50)
    print("  Machine à café Lunar White")
    print("  Serveur Flask démarré")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
