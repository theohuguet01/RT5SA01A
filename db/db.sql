-- TABLE ÉTUDIANTS
CREATE TABLE users (
    Num_Etudiant  CHAR(8) PRIMARY KEY,
    Nom           VARCHAR(255) NOT NULL,
    Prenom        VARCHAR(255) NOT NULL,
    Password_Hash VARCHAR(255) NOT NULL,
    Date_Creation DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE AGENTS ADMINISTRATIFS
CREATE TABLE Agents (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    Identifiant   VARCHAR(50) NOT NULL UNIQUE,
    Nom           VARCHAR(255) NOT NULL,
    Prenom        VARCHAR(255) NOT NULL,
    Password_Hash VARCHAR(255) NOT NULL,
    Role          ENUM('ADMIN', 'AGENT') NOT NULL DEFAULT 'AGENT',
    Date_Creation DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE COMPTE ÉTUDIANT
CREATE TABLE Compte (
    Num_Etudiant   CHAR(8) PRIMARY KEY,
    Solde_Actuel   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Date_Ouverture DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE CARTE ÉTUDIANT
CREATE TABLE Carte (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    Num_Etudiant   CHAR(8) NOT NULL,
    Num_Carte      VARCHAR(15) NOT NULL,
    Date_Creation  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Actif          BOOLEAN NOT NULL DEFAULT TRUE
);

-- TABLE TRANSACTIONS
CREATE TABLE Transactions (
    id                BIGINT AUTO_INCREMENT PRIMARY KEY,
    Num_Etudiant      CHAR(8) NOT NULL,
    Montant           DECIMAL(10,2) NOT NULL,
    Type              ENUM('CREDIT', 'DEBIT') NOT NULL,
    Date_Transaction  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Commentaire       VARCHAR(255)
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


DELIMITER //

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
END //
//

CREATE PROCEDURE CrediterCompte (
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
END //
//

CREATE PROCEDURE DebiterCompte (
    IN p_Num_Etudiant CHAR(8),
    IN p_Montant      DECIMAL(10,2),
    IN p_Commentaire  VARCHAR(255)
)
BEGIN
    DECLARE v_solde   DECIMAL(10,2);
    DECLARE v_exists  INT DEFAULT 0;

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
END //
//

DELIMITER ;
