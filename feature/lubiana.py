import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp

conn_reader = None


# =========================
#  OUTILS AFFICHAGE
# =========================

def _hex_bytes(data):
    """Affiche une liste d'octets sous forme '0xAA 0xBB ...'"""
    if not data:
        return "(vide)"
    return " ".join(f"0x{b:02X}" for b in data)


def _print_sw(sw1, sw2, prefix=""):
    if prefix:
        print(f"{prefix}SW1=0x{sw1:02X}, SW2=0x{sw2:02X}")
    else:
        print(f"SW1=0x{sw1:02X}, SW2=0x{sw2:02X}")


# =========================
#  INIT SMART CARD
# =========================

def init_smart_card():
    try:
        lst_readers = scardsys.readers()
    except scardexcp.Exceptions as e:
        print("[ERREUR] Impossible de lister les lecteurs de cartes : ", e)
        return

    if len(lst_readers) < 1:
        print("[ERREUR] Aucun lecteur de carte n'est connecté.")
        exit()

    try:
        global conn_reader
        conn_reader = lst_readers[0].createConnection()
        conn_reader.connect()
        print("==============================================")
        print("  Lecteur initialisé avec succès")
        print("  ATR :", scardutil.toHexString(conn_reader.getATR()))
        print("==============================================\n")
    except scardexcp.NoCardException as e:
        print("[ERREUR] Aucune carte dans le lecteur : ", e)
        exit()
    return


# =========================
#  UI
# =========================

def print_hello_message():
    print("---------------------------------------------------")
    print("--   Logiciel de personnalisation : Lubiana      --")
    print("---------------------------------------------------\n")


def print_menu():
    print("============== MENU PRINCIPAL =====================")
    print(" 1 - Afficher la version de la carte")
    print(" 2 - Afficher les données de la carte")
    print(" 3 - Attribuer la carte")
    print(" 4 - Mettre le solde initial")
    print(" 5 - Consulter le solde")
    print(" 6 - Changer le code PIN")
    print(" 7 - Quitter")
    print("===================================================")


# =========================
#  FONCTION 1 - Version
# =========================

def print_version():
    apdu = [0x81, 0x00, 0x00, 0x00, 0x04]

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.Exceptions as e:
        print("[ERREUR] Lecture de la version de la carte :", e)
        return

    if sw1 == 0x6C:
        apdu[4] = sw2
        try:
            data, sw1, sw2 = conn_reader.transmit(apdu)
        except scardexcp.Exceptions as e:
            print("[ERREUR] Lecture de la version (2e essai) :", e)
            return

    if sw1 != 0x90 or sw2 != 0x00:
        _print_sw(sw1, sw2)
        print("[ERREUR] Impossible de lire la version de la carte.\n")
        return

    s = "".join(chr(e) for e in data)
    print("\n=== Version de la carte ===")
    print(f"  Version : {s}")
    _print_sw(sw1, sw2, prefix="  ")
    print()


# ===========================
#  FONCTION 2 - données perso
# ===========================

def print_data():
    apdu = [0x81, 0x02, 0x00, 0x00, 0x05]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Lecture des données de la carte :", e)
        return

    if sw1 == 0x6C:
        apdu[4] = sw2
        try:
            data, sw1, sw2 = conn_reader.transmit(apdu)
        except scardexcp.CardConnectionException as e:
            print("[ERREUR] Lecture des données (2e essai) :", e)
            return

    if sw1 != 0x90 or sw2 != 0x00:
        _print_sw(sw1, sw2)
        print("[ERREUR] Impossible de lire les données de la carte.\n")
        return

    # IMPORTANT: on ne jette PAS le premier octet (dans votre cas la perso commence directement)
    perso_bytes = data[:] if data else []

    print("\n=== Données de la carte ===")
    _print_sw(sw1, sw2, prefix="  ")

    if not perso_bytes:
        print("  Carte non attribuée : aucune donnée de personnalisation.\n")
        return

    s = "".join(chr(e) for e in perso_bytes)
    parts = s.split(";")

    num = parts[0].strip() if len(parts) > 0 else ""
    nom = parts[1].strip() if len(parts) > 1 else ""
    prenom = parts[2].strip() if len(parts) > 2 else ""

    print("  Numéro étudiant        :", num or "(inconnu)")
    print("  Nom de l'étudiant(e)   :", nom or "(inconnu)")
    print("  Prénom de l'étudiant(e):", prenom or "(inconnu)")
    print()


