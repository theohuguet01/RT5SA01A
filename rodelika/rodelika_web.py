#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rodelika Web (Flask)
--------------------
Version Web du logiciel de gestion, avec :
- Authentification via Agents (bcrypt) + rôles (ADMIN / AGENT / PROF)
- Gestion étudiants / comptes / bonus
- Gestion des agents/profs (ADMIN / AGENT)
- Logo UVSQ IUT Vélizy dans la navbar
- Footer corporate
- Dashboard d'accueil (stats + dernières transactions)
- Liste complète des transactions avec recherche
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
app.secret_key = os.environ.get(
    "RODELIKA_SECRET_KEY",
    "kNOYSs9JgOubtCmPoQYcHDtIEQb1MorM9ZN7EW_5W0M=",
)


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# =========================
# AUTH / ROLES
# =========================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "agent_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def current_role():
    return session.get("agent_role")


def require_roles(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_role() not in roles:
                flash("Vous n'êtes pas autorisé à accéder à cette page.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# =========================
# TEMPLATE GLOBAL
# =========================

BASE_HTML = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Rodelika Web</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

  <style>
    body { background: #f4f6fb; }
    .navbar {
      box-shadow: 0 2px 8px rgba(15,23,42,0.15);
      background: linear-gradient(90deg, #111827 0%, #1f2937 50%, #0f172a 100%) !important;
    }
    .navbar-nav .nav-link {
      padding: .35rem .75rem;
      border-radius: 999px;
      font-size: .9rem;
      margin-right: .25rem;
    }
    .navbar-nav .nav-link.active,
    .navbar-nav .nav-link:hover {
      background: rgba(148,163,184,.25);
    }
    main.container { max-width: 1100px; }

    .card-kpi {
      border: 0;
      border-radius: .9rem;
      box-shadow: 0 6px 18px rgba(15,23,42,.08);
    }
    .card-kpi .fw-semibold {
      font-size: .8rem; text-transform: uppercase;
      color: #6b7280; letter-spacing:.06em;
    }
    .card-kpi .fs-4 {
      font-weight: 600; color: #111827;
    }
    table.table thead th {
      background: #eef1f7;
      border-bottom: 2px solid #d1d5db;
      font-size:.82rem; text-transform:uppercase; color:#4b5563;
      letter-spacing:.05em;
    }

    footer {
      border-top: 1px solid #e5e7eb;
      background:#f9fafb !important;
      font-size:.8rem;
    }
    footer small { color:#6b7280; }
  </style>
</head>

<body class="d-flex flex-column min-vh-100">

<nav class="navbar navbar-expand-lg navbar-dark mb-4">
  <div class="container-fluid">
    <a class="navbar-brand d-flex align-items-center" href="{{ url_for('index') }}">
      <img src="https://www.uvsq.fr/medias/photo/iut-velizy-villacoublay-logo-2020-ecran_1580904185110-jpg?ID_FICHE=214049"
           style="height:40px; background:white; border-radius:4px; padding:2px;">
      <span class="ms-2" style="font-weight:600; letter-spacing:.03em; text-transform:uppercase; font-size:.9rem;">
        Rodelika Web
      </span>
    </a>

    <div class="navbar-nav">
      {% if session.get('agent_id') %}
        {% set role=session.get('agent_role') %}

        {% if role in ['ADMIN','AGENT'] %}
          <a class="nav-link {% if request.endpoint=='list_students'%}active{% endif %}"
             href="{{ url_for('list_students') }}">Étudiants</a>
          <a class="nav-link {% if request.endpoint=='list_soldes'%}active{% endif %}"
             href="{{ url_for('list_soldes') }}">Soldes</a>
          <a class="nav-link {% if request.endpoint=='new_student'%}active{% endif %}"
             href="{{ url_for('new_student') }}">Nouvel étudiant</a>
          <a class="nav-link {% if request.endpoint=='add_bonus'%}active{% endif %}"
             href="{{ url_for('add_bonus') }}">Attribuer un bonus</a>
          <a class="nav-link {% if request.endpoint=='list_transactions'%}active{% endif %}"
             href="{{ url_for('list_transactions') }}">Transactions</a>
          <a class="nav-link {% if request.endpoint=='list_agents'%}active{% endif %}"
             href="{{ url_for('list_agents') }}">Agents</a>

        {% elif role=='PROF' %}
          <a class="nav-link {% if request.endpoint=='list_students'%}active{% endif %}"
             href="{{ url_for('list_students') }}">Étudiants</a>
          <a class="nav-link {% if request.endpoint=='list_soldes'%}active{% endif %}"
             href="{{ url_for('list_soldes') }}">Soldes</a>
          <a class="nav-link {% if request.endpoint=='add_bonus'%}active{% endif %}"
             href="{{ url_for('add_bonus') }}">Attribuer un bonus</a>
        {% endif %}
      {% endif %}
    </div>

    <div class="ms-auto d-flex align-items-center">
      {% if session.get('agent_id') %}
        <span class="navbar-text text-light me-3">
          {{ session.get('agent_prenom') }} {{ session.get('agent_nom') }}
          ({{ session.get('agent_role') }})
        </span>
        <a href="{{ url_for('logout') }}" class="btn btn-outline-light btn-sm">Déconnexion</a>
      {% else %}
        <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-sm">Connexion</a>
      {% endif %}
    </div>

  </div>
</nav>

<main class="container flex-fill mb-5">
  {% with m=get_flashed_messages(with_categories=true) %}
    {% if m %}
      {% for cat,msg in m %}
        <div class="alert alert-{{cat}} alert-dismissible fade show" role="alert">
          {{msg}}
          <button class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {{ content|safe }}
</main>

<footer class="text-center text-muted py-3 mt-auto">
  <small>
    © 2025 Rodelika – Projet « La Carotte Électronique » –
    IUT de Vélizy-Villacoublay (UVSQ / Université Paris-Saclay).
    <br>Application interne de gestion des comptes étudiants.
  </small>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

</body>
</html>
"""


# =========================
# LOGIN / LOGOUT
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        password = request.form.get("password", "").strip()

        agent = None
        try:
            cnx = get_db()
            cursor = cnx.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Agents WHERE Identifiant=%s", (identifiant,))
            agent = cursor.fetchone()
        except mysql.connector.Error as e:
            flash(f"Erreur BDD : {e}", "danger")
        finally:
            if "cnx" in locals():
                cnx.close()

        if agent and bcrypt.checkpw(password.encode(), agent["Password_Hash"].encode()):
            session["agent_id"] = agent["id"]
            session["agent_ident"] = agent["Identifiant"]
            session["agent_role"] = agent["Role"]
            session["agent_nom"] = agent["Nom"].upper()
            session["agent_prenom"] = agent["Prenom"].capitalize()
            flash("Connexion réussie.", "success")
            return redirect(url_for("index"))
        else:
            flash("Identifiant ou mot de passe invalide.", "danger")

    tpl = """
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
    inner_html = render_template_string(tpl)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/logout")
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for("login"))


# =========================
# DASHBOARD / ACCUEIL
# =========================

@app.route("/")
@login_required
def index():
    stats = {
        "nb_etudiants": 0,
        "nb_comptes": 0,
        "solde_total": 0.0,
        "credits_today": 0.0,
    }
    transactions = []

    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS n FROM users")
        stats["nb_etudiants"] = cursor.fetchone()["n"]

        cursor.execute("SELECT COUNT(*) AS n FROM Compte")
        stats["nb_comptes"] = cursor.fetchone()["n"]

        cursor.execute("SELECT SUM(Solde_Actuel) AS total FROM Compte")
        stats["solde_total"] = cursor.fetchone()["total"] or 0.0

        cursor.execute("""
            SELECT SUM(Montant) AS total
            FROM Transactions
            WHERE Type='CREDIT'
              AND DATE(Date_Transaction)=CURDATE()
        """)
        stats["credits_today"] = cursor.fetchone()["total"] or 0.0

        cursor.execute("""
            SELECT 
                t.Date_Transaction,
                t.Num_Etudiant,
                t.Montant, t.Type, t.Commentaire,
                u.Nom, u.Prenom
            FROM Transactions t
            JOIN users u ON u.Num_Etudiant=t.Num_Etudiant
            ORDER BY t.Date_Transaction DESC
            LIMIT 10
        """)
        transactions = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
    finally:
        if "cnx" in locals():
            cnx.close()

    tpl = """
    <div class="mb-4">
      <h1 class="mb-2">Bonjour {{ agent_prenom }} {{ agent_nom }}</h1>
      <p class="text-muted">
        Interface de gestion des comptes étudiants — bonus, paiements et soldes.
      </p>
    </div>

    <div class="row mb-4">
      <div class="col-md-3 mb-3">
        <div class="card card-kpi"><div class="card-body">
          <div class="fw-semibold">Étudiants</div>
          <div class="fs-4">{{ stats.nb_etudiants }}</div>
        </div></div>
      </div>
      <div class="col-md-3 mb-3">
        <div class="card card-kpi"><div class="card-body">
          <div class="fw-semibold">Comptes</div>
          <div class="fs-4">{{ stats.nb_comptes }}</div>
        </div></div>
      </div>
      <div class="col-md-3 mb-3">
        <div class="card card-kpi"><div class="card-body">
          <div class="fw-semibold">Solde total</div>
          <div class="fs-4">{{ "%.2f"|format(stats.solde_total) }} €</div>
        </div></div>
      </div>
      <div class="col-md-3 mb-3">
        <div class="card card-kpi"><div class="card-body">
          <div class="fw-semibold">Crédits du jour</div>
          <div class="fs-4">{{ "%.2f"|format(stats.credits_today) }} €</div>
        </div></div>
      </div>
    </div>

    <div class="row mb-5">
      <div class="col-lg-4">
        <h2>Actions rapides</h2>
        <ul>
          <li><a href="{{ url_for('list_students') }}">Liste des étudiants</a></li>
          <li><a href="{{ url_for('list_soldes') }}">Solde des comptes</a></li>
          <li><a href="{{ url_for('new_student') }}">Créer un étudiant</a></li>
          <li><a href="{{ url_for('add_bonus') }}">Attribuer un bonus</a></li>
          <li><a href="{{ url_for('list_transactions') }}">Toutes les transactions</a></li>
        </ul>
      </div>

      <div class="col-lg-8">
        <h2>Dernières transactions</h2>

        {% if transactions %}
        <div class="table-responsive">
          <table class="table table-sm table-striped">
            <thead>
              <tr>
                <th>Date</th>
                <th>Étudiant</th>
                <th>Type</th>
                <th class="text-end">Montant</th>
                <th>Commentaire</th>
              </tr>
            </thead>
            <tbody>
            {% for t in transactions %}
              <tr>
                <td>{{ t.Date_Transaction.strftime("%d/%m/%Y %H:%M") }}</td>
                <td>{{ t.Num_Etudiant }} – {{ t.Prenom }} {{ t.Nom }}</td>
                <td>
                  {% if t.Type == "CREDIT" %}
                    <span class="badge bg-success">CREDIT</span>
                  {% else %}
                    <span class="badge bg-danger">DEBIT</span>
                  {% endif %}
                </td>
                <td class="text-end font-monospace">
                  {% if t.Type == "DEBIT" %}
                    -{{ "%.2f"|format(t.Montant) }} €
                  {% else %}
                    +{{ "%.2f"|format(t.Montant) }} €
                  {% endif %}
                </td>
                <td>{{ t.Commentaire }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>

        <a href="{{ url_for('list_transactions') }}" class="btn btn-outline-secondary btn-sm mt-2">
          Voir toutes les transactions
        </a>
        {% else %}
          <p class="text-muted">Aucune transaction enregistrée.</p>
        {% endif %}
      </div>
    </div>
    """
    inner_html = render_template_string(
        tpl,
        stats=stats,
        transactions=transactions,
        agent_prenom=session.get("agent_prenom"),
        agent_nom=session.get("agent_nom"),
    )
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# LISTE ÉTUDIANTS
# =========================

@app.route("/etudiants")
@login_required
def list_students():
    etudiants = []
    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("SELECT Num_Etudiant, Nom, Prenom FROM users ORDER BY Num_Etudiant")
        etudiants = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
    finally:
        if "cnx" in locals():
            cnx.close()

    tpl = """
    <h2>Liste des étudiants</h2>

    {% if etudiants %}
    <div class="table-responsive">
      <table class="table table-striped table-sm">
        <thead>
          <tr><th>Numéro</th><th>Nom</th><th>Prénom</th></tr>
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
    </div>
    {% else %}
      <p class="text-muted">Aucun étudiant.</p>
    {% endif %}
    """
    inner_html = render_template_string(tpl, etudiants=etudiants)
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# SOLDES
# =========================

@app.route("/soldes")
@login_required
def list_soldes():
    soldes = []
    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.Num_Etudiant, u.Nom, u.Prenom, c.Solde_Actuel
            FROM users u
            JOIN Compte c ON c.Num_Etudiant = u.Num_Etudiant
            ORDER BY u.Num_Etudiant
        """)
        soldes = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
    finally:
        if "cnx" in locals():
            cnx.close()

    tpl = """
    <h2>Solde des étudiants</h2>

    {% if soldes %}
    <div class="table-responsive">
      <table class="table table-striped table-sm">
        <thead>
          <tr><th>Numéro</th><th>Nom</th><th>Prénom</th><th>Solde</th></tr>
        </thead>
        <tbody>
        {% for s in soldes %}
          <tr>
            <td>{{ s.Num_Etudiant }}</td>
            <td>{{ s.Nom }}</td>
            <td>{{ s.Prenom }}</td>
            <td>{{ "%.2f"|format(s.Solde_Actuel) }} €</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <p class="text-muted">Aucun compte.</p>
    {% endif %}
    """
    inner_html = render_template_string(tpl, soldes=soldes)
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# CRÉER ÉTUDIANT (ADMIN/AGENT)
# =========================

@app.route("/etudiants/nouveau", methods=["GET", "POST"])
@login_required
@require_roles("ADMIN", "AGENT")
def new_student():
    if request.method == "POST":
        num = request.form.get("num", "").strip()
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()

        if len(num) != 8:
            flash("Numéro étudiant = 8 caractères.", "danger")
        elif not nom or not prenom:
            flash("Nom et prénom obligatoires.", "danger")
        else:
            try:
                cnx = get_db()
                cursor = cnx.cursor()
                cursor.execute("""
                    INSERT INTO users (Num_Etudiant, Nom, Prenom, Password_Hash)
                    VALUES (%s, %s, %s, 'RODELIKA_NO_LOGIN')
                """, (num, nom, prenom))
                cursor.execute("""
                    INSERT INTO Compte (Num_Etudiant, Solde_Actuel)
                    VALUES (%s, 0.00)
                """, (num,))
                cnx.commit()
                flash("Étudiant créé.", "success")
                return redirect(url_for("list_students"))
            except mysql.connector.Error as e:
                flash(f"Erreur BDD : {e}", "danger")
            finally:
                if "cnx" in locals():
                    cnx.close()

    tpl = """
    <h2>Nouvel étudiant</h2>
    <form method="post" style="max-width:500px;">
      <div class="mb-3">
        <label>Numéro (8 caractères)</label>
        <input class="form-control" name="num" required maxlength="8">
      </div>
      <div class="mb-3">
        <label>Nom</label>
        <input class="form-control" name="nom" required>
      </div>
      <div class="mb-3">
        <label>Prénom</label>
        <input class="form-control" name="prenom" required>
      </div>
      <button class="btn btn-primary">Créer</button>
    </form>
    """
    inner_html = render_template_string(tpl)
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# BONUS (tous les rôles connectés)
# =========================

@app.route("/bonus", methods=["GET", "POST"])
@login_required
def add_bonus():
    if request.method == "POST":
        num = request.form.get("num", "").strip()
        montant_str = request.form.get("montant", "").strip()
        commentaire_base = request.form.get("commentaire", "").strip() or "Bonus"

        try:
            montant = float(montant_str.replace(",", "."))
        except ValueError:
            flash("Montant invalide.", "danger")
            montant = None

        if montant is not None and montant > 0:
            commentaire = f"{commentaire_base} (par {session.get('agent_prenom')} {session.get('agent_nom')})"
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
        else:
            flash("Le montant doit être strictement positif.", "danger")

    tpl = """
    <h2>Attribuer un bonus</h2>
    <form method="post" style="max-width:500px;">
      <div class="mb-3">
        <label>Numéro étudiant</label>
        <input class="form-control" name="num" required>
      </div>
      <div class="mb-3">
        <label>Montant (€)</label>
        <input class="form-control" name="montant" required step="0.01">
      </div>
      <div class="mb-3">
        <label>Commentaire</label>
        <input class="form-control" name="commentaire">
      </div>
      <button class="btn btn-success">Attribuer</button>
    </form>
    """
    inner_html = render_template_string(tpl)
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# TRANSACTIONS (ADMIN/AGENT)
# =========================

@app.route("/transactions")
@login_required
@require_roles("ADMIN", "AGENT")
def list_transactions():
    q = request.args.get("q", "").strip()
    transactions = []
    params = []

    sql = """
        SELECT 
            t.Date_Transaction,
            t.Num_Etudiant,
            t.Montant, t.Type, t.Commentaire,
            u.Nom, u.Prenom
        FROM Transactions t
        JOIN users u ON u.Num_Etudiant = t.Num_Etudiant
    """

    if q:
        sql += """
            WHERE t.Num_Etudiant = %s
               OR u.Nom LIKE %s
               OR u.Prenom LIKE %s
        """
        like = f"%{q}%"
        params = [q, like, like]

    sql += " ORDER BY t.Date_Transaction DESC LIMIT 200"

    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute(sql, params)
        transactions = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
    finally:
        if "cnx" in locals():
            cnx.close()

    tpl = """
    <h2>Transactions</h2>

    <form class="row g-2 mb-3" method="get">
      <div class="col-md-4">
        <input class="form-control" type="text" name="q"
               placeholder="Recherche (numéro, nom, prénom)" value="{{ q }}">
      </div>
      <div class="col-md-2">
        <button class="btn btn-primary">Filtrer</button>
      </div>
      {% if q %}
      <div class="col-md-2">
        <a class="btn btn-outline-secondary" href="{{ url_for('list_transactions') }}">Réinitialiser</a>
      </div>
      {% endif %}
    </form>

    {% if transactions %}
    <div class="table-responsive">
      <table class="table table-sm table-striped">
        <thead>
          <tr>
            <th>Date</th><th>Étudiant</th><th>Type</th>
            <th class="text-end">Montant</th><th>Commentaire</th>
          </tr>
        </thead>
        <tbody>
        {% for t in transactions %}
          <tr>
            <td>{{ t.Date_Transaction.strftime("%d/%m/%Y %H:%M") }}</td>
            <td>{{ t.Num_Etudiant }} – {{ t.Prenom }} {{ t.Nom }}</td>
            <td>
              {% if t.Type == "CREDIT" %}
                <span class="badge bg-success">CREDIT</span>
              {% else %}
                <span class="badge bg-danger">DEBIT</span>
              {% endif %}
            </td>
            <td class="text-end font-monospace">
              {% if t.Type == "DEBIT" %}
                -{{ "%.2f"|format(t.Montant) }} €
              {% else %}
                +{{ "%.2f"|format(t.Montant) }} €
              {% endif %}
            </td>
            <td>{{ t.Commentaire }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <p class="text-muted">Aucune transaction ne correspond au filtre.</p>
    {% endif %}
    """
    inner_html = render_template_string(tpl, transactions=transactions, q=q)
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# GESTION DES AGENTS (ADMIN + AGENT)
# =========================

@app.route("/agents")
@login_required
@require_roles("ADMIN", "AGENT")
def list_agents():
    agents = []
    try:
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, Identifiant, Nom, Prenom, Role, Date_Creation
            FROM Agents
            ORDER BY Role, Nom, Prenom
        """)
        agents = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Erreur BDD : {e}", "danger")
    finally:
        if "cnx" in locals():
            cnx.close()

    tpl = """
    <h2>Agents / Profs</h2>

    <p>
      <a href="{{ url_for('new_agent') }}" class="btn btn-primary btn-sm">
        Ajouter un agent / prof
      </a>
    </p>

    {% if agents %}
    <div class="table-responsive">
      <table class="table table-striped table-sm align-middle">
        <thead>
          <tr>
            <th>ID</th>
            <th>Identifiant</th>
            <th>Nom</th>
            <th>Prénom</th>
            <th>Rôle</th>
            <th>Création</th>
          </tr>
        </thead>
        <tbody>
        {% for a in agents %}
          <tr>
            <td>{{ a.id }}</td>
            <td>{{ a.Identifiant }}</td>
            <td>{{ a.Nom }}</td>
            <td>{{ a.Prenom }}</td>
            <td>
              {% if a.Role == 'ADMIN' %}
                <span class="badge bg-danger">ADMIN</span>
              {% elif a.Role == 'AGENT' %}
                <span class="badge bg-primary">AGENT</span>
              {% else %}
                <span class="badge bg-secondary">PROF</span>
              {% endif %}
            </td>
            <td>{{ a.Date_Creation }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <p class="text-muted">Aucun agent/prof enregistré.</p>
    {% endif %}
    """
    inner_html = render_template_string(tpl, agents=agents)
    return render_template_string(BASE_HTML, content=inner_html)


@app.route("/agents/nouveau", methods=["GET", "POST"])
@login_required
@require_roles("ADMIN", "AGENT")
def new_agent():
    role_courant = current_role()

    # ADMIN peut choisir ADMIN / AGENT / PROF
    # AGENT ne peut créer que PROF (rôle verrouillé)
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        password = request.form.get("password", "").strip()
        role_form = (request.form.get("role") or "").strip().upper()

        if not identifiant or not nom or not prenom or not password:
            flash("Tous les champs sont obligatoires.", "danger")
        else:
            if role_courant == "ADMIN":
                if role_form not in ("ADMIN", "AGENT", "PROF"):
                    flash("Rôle invalide.", "danger")
                    return redirect(url_for("new_agent"))
                role_to_create = role_form
            elif role_courant == "AGENT":
                # Forçage en PROF pour un agent
                role_to_create = "PROF"
            else:
                flash("Vous n'êtes pas autorisé à créer des comptes.", "danger")
                return redirect(url_for("index"))

            try:
                pwd_hash = bcrypt.hashpw(
                    password.encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                cnx = get_db()
                cursor = cnx.cursor()
                cursor.execute(
                    """
                    INSERT INTO Agents (Identifiant, Nom, Prenom, Password_Hash, Role)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (identifiant, nom, prenom, pwd_hash, role_to_create),
                )
                cnx.commit()
                flash(f"Compte {role_to_create} créé pour {prenom} {nom}.", "success")
                return redirect(url_for("list_agents"))
            except mysql.connector.Error as e:
                if e.errno == 1062:
                    flash("Identifiant déjà utilisé.", "danger")
                else:
                    flash(f"Erreur BDD : {e}", "danger")
            finally:
                if "cnx" in locals():
                    cnx.close()

    # GET : on affiche le formulaire
    tpl = """
    <h2>Nouvel agent / prof</h2>

    <form method="post" style="max-width:500px;">
      <div class="mb-3">
        <label class="form-label">Identifiant de connexion</label>
        <input class="form-control" name="identifiant" required>
      </div>

      <div class="mb-3">
        <label class="form-label">Nom</label>
        <input class="form-control" name="nom" required>
      </div>

      <div class="mb-3">
        <label class="form-label">Prénom</label>
        <input class="form-control" name="prenom" required>
      </div>

      <div class="mb-3">
        <label class="form-label">Mot de passe</label>
        <input class="form-control" type="password" name="password" required>
      </div>

      {% if role_courant == 'ADMIN' %}
      <div class="mb-3">
        <label class="form-label">Rôle</label>
        <select class="form-select" name="role" required>
          <option value="AGENT">Agent</option>
          <option value="PROF">Prof</option>
          <option value="ADMIN">Admin</option>
        </select>
      </div>
      {% else %}
      <div class="mb-3">
        <label class="form-label">Rôle</label>
        <input class="form-control" value="PROF" disabled>
        <input type="hidden" name="role" value="PROF">
        <div class="form-text">En tant qu'agent, vous ne pouvez créer que des comptes PROF.</div>
      </div>
      {% endif %}

      <button class="btn btn-primary" type="submit">Créer le compte</button>
    </form>
    """
    inner_html = render_template_string(tpl, role_courant=role_courant)
    return render_template_string(BASE_HTML, content=inner_html)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
