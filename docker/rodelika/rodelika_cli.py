#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rodelika CLI interactif (bonus positif uniquement)
--------------------------------------------------
- Auth via table Agents (bcrypt)
- Gestion des étudiants et comptes
- Crédit uniquement via "bonus" (montant strictement positif)
"""

import getpass
import bcrypt
import mysql.connector
from typing import Optional, Dict

DB_CONFIG = {
    "host": "purple-dragon-db",
    "port": 3306,
    "user": "rodelika",
    "password": "rodelika",
    "database": "carote_electronique",
}

CURRENT_AGENT: Optional[Dict] = None


# ===========================
# DB UTILS
# ===========================

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def ensure_default_admin():
    """Crée automatiquement admin/admin si absent (pour le dev)."""
    try:
        cnx = get_db()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT id FROM Agents WHERE Identifiant='admin'")
        if cur.fetchone():
            return
        pwd_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()
        cur.execute("""
            INSERT INTO Agents (Identifiant,Nom,Prenom,Password_Hash,Role)
            VALUES ('admin','Admin','Dev',%s,'ADMIN')
        """, (pwd_hash,))
        cnx.commit()
        print("✔ Compte admin/admin créé.")
    except Exception as e:
        print(f"[WARN] Impossible de créer l’admin : {e}")
    finally:
        try:
            cnx.close()
        except:
            pass


# ===========================
# AUTH
# ===========================

def login() -> Optional[Dict]:
    print("\n=== Connexion agent ===")
    ident = input("Identifiant : ").strip()
    pwd = getpass.getpass("Mot de passe : ")

    try:
        cnx = get_db()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT * FROM Agents WHERE Identifiant=%s", (ident,))
        agent = cur.fetchone()
    except Exception as e:
        print(f"× Erreur BDD : {e}")
        return None
    finally:
        try:
            cnx.close()
        except:
            pass

    if not agent:
        print("× Identifiant incorrect.")
        return None

    if not bcrypt.checkpw(pwd.encode(), agent["Password_Hash"].encode()):
        print("× Mot de passe incorrect.")
        return None

    print(f"✔ Connecté comme {agent['Identifiant']} ({agent['Role']})")
    return {"id": agent["id"], "ident": ident, "role": agent["Role"]}


# ===========================
# ÉTUDIANTS & COMPTES
# ===========================

def list_students():
    print("\n=== Liste des étudiants ===")
    try:
        cnx = get_db()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT Num_Etudiant,Nom,Prenom FROM users ORDER BY Num_Etudiant")
        rows = cur.fetchall()
        if not rows:
            print("Aucun étudiant.")
        else:
            for r in rows:
                print(f"- {r['Num_Etudiant']} : {r['Nom']} {r['Prenom']}")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        try:
            cnx.close()
        except:
            pass


def add_student():
    print("\n=== Nouvel étudiant ===")
    num = input("Numéro étudiant (8 char) : ").strip()
    nom = input("Nom : ").strip()
    prenom = input("Prénom : ").strip()

    if len(num) != 8:
        print("× Numéro étudiant invalide, 8 caractères requis.")
        return

    if not nom or not prenom:
        print("× Nom et prénom obligatoires.")
        return

    try:
        cnx = get_db()
        cur = cnx.cursor()
        cur.execute("""
            INSERT INTO users (Num_Etudiant,Nom,Prenom,Password_Hash)
            VALUES (%s,%s,%s,'RODELIKA_NO_LOGIN')
        """, (num, nom, prenom))
        cur.execute("""
            INSERT INTO Compte (Num_Etudiant,Solde_Actuel)
            VALUES (%s,0.00)
        """, (num,))
        cnx.commit()
        print(f"✔ Étudiant {num} créé.")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        try:
            cnx.close()
        except:
            pass


def list_balances():
    print("\n=== Soldes des comptes ===")
    try:
        cnx = get_db()
        cur = cnx.cursor(dictionary=True)
        cur.execute("""
            SELECT users.Num_Etudiant,Nom,Prenom,Solde_Actuel
            FROM users JOIN Compte USING(Num_Etudiant)
            ORDER BY Num_Etudiant
        """)
        rows = cur.fetchall()
        if not rows:
            print("Aucun compte.")
        else:
            for r in rows:
                print(f"{r['Num_Etudiant']} | {r['Nom']} {r['Prenom']} → {r['Solde_Actuel']:.2f} €")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        try:
            cnx.close()
        except:
            pass


# ===========================
# BONUS (positif uniquement)
# ===========================

def add_bonus():
    print("\n=== Attribuer un bonus (positif uniquement) ===")

    num = input("Num étudiant : ").strip()
    montant_str = input("Montant du bonus (€) : ").strip().replace(",", ".")
    commentaire_base = input("Commentaire : ").strip()

    # Validation du montant
    try:
        montant = float(montant_str)
    except Exception:
        print("× Montant invalide.")
        return

    if montant <= 0:
        print("× Le montant du bonus doit être strictement positif.")
        return

    # Normalisation du commentaire : toujours commencer par "Bonus"
    # (obligatoire pour la détection côté Berlicum)
    if not commentaire_base:
        commentaire_base = "Bonus CLI"
    elif not commentaire_base.lower().startswith("bonus"):
        commentaire_base = f"Bonus - {commentaire_base}"

    commentaire = commentaire_base

    try:
        cnx = get_db()
        cur = cnx.cursor()
        # Bonus = crédit (logique unifiée avec rodelika_web)
        cur.callproc("CrediterCompte", [num, montant, commentaire])
        cnx.commit()
        print(f"✔ Bonus de {montant:.2f} € attribué à {num}.")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        try:
            cnx.close()
        except:
            pass



# ===========================
# AGENTS (ADMIN)
# ===========================

def add_agent():
    if CURRENT_AGENT["role"] != "ADMIN":
        print("× Seul un ADMIN peut créer un agent.")
        return

    print("\n=== Création agent ===")
    ident = input("Identifiant : ").strip()
    nom = input("Nom : ").strip()
    prenom = input("Prénom : ").strip()
    role = input("Rôle (ADMIN/AGENT) [AGENT] : ").strip().upper() or "AGENT"

    pwd = getpass.getpass("Mot de passe : ")
    pwd2 = getpass.getpass("Confirmation : ")

    if pwd != pwd2:
        print("× Les mots de passe ne correspondent pas.")
        return

    pwd_hash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

    try:
        cnx = get_db()
        cur = cnx.cursor()
        cur.execute("""
            INSERT INTO Agents (Identifiant,Nom,Prenom,Password_Hash,Role)
            VALUES (%s,%s,%s,%s,%s)
        """, (ident, nom, prenom, pwd_hash, role))
        cnx.commit()
        print(f"✔ Agent '{ident}' créé.")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        try:
            cnx.close()
        except:
            pass


# ===========================
# MENU PRINCIPAL
# ===========================

def main_menu():
    global CURRENT_AGENT
    while True:
        print("\n==============================")
        print("  Rodelika CLI - Menu principal")
        print("==============================")
        print(f"Connecté : {CURRENT_AGENT['ident']} ({CURRENT_AGENT['role']})")
        print("1) Lister les étudiants")
        print("2) Créer un étudiant")
        print("3) Voir les soldes")
        print("4) Attribuer un bonus")
        if CURRENT_AGENT["role"] == "ADMIN":
            print("5) Créer un agent")
            print("6) Déconnexion")
            print("7) Quitter")
        else:
            print("5) Déconnexion")
            print("6) Quitter")

        choix = input("Votre choix : ").strip()

        if CURRENT_AGENT["role"] == "ADMIN":
            if choix == "1":
                list_students()
            elif choix == "2":
                add_student()
            elif choix == "3":
                list_balances()
            elif choix == "4":
                add_bonus()
            elif choix == "5":
                add_agent()
            elif choix == "6":
                break
            elif choix == "7":
                print("Au revoir.")
                exit(0)
            else:
                print("Choix invalide.")
        else:
            if choix == "1":
                list_students()
            elif choix == "2":
                add_student()
            elif choix == "3":
                list_balances()
            elif choix == "4":
                add_bonus()
            elif choix == "5":
                break
            elif choix == "6":
                print("Au revoir.")
                exit(0)
            else:
                print("Choix invalide.")


def run():
    global CURRENT_AGENT
    ensure_default_admin()
    print("=== Rodelika CLI interactif ===")

    while True:
        CURRENT_AGENT = login()
        if not CURRENT_AGENT:
            if input("Réessayer ? (o/N) : ").lower() != "o":
                print("Au revoir.")
                return
        else:
            main_menu()
            CURRENT_AGENT = None
            if input("Se reconnecter ? (o/N) : ").lower() != "o":
                print("Au revoir.")
                break


if __name__ == "__main__":
    run()