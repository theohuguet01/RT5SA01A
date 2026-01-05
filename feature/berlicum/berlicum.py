#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp

import mysql.connector
from decimal import Decimal

# =========================
#  CONFIG BDD
# =========================

DB_CONFIG = {
    "host": "172.20.10.3",
    "port": 3306,
    "user": "rodelika",
    "password": "rodelika",
    "database": "carote_electronique",
}

cnx = None          # connexion MySQL
conn_reader = None  # connexion lecteur de carte


# =========================
#  INIT SMARTCARD / BDD
# =========================

def init_smart_card():
    """Initialise la connexion au premier lecteur de carte disponible."""
    try:
        lst_readers = scardsys.readers()
    except scardexcp.Exceptions as e:
        print("Erreur lecteurs :", e)
        return

    if len(lst_readers) < 1:
        print(" Pas de lecteur de carte connecté !")
        exit(1)

    try:
        global conn_reader
        conn_reader = lst_readers[0].createConnection()
        conn_reader.connect()
        print("ATR : ", scardutil.toHexString(conn_reader.getATR()))
    except scardexcp.NoCardException as e:
        print(" Pas de carte dans le lecteur : ", e)
        exit(1)


def init_db():
    """Initialise la connexion MySQL."""
    global cnx
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print("Erreur de connexion MySQL :", err)
        exit(1)


# =========================
#  UI
# =========================

def print_hello_message():
    print("---------------------------------------------")
    print("-- Borne de recharge : Berlicum            --")
    print("---------------------------------------------")


def print_menu():
    print(" 1 - Afficher mes informations")
    print(" 2 - Consulter mes bonus")
    print(" 3 - Transférer mes bonus sur ma carte")
    print(" 4 - Consulter le crédit disponible sur ma carte")
    print(" 5 - Recharger avec ma carte bancaire")
    print(" 6 - Quitter")


# =========================
#  FONCTIONS CARTE
# =========================

def print_version():
    """Lecture de la version de la carte (comme Lubiana)."""
    apdu = [0x81, 0x00, 0x00, 0x00, 0x04]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.Exceptions as e:
        print("Error", e)
        return

    # si taille incorrecte, la carte renvoie 6C xx
    if sw1 == 0x6C:
        apdu[4] = sw2
        try:
            data, sw1, sw2 = conn_reader.transmit(apdu)
        except scardexcp.Exceptions as e:
            print("Error", e)
            return

    if sw1 != 0x90 or sw2 != 0x00:
        print(
            "sw1 : 0x%02X | sw2 : 0x%02X | version : erreur de lecture version"
            % (sw1, sw2)
        )
        return

    s = "".join(chr(e) for e in data)
    print("sw1 : 0x%02X | sw2 : 0x%02X | version %s" % (sw1, sw2, s))


def _read_perso_raw():
    """
    Lecture des données perso brutes (sans affichage).
    Retourne la chaîne "num;nom;prenom" ou None.
    """
    apdu = [0x81, 0x02, 0x00, 0x00, 0x05]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("Erreur lecture perso :", e)
        return None

    if sw1 == 0x6C:
        apdu[4] = sw2
        try:
            data, sw1, sw2 = conn_reader.transmit(apdu)
        except scardexcp.CardConnectionException as e:
            print("Erreur lecture perso :", e)
            return None

    if sw1 != 0x90 or sw2 != 0x00:
        print("sw1 : 0x%02X | sw2 : 0x%02X | Erreur lecture données" % (sw1, sw2))
        return None

    if data and len(data) > 1:
        perso_bytes = data[1:]
    else:
        perso_bytes = []

    if not perso_bytes:
        return ""

    return "".join(chr(e) for e in perso_bytes)


def print_data():
    """Affiche les données perso de la carte (debug)."""
    perso = _read_perso_raw()
    if perso is None:
        return
    if perso == "":
        print("Carte non attribuée (aucune donnée).")
    else:
        print("Données perso :", perso)


def get_student_number_from_card():
    """
    Récupère le Num_Etudiant à partir de la perso.
    Format attendu : 'num;nom;prenom'
    Retourne une chaîne CHAR(8) (zéro-pad, ex: '00000001') ou None.
    """
    perso = _read_perso_raw()
    if perso is None:
        return None
    if perso == "":
        print("Erreur : carte non attribuée (pas de perso).")
        return None

    parts = perso.split(";")
    if len(parts) < 1:
        print("Erreur : format perso inattendu :", perso)
        return None

    raw_num = parts[0].strip()
    if not raw_num.isdigit():
        print("Erreur : numéro étudiant invalide dans la perso :", raw_num)
        return None

    etu_num = raw_num.zfill(8)
    return etu_num


