#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template_string, request, jsonify
import smartcard.System as scardsys
import mysql.connector
from decimal import Decimal
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# =========================
#  CONFIG BDD
# =========================

DB_CONFIG = {
    "host": "purple-dragon-db",
    "port": 3306,
    "user": "rodelika",
    "password": "rodelika",
    "database": "carote_electronique",
}

conn_reader = None

# =========================
#  INIT SMARTCARD
# =========================

def get_card_connection():
    """Obtient une connexion au lecteur de carte."""
    global conn_reader
    if conn_reader is not None:
        try:
            conn_reader.getATR()
            return conn_reader
        except Exception as e:
            print(f"[DEBUG] get_card_connection: connexion existante invalide: {e}")
            conn_reader = None

    try:
        lst_readers = scardsys.readers()
        print(f"[DEBUG] Lecteurs détectés : {lst_readers}")
        if len(lst_readers) < 1:
            print("[DEBUG] Aucun lecteur détecté")
            return None
        conn_reader = lst_readers[0].createConnection()
        conn_reader.connect()
        print("[DEBUG] Connexion carte OK")
        return conn_reader
    except Exception as e:
        print(f"Erreur connexion carte: {e}")
        return None

def get_db_connection():
    """Obtient une connexion MySQL."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        print(f"[DEBUG] Connexion MySQL OK vers {DB_CONFIG['host']} / {DB_CONFIG['database']}")
        return cnx
    except mysql.connector.Error as err:
        print(f"Erreur MySQL: {err}")
        return None

# =========================
#  FONCTIONS CARTE
# =========================

def _read_perso_raw():
    """Lecture des données perso brutes."""
    conn = get_card_connection()
    if not conn:
        print("[DEBUG] _read_perso_raw: pas de connexion carte")
        return None

    apdu = [0x81, 0x02, 0x00, 0x00, 0x05]
    try:
        data, sw1, sw2 = conn.transmit(apdu)
        print(f"[DEBUG] APDU perso: data={data}, sw1={hex(sw1)}, sw2={hex(sw2)}")
        if sw1 == 0x6C:
            apdu[4] = sw2
            data, sw1, sw2 = conn.transmit(apdu)
            print(f"[DEBUG] APDU perso (retry): data={data}, sw1={hex(sw1)}, sw2={hex(sw2)}")

        if sw1 != 0x90 or sw2 != 0x00:
            print("[DEBUG] _read_perso_raw: SW non OK")
            return None

        if not data:
            print("[DEBUG] _read_perso_raw: data vide")
            return ""

        # Chaîne brute complète renvoyée par la carte (pour diagnostic)
        full_str = "".join(chr(e) for e in data)
        print(f"[DEBUG] FULL perso string (data complet) = {repr(full_str)}")

        perso_bytes = data[:]
        print(f"[DEBUG] perso_bytes (tous les octets conservés) = {perso_bytes}")

        if not perso_bytes:
            print("[DEBUG] _read_perso_raw: perso_bytes vide après traitement")
            return ""

        perso_str = "".join(chr(e) for e in perso_bytes)
        print(f"[DEBUG] perso_str={repr(perso_str)}")
        return perso_str
    except Exception as e:
        print(f"Erreur lecture perso: {e}")
        return None

def get_student_info_from_card():
    """Retourne (Num_Etudiant, Nom, Prenom)."""
    perso = _read_perso_raw()
    print(f"[DEBUG] get_student_info_from_card: perso={repr(perso)}")
    if perso is None or perso == "":
        return None, None, None

    parts = perso.split(";")
    print(f"[DEBUG] get_student_info_from_card: parts={parts}")
    if len(parts) < 3:
        print("[DEBUG] get_student_info_from_card: moins de 3 champs dans perso")
        return None, None, None

    raw_num = parts[0].strip()
    nom = parts[1].strip()
    prenom = parts[2].strip()

    print(f"[DEBUG] raw_num={repr(raw_num)}, nom={repr(nom)}, prenom={repr(prenom)}")

    if not raw_num.isdigit():
        print("[DEBUG] raw_num n'est pas composé uniquement de chiffres")
        return None, None, None

    etu_num = raw_num.zfill(8)
    print(f"[DEBUG] etu_num après zfill(8) = {repr(etu_num)}")
    return etu_num, nom, prenom

def verify_pin(pin_str):
    """Vérifie le PIN."""
    conn = get_card_connection()
    if not conn:
        return False, "Erreur de connexion à la carte"

    if len(pin_str) != 4 or not pin_str.isdigit():
        return False, "PIN invalide (4 chiffres requis)"

    pin_bytes = [int(ch) & 0xFF for ch in pin_str]
    apdu = [0x82, 0x04, 0x00, 0x00, 0x04] + pin_bytes

    try:
        data, sw1, sw2 = conn.transmit(apdu)
        print(f"[DEBUG] verify_pin: sw1={hex(sw1)}, sw2={hex(sw2)}, data={data}")
        if sw1 == 0x90 and sw2 == 0x00:
            return True, "PIN correct"
        elif sw1 == 0x63:
            return False, f"PIN incorrect. Essais restants: {sw2 & 0x0F}"
        elif sw1 == 0x69 and sw2 == 0x83:
            return False, "PIN bloqué"
        elif sw1 == 0x6C:
            return False, f"Erreur de longueur (la carte attend {sw2} octets)"
        else:
            return False, "Erreur de vérification"
    except Exception as e:
        return False, f"Erreur: {e}"

def read_counter():
    """Lecture du compteur anti-rejoue."""
    conn = get_card_connection()
    if not conn:
        return None

    apdu = [0x82, 0x07, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn.transmit(apdu)
        print(f"[DEBUG] read_counter: data={data}, sw1={hex(sw1)}, sw2={hex(sw2)}")
        if sw1 != 0x90 or sw2 != 0x00 or not data or len(data) < 2:
            return None
        return int(data[0]) | (int(data[1]) << 8)
    except Exception as e:
        print(f"[DEBUG] read_counter exception: {e}")
        return None

def _read_sold_core():
    """Lecture du solde (en cents)."""
    conn = get_card_connection()
    if not conn:
        return None

    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn.transmit(apdu)
        print(f"[DEBUG] _read_sold_core: data={data}, sw1={hex(sw1)}, sw2={hex(sw2)}")
        if sw1 != 0x90 or sw2 != 0x00:
            return None
        if not data or len(data) < 2:
            return None
        return int(data[0]) | (int(data[1]) << 8)
    except Exception as e:
        print(f"[DEBUG] _read_sold_core exception: {e}")
        return None

def credit_card_amount(euros_amount, pin_str):
    """Crédite la carte."""
    conn = get_card_connection()
    if not conn:
        return False, "Erreur de connexion à la carte"

    ok, msg = verify_pin(pin_str)
    if not ok:
        return False, msg

    ctr = read_counter()
    if ctr is None:
        return False, "Compteur indisponible"

    if isinstance(euros_amount, Decimal):
        cents = int((euros_amount * 100).to_integral_value())
    else:
        cents = int(round(float(euros_amount) * 100))

    if cents <= 0:
        return False, "Montant invalide"

    montant_lsb = cents & 0xFF
    montant_msb = (cents >> 8) & 0xFF
    p1 = ctr & 0xFF
    p2 = (ctr >> 8) & 0xFF

    apdu = [0x82, 0x02, p1, p2, 0x02, montant_lsb, montant_msb]
    print(f"[DEBUG] credit_card_amount: APDU={apdu}, cents={cents}")

    try:
        data, sw1, sw2 = conn.transmit(apdu)
        print(f"[DEBUG] credit_card_amount: data={data}, sw1={hex(sw1)}, sw2={hex(sw2)}")
        if sw1 == 0x90 and sw2 == 0x00:
            return True, f"Crédit effectué: {cents/100.0:.2f} €"
        elif sw1 == 0x61 and sw2 == 0x00:
            return False, "Capacité maximale dépassée"
        elif sw1 == 0x69 and sw2 == 0x82:
            return False, "Statut de sécurité non satisfait"
        elif sw1 == 0x69 and sw2 == 0x84:
            return False, "Erreur anti-rejoue"
        elif sw1 == 0x6C:
            return False, f"Erreur de longueur (la carte attend {sw2} octets)"
        else:
            return False, "Erreur lors du crédit"
    except Exception as e:
        return False, f"Erreur: {e}"

# =========================
#  FONCTIONS BDD
# =========================

def get_bonus_disponible(etu_num):
    """Retourne le total des bonus non transférés."""
    cnx = get_db_connection()
    if not cnx:
        return None

    sql = """
        SELECT COALESCE(SUM(Montant), 0)
        FROM Transactions
        WHERE Num_Etudiant = %s
          AND Type = 'CREDIT'
          AND Commentaire LIKE 'Bonus%%'
          AND Commentaire NOT LIKE '%%transféré%%'
    """
    try:
        cursor = cnx.cursor()
        print(f"[DEBUG] get_bonus_disponible: etu_num={repr(etu_num)}")
        cursor.execute(sql, (etu_num,))
        row = cursor.fetchone()
        cursor.close()
        cnx.close()

        if row is None or row[0] is None:
            return Decimal("0.00")
        montant = Decimal(str(row[0]))
        print(f"[DEBUG] get_bonus_disponible: montant={montant}")
        return montant
    except Exception as e:
        print(f"Erreur get_bonus_disponible: {e}")
        if cnx:
            cnx.close()
        return None

def marquer_bonus_transfere(etu_num):
    """Marque les bonus comme transférés."""
    cnx = get_db_connection()
    if not cnx:
        return 0

    sql = """
        UPDATE Transactions
        SET Commentaire = CONCAT(Commentaire, ' (transféré)')
        WHERE Num_Etudiant = %s
          AND Type = 'CREDIT'
          AND Commentaire LIKE 'Bonus%%'
          AND Commentaire NOT LIKE '%%transféré%%'
    """
    try:
        cursor = cnx.cursor()
        print(f"[DEBUG] marquer_bonus_transfere: etu_num={repr(etu_num)}")
        cursor.execute(sql, (etu_num,))
        cnx.commit()
        nb = cursor.rowcount
        cursor.close()
        cnx.close()
        print(f"[DEBUG] marquer_bonus_transfere: nb={nb}")
        return nb
    except Exception as e:
        print(f"Erreur marquer_bonus_transfere: {e}")
        if cnx:
            cnx.close()
        return 0

def crediter_compte_bdd(etu_num, montant):
    """Crédite le compte en BDD via la procédure stockée CrediterCompte."""
    print(f"[DEBUG] crediter_compte_bdd: etu_num={repr(etu_num)}, montant={montant}")
    cnx = get_db_connection()
    if not cnx:
        print("[DEBUG] crediter_compte_bdd: connexion BDD impossible")
        return False

    try:
        cursor = cnx.cursor()
        cursor.callproc("CrediterCompte", [etu_num, float(montant), "Recharge CB Berlicum"])
        cnx.commit()
        cursor.close()
        cnx.close()
        print("[DEBUG] crediter_compte_bdd: OK (procédure exécutée)")
        return True
    except mysql.connector.Error as e:
        print(f"Erreur BDD crediter_compte_bdd: {e}")
        if cnx:
            try:
                cnx.close()
            except:
                pass
        return False

# =========================
#  TEMPLATE HTML
# =========================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Borne de recharge - Berlicum</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{
            font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
            background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
            min-height:100vh;display:flex;justify-content:center;align-items:center;
            padding:20px;position:relative;overflow:hidden;
        }
        .background-animation{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;}
        .floating-shape{position:absolute;opacity:0.1;animation:float 20s infinite ease-in-out;}
        .circle{border-radius:50%;background:white;}
        .square{background:white;transform:rotate(45deg);}
        @keyframes float{
            0%,100%{transform:translateY(0) translateX(0) rotate(0deg);}
            25%{transform:translateY(-30px) translateX(20px) rotate(90deg);}
            50%{transform:translateY(-60px) translateX(-20px) rotate(180deg);}
            75%{transform:translateY(-30px) translateX(-40px) rotate(270deg);}
        }
        @keyframes pulse{
            0%,100%{transform:scale(1);opacity:0.1;}
            50%{transform:scale(1.1);opacity:0.15;}
        }
        @keyframes slide{
            0%{transform:translateX(-100px);}
            100%{transform:translateX(calc(100vw + 100px));}
        }
        @keyframes cardInsert{
            0%   {transform:translateX(-200px) rotate(-10deg);opacity:0;}
            50%  {transform:translateX(0) rotate(0deg);opacity:1;}
            70%  {transform:scale(1.1);}
            100% {transform:scale(1);opacity:1;}
        }

        .container{
            background:white;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);
            max-width:500px;width:100%;padding:40px;position:relative;z-index:1;
        }
        .logo-container{text-align:center;margin-bottom:20px;}
        .logo-container img{max-width:200px;height:auto;}
        h1{color:#667eea;text-align:center;margin-bottom:10px;font-size:28px;}
        .subtitle{text-align:center;color:#666;margin-bottom:30px;font-size:14px;}

        .welcome-screen{text-align:center;padding:40px 20px;display:none;}
        .welcome-screen.active{display:block;}
        .insert-card-prompt{color:#667eea;font-size:18px;margin-bottom:30px;animation:pulse-text 2s ease infinite;}
        @keyframes pulse-text{0%,100%{opacity:1;}50%{opacity:0.5;}}
        .student-name{color:#333;font-size:24px;font-weight:600;margin-bottom:30px;}
        .card-animation{margin:40px auto;}
        .card-animation.waiting{animation:cardWaiting 2s ease infinite;}
        @keyframes cardWaiting{
            0%,100%{transform:translateX(-50px) rotate(-5deg);opacity:0.7;}
            50%{transform:translateX(-30px) rotate(-3deg);opacity:1;}
        }
        .card-icon{
            width:120px;height:80px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
            border-radius:10px;margin:0 auto;position:relative;box-shadow:0 10px 30px rgba(102,126,234,0.3);
            display:flex;align-items:center;justify-content:center;color:white;font-size:40px;
        }
        .card-chip{
            width:30px;height:25px;background:linear-gradient(135deg,#ffd700,#ffed4e);
            border-radius:4px;position:absolute;top:15px;left:15px;
        }
        .loading-dots{margin-top:20px;}
        .loading-dots span{
            display:inline-block;width:8px;height:8px;background:#667eea;
            border-radius:50%;margin:0 4px;animation:bounce 1.4s infinite ease-in-out both;
        }
        .loading-dots span:nth-child(1){animation-delay:-0.32s;}
        .loading-dots span:nth-child(2){animation-delay:-0.16s;}
        @keyframes bounce{
            0%,80%,100%{transform:scale(0);}
            40%{transform:scale(1);}
        }

        .menu-container{display:none;}
        .menu-container.active{display:block;}
        .main-menu{display:none;}
        .main-menu.active{display:block;}

        .menu{list-style:none;}
        .menu li{margin:12px 0;}
        .menu button{
            width:100%;padding:15px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
            color:white;border:none;border-radius:10px;font-size:16px;cursor:pointer;
            transition:transform 0.2s,box-shadow 0.2s;
        }
        .menu button:hover{
            transform:translateY(-2px);box-shadow:0 10px 20px rgba(102,126,234,0.3);
        }

        .info-display-card{
            background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
            color:white;padding:25px;border-radius:15px;margin-top:20px;
            box-shadow:0 10px 30px rgba(102,126,234,0.3);
        }
        .info-item{
            background:rgba(255,255,255,0.2);padding:12px;border-radius:8px;
            margin:10px 0;backdrop-filter:blur(10px);
        }
        .info-item strong{display:block;font-size:12px;opacity:0.9;margin-bottom:5px;}
        .info-item span{font-size:18px;font-weight:600;}

        .result{
            margin-top:20px;padding:15px;border-radius:10px;display:none;
        }
        .result.success{background:#d4edda;border:1px solid #c3e6cb;color:#155724;}
        .result.error{background:#f8d7da;border:1px solid #f5c6cb;color:#721c24;}
        .result.info{background:#d1ecf1;border:1px solid #bee5eb;color:#0c5460;}

        .payment-logos,
        .partner-logos{
            text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #e0e0e0;
        }
        /* Texte gris comme avant */
        .payment-logos p,
        .partner-logos p{
            font-size:12px;
            color:#999;
            margin-bottom:15px;
        }
        .payment-logos-container,
        .partner-logos-container{
            display:flex;justify-content:center;align-items:center;gap:20px;flex-wrap:wrap;
        }
        .payment-logos img{height:30px;opacity:0.7;transition:opacity 0.3s;}
        .payment-logos img:hover{opacity:1;}
        .partner-logos img{height:40px;opacity:0.8;transition:opacity 0.3s;}
        .partner-logos img:hover{opacity:1;}

        .modal{
            display:none;position:fixed;top:0;left:0;width:100%;height:100%;
            background:rgba(0,0,0,0.5);justify-content:center;align-items:center;z-index:1000;
        }
        .modal.active{display:flex;}
        .modal-content{
            background:white;padding:30px;border-radius:15px;max-width:400px;width:90%;
        }
        .modal h2{color:#667eea;margin-bottom:20px;font-size:22px;}
        .form-group{margin:15px 0;}
        .form-group label{display:block;margin-bottom:5px;color:#333;font-weight:500;}
        .form-group input{
            width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:8px;font-size:16px;
        }
        .form-group input:focus{outline:none;border-color:#667eea;}
        .modal-buttons{display:flex;gap:10px;margin-top:20px;}
        .modal-buttons button{
            flex:1;padding:12px;border:none;border-radius:8px;font-size:16px;cursor:pointer;
        }
        .btn-primary{
            background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;
        }
        .btn-secondary{background:#e0e0e0;color:#333;}
    </style>
</head>
<body>
    <div class="background-animation">
        <div class="floating-shape circle" style="width:80px;height:80px;top:10%;left:10%;animation-duration:15s;"></div>
        <div class="floating-shape circle" style="width:60px;height:60px;top:20%;right:15%;animation-duration:20s;animation-delay:-5s;"></div>
        <div class="floating-shape square" style="width:70px;height:70px;bottom:15%;left:20%;animation-duration:18s;animation-delay:-10s;"></div>
        <div class="floating-shape circle" style="width:100px;height:100px;top:60%;right:10%;animation-duration:22s;animation-delay:-7s;"></div>
        <div class="floating-shape square" style="width:50px;height:50px;top:40%;left:5%;animation-duration:16s;animation-delay:-12s;"></div>
        <div class="floating-shape circle" style="width:90px;height:90px;bottom:25%;right:25%;animation-duration:19s;animation-delay:-3s;"></div>
        <div class="floating-shape circle" style="width:120px;height:120px;top:15%;left:50%;animation-name:pulse;animation-duration:8s;"></div>
        <div class="floating-shape square" style="width:80px;height:80px;bottom:20%;left:45%;animation-name:pulse;animation-duration:10s;animation-delay:-4s;"></div>
        <div class="floating-shape circle" style="width:30px;height:30px;top:30%;animation-name:slide;animation-duration:25s;animation-iteration-count:infinite;"></div>
        <div class="floating-shape circle" style="width:40px;height:40px;top:70%;animation-name:slide;animation-duration:30s;animation-iteration-count:infinite;animation-delay:-10s;"></div>
        <div class="floating-shape square" style="width:35px;height:35px;top:50%;animation-name:slide;animation-duration:28s;animation-iteration-count:infinite;animation-delay:-15s;"></div>
    </div>

    <div class="container">
        <div class="logo-container">
            <img src="https://www.uvsq.fr/medias/photo/iut-velizy-villacoublay-logo-2020-ecran_1580904185110-jpg?ID_FICHE=214049" alt="IUT de Vélizy-Villacoublay">
        </div>

        <!-- Écran de bienvenue -->
        <div id="welcomeScreen" class="welcome-screen active">
            <h2 id="welcomeTitle">Veuillez insérer votre carte</h2>
            <div class="insert-card-prompt" id="insertPrompt">👇 Insérez votre carte étudiante</div>
            <div class="student-name" id="studentName" style="display:none;"></div>
            <div class="card-animation waiting" id="cardAnimation">
                <div class="card-icon">
                    <div class="card-chip"></div>
                    💳
                </div>
            </div>
            <div class="loading-dots" id="loadingDots" style="display:none;">
                <span></span><span></span><span></span>
            </div>
        </div>

        <!-- Menu principal -->
        <div id="menuContainer" class="menu-container">
            <h1>🏦 Borne de recharge</h1>
            <p class="subtitle">Berlicum</p>

            <div id="mainMenu" class="main-menu">
                <ul class="menu">
                    <li><button onclick="toggleInfos()">👤 Vos informations</button></li>
                    <li><button onclick="consulterBonus()">🎁 Consulter mes bonus</button></li>
                    <li><button onclick="transfererBonus()">💳 Transférer mes bonus sur ma carte</button></li>
                    <li><button onclick="consulterSolde()">💰 Consulter le crédit sur ma carte</button></li>
                    <li><button onclick="rechargerCB()">💵 Recharger avec ma carte bancaire</button></li>
                </ul>

                <div id="infoPanel" class="info-display-card" style="display:none;">
                    <h3>👤 Vos informations</h3>
                    <div class="info-item">
                        <strong>NUMÉRO ÉTUDIANT</strong>
                        <span id="displayNumEtu">-</span>
                    </div>
                    <div class="info-item">
                        <strong>NOM</strong>
                        <span id="displayNom">-</span>
                    </div>
                    <div class="info-item">
                        <strong>PRÉNOM</strong>
                        <span id="displayPrenom">-</span>
                    </div>
                </div>

                <div id="result" class="result"></div>
            </div>
        </div>

        <div class="payment-logos">
            <p>Moyens de paiement acceptés</p>
            <div class="payment-logos-container">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Visa_Inc._logo.svg/1599px-Visa_Inc._logo.svg.png" alt="Visa">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Mastercard-logo.svg/1544px-Mastercard-logo.svg.png" alt="Mastercard">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/langfr-2560px-American_Express_logo_%282018%29.svg.png" alt="American Express">
                <img src="https://upload.wikimedia.org/wikipedia/commons/d/d2/Izly_by_Crous.png" alt="Izly">
            </div>
        </div>

        <div class="partner-logos">
            <p>En partenariat avec</p>
            <div class="partner-logos-container">
                <img src="https://www.uvsq.fr/medias/photo/logo-crous-versailles_1693915638161-png?ID_FICHE=281601" alt="CROUS Versailles">
            </div>
        </div>
    </div>

    <!-- Modal PIN -->
    <div id="pinModal" class="modal">
        <div class="modal-content">
            <h2>Vérification PIN</h2>
            <div class="form-group">
                <label for="pinInput">Code PIN (4 chiffres)</label>
                <input type="password" id="pinInput" maxlength="4" pattern="[0-9]{4}" placeholder="****">
            </div>
            <div class="modal-buttons">
                <button class="btn-secondary" onclick="closeModal()">Annuler</button>
                <button class="btn-primary" onclick="submitPin()">Valider</button>
            </div>
        </div>
    </div>

    <!-- Modal Montant -->
    <div id="montantModal" class="modal">
        <div class="modal-content">
            <h2>Montant à recharger</h2>
            <div class="form-group">
                <label for="montantInput">Montant (en euros)</label>
                <input type="number" id="montantInput" step="0.01" min="0.01" placeholder="5.00">
            </div>
            <div class="modal-buttons">
                <button class="btn-secondary" onclick="closeModal()">Annuler</button>
                <button class="btn-primary" onclick="submitMontant()">Valider</button>
            </div>
        </div>
    </div>

    <script>
        let currentAction = null;
        let currentData = {};
        let cardPresent = false;
        let studentData = {};

        window.addEventListener('load', () => {
            pollCard();
        });

        async function pollCard() {
            while (true) {
                try {
                    const response = await fetch('/api/infos');
                    const data = await response.json();

                    if (data.success) {
                        if (!cardPresent) {
                            cardPresent = true;
                            handleCardInserted(data);
                        }
                    } else {
                        if (cardPresent) {
                            // Carte retirée => retour écran d'accueil
                            location.reload();
                            return;
                        }
                    }
                } catch (e) {
                    console.log('Erreur pollCard', e);
                    if (cardPresent) {
                        location.reload();
                        return;
                    }
                }

                await new Promise(r => setTimeout(r, 2000));
            }
        }

        function handleCardInserted(data) {
            const welcomeScreen = document.getElementById('welcomeScreen');
            const menuContainer = document.getElementById('menuContainer');
            const welcomeTitle = document.getElementById('welcomeTitle');
            const insertPrompt = document.getElementById('insertPrompt');
            const studentName = document.getElementById('studentName');
            const cardAnimation = document.getElementById('cardAnimation');
            const loadingDots = document.getElementById('loadingDots');
            const mainMenu = document.getElementById('mainMenu');

            studentData = data;

            insertPrompt.style.display = 'none';
            cardAnimation.classList.remove('waiting');
            cardAnimation.style.animation = 'cardInsert 2s ease both';

            welcomeTitle.textContent = 'Bonjour';
            studentName.textContent = `${data.prenom} ${data.nom}`;
            studentName.style.display = 'block';
            loadingDots.style.display = 'block';

            setTimeout(() => {
                welcomeScreen.classList.remove('active');
                menuContainer.classList.add('active');
                mainMenu.classList.add('active');

                document.getElementById('displayNumEtu').textContent = data.num_etudiant;
                document.getElementById('displayNom').textContent = data.nom;
                document.getElementById('displayPrenom').textContent = data.prenom;
            }, 3500);
        }

        function toggleInfos() {
            const panel = document.getElementById('infoPanel');
            panel.style.display = (panel.style.display === 'none' || panel.style.display === '') ? 'block' : 'none';
        }

        function showResult(message, type) {
            const result = document.getElementById('result');
            result.textContent = message;
            result.className = 'result ' + type;
            result.style.display = 'block';
            setTimeout(() => {
                result.style.display = 'none';
            }, 5000);
        }

        function showModal(modalId) {
            document.getElementById(modalId).classList.add('active');
        }

        function closeModal() {
            document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
        }

        async function consulterBonus() {
            showResult('Consultation des bonus...', 'info');
            try {
                const response = await fetch('/api/bonus');
                const data = await response.json();
                if (data.success) {
                    showResult(`Bonus disponibles: ${data.montant} €`, 'info');
                } else {
                    showResult(data.message, 'error');
                }
            } catch (error) {
                showResult('Erreur de communication', 'error');
            }
        }

        function transfererBonus() {
            currentAction = 'transfert';
            showModal('pinModal');
        }

        function consulterSolde() {
            currentAction = 'solde';
            showModal('pinModal');
        }

        function rechargerCB() {
            currentAction = 'recharge';
            showModal('montantModal');
        }

        async function submitPin() {
            const pin = document.getElementById('pinInput').value;

            if (pin.length !== 4 || !/^\\d{4}$/.test(pin)) {
                showResult('PIN invalide (4 chiffres requis)', 'error');
                return;
            }

            closeModal();
            document.getElementById('pinInput').value = '';

            if (currentAction === 'transfert') {
                showResult('Transfert en cours...', 'info');
                try {
                    const response = await fetch('/api/transfert_bonus', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({pin: pin})
                    });
                    const data = await response.json();
                    showResult(data.message, data.success ? 'success' : 'error');
                } catch (error) {
                    showResult('Erreur de communication', 'error');
                }
                currentAction = null;

            } else if (currentAction === 'solde') {
                showResult('Lecture du solde...', 'info');
                try {
                    const response = await fetch('/api/solde', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({pin: pin})
                    });
                    const data = await response.json();
                    if (data.success) {
                        // Sécurisation / formatage du solde
                        let texteSolde;
                        if (typeof data.solde === 'string') {
                            const v = parseFloat(data.solde.replace(',', '.'));
                            if (!isNaN(v)) {
                                texteSolde = v.toFixed(2) + ' €';
                            } else {
                                texteSolde = data.solde + ' €';
                            }
                        } else if (typeof data.solde === 'number') {
                            texteSolde = data.solde.toFixed(2) + ' €';
                        } else {
                            texteSolde = 'inconnu';
                        }
                        showResult(`Solde disponible: ${texteSolde}`, 'success');
                    } else {
                        showResult(data.message, 'error');
                    }
                } catch (error) {
                    showResult('Erreur de communication', 'error');
                }
                currentAction = null;

            } else if (currentAction === 'recharge_confirm' && currentData.montant) {
                showResult('Recharge en cours...', 'info');
                try {
                    const response = await fetch('/api/recharge', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            montant: currentData.montant,
                            pin: pin
                        })
                    });
                    const data = await response.json();
                    showResult(data.message, data.success ? 'success' : 'error');
                    currentData = {};
                    currentAction = null;
                } catch (error) {
                    showResult('Erreur de communication', 'error');
                }
            }
        }

        async function submitMontant() {
            const montant = document.getElementById('montantInput').value;
            if (!montant || parseFloat(montant) <= 0) {
                showResult('Montant invalide', 'error');
                return;
            }

            currentData.montant = montant;
            closeModal();
            document.getElementById('montantInput').value = '';
            currentAction = 'recharge_confirm';
            showModal('pinModal');
        }

        document.getElementById('pinInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') submitPin();
        });

        document.getElementById('montantInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') submitMontant();
        });
    </script>
</body>
</html>
"""

