#include <avr/io.h>
#include <stdint.h>
#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <stdarg.h>

// ------------------------------------------------------
// Déclarations des fonctions d'E/S (en assembleur, io.s)
// ------------------------------------------------------
extern void sendbytet0(uint8_t b);
extern uint8_t recbytet0(void);

// ----------------------
// Variables globales RAM
// ----------------------
uint8_t cla, ins, p1, p2, p3;  // header APDU
uint8_t sw1, sw2;              // status word

// ========================
// ATR (identification carte)
// ========================
#define ATR_HIST_LEN 7
const char atr_hist[ATR_HIST_LEN] PROGMEM = "carotte";

void atr(void)
{
    uint8_t i;

    // Octet TS : convention de codage
    sendbytet0(0x3B);

    // T0 : nombre d'octets d'historique (dans les 4 bits de poids faible)
    // ici : 5 octets de paramètres + ATR_HIST_LEN octets d'historique
    uint8_t n = 0xF0 + ATR_HIST_LEN + 1;
    sendbytet0(n);

    // Paramètres (TA, TB, TC, TD, CAT) – valeurs d'exemple
    sendbytet0(0x01); // TA
    sendbytet0(0x05); // TB
    sendbytet0(0x05); // TC
    sendbytet0(0x00); // TD (T=0)
    sendbytet0(0x00); // CAT

    // Octets d'historique : "carotte"
    for (i = 0; i < ATR_HIST_LEN; i++) {
        sendbytet0(pgm_read_byte(atr_hist + i));
    }
}

// ==========================
// Version de l'application
// ==========================
#define SIZE_VER 4
const char ver_str[SIZE_VER] PROGMEM = "1.00";

// CLS 0x81 / INS 0x00
// APDU : 81 00 00 00 04  → "1.00" 90 00
void version(void)
{
    uint8_t i;

    // Vérification de la taille attendue
    if (p3 != SIZE_VER) {
        sw1 = 0x6C;        // taille incorrecte
        sw2 = SIZE_VER;    // taille correcte attendue
        return;
    }

    // Acquittement : renvoi du INS
    sendbytet0(ins);

    // Envoi de la chaîne "1.00"
    for (i = 0; i < p3; i++) {
        sendbytet0(pgm_read_byte(ver_str + i));
    }

    sw1 = 0x90;
}

// ==========================
// Transactions anti-arrachement
// ==========================

// nombre maximal d'opérations dans une transaction
#define MAX_OPE   3
// taille maximale du buffer de données
#define MAX_DATA  64

// état du buffer de transaction
typedef enum { vide = 0, plein = 0x1C } state_t;

// Structure stockée en EEPROM
struct {
    state_t  state;               // état
    uint8_t  nb_ope;              // nombre d'opérations
    uint8_t  tt[MAX_OPE];         // tailles des transferts
    uint8_t* p_dst[MAX_OPE];      // destinations
    uint8_t  buffer[MAX_DATA];    // données à transférer
} ee_trans EEMEM = { vide };

// Validation de la transaction : applique les écritures en attente
void valide(void)
{
    state_t e;
    uint8_t nb_ope;
    uint8_t *p_src, *p_dst;
    uint8_t i, j;
    uint8_t tt;

    // lecture de l'état
    e = (state_t)eeprom_read_byte((uint8_t*)&ee_trans.state);

    if (e == plein) {
        // il y a des données à valider
        nb_ope = eeprom_read_byte(&ee_trans.nb_ope);
        p_src  = ee_trans.buffer;

        for (i = 0; i < nb_ope; i++) {
            // taille à transférer
            tt = eeprom_read_byte(&ee_trans.tt[i]);
            // adresse de destination
            p_dst = (uint8_t*)eeprom_read_word((uint16_t*)&ee_trans.p_dst[i]);
            // transfert EEPROM → EEPROM
            for (j = 0; j < tt; j++) {
                eeprom_write_byte(p_dst++, eeprom_read_byte(p_src++));
            }
        }
    }

    // on repasse l'état à "vide"
    eeprom_write_byte((uint8_t*)&ee_trans.state, vide);
}

