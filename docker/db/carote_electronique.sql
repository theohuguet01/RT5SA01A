-- Init carote_electronique (MySQL 8.3)

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET time_zone = '+00:00';

DROP DATABASE IF EXISTS carote_electronique;
CREATE DATABASE carote_electronique
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE carote_electronique;

SET FOREIGN_KEY_CHECKS = 0;

-- =========================
-- Tables
-- =========================

DROP TABLE IF EXISTS Transactions;
DROP TABLE IF EXISTS Carte;
DROP TABLE IF EXISTS Compte;
DROP TABLE IF EXISTS Agents;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  Num_Etudiant   CHAR(8)      NOT NULL,
  Nom           VARCHAR(255)  NOT NULL,
  Prenom        VARCHAR(255)  NOT NULL,
  Password_Hash VARCHAR(255)  NOT NULL,
  Date_Creation DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (Num_Etudiant)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Agents (
  id            INT           NOT NULL AUTO_INCREMENT,
  Identifiant   VARCHAR(50)   NOT NULL,
  Nom           VARCHAR(255)  NOT NULL,
  Prenom        VARCHAR(255)  NOT NULL,
  Password_Hash VARCHAR(255)  NOT NULL,
  Role          ENUM('ADMIN','AGENT','PROF') NOT NULL DEFAULT 'AGENT',
  Date_Creation DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY Identifiant (Identifiant)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Compte (
  Num_Etudiant   CHAR(8)       NOT NULL,
  Solde_Actuel   DECIMAL(10,2) NOT NULL DEFAULT '0.00',
  Date_Ouverture DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (Num_Etudiant)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Carte (
  id            INT          NOT NULL AUTO_INCREMENT,
  Num_Etudiant  CHAR(8)      NOT NULL,
  Num_Carte     VARCHAR(15)  NOT NULL,
  Date_Creation DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  Actif         TINYINT(1)   NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_carte (Num_Carte),
  KEY fk_carte_user (Num_Etudiant)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Transactions (
  id               BIGINT       NOT NULL AUTO_INCREMENT,
  Num_Etudiant      CHAR(8)      NOT NULL,
  Montant           DECIMAL(10,2) NOT NULL,
  Type              ENUM('CREDIT','DEBIT') NOT NULL,
  Date_Transaction   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  Commentaire        VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY fk_transaction_compte (Num_Etudiant)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================
-- Foreign Keys
-- =========================

ALTER TABLE Compte
  ADD CONSTRAINT fk_compte_user
  FOREIGN KEY (Num_Etudiant) REFERENCES users (Num_Etudiant);

ALTER TABLE Carte
  ADD CONSTRAINT fk_carte_user
  FOREIGN KEY (Num_Etudiant) REFERENCES users (Num_Etudiant);

ALTER TABLE Transactions
  ADD CONSTRAINT fk_transaction_compte
  FOREIGN KEY (Num_Etudiant) REFERENCES Compte (Num_Etudiant);

SET FOREIGN_KEY_CHECKS = 1;

-- =========================
-- Trigger
-- =========================

DROP TRIGGER IF EXISTS trg_after_insert_transactions;

DELIMITER $$
CREATE TRIGGER trg_after_insert_transactions
AFTER INSERT ON Transactions
FOR EACH ROW
BEGIN
  IF NEW.Type = 'CREDIT' THEN
    UPDATE Compte
      SET Solde_Actuel = Solde_Actuel + NEW.Montant
      WHERE Num_Etudiant = NEW.Num_Etudiant;
  ELSEIF NEW.Type = 'DEBIT' THEN
    UPDATE Compte
      SET Solde_Actuel = Solde_Actuel - NEW.Montant
      WHERE Num_Etudiant = NEW.Num_Etudiant;
  END IF;
END $$
DELIMITER ;

-- =========================
-- Routines (sans DEFINER)
-- =========================

DROP PROCEDURE IF EXISTS CrediterCompte;
DROP PROCEDURE IF EXISTS DebiterCompte;

DELIMITER $$

CREATE PROCEDURE CrediterCompte(
  IN p_Num_Etudiant CHAR(8),
  IN p_Montant      DECIMAL(10,2),
  IN p_Commentaire  VARCHAR(255)
)
BEGIN
  DECLARE v_exists INT DEFAULT 0;

  IF p_Montant <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Le montant du crédit doit être strictement positif';
  END IF;

  SELECT COUNT(*) INTO v_exists
  FROM Compte
  WHERE Num_Etudiant = p_Num_Etudiant;

  IF v_exists = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Compte inexistant pour cet étudiant';
  END IF;

  INSERT INTO Transactions (Num_Etudiant, Montant, Type, Commentaire)
  VALUES (p_Num_Etudiant, p_Montant, 'CREDIT', p_Commentaire);
END $$

CREATE PROCEDURE DebiterCompte(
  IN p_Num_Etudiant CHAR(8),
  IN p_Montant      DECIMAL(10,2),
  IN p_Commentaire  VARCHAR(255)
)
BEGIN
  DECLARE v_solde  DECIMAL(10,2);
  DECLARE v_exists INT DEFAULT 0;

  IF p_Montant <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Le montant du débit doit être strictement positif';
  END IF;

  SELECT COUNT(*), Solde_Actuel
  INTO v_exists, v_solde
  FROM Compte
  WHERE Num_Etudiant = p_Num_Etudiant;

  IF v_exists = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Compte inexistant pour cet étudiant';
  END IF;

  IF v_solde < p_Montant THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Solde insuffisant pour effectuer ce débit';
  END IF;

  INSERT INTO Transactions (Num_Etudiant, Montant, Type, Commentaire)
  VALUES (p_Num_Etudiant, p_Montant, 'DEBIT', p_Commentaire);
END $$

DELIMITER ;

-- =========================
-- Data: Agents uniquement
-- =========================

INSERT INTO Agents (id, Identifiant, Nom, Prenom, Password_Hash, Role, Date_Creation) VALUES
(1,'admin.uvsq','UVSQ','Admin','$2b$12$1na3/amynQF.0gV7b1yiIO4nCy1tcQS.wnDI6DVw9lq.z0mIqL5Lu','ADMIN','2025-11-25 11:20:18'),
(2,'marina.krasnicki','KRASNICKI','Marina','$2b$12$1na3/amynQF.0gV7b1yiIO4nCy1tcQS.wnDI6DVw9lq.z0mIqL5Lu','AGENT','2025-11-25 11:24:41'),
(3,'samuel.marty','MARTY','Samuel','$2b$12$1na3/amynQF.0gV7b1yiIO4nCy1tcQS.wnDI6DVw9lq.z0mIqL5Lu','PROF','2025-11-25 14:24:00');