def get_student_info_from_card():
    """
    Retourne (Num_Etudiant CHAR(8), Nom, Prenom) à partir de la carte,
    ou (None, None, None) en cas d’erreur.
    """
    perso = _read_perso_raw()
    if perso is None or perso == "":
        print("Erreur : carte non attribuée ou perso illisible.")
        return None, None, None

    parts = perso.split(";")
    if len(parts) < 3:
        print("Erreur : format perso inattendu :", perso)
        return None, None, None

    raw_num = parts[0].strip()
    nom = parts[1].strip()
    prenom = parts[2].strip()

    if not raw_num.isdigit():
        print("Erreur : numéro étudiant invalide dans la perso :", raw_num)
        return None, None, None

    etu_num = raw_num.zfill(8)
    return etu_num, nom, prenom


def _ask_pin_octets(message):
    """
    Demande un PIN sur 4 chiffres collés, ex: 1234
    Renvoie une liste de 4 entiers [b0, b1, b2, b3].
    """
    while True:
        raw = input(message + " (4 chiffres, ex: 1234) : ").strip()
        if len(raw) != 4 or not raw.isdigit():
            print("Veuillez entrer exactement 4 chiffres (ex: 1234).")
            continue
        return [int(ch) & 0xFF for ch in raw]


def verify_pin_interactive():
    """
    Vérifie le PIN auprès de la carte.
    APDU : 82 04 00 00 04 [PIN(4 octets)]
    """
    pin_bytes = _ask_pin_octets("PIN")
    apdu = [0x82, 0x04, 0x00, 0x00, 0x04] + pin_bytes

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return False

    if sw1 == 0x90 and sw2 == 0x00:
        print("PIN correct, authentification réussie.")
        return True
    elif sw1 == 0x63:
        print("PIN incorrect. Essais restants : %d" % sw2)
        return False
    elif sw1 == 0x69 and sw2 == 0x83:
        print("PIN bloqué (plus d'essais).")
        return False
    elif sw1 == 0x6C:
        print("Erreur de longueur (la carte attend %d octets)." % sw2)
        return False
    else:
        print("Erreur lors de la vérification du PIN.")
        return False