// Engagement d'une transaction
// Forme : engage(n1, p_src1, p_dst1, n2, p_src2, p_dst2, ... 0)
void engage(int tt, ...)
{
    va_list args;
    uint8_t nb_ope = 0;
    uint8_t *p_src;
    uint8_t *p_buf;

    // on commence par marquer le buffer comme vide
    eeprom_write_byte((uint8_t*)&ee_trans.state, vide);

    va_start(args, tt);
    p_buf = ee_trans.buffer;

    while (tt != 0) {
        // 1) copie des données source dans le buffer
        p_src = va_arg(args, uint8_t*);
        eeprom_write_block(p_src, p_buf, tt);
        p_buf += tt;

        // 2) enregistrement de l'adresse de destination
        eeprom_write_word((uint16_t*)&ee_trans.p_dst[nb_ope],
                          (uint16_t)va_arg(args, uint8_t*));

        // 3) enregistrement de la taille
        eeprom_write_byte(&ee_trans.tt[nb_ope], tt);

        nb_ope++;
        tt = va_arg(args, int);   // taille suivante
    }

    // nombre total d'opérations
    eeprom_write_byte(&ee_trans.nb_ope, nb_ope);
    va_end(args);

    // on marque l'état comme "plein" (des données à valider au prochain reset)
    eeprom_write_byte((uint8_t*)&ee_trans.state, plein);
}

// ===================================
// Personnalisation (nom / prénom etc.)
// ===================================
#define MAX_PERSO 32

uint8_t ee_taille_perso EEMEM = 0;
unsigned char ee_perso[MAX_PERSO] EEMEM;

// CLS 0x81 / INS 0x01
// APDU : 81 01 00 00 Lc "data"
void intro_perso(void)
{
    int i;
    unsigned char data[MAX_PERSO];

    // vérification de la taille
    if (p3 > MAX_PERSO) {
        sw1 = 0x6C;         // P3 incorrect
        sw2 = MAX_PERSO;    // taille max
        return;
    }

    // acquittement
    sendbytet0(ins);

    // réception des données en RAM (pas d'accès EEPROM durant la RX)
    for (i = 0; i < p3; i++) {
        data[i] = recbytet0();
    }

    // transaction EEPROM : taille + données
    // 1 octet de taille, puis p3 octets de perso
    engage(1,  &p3,  &ee_taille_perso,
           p3, data, ee_perso,
           0);
    // Validation immédiate (sur reset réel ce serait au prochain ATR)
    valide();

    sw1 = 0x90;
}

// CLS 0x81 / INS 0x02
// Lecture personnalisation
// APDU : 81 02 00 00 Lc → "data" 90 00
void lire_perso(void)
{
    int i;
    uint8_t taille;

    // taille réelle en EEPROM
    taille = eeprom_read_byte(&ee_taille_perso);

    // si P3 ne matche pas, renvoyer erreur + taille attendue dans SW2
    if (p3 != taille) {
        sw1 = 0x6C;
        sw2 = taille;
        return;
    }

    // acquittement
    sendbytet0(ins);

    // émission des données
    for (i = 0; i < p3; i++) {
        sendbytet0(eeprom_read_byte(ee_perso + i));
    }

    sw1 = 0x90;
}

// ====================
// Gestion du solde
// ====================
uint16_t ee_solde EEMEM = 0;

// CLS 0x82 / INS 0x01
// Lire solde : 82 01 00 00 02 → MSB LSB 90 00 (big endian)
void lire_solde(void)
{
    uint16_t s;

    if (p3 != 2) {
        sw1 = 0x6C;
        sw2 = 2;
        return;
    }

    // acquittement
    sendbytet0(ins);

    // lecture du solde en EEPROM (en centimes)
    s = eeprom_read_word(&ee_solde);

    // big endian : d'abord octet de poids fort, puis octet de poids faible
    sendbytet0((uint8_t)(s >> 8));
    sendbytet0((uint8_t)(s & 0xFF));

    sw1 = 0x90;
}

