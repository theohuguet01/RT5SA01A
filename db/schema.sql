USE carote_electronique;

-- On nettoie pour pouvoir rejouer le script sans erreur
SET FOREIGN_KEY_CHECKS
= 0;
DROP TABLE IF EXISTS Transactions;
DROP TABLE IF EXISTS Carte;
DROP TABLE IF EXISTS Compte;
DROP TABLE IF EXISTS Agents;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS
= 1;

-- TABLE ÉTUDIANTS
CREATE TABLE users
(
    Num_Etudiant CHAR(8) PRIMARY KEY,
    Nom VARCHAR(255) NOT NULL,
    Prenom VARCHAR(255) NOT NULL,
    Password_Hash VARCHAR(255) NOT NULL,
    Date_Creation DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE AGENTS ADMINISTRATIFS
CREATE TABLE Agents
(
    id INT
    AUTO_INCREMENT PRIMARY KEY,
    Identifiant   VARCHAR
    (50) NOT NULL UNIQUE,
    Nom           VARCHAR
    (255) NOT NULL,
    Prenom        VARCHAR
    (255) NOT NULL,
    Password_Hash VARCHAR
    (255) NOT NULL,
    Role          ENUM
    ('ADMIN', 'AGENT', 'PROF') NOT NULL DEFAULT 'AGENT',
    Date_Creation DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

    -- TABLE COMPTE ÉTUDIANT
    CREATE TABLE Compte
    (
        Num_Etudiant CHAR(8) PRIMARY KEY,
        Solde_Actuel DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        Date_Ouverture DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- TABLE CARTE ÉTUDIANT
    CREATE TABLE Carte
    (
        id INT
        AUTO_INCREMENT PRIMARY KEY,
    Num_Etudiant   CHAR
        (8) NOT NULL,
    Num_Carte      VARCHAR
        (15) NOT NULL,
    Date_Creation  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Actif          BOOLEAN NOT NULL DEFAULT TRUE
);

        -- TABLE TRANSACTIONS
        CREATE TABLE Transactions
        (
            id BIGINT
            AUTO_INCREMENT PRIMARY KEY,
    Num_Etudiant      CHAR
            (8) NOT NULL,
    Montant           DECIMAL
            (10,2) NOT NULL,
    Type              ENUM
            ('CREDIT', 'DEBIT') NOT NULL,
    Date_Transaction  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Commentaire       VARCHAR
            (255)
);

            -- CONTRAINTES (FK + UNIQUE) ------------------------------

            ALTER TABLE Compte
ADD CONSTRAINT fk_compte_user
    FOREIGN KEY (Num_Etudiant)
    REFERENCES users(Num_Etudiant);

            ALTER TABLE Carte
ADD CONSTRAINT uq_carte UNIQUE (Num_Carte);

            ALTER TABLE Carte
ADD CONSTRAINT fk_carte_user
    FOREIGN KEY (Num_Etudiant)
    REFERENCES users(Num_Etudiant);

            ALTER TABLE Transactions
ADD CONSTRAINT fk_transaction_compte
    FOREIGN KEY (Num_Etudiant)
    REFERENCES Compte(Num_Etudiant);
