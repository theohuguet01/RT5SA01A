import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp

conn_reader = None


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
        print("  ATR : ", scardutil.toHexString(conn_reader.getATR()))
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
    # Version : CLA=0x81, INS=0x00, P3=4 (taille de "2.00")
    apdu = [0x81, 0x00, 0x00, 0x00, 0x04]

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.Exceptions as e:
        print("[ERREUR] Lecture de la version de la carte :", e)
        return

    # si taille incorrecte, la carte renvoie 6C xx
    if sw1 == 0x6C:
        apdu[4] = sw2
        try:
            data, sw1, sw2 = conn_reader.transmit(apdu)
        except scardexcp.Exceptions as e:
            print("[ERREUR] Lecture de la version (2e essai) :", e)
            return

    if sw1 != 0x90 or sw2 != 0x00:
        print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
        print("[ERREUR] Impossible de lire la version de la carte.\n")
        return

    s = "".join(chr(e) for e in data)
    print("\n=== Version de la carte ===")
    print("  Version : %s" % s)
    print("  (SW1=0x%02X, SW2=0x%02X)\n" % (sw1, sw2))


# ===========================
#  FONCTION 2 - données perso
# ===========================

def print_data():
    """
    Affiche les données de personnalisation (perso).
    Si la carte n’est pas attribuée (taille 0) → message explicite.
    """
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
        print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
        print("[ERREUR] Impossible de lire les données de la carte.\n")
        return

    # ICI LA CORRECTION : on ne jette plus le premier octet
    if data:
        perso_bytes = data[:]      # tout le buffer
    else:
        perso_bytes = []

    print("\n=== Données de la carte ===")
    print("  (SW1=0x%02X, SW2=0x%02X)" % (sw1, sw2))

    if not perso_bytes:
        print("  Carte non attribuée : aucune donnée de personnalisation.\n")
        return

    s = "".join(chr(e) for e in perso_bytes)
    parts = s.split(";")

    num = parts[0].strip() if len(parts) > 0 else ""
    nom = parts[1].strip() if len(parts) > 1 else ""
    prenom = parts[2].strip() if len(parts) > 2 else ""

    print("  Numéro étudiant        : %s" % (num or "(inconnu)"))
    print("  Nom de l'étudiant(e)   : %s" % (nom or "(inconnu)"))
    print("  Prénom de l'étudiant(e): %s\n" % (prenom or "(inconnu)"))



# =========================
#  PERSO
# =========================

def assign_card():
    print("\n=== Attribution / personnalisation de la carte ===")
    # intro_perso() : APDU 81 01 00 00 Lc [perso]
    apdu = [0x81, 0x01, 0x00, 0x00]

    num = input("  Numéro d'étudiant : ")
    nom = input("  Nom               : ")
    prenom = input("  Prénom            : ")

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

    print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] Carte personnalisée avec succès.\n")
    elif sw1 == 0x6C:
        print("[ERREUR] Taille incorrecte, la carte attend %d octets.\n" % sw2)
    else:
        print("[ERREUR] Échec de la personnalisation de la carte.\n")


# =========================
#  PIN / COMPTEUR / SOLDE
# =========================

def _ask_pin_octets(message):
    """
    Demande un PIN sur 4 chiffres collés, ex: 1234
    Renvoie une liste de 4 entiers [b0, b1, b2, b3].
    """
    while True:
        raw = input(message + " (4 chiffres, ex: 1234) : ").strip()
        if len(raw) != 4 or not raw.isdigit():
            print("  Veuillez entrer exactement 4 chiffres (ex: 1234).")
            continue
        return [int(ch) & 0xFF for ch in raw]


def verify_pin_interactive():
    """
    Vérifie le PIN auprès de la carte.
    APDU : 82 04 00 00 04 [PIN(4 octets)]
    """
    print("\n=== Vérification du code PIN ===")
    pin_bytes = _ask_pin_octets("  PIN")
    apdu = [0x82, 0x04, 0x00, 0x00, 0x04] + pin_bytes

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Vérification du PIN :", e)
        return False

    print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] PIN correct, authentification réussie.\n")
        return True
    elif sw1 == 0x63:
        print("[ERREUR] PIN incorrect. Essais restants : %d\n" % sw2)
        return False
    elif sw1 == 0x69 and sw2 == 0x83:
        print("[ERREUR] PIN bloqué (plus d'essais).\n")
        return False
    elif sw1 == 0x6C:
        print("[ERREUR] Longueur PIN incorrecte, la carte attend %d octets.\n" % sw2)
        return False
    else:
        print("[ERREUR] Échec lors de la vérification du PIN.\n")
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
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Lecture du compteur :", e)
        return None

    print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
    if sw1 != 0x90 or sw2 != 0x00 or not data or len(data) < 2:
        print("[ERREUR] Impossible de lire le compteur.\n")
        return None

    ctr = int(data[0]) | (int(data[1]) << 8)
    print("Compteur actuel : %d\n" % ctr)
    return ctr