// CLS 0x82 / INS 0x02
// Crédit : 82 02 00 00 02 MSB LSB → 90 00 ou 61 00 (overflow)
void credit(void)
{
    uint16_t s;
    uint16_t c;
    uint16_t nouveau;

    if (p3 != 2) {
        sw1 = 0x6C;
        sw2 = 2;
        return;
    }

    // acquittement
    sendbytet0(ins);

    // montant à créditer (big endian : MSB, LSB)
    c  = (uint16_t)recbytet0() << 8;
    c |= (uint16_t)recbytet0();

    // solde actuel
    s = eeprom_read_word(&ee_solde);
    nouveau = s + c;

    // test de débordement (overflow)
    if (nouveau < s) {
        sw1 = 0x61;  // erreur de capacité
        return;
    }

    // écriture directe (on pourrait aussi utiliser engage/valide)
    eeprom_write_word(&ee_solde, nouveau);

    sw1 = 0x90;
}

// CLS 0x82 / INS 0x03
// Débit : 82 03 00 00 02 MSB LSB → 90 00 ou 61 00 (solde insuffisant)
void debit(void)
{
    uint16_t s;
    uint16_t d;
    uint16_t nouveau;

    if (p3 != 2) {
        sw1 = 0x6C;
        sw2 = 2;
        return;
    }

    // acquittement
    sendbytet0(ins);

    // montant à débiter (big endian)
    d  = (uint16_t)recbytet0() << 8;
    d |= (uint16_t)recbytet0();

    // lecture du solde actuel
    s = eeprom_read_word(&ee_solde);.

    // solde insuffisant
    if (d > s) {
        sw1 = 0x61;
        return;
    }

    nouveau = s - d;

    // ici on utilise une transaction (anti-arrachement)
    engage(2, (uint8_t*)&nouveau, (uint8_t*)&ee_solde,
           0);
    valide();

    sw1 = 0x90;
}

// =========================
// Programme principal carte
// =========================
int main(void)
{
    // Initialisation bas niveau (ports, alim, etc.)
    ACSR  = 0x80;
    PRR   = 0x87;
    PORTB = 0xFF;
    DDRB  = 0xFF;
    PORTC = 0xFF;
    DDRC  = 0xFF;
    DDRD  = 0x00;
    PORTD = 0xFF;
    ASSR  = (1 << EXCLK) | (1 << AS2);

    // Envoi de l'ATR
    atr();

    // Validation d'une éventuelle transaction en attente
    valide();

    sw2 = 0;    // SW2 vaut 0 par défaut

    // Boucle infinie de traitement APDU
    for (;;) {
        // Lecture de l'entête APDU
        cla = recbytet0();
        ins = recbytet0();
        p1  = recbytet0();
        p2  = recbytet0();
        p3  = recbytet0();

        sw2 = 0;  // réinitialisation

        switch (cla) {
            // -----------------------------
            // Classe 0x81 : personnalisation
            // -----------------------------
            case 0x81:
                switch (ins) {
                    case 0x00:
                        version();
                        break;
                    case 0x01:
                        intro_perso();
                        break;
                    case 0x02:
                        lire_perso();
                        break;
                    default:
                        sw1 = 0x6D; // INS inconnu
                        break;
                }
                break;

            // -----------------------------
            // Classe 0x82 : gestion du solde
            // -----------------------------
            case 0x82:
                switch (ins) {
                    case 0x01:
                        lire_solde();
                        break;
                    case 0x02:
                        credit();
                        break;
                    case 0x03:
                        debit();
                        break;
                    default:
                        sw1 = 0x6D; // INS inconnu
                        break;
                }
                break;

            default:
                sw1 = 0x6E; // CLA inconnue
                break;
        }

        // Envoi du status word à la fin de chaque commande
        sendbytet0(sw1);
        sendbytet0(sw2);
    }

    return 0;
}
