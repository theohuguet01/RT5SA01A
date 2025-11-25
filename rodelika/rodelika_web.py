#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rodelika Web (Flask)
--------------------
Version Web du logiciel de gestion, avec :
- Authentification via Agents (bcrypt)
- Gestion étudiants / comptes / bonus
- Logo UVSQ IUT Vélizy dans la navbar
- Footer corporate
"""

from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
)
import mysql.connector
import os
import bcrypt
from functools import wraps

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "rodelika",
    "password": "rodelika",
    "database": "carote_electronique",
}

app = Flask(__name__)
# Clé secrète : variable d'env prioritaire, sinon valeur de dev
app.secret_key = os.environ.get(
    "RODELIKA_SECRET_KEY",
    "kNOYSs9JgOubtCmPoQYcHDtIEQb1MorM9ZN7EW_5W0M=",
)


def get_db():
    """Connexion MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


# ==============
# AUTH HELPERS
# ==============

def login_required(f):
    """Décorateur pour exiger une connexion agent."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "agent_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def ensure_default_admin():
    """
    Crée un compte agent admin/admin si aucun agent 'admin' n'existe.
    À utiliser uniquement pour le dev.
    """
    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Agents WHERE Identifiant = %s", ("admin",))
        row = cursor.fetchone()
        if row:
            return  # admin existe déjà

        pwd_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            """
            INSERT INTO Agents (Identifiant, Nom, Prenom, Password_Hash, Role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            ("admin", "Admin", "Défaut", pwd_hash, "ADMIN"),
        )
        cnx.commit()
        print("Compte agent par défaut créé : identifiant='admin' / mot de passe='admin'")
    except mysql.connector.Error as e:
        print(f"[WARN] Impossible de créer le compte admin par défaut : {e}")
    finally:
        if "cnx" in locals():
            cnx.close()


# ===========================
# TEMPLATE GLOBAL
# ===========================

BASE_HTML = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Rodelika Web</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    rel="stylesheet">
</head>
<body class="d-flex flex-column min-vh-100">
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container-fluid">
    <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
      <img src="https://www.uvsq.fr/medias/photo/iut-velizy-villacoublay-logo-2020-ecran_1580904185110-jpg?ID_FICHE=214049"
           alt="UVSQ - IUT de Vélizy-Villacoublay"
           class="me-2"
           style="height:40px; background-color:white; border-radius:4px; padding:2px;">
      <span>Rodelika Web</span>
    </a>
    <div class="navbar-nav">
      {% if session.get('agent_id') %}
        <a class="nav-link" href="{{ url_for('list_students') }}">Étudiants</a>
        <a class="nav-link" href="{{ url_for('list_soldes') }}">Soldes</a>
        <a class="nav-link" href="{{ url_for('new_student') }}">Nouvel étudiant</a>
        <a class="nav-link" href="{{ url_for('add_bonus') }}">Attribuer un bonus</a>
      {% endif %}
    </div>
    <div class="ms-auto d-flex align-items-center">
      {% if session.get('agent_id') %}
        <span class="navbar-text text-light me-3">
          {{ session.get('agent_ident') }} ({{ session.get('agent_role') }})
        </span>
        <a class="btn btn-outline-light btn-sm" href="{{ url_for('logout') }}">Déconnexion</a>
      {% else %}
        <a class="btn btn-outline-light btn-sm" href="{{ url_for('login') }}">Connexion</a>
      {% endif %}
    </div>
  </div>
</nav>

<main class="container mb-5 flex-fill">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="alert alert-{{ cat }} alert-dismissible fade show" role="alert">
          {{ msg }}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {{ content|safe }}
</main>

<footer class="bg-light text-center text-muted py-3 mt-auto">
  <small>
    © 2025 Rodelika – Projet « La Carotte Électronique » – IUT de Vélizy-Villacoublay (UVSQ / Université Paris-Saclay).
    <br>
    Application interne de gestion des comptes étudiants (version Web).
  </small>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