# =========================
#  ROUTES FLASK
# =========================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/infos')
def api_infos():
    etu_num, nom, prenom = get_student_info_from_card()
    print(f"[DEBUG] /api/infos: etu_num={repr(etu_num)}, nom={repr(nom)}, prenom={repr(prenom)}")
    if etu_num is None:
        return jsonify({'success': False, 'message': 'Erreur lecture carte'})
    return jsonify({
        'success': True,
        'num_etudiant': etu_num,
        'nom': nom,
        'prenom': prenom
    })

@app.route('/api/bonus')
def api_bonus():
    etu_num, _, _ = get_student_info_from_card()
    print(f"[DEBUG] /api/bonus: etu_num={repr(etu_num)}")
    if etu_num is None:
        return jsonify({'success': False, 'message': 'Erreur lecture carte'})

    montant = get_bonus_disponible(etu_num)
    if montant is None:
        return jsonify({'success': False, 'message': 'Erreur BDD'})

    return jsonify({
        'success': True,
        'montant': f"{montant:.2f}"
    })

@app.route('/api/solde', methods=['POST'])
def api_solde():
    data = request.json
    pin = data.get('pin')

    if not pin:
        return jsonify({'success': False, 'message': 'PIN requis'})

    ok, msg = verify_pin(pin)
    if not ok:
        return jsonify({'success': False, 'message': msg})

    cents = _read_sold_core()
    if cents is None:
        return jsonify({'success': False, 'message': 'Erreur lecture solde'})

    return jsonify({
        'success': True,
        'solde': f"{cents/100.0:.2f}"
    })

