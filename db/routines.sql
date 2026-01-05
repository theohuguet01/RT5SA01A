USE carote_electronique;

DELIMITER //

CREATE TRIGGER trg_after_insert_transactions
AFTER
INSERT ON
Transactions
FOR
EACH
ROW
BEGIN
    IF NEW.Type = 'CREDIT' THEN
    UPDATE Compte
        SET Solde_Actuel = Solde_Actuel + NEW.Montant
        WHERE Num_Etudiant = NEW.Num_Etudiant;
    ELSEIF NEW.Type = 'DEBIT' THEN
    UPDATE Compte
        SET Solde_Actuel = Solde_Actuel - NEW.Montant
        WHERE Num_Etudiant = NEW.Num_Etudiant;
END
IF;
END//

CREATE PROCEDURE CrediterCompte (
    IN p_Num_Etudiant CHAR
(8),
    IN p_Montant      DECIMAL
(10,2),
    IN p_Commentaire  VARCHAR
(255)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;

    IF p_Montant <= 0 THEN
        SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT
    = 'Le montant du crédit doit être strictement positif';
END
IF;

    SELECT COUNT(*)
INTO v_exists
FROM Compte
WHERE Num_Etudiant = p_Num_Etudiant;

IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
SET MESSAGE_TEXT
= 'Compte inexistant pour cet étudiant';
END
IF;

    INSERT INTO Transactions
    (Num_Etudiant, Montant, Type, Commentaire)
VALUES
    (p_Num_Etudiant, p_Montant, 'CREDIT', p_Commentaire);
END//

CREATE PROCEDURE DebiterCompte (
    IN p_Num_Etudiant CHAR
(8),
    IN p_Montant      DECIMAL
(10,2),
    IN p_Commentaire  VARCHAR
(255)
)
BEGIN
    DECLARE v_solde   DECIMAL
    (10,2);
    DECLARE v_exists  INT DEFAULT 0;

IF p_Montant <= 0 THEN
        SIGNAL SQLSTATE '45000'
SET MESSAGE_TEXT
= 'Le montant du débit doit être strictement positif';
END
IF;

    SELECT COUNT(*), Solde_Actuel
INTO v_exists
, v_solde
    FROM Compte
    WHERE Num_Etudiant = p_Num_Etudiant;

IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
SET MESSAGE_TEXT
= 'Compte inexistant pour cet étudiant';
END
IF;

    IF v_solde < p_Montant THEN
        SIGNAL SQLSTATE '45000'
SET MESSAGE_TEXT
= 'Solde insuffisant pour effectuer ce débit';
END
IF;

    INSERT INTO Transactions
    (Num_Etudiant, Montant, Type, Commentaire)
VALUES
    (p_Num_Etudiant, p_Montant, 'DEBIT', p_Commentaire);
END//

DELIMITER ;