# ===========================
# ROUTES AUTH
# ===========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        password = request.form.get("password", "").strip()

        try:
            cnx = get_db()
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM Agents WHERE Identifiant = %s",
                (identifiant,),
            )
            agent = cursor.fetchone()
        except mysql.connector.Error as e:
            flash(f"Erreur BDD : {e}", "danger")
            agent = None
        finally:
            if "cnx" in locals():
                cnx.close()

        if agent and bcrypt.checkpw(
            password.encode("utf-8"),
            agent["Password_Hash"].encode("utf-8"),
        ):
            session["agent_id"] = agent["id"]
            session["agent_ident"] = agent["Identifiant"]
            session["agent_role"] = agent["Role"]
            flash("Connexion réussie.", "success")
            return redirect(url_for("index"))
        else:
            flash("Identifiant ou mot de passe invalide.", "danger")

    content_tpl = """
    <h2>Connexion agent</h2>
    <form method="post" style="max-width:400px;">
      <div class="mb-3">
        <label class="form-label">Identifiant</label>
        <input class="form-control" type="text" name="identifiant" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Mot de passe</label>
        <input class="form-control" type="password" name="password" required>
      </div>
      <button class="btn btn-primary" type="submit">Se connecter</button>
    </form>
    """
    inner_html = render_template_string(content_tpl)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/logout")
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for("login"))


# ===========================
# ROUTES APPLI
# ===========================

@app.route("/")
@login_required
def index():
    content_tpl = """
    <h1>Logiciel de gestion : Rodelika Web</h1>
    <p>Version Web de Rodelika pour gérer les étudiants, leurs comptes et les bonus.</p>
    <ul>
      <li><a href="{{ url_for('list_students') }}">Afficher la liste des étudiants</a></li>
      <li><a href="{{ url_for('list_soldes') }}">Afficher le solde des étudiants</a></li>
      <li><a href="{{ url_for('new_student') }}">Saisir un nouvel étudiant</a></li>
      <li><a href="{{ url_for('add_bonus') }}">Attribuer un bonus</a></li>
    </ul>
    """
    inner_html = render_template_string(content_tpl)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/etudiants")
@login_required
def list_students():
    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT Num_Etudiant, Nom, Prenom FROM users ORDER BY Num_Etudiant")
        etudiants = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
        etudiants = []
    finally:
        if "cnx" in locals():
            cnx.close()

    content_tpl = """
    <h2>Liste des étudiants</h2>
    {% if etudiants %}
    <table class="table table-striped table-sm">
      <thead>
        <tr>
          <th>Numéro</th>
          <th>Nom</th>
          <th>Prénom</th>
        </tr>
      </thead>
      <tbody>
      {% for e in etudiants %}
        <tr>
          <td>{{ e.Num_Etudiant }}</td>
          <td>{{ e.Nom }}</td>
          <td>{{ e.Prenom }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
      <p>Aucun étudiant.</p>
    {% endif %}
    """
    inner_html = render_template_string(content_tpl, etudiants=etudiants)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/soldes")
@login_required
def list_soldes():
    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        sql = """
            SELECT u.Num_Etudiant, u.Nom, u.Prenom, c.Solde_Actuel
            FROM users u
            JOIN Compte c ON u.Num_Etudiant = c.Num_Etudiant
            ORDER BY u.Num_Etudiant;
        """
        cursor.execute(sql)
        soldes = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
        soldes = []
    finally:
        if "cnx" in locals():
            cnx.close()

    content_tpl = """
    <h2>Solde des étudiants</h2>
    {% if soldes %}
    <table class="table table-striped table-sm">
      <thead>
        <tr>
          <th>Numéro</th>
          <th>Nom</th>
          <th>Prénom</th>
          <th>Solde</th>
        </tr>
      </thead>
      <tbody>
      {% for s in soldes %}
        <tr>
          <td>{{ s.Num_Etudiant }}</td>
          <td>{{ s.Nom }}</td>
          <td>{{ s.Prenom }}</td>
          <td>{{ "%.2f"|format(s.Solde_Actuel or 0) }} €</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
      <p>Aucun compte.</p>
    {% endif %}
    """
    inner_html = render_template_string(content_tpl, soldes=soldes)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/etudiants/nouveau", methods=["GET", "POST"])