# =========================
#  PERSO
# =========================

def assign_card():
    print("\n=== Attribution / personnalisation de la carte ===")
    apdu = [0x81, 0x01, 0x00, 0x00]

    num = input("  Numéro d'étudiant : ").strip()
    nom = input("  Nom               : ").strip()
    prenom = input("  Prénom            : ").strip()

    infos = f"{num};{nom};{prenom}"
    length = len(infos)

    if length > 255:
        print("[ERREUR] Chaîne de personnalisation trop longue.\n")
        return

    apdu.append(length)
    for c in infos:
        apdu.append(ord(c))

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Personnalisation de la carte :", e)
        return

    _print_sw(sw1, sw2)
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] Carte personnalisée avec succès.\n")
    elif sw1 == 0x6C:
        print(f"[ERREUR] Taille incorrecte, la carte attend {sw2} octets.\n")
    else:
        print("[ERREUR] Échec de la personnalisation de la carte.\n")


# =========================
#  PIN / COMPTEUR / SOLDE
# =========================

def _ask_pin_octets(message):
    while True:
        raw = input(message + " (4 chiffres, ex: 1234) : ").strip()
        if len(raw) != 4 or not raw.isdigit():
            print("  Veuillez entrer exactement 4 chiffres (ex: 1234).")
            continue
        return [int(ch) & 0xFF for ch in raw]


def verify_pin_interactive():
    print("\n=== Vérification du code PIN ===")
    pin_bytes = _ask_pin_octets("  PIN")
    apdu = [0x82, 0x04, 0x00, 0x00, 0x04] + pin_bytes

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Vérification du PIN :", e)
        return False

    _print_sw(sw1, sw2)
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] PIN correct.\n")
        return True
    elif sw1 == 0x63:
        print(f"[ERREUR] PIN incorrect. Essais restants : {sw2}\n")
        return False
    elif sw1 == 0x69 and sw2 == 0x83:
        print("[ERREUR] PIN bloqué (plus d'essais).\n")
        return False
    elif sw1 == 0x6C:
        print(f"[ERREUR] Longueur PIN incorrecte, la carte attend {sw2} octets.\n")
        return False
    else:
        print("[ERREUR] Échec lors de la vérification du PIN.\n")
        return False


