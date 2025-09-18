# 🎓 SAE 5.01 / 5.02 — La Carotte Électronique

## 📌 Présentation
Ce projet, réalisé dans le cadre des SAÉ 5.01 *Concevoir, réaliser et présenter une solution technique* et SAÉ 5.02 *Piloter un projet informatique*, consiste à développer un **système de porte-monnaie électronique basé sur des cartes à puce**.  

Le projet a pour but de comprendre les mécanismes de sécurité des cartes à puce et de développer des compétences en gestion de projet collaboratif avec Git/GitHub.

---

## 🎯 Objectifs pédagogiques
- Concevoir un système de paiement électronique sécurisé avec carte à puce.  
- Développer des logiciels associés (personnalisation, gestion, borne de recharge, machine à café).  
- Mettre en place une base de données centralisée pour la gestion des comptes.  
- Utiliser Git/GitHub pour le travail collaboratif.  
- Étudier et documenter les vulnérabilités possibles.  

---

## 🧩 Composants du projet
Le projet se décompose en plusieurs briques logicielles et matérielles :

1. **Carte à puce — Rubrovitamin**  
   - Stockage des informations étudiant et du solde.  
   - Instructions APDU pour créditer, débiter, lire et personnaliser.  
   - Sécurités implémentées (anti-arrachement, PIN/PUK en option).

2. **Logiciel de personnalisation — Lubiana**  
   - Outil Python (pyscard) pour l’administration.  
   - Attribution de carte, initialisation du solde, consultation des données.

3. **Base de données — Purple Dragon**  
   - Stocke les étudiants, opérations (bonus, crédits, débits).  
   - Implémentation MySQL/MariaDB.

4. **Logiciel de gestion — Rodelika**  
   - Interface Python CLI connectée à la BDD.  
   - Permet d’ajouter un étudiant, attribuer des bonus, consulter soldes.

5. **Application Web — Rodelika Web**  
   - Backend : Node.js (Express + MySQL2).  
   - Frontend : Vue.js.

6. **Borne de recharge — Berlicum**  
   - Consultation des bonus disponibles.  
   - Transfert des bonus vers la carte.  
   - Recharge manuelle (simulation carte bancaire).  

7. **Machine à café — Lunar White**  
   - Débit automatique de **0,20 €** par boisson (café/thé/chocolat).  
   - Fonctionnement autonome basé uniquement sur la carte.

## 🔐 Sécurité et vulnérabilités
Les sécurités minimales à implémenter :
- ✅ Anti-arrachement obligatoire.  
- 🔒 PIN/PUK facultatif.  
- 🚫 Protection contre la rejoue (facultatif).  

Un **rapport dédié** doit analyser les vulnérabilités possibles (logicielles, matérielles, réseau) et proposer des contre-mesures.

---

## 📦 Livrables attendus
- Code source complet (sur GitHub/GitLab).  
- Rapport PDF (20–30 pages, focus vulnérabilités).  
- Présentation (Beamer ou PPT).  
- Démonstration fonctionnelle (15 min + questions).  
- Examen sur table (2h).  

---

## 🚀 Installation / Dépendances
### Python
- `pyscard`  
- `mysql-connector`

### Node.js (Rodelika Web)
- `express`  
- `mysql2`  
- `vue`  

### Base de données
- MySQL/MariaDB ≥ 10.5

---

## ✍️ Auteur & Révision
Projet **La Carotte Électronique**  
IUT de Vélizy — Département Réseaux & Télécommunications
UVSQ - Université Paris-Saclay