@login_required
def new_student():
    if request.method == "POST":
        num = request.form.get("num", "").strip()
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()

        if len(num) != 8:
            flash("Num_Etudiant doit faire 8 caractères.", "danger")
        elif not nom or not prenom:
            flash("Nom et prénom obligatoires.", "danger")
        else:
            try:
                cnx = get_db()
                cursor = cnx.cursor()

                # Pas d'auth étudiant : mot de passe factice
                fake_pwd_hash = "RODELIKA_NO_LOGIN"

                sql_user = """
                    INSERT INTO users (Num_Etudiant, Nom, Prenom, Password_Hash)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql_user, (num, nom, prenom, fake_pwd_hash))

                sql_compte = """
                    INSERT INTO Compte (Num_Etudiant, Solde_Actuel)
                    VALUES (%s, 0.00)
                """
                cursor.execute(sql_compte, (num,))

                cnx.commit()
                flash(f"Étudiant {num} créé avec succès.", "success")
                return redirect(url_for("list_students"))
            except mysql.connector.Error as e:
                flash(f"Erreur BDD : {e}", "danger")
            finally:
                if "cnx" in locals():
                    cnx.close()

    content_tpl = """
    <h2>Nouvel étudiant</h2>
    <form method="post" style="max-width:500px;">
      <div class="mb-3">
        <label class="form-label">Numéro d'étudiant (8 caractères)</label>
        <input class="form-control" type="text" name="num" maxlength="8" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Nom</label>
        <input class="form-control" type="text" name="nom" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Prénom</label>
        <input class="form-control" type="text" name="prenom" required>
      </div>
      <button class="btn btn-primary" type="submit">Créer</button>
    </form>
    """
    inner_html = render_template_string(content_tpl)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/bonus", methods=["GET", "POST"])
@login_required
def add_bonus():
    """
    Attribution d'un bonus CREDITER sur un compte étudiant.
    -> Montant variable (positif uniquement).
    -> Utilise la procédure stockée CrediterCompte.
    """
    if request.method == "POST":
        num = request.form.get("num", "").strip()
        montant_str = request.form.get("montant", "").strip()
        commentaire = request.form.get("commentaire", "").strip() or "Bonus Rodelika Web"

        # Conversion montant (accepte virgule)
        try:
            montant = float(montant_str.replace(",", "."))
        except ValueError:
            flash("Montant invalide.", "danger")
            montant = None

        if montant is not None:
            if montant <= 0:
                flash("Le montant du bonus doit être strictement positif.", "danger")
            else:
                try:
                    cnx = get_db()
                    cursor = cnx.cursor()
                    cursor.callproc("CrediterCompte", [num, montant, commentaire])
                    cnx.commit()
                    flash(f"Bonus de {montant:.2f} € attribué à {num}.", "success")
                    return redirect(url_for("list_soldes"))
                except mysql.connector.Error as e:
                    flash(f"Erreur BDD : {e}", "danger")
                finally:
                    if "cnx" in locals():
                        cnx.close()

    content_tpl = """
    <h2>Attribuer un bonus</h2>
    <form method="post" style="max-width:500px;">
      <div class="mb-3">
        <label class="form-label">Numéro d'étudiant</label>
        <input class="form-control" type="text" name="num" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Montant du bonus (€)</label>
        <input class="form-control" type="number" step="0.01" name="montant" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Commentaire</label>
        <input class="form-control" type="text" name="commentaire" placeholder="Bonus, campagne, etc.">
      </div>
      <button class="btn btn-success" type="submit">Attribuer le bonus</button>
    </form>
    """
    inner_html = render_template_string(content_tpl)
    return render_template_string(BASE_HTML, content=inner_html)


# ===========================
# MAIN
# ===========================

if __name__ == "__main__":
    import argparse

    ensure_default_admin()  # création éventuelle de admin/admin pour le dev

    parser = argparse.ArgumentParser(description="Serveur web Rodelika")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute (par défaut 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port d'écoute (par défaut 8080)")
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug Flask")
    args = parser.parse_args()

    app.run(
        host=args.host,
        port=args.port,
        debug=bool(args.debug),
    )