def _read_sold_core():
    """
    Lecture basse-niveau du solde, en supposant que le PIN vient
    d’être vérifié côté carte (pin_ok=1).
    APDU : 82 01 00 00 02
    Retourne le solde en centimes (int) ou None.
    """
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Lecture du solde (basse-niveau) :", e)
        return None

    print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
    if sw1 != 0x90 or sw2 != 0x00:
        if sw1 == 0x69 and sw2 == 0x82:
            print("[ERREUR] PIN non vérifié (security status not satisfied).\n")
        else:
            print("[ERREUR] Erreur lors de la lecture du solde.\n")
        return None

    if not data or len(data) < 2:
        print("[ERREUR] Données de solde invalides ou manquantes.\n")
        return None

    cents = int(data[0]) | (int(data[1]) << 8)
    return cents


# =========================
#  FONCTION 4 - solde initial
# =========================

def assign_inital_sold():
    """
    Créditer 1.00 € sur la carte, seulement si solde actuel = 0.
    """
    print("\n=== Mise du solde initial à 1.00 € ===")

    print("[Étape 1] Vérification du PIN pour lecture du solde...")
    if not verify_pin_interactive():
        print("[ERREUR] Impossible de vérifier le solde : PIN non vérifié.\n")
        return

    cents = _read_sold_core()
    if cents is None:
        print("[ERREUR] Impossible de vérifier si la carte a déjà un solde.\n")
        return

    if cents > 0:
        euros = cents / 100.0
        print("[INFO] Carte déjà initialisée, solde actuel = %.2f €." % euros)
        print("       Crédit initial non appliqué.\n")
        return

    print("[OK] Solde actuel = 0.00 €, initialisation possible.\n")

    print("[Étape 2] Vérification du PIN pour le crédit initial...")
    if not verify_pin_interactive():
        print("[ERREUR] Impossible de créditer : PIN non vérifié.\n")
        return

    ctr = read_counter()
    if ctr is None:
        print("[ERREUR] Impossible de créditer : compteur indisponible.\n")
        return

    montant = 100
    montant_lsb = montant & 0xFF
    montant_msb = (montant >> 8) & 0xFF

    p1 = ctr & 0xFF
    p2 = (ctr >> 8) & 0xFF

    apdu = [0x82, 0x02, p1, p2, 0x02, montant_lsb, montant_msb]

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Crédit du solde initial :", e)
        return

    print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] Solde initial crédité : 1.00 €\n")
    elif sw1 == 0x61 and sw2 == 0x00:
        print("[ERREUR] Capacité maximale de rechargement dépassée.\n")
    elif sw1 == 0x69 and sw2 == 0x82:
        print("[ERREUR] Statut de sécurité non satisfait (PIN non vérifié).\n")
    elif sw1 == 0x69 and sw2 == 0x84:
        print("[ERREUR] Erreur anti-rejoue (compteur invalide).\n")
    elif sw1 == 0x6C:
        print("[ERREUR] Erreur de longueur (la carte attend %d octets).\n" % sw2)
    else:
        print("[ERREUR] Échec lors de la mise du solde initial.\n")


# =========================
#  FONCTION 5 - consultation solde
# =========================

def read_sold():
    """
    Consultation du solde : on vérifie le PIN à chaque fois,
    puis on lit le solde via _read_sold_core().
    """
    print("\n=== Consultation du solde ===")
    if not verify_pin_interactive():
        print("[ERREUR] Impossible de lire le solde : PIN non vérifié.\n")
        return

    cents = _read_sold_core()
    if cents is None:
        return

    euros = cents / 100.0
    print("[OK] Solde disponible : %.2f €\n" % euros)


# =========================
#  Changement de PIN
# =========================

def change_pin():
    """
    Changer le code PIN :
    APDU : 82 05 00 00 08 [ancien PIN(4)][nouveau PIN(4)]
    """
    print("\n=== Changement de PIN ===")
    old_pin = _ask_pin_octets("  Ancien PIN")
    new_pin = _ask_pin_octets("  Nouveau PIN")

    apdu = [0x82, 0x05, 0x00, 0x00, 0x08]
    apdu.extend(old_pin)
    apdu.extend(new_pin)

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.CardConnectionException as e:
        print("[ERREUR] Changement de PIN :", e)
        return

    print("SW1=0x%02X, SW2=0x%02X" % (sw1, sw2))
    if sw1 == 0x90 and sw2 == 0x00:
        print("[OK] PIN changé avec succès.\n")
    elif sw1 == 0x6C and sw2 == 0x08:
        print("[ERREUR] Erreur de longueur (P3 doit être 8).\n")
    elif sw1 == 0x63:
        print("[ERREUR] Ancien PIN incorrect. Essais restants : %d\n" % sw2)
    elif sw1 == 0x69 and sw2 == 0x83:
        print("[ERREUR] PIN bloqué (plus d'essais).\n")
    else:
        print("[ERREUR] Échec lors du changement de PIN.\n")


# =========================
#  Boucle principale
# =========================

def main():
    init_smart_card()
    print_hello_message()
    while True:
        print_menu()
        try:
            cmd = int(input("Choix : "))
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
