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
    print(" 6 - Quitter ")


def print_version():
    apdu = [0x81, 0x00, 0x00, 0x00, 0x04]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
    except scardexcp.Exceptions as e:
        print("Error", e)
        return

    if sw1 != 0x90 and sw2 != 0x00:
        print(
            "sw1 : 0x%02X | sw2 : 0x%02X | version : erreur de lecture version"
            % (sw1, sw2)
        )
    s = ""
    for e in data:
        s += chr(e)
    print("sw1 : 0x%02X | sw2 : 0x%02X | version %s" % (sw1, sw2, s))
    return


def print_data():
    apdu = [0x81, 0x02, 0x00, 0x00, 0x05]
    data, sw1, sw2 = conn_reader.transmit(apdu)
    print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))

    # on réutilise sw2 comme longueur attendue
    apdu[4] = sw2
    data, sw1, sw2 = conn_reader.transmit(apdu)
    s = ""
    for e in data:
        s += chr(e)
    print("sw1 : 0x%02X | sw2 : 0x%02X | Données %s" % (sw1, sw2, s))
    return


def assign_card():
    apdu = [0x81, 0x01, 0x00, 0x00]

    # Lubiana : on attribue la carte à un étudiant (num, nom, prénom)
    num = input("Numéro d'étudiant : ")
    nom = input("Nom : ")
    prenom = input("Prénom : ")

    # format simple : "num;nom;prenom"
    infos = f"{num};{nom};{prenom}"
    length = len(infos)

    apdu.append(length)
    for c in infos:
        apdu.append(ord(c))

    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return


def assign_inital_sold():
    # Créditer 1.00 € : CLA 0x82, INS 0x02, P1=0x00, P2=0x00, Lc=0x02, Data=0x00 0x64
    apdu = [0x82, 0x02, 0x00, 0x00, 0x02, 0x00, 0x64]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
        if sw1 == 0x90 and sw2 == 0x00:
            print("Solde initial crédité : 1.00 €")
        elif sw1 == 0x61 and sw2 == 0x00:
            print("Capacité maximale de rechargement dépassée.")
        else:
            print("Erreur lors de la mise du solde initial.")
    except scardexcp.CardConnectionException as e:
        print("error : ", e)



def read_sold():
    # Lire solde : CLA 0x82, INS 0x01, P1=0x00, P2=0x00, Le=0x02
    apdu = [0x82, 0x01, 0x00, 0x00, 0x02]
    try:
        data, sw1, sw2 = conn_reader.transmit(apdu)
        print("sw1 : 0x%02X | sw2 : 0x%02X" % (sw1, sw2))
    except scardexcp.CardConnectionException as e:
        print("error : ", e)
        return

    # Si la carte renvoie une erreur, on ne touche pas à data
    if sw1 != 0x90 or sw2 != 0x00:
        print("Erreur lors de la lecture du solde (pas de données valides).")
        return

    if not data or len(data) < 2:
        print("Données de solde invalides ou manquantes.")
        return

    # Big endian : data[0] = octet de poids fort, data[1] = octet de poids faible
    cents = (int(data[0]) << 8) + int(data[1])
    sld = cents / 100.0
    print("sw1 : 0x%02X | sw2 : 0x%02X | Solde %.2f" % (sw1, sw2, sld))



def main():
    init_smart_card()
    print_hello_message()
    while True:
        print_menu()
        cmd = int(input("Choix : "))
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
            return
        else:
            print("Commande inconnue !")
        print("\n ---\n ")
        print_menu()


if __name__ == "__main__":
    main()