def read_counter_with_response(label=""):
    """
    Lecture compteur anti-rejoue + affichage complet DATA + SW.
    Retourne (ctr:int|None).
    """
    apdu = [0x82, 0x07, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Lecture du compteur :", e)
        return None

    tag = f"{label} " if label else ""
    print(f"{tag}Compteur -> DATA={_hex_bytes(data)} | SW1=0x{sw1:02X}, SW2=0x{sw2:02X}")

    if sw1 != 0x90 or sw2 != 0x00 or not data or len(data) < 2:
        print("[ERREUR] Impossible de lire le compteur.\n")
        return None

    ctr = int(data[0]) | (int(data[1]) << 8)
    return ctr


def _read_sold_core():
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Lecture du solde :", e)
        return None

    _print_sw(sw1, sw2)
    if sw1 != 0x90 or sw2 != 0x00:
        if sw1 == 0x69 and sw2 == 0x82:
            print("[ERREUR] PIN non vérifié.\n")
        else:
            print("[ERREUR] Erreur lors de la lecture du solde.\n")
        return None

    if not data or len(data) < 2:
        print("[ERREUR] Données de solde invalides.\n")
        return None

    return int(data[0]) | (int(data[1]) << 8)


# =========================
#  FONCTION 4 - solde initial + TEST anti-rejoue
# =========================

def assign_inital_sold():
    print("\n=== Mise du solde initial à 1.00 € ===")

    print("[1/3] Vérification du PIN pour lire le solde...")
    if not verify_pin_interactive():
        print("[ERREUR] PIN non vérifié.\n")
        return

    cents = _read_sold_core()
    if cents is None:
        return

    if cents > 0:
        print(f"[INFO] Solde actuel : {cents/100.0:.2f} € -> pas de crédit initial.\n")
        return

    print("[OK] Solde = 0.00 € -> crédit initial autorisé.\n")

    print("[2/3] Vérification du PIN pour le crédit...")
    if not verify_pin_interactive():
        print("[ERREUR] PIN non vérifié.\n")
        return

    print("\n--- Test anti-rejoue : compteur AVANT / APRÈS crédit ---")
    ctr_before = read_counter_with_response(label="AVANT")
    if ctr_before is None:
        print("[ERREUR] Compteur indisponible, crédit annulé.\n")
        return

    montant = 100  # centimes
    montant_lsb = montant & 0xFF
    montant_msb = (montant >> 8) & 0xFF

    p1 = ctr_before & 0xFF
    p2 = (ctr_before >> 8) & 0xFF

    apdu_credit = [0x82, 0x02, p1, p2, 0x02, montant_lsb, montant_msb]

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu_credit)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Crédit :", e)
        return

    print(f"CRÉDIT -> SW1=0x{sw1:02X}, SW2=0x{sw2:02X}")

    # Lecture compteur après l'opération, pour comparaison (même si le crédit échoue)
    ctr_after = read_counter_with_response(label="APRES")
    if ctr_after is not None:
        print(f"Comparaison compteur : AVANT={ctr_before} | APRES={ctr_after}\n")
    else:
        print("Comparaison compteur : impossible de relire le compteur après.\n")

    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] Solde initial crédité : 1.00 €\n")
    elif sw1 == 0x61 and sw2 == 0x00:
        print("[ERREUR] Capacité maximale dépassée.\n")
    elif sw1 == 0x69 and sw2 == 0x82:
        print("[ERREUR] Statut de sécurité non satisfait (PIN non vérifié côté carte).\n")
    elif sw1 == 0x69 and sw2 == 0x84:
        print("[ERREUR] Anti-rejoue : compteur invalide (opération rejetée).\n")
    elif sw1 == 0x6C:
        print(f"[ERREUR] Longueur incorrecte (attendu {sw2} octets).\n")
    else:
        print("[ERREUR] Échec crédit initial.\n")


# =========================
#  FONCTION 5 - consultation solde
# =========================

def read_sold():
    print("\n=== Consultation du solde ===")
    if not verify_pin_interactive():
        print("[ERREUR] PIN non vérifié.\n")
        return

    cents = _read_sold_core()
    if cents is None:
        return

    print(f"[OK] Solde disponible : {cents/100.0:.2f} €\n")


# =========================
#  Changement de PIN
# =========================

def change_pin():
    print("\n=== Changement de PIN ===")
    old_pin = _ask_pin_octets("  Ancien PIN")
    new_pin = _ask_pin_octets("  Nouveau PIN")

    apdu = [0x82, 0x05, 0x00, 0x00, 0x08] + old_pin + new_pin

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Changement de PIN :", e)
        return

    _print_sw(sw1, sw2)
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] PIN changé avec succès.\n")
    elif sw1 == 0x63:
        print(f"[ERREUR] Ancien PIN incorrect. Essais restants : {sw2}\n")
    elif sw1 == 0x69 and sw2 == 0x83:
        print("[ERREUR] PIN bloqué.\n")
    else:
        print("[ERREUR] Échec changement de PIN.\n")


# =========================
#  Boucle principale
# =========================

def main():
    init_smart_card()
    print_hello_message()

    while True:
        print_menu()
        try:
            cmd = int(input("Choix : ").strip())
        except ValueError:
            print("[WARN] Veuillez saisir un nombre.\n")
            continue

        if cmd == 1:
            print_version()
        elif cmd == 2:
            print_data()
        elif cmd == 3:
            assign_card()
        elif cmd == 4:
            assign_inital_sold()
        elif cmd == 5:
            read_sold()
        elif cmd == 6:
            change_pin()
        elif cmd == 7:
            print("\n[INFO] Fermeture du logiciel Lubiana. Au revoir.\n")
            break
        else:
            print("[WARN] Commande inconnue !\n")

        try:
            input("Appuyez sur Entrée pour revenir au menu...\n")
        except KeyboardInterrupt:
            print("\n[INFO] Interruption par l'utilisateur. Arrêt du programme.")
            break


if __name__ == "__main__":
    main()