@app.route('/api/transfert_bonus', methods=['POST'])
def api_transfert_bonus():
    data = request.json
    pin = data.get('pin')

    if not pin:
        return jsonify({'success': False, 'message': 'PIN requis'})

    etu_num, _, _ = get_student_info_from_card()
    print(f"[DEBUG] /api/transfert_bonus: etu_num={repr(etu_num)}")
    if etu_num is None:
        return jsonify({'success': False, 'message': 'Erreur lecture carte'})

    montant = get_bonus_disponible(etu_num)
    if montant is None:
        return jsonify({'success': False, 'message': 'Erreur BDD'})

    if montant <= 0:
        return jsonify({'success': False, 'message': 'Aucun bonus disponible'})

    ok, msg = credit_card_amount(montant, pin)
    if not ok:
        return jsonify({'success': False, 'message': msg})

    nb = marquer_bonus_transfere(etu_num)
    return jsonify({
        'success': True,
        'message': f"Transfert réussi: {montant:.2f} € ({nb} bonus transférés)"
    })

@app.route('/api/recharge', methods=['POST'])
def api_recharge():
    data = request.json
    montant_str = data.get('montant')
    pin = data.get('pin')

    if not pin:
        return jsonify({'success': False, 'message': 'PIN requis'})

    if not montant_str:
        return jsonify({'success': False, 'message': 'Montant requis'})

    try:
        montant = Decimal(montant_str)
        if montant <= 0:
            return jsonify({'success': False, 'message': 'Montant invalide'})
    except Exception:
        return jsonify({'success': False, 'message': 'Montant invalide'})

    etu_num, _, _ = get_student_info_from_card()
    print(f"[DEBUG] /api/recharge: etu_num={repr(etu_num)}, montant={montant}")
    if etu_num is None:
        return jsonify({'success': False, 'message': 'Erreur lecture carte'})

    ok, msg = credit_card_amount(montant, pin)
    if not ok:
        return jsonify({'success': False, 'message': msg})

    ok_bdd = crediter_compte_bdd(etu_num, montant)
    if not ok_bdd:
        return jsonify({
            'success': True,
            'message': f"Carte créditée ({montant:.2f} €) mais erreur BDD. Contactez l'administrateur."
        })

    return jsonify({
        'success': True,
        'message': f"Recharge réussie: {montant:.2f} €"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
