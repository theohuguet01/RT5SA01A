import smartcard.System as scardsys
import smartcard.util as scardutil
import smartcard.Exceptions as scardexcp

conn_reader = None


def init_smart_card():
    try:
        lst_readers = scardsys.readers()
    except scardexcp.Exceptions as e:
        print(e)
        return

    if len(lst_readers) < 1:
        print(" Pas de lecteur de carte connecté !")
        exit()

    try:
        global conn_reader
        conn_reader = lst_readers[0].createConnection()
        conn_reader.connect()
        print("ATR : ", scardutil.toHexString(conn_reader.getATR()))
    except scardexcp.NoCardException as e:
        print(" Pas de carte dans le lecteur : ", e)
        exit()
    return


def print_hello_message():
    print("---------------------------------------------")
    print("-- Logiciel de personnalisation : Lubiana --")
    print("---------------------------------------------")


def print_menu():
    print(" 1 - Afficher la version de carte ")
    print(" 2 - Afficher les données de la carte ")
    print(" 3 - Attribuer la carte ")
    print(" 4 - Mettre le solde initial ")
    print(" 5 - Consulter le solde ")
    print(" 6 - Changer le code PIN ")
    print(" 7 - Quitter ")


def print_version():
    # Version : CLA=0x81, INS=0x00, P3=4 (taille de "2.00")
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

    # la carte envoie d’abord INS (0x00), puis "2.00"
    s = "".join(chr(e) for e in data)
    print("sw1 : 0x%02X | sw2 : 0x%02X | version %s" % (sw1, sw2, s))


# =========================
#  FONCTION 2 - données perso
# =========================

def print_data():
    """
    Affiche les données de personnalisation (perso).
    Si la carte n’est pas attribuée (taille 0) → message explicite.
    """
    # 1er essai avec une longueur "guess"
    apdu = [0x81, 0x02, 0x00, 0x00, 0x05]
    data, sw1, sw2 = conn_reader.transmit(apdu)

    if sw1 == 0x6C:
        # sw2 = taille réelle des données perso (peut être 0 !)
        apdu[4] = sw2
        data, sw1, sw2 = conn_reader.transmit(apdu)

    if sw1 != 0x90 or sw2 != 0x00:
        print("sw1 : 0x%02X | sw2 : 0x%02X | Erreur lecture données" % (sw1, sw2))
        return

    # data[0] = INS (0x02), puis la perso
    if data and len(data) > 1:
        perso_bytes = data[1:]
    else:
        perso_bytes = []

    if not perso_bytes:
        print("sw1 : 0x%02X | sw2 : 0x%02X | Carte non attribuée (aucune donnée)."
              % (sw1, sw2))
    else:
        s = "".join(chr(e) for e in perso_bytes)
        print("sw1 : 0x%02X | sw2 : 0x%02X | Données %s" % (sw1, sw2, s))


# =========================
#  PERSO
# =========================

def assign_card():
    # intro_perso() : APDU 81 01 00 00 Lc [perso]
    apdu = [0x81, 0x01, 0x00, 0x00]

    # Lubiana : on attribue la carte à un étudiant (num, nom, prénom)
    num = input("Numéro d'étudiant : ")
    nom = input("Nom : ")
    prenom = input("Prénom : ")

    # format simple : "num;nom;prenom"
    infos = f"{num};{nom};{prenom}"
    length = len(infos)

    if length > 255:
        print("Chaîne de personnalisation trop longue.")
        return

    apdu.append(length)
    for c in infos:
        apdu.append(ord(c))

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return

    if sw1 == 0x90 and sw2 == 0x00:
        print("Carte personnalisée avec succès.")
    elif sw1 == 0x6C:
        print("Taille incorrecte, la carte attend %d octets." % sw2)
    else:
        print("Erreur lors de la personnalisation de la carte.")


# =========================
#  PIN / COMPTEUR / SOLDE
# =========================

def _ask_pin_octets(message):
    """
    Demande un PIN sur 4 chiffres collés, ex: 1234
    Renvoie une liste de 4 entiers [b0, b1, b2, b3].
    Chaque chiffre est converti en entier (ex: '1' -> 1).
    """
    while True:
        raw = input(message + " (4 chiffres, ex: 1234) : ").strip()
        if len(raw) != 4 or not raw.isdigit():
            print("Veuillez entrer exactement 4 chiffres (ex: 1234).")
            continue
        # Chaque caractère est un chiffre : '1','2','3','4' -> [1,2,3,4]
        bytes_pin = [int(ch) & 0xFF for ch in raw]
        return bytes_pin


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
    Renvoie le compteur (int) ou None en cas d'erreur.
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

    # Little-endian : LSB puis MSB
    ctr = int(data[0]) | (int(data[1]) << 8)
    print("Compteur actuel : %d" % ctr)
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

    # Little-endian : LSB puis MSB
    cents = int(data[0]) | (int(data[1]) << 8)
    return cents