def read_counter():
    """
    Lecture du compteur anti-rejoue.
    APDU : 82 07 00 00 02
    Renvoie le compteur (int) ou None.
    """
    apdu = [0x82, 0x07, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("Compteur - sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return None

    if sw1 != 0x90 or sw2 != 0x00 or not data or len(data) < 2:
        print("Erreur lors de la lecture du compteur.")
        return None

    ctr = int(data[0]) | (int(data[1]) << 8)
    print("Compteur actuel : %d" % ctr)
    return ctr


def _read_sold_core():
    """
    Lecture bas niveau du solde, en supposant PIN déjà vérifié.
    APDU : 82 01 00 00 02
    Retourne le solde en centimes (int) ou None.
    """
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("Lecture solde - sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return None

    if sw1 != 0x90 or sw2 != 0x00:
        if sw1 == 0x69 and sw2 == 0x82:
            print("PIN non vérifié (security status not satisfied).")
        else:
            print("Erreur lors de la lecture du solde.")
        return None

    if not data or len(data) < 2:
        print("Données de solde invalides ou manquantes.")
        return None

    cents = int(data[0]) | (int(data[1]) << 8)
    return cents


def read_sold():
    """Consultation du solde de la carte (avec vérif PIN)."""
    print("=== Consultation du solde carte ===")
    if not verify_pin_interactive():
        print("Impossible de lire le solde : PIN non vérifié.")
        return

    cents = _read_sold_core()
    if cents is None:
        return

    euros = cents / 100.0
    print("Solde disponible sur la carte : %.2f €" % euros)


def credit_card_amount(euros_amount):
    """
    Crédite la carte du montant 'euros_amount' (Decimal ou float).
    - Vérifie le PIN
    - Lit le compteur
    - APDU 82 02 P1 P2 02 [montant_LSB][montant_MSB]
    """
    print("=== Crédit de la carte ===")

    # 1) Vérif PIN
    if not verify_pin_interactive():
        print("Impossible de créditer : PIN non vérifié.")
        return False

    # 2) Lecture compteur anti-rejoue
    ctr = read_counter()
    if ctr is None:
        print("Impossible de créditer : compteur indisponible.")
        return False

    # 3) Conversion du montant en centimes
    if isinstance(euros_amount, Decimal):
        cents = int((euros_amount * 100).to_integral_value())
    else:
        cents = int(round(float(euros_amount) * 100))

    if cents <= 0:
        print("Montant à créditer nul ou négatif, rien à faire.")
        return False

    montant_lsb = cents & 0xFF
    montant_msb = (cents >> 8) & 0xFF

    p1 = ctr & 0xFF
    p2 = (ctr >> 8) & 0xFF

    apdu = [0x82, 0x02, p1, p2, 0x02, montant_lsb, montant_msb]

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("Crédit - sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return False

    if sw1 == 0x90 and sw2 == 0x00:
        print("Crédit effectué : %.2f €" % (cents / 100.0))
        return True
    elif sw1 == 0x61 and sw2 == 0x00:
        print("Capacité maximale de rechargement dépassée.")
    elif sw1 == 0x69 and sw2 == 0x82:
        print("Statut de sécurité non satisfait (PIN non vérifié côté carte).")
    elif sw1 == 0x69 and sw2 == 0x84:
        print("Erreur anti-rejoue (compteur invalide).")
    elif sw1 == 0x6C:
        print("Erreur de longueur (la carte attend %d octets)." % sw2)
    else:
        print("Erreur lors du crédit.")
    return False


# =========================
#  FONCTIONS BDD (Transactions)
# =========================

def get_bonus_disponible(etu_num):
    """
    Retourne le total des bonus non transférés pour l’étudiant (Num_Etudiant CHAR(8)).
    On utilise la table Transactions :

      - Type = 'CREDIT'
      - Commentaire commence par 'Bonus'
      - Commentaire ne contient pas encore 'transféré'
    """
    sql = """
        SELECT COALESCE(SUM(Montant), 0)
        FROM Transactions
        WHERE Num_Etudiant = %s
          AND Type = 'CREDIT'
          AND Commentaire LIKE 'Bonus%%'
          AND Commentaire NOT LIKE '%%transféré%%'
    """
    cursor = cnx.cursor()
    cursor.execute(sql, (etu_num,))
    row = cursor.fetchone()
    cursor.close()

    if row is None or row[0] is None:
        return Decimal("0.00")

    return Decimal(str(row[0]))


def marquer_bonus_transfere(etu_num):
    """
    Marque tous les bonus non transférés de cet étudiant comme 'transférés'
    en suffixant le commentaire.

    On reste dans la table Transactions (aucun changement de schéma).
    """
    sql = """
        UPDATE Transactions
        SET Commentaire = CONCAT(Commentaire, ' (transféré)')
        WHERE Num_Etudiant = %s
          AND Type = 'CREDIT'
          AND Commentaire LIKE 'Bonus%%'
          AND Commentaire NOT LIKE '%%transféré%%'
    """
    cursor = cnx.cursor()
    cursor.execute(sql, (etu_num,))
    cnx.commit()
    nb = cursor.rowcount
    cursor.close()
    return nb


def debiter_compte_recharge(etu_num, montant):
    """
    Crédite le compte en BDD (fonds propres) via la procédure CrediterCompte.
    Commentaire : 'Recharge CB Berlicum'.
    """
    try:
        cursor = cnx.cursor()
        cursor.callproc("CrediterCompte", [etu_num, float(montant), "Recharge CB Berlicum"])
        cnx.commit()
        cursor.close()
        print(f"Compte BDD crédité de {montant:.2f} € pour {etu_num}.")
        return True
    except mysql.connector.Error as e:
        print("ERREUR : la carte a été créditée, mais le crédit BDD a échoué :", e)
        return False


# =========================
#  LOGIQUE BERLICUM
# =========================

def consulter_et_transferer_bonus():
    """
    - Lit le numéro étudiant sur la carte
    - Calcule le total des bonus disponibles en BDD
      (Transactions.Type='CREDIT' & Commentaire 'Bonus...' pas encore 'transféré')
    - Affiche ce montant
    - Propose de le transférer sur la carte
    - Si OK : crédite la carte puis marque ces bonus comme transférés en BDD
    """
    print("=== Consultation / Transfert des bonus BDD -> carte ===")

    etu_num = get_student_number_from_card()
    if etu_num is None:
        return

    print(f"Numéro étudiant trouvé sur la carte : {etu_num}")

    montant_bonus = get_bonus_disponible(etu_num)
    if montant_bonus <= 0:
        print("Aucun bonus disponible en base pour cet étudiant.")
        return

    print("Bonus disponible en base pour cet étudiant : %.2f €" % montant_bonus)

    rep = input("Souhaitez-vous transférer ce montant sur la carte ? (o/n) : ").strip().lower()
    if rep not in ("o", "oui", "y", "yes"):
        print("Transfert annulé.")
        return

    # Créditer la carte
    if not credit_card_amount(montant_bonus):
        print("Transfert annulé suite à une erreur de crédit sur la carte.")
        return

    # Mise à jour BDD : marquer bonus comme transférés
    nb = marquer_bonus_transfere(etu_num)
    print(f"Bonus transférés en base de données (lignes mises à jour : {nb}).")


# =========================
#  NOUVELLES FONCTIONS MENU ÉTUDIANT
# =========================

def afficher_mes_informations():
    """Option 1 : affiche Num_Etudiant, Nom, Prénom à partir de la carte."""
    print("=== Mes informations ===")
    etu_num, nom, prenom = get_student_info_from_card()
    if etu_num is None:
        return
    print(f"Numéro étudiant : {etu_num}")
    print(f"Nom            : {nom}")
    print(f"Prénom         : {prenom}")


def consulter_mes_bonus():
    """Option 2 : affiche les bonus disponibles en BDD pour l'étudiant de la carte."""
    print("=== Mes bonus disponibles ===")
    etu_num = get_student_number_from_card()
    if etu_num is None:
        return
    montant = get_bonus_disponible(etu_num)
    print(f"Bonus disponibles pour {etu_num} : {montant:.2f} €")


def recharger_avec_cb():
    """
    Option 5 : Recharger la carte avec une 'carte bancaire'.
    Ici on simule juste la partie encaissement en demandant le montant.
    Logique :
      - lit Num_Etudiant sur la carte
      - demande un montant
      - crédite la carte (APDU)
      - crédite la BDD via CrediterCompte
    """
    print("=== Recharge par carte bancaire ===")
    etu_num = get_student_number_from_card()
    if etu_num is None:
        return

    print(f"Étudiant détecté : {etu_num}")
    montant_str = input("Montant à recharger (en euros, ex: 5.00) : ").replace(",", ".").strip()
    try:
        montant = Decimal(montant_str)
    except Exception:
        print("Montant invalide.")
        return

    if montant <= 0:
        print("Le montant doit être strictement positif.")
        return

    print(f"Vous allez recharger {montant:.2f} € sur la carte et le compte BDD.")
    confirm = input("Confirmer ? (o/n) : ").strip().lower()
    if confirm not in ("o", "oui", "y", "yes"):
        print("Recharge annulée.")
        return

    # 1) Créditer la carte
    if not credit_card_amount(montant):
        print("Recharge annulée suite à une erreur de crédit sur la carte.")
        return

    # 2) Créditer la BDD
    debiter_compte_recharge(etu_num, montant)


# =========================
#  MAIN LOOP
# =========================

def main():
    init_smart_card()
    init_db()
    print_hello_message()

    while True:
        print_menu()
        try:
            cmd = int(input("Choix : "))
        except ValueError:
            print("Veuillez saisir un nombre.")
            continue

        if cmd == 1:
            afficher_mes_informations()
        elif cmd == 2:
            consulter_mes_bonus()
        elif cmd == 3:
            consulter_et_transferer_bonus()
        elif cmd == 4:
            read_sold()
        elif cmd == 5:
            recharger_avec_cb()
        elif cmd == 6:
            print("Au revoir.")
            break
        else:
            print("Commande inconnue !")

        try:
            input("\nAppuyez sur Entrée pour revenir au menu...")
        except KeyboardInterrupt:
            print("\nInterruption par l'utilisateur.")
            break


if __name__ == "__main__":
    main()