# =========================
#  FONCTION 4 - solde initial
# =========================

def assign_inital_sold():
    """
    Créditer 1.00 € sur la carte, seulement si solde actuel = 0.
    - Vérifie d'abord le PIN pour lire le solde
    - Si solde > 0 → on refuse le crédit initial
    - Si solde = 0 → on re-vérifie le PIN, lit le compteur, puis crédit 1.00 €
    """
    print("=== Mise du solde initial à 1.00 € ===")

    # 1) PIN pour lecture solde
    print("Vérification PIN pour lecture du solde...")
    if not verify_pin_interactive():
        print("Impossible de vérifier le solde : PIN non vérifié.")
        return

    # 2) Lecture du solde (consomme le ticket PIN côté carte)
    cents = _read_sold_core()
    if cents is None:
        print("Impossible de vérifier si la carte a déjà un solde.")
        return

    if cents > 0:
        euros = cents / 100.0
        print(
            f"Carte déjà attribuée / initialisée (solde actuel = {euros:.2f} €). "
            "Crédit initial non appliqué."
        )
        return

    print("Solde actuel = 0.00 €, initialisation possible.")

    # 3) PIN à nouveau pour l’opération de crédit (la carte consomme le PIN à chaque op sensible)
    print("Vérification PIN pour le crédit initial...")
    if not verify_pin_interactive():
        print("Impossible de créditer : PIN non vérifié.")
        return

    # 4) Lecture du compteur anti-rejoue
    ctr = read_counter()
    if ctr is None:
        print("Impossible de créditer : compteur indisponible.")
        return

    # 5) Crédit de 1.00 € = 100 centimes
    montant = 100
    montant_lsb = montant & 0xFF
    montant_msb = (montant >> 8) & 0xFF

    p1 = ctr & 0xFF          # LSB compteur
    p2 = (ctr >> 8) & 0xFF   # MSB compteur

    # APDU : 82 02 P1 P2 02 [montant_LSB][montant_MSB]
    apdu = [0x82, 0x02, p1, p2, 0x02, montant_lsb, montant_msb]

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("Crédit - sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return

    if sw1 == 0x90 and sw2 == 0x00:
        print("Solde initial crédité : 1.00 €")
    elif sw1 == 0x61 and sw2 == 0x00:
        print("Capacité maximale de rechargement dépassée.")
    elif sw1 == 0x69 and sw2 == 0x82:
        print("Statut de sécurité non satisfait (PIN non vérifié côté carte).")
    elif sw1 == 0x69 and sw2 == 0x84:
        print("Erreur anti-rejoue (compteur invalide).")
    elif sw1 == 0x6C:
        print("Erreur de longueur (la carte attend %d octets)." % sw2)
    else:
        print("Erreur lors de la mise du solde initial.")


# =========================
#  FONCTION 5 - consultation solde
# =========================

def read_sold():
    """
    Consultation du solde : on vérifie le PIN à chaque fois,
    puis on lit le solde via _read_sold_core().
    """
    print("=== Consultation du solde ===")
    if not verify_pin_interactive():
        print("Impossible de lire le solde : PIN non vérifié.")
        return

    cents = _read_sold_core()
    if cents is None:
        return

    euros = cents / 100.0
    print("Solde disponible : %.2f €" % euros)


# =========================
#  Changement de PIN
# =========================

def change_pin():
    """
    Changer le code PIN :
    APDU : 82 05 00 00 08 [ancien PIN(4)][nouveau PIN(4)]
    """
    print("=== Changement de PIN ===")
    # Saisie de l'ancien et du nouveau PIN
    old_pin = _ask_pin_octets("Ancien PIN")
    new_pin = _ask_pin_octets("Nouveau PIN")

    apdu = [0x82, 0x05, 0x00, 0x00, 0x08]
    apdu.extend(old_pin)
    apdu.extend(new_pin)

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return

    if sw1 == 0x90 and sw2 == 0x00:
        print("PIN changé avec succès.")
    elif sw1 == 0x6C and sw2 == 0x08:
        print("Erreur de longueur (P3 doit être 8).")
    elif sw1 == 0x63:
        print("Ancien PIN incorrect. Essais restants : %d" % sw2)
    elif sw1 == 0x69 and sw2 == 0x83:
        print("PIN bloqué (plus d'essais).")
    else:
        print("Erreur lors du changement de PIN.")


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
            print("Veuillez saisir un nombre.")
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
            print("Au revoir.")
            break
        else:
            print("Commande inconnue !")

        # Pause avant de revenir au menu (sauf si l'utilisateur fait CTRL-C)
        try:
            input("\nAppuyez sur Entrée pour revenir au menu...")
        except KeyboardInterrupt:
            print("\nInterruption par l'utilisateur.")
            break


if __name__ == "__main__":
    main()
