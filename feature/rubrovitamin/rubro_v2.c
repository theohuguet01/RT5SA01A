#include <avr/io.h>
#include <stdint.h>
#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <stdarg.h>

//---------------------
//
// Programme bourse.c
//
//---------------------


// déclaration des fonctions d'entrée/sortie
// écrites en assembleur dans le fichier io.s
extern void sendbytet0(uint8_t b);
extern uint8_t recbytet0(void);

// variables globales en static ram
uint8_t cla, ins, p1, p2, p3;  // header de commande
uint8_t sw1, sw2;              // status word


//======================================================================
// ATR
//======================================================================

#define size_atr 0x6
const char atr_str[size_atr] PROGMEM = "rubro";

// Procédure qui renvoie l'ATR
void atr(void)
{
    int i;

    sendbytet0(0x3b);              // définition du protocole
    uint8_t n = 0xF0 + size_atr + 1;
    sendbytet0(n);                 // nombre d'octets d'historique
    sendbytet0(0x01);              // TA
    sendbytet0(0x05);              // TB
    sendbytet0(0x05);              // TC
    sendbytet0(0x00);              // TD protocole t=0
    sendbytet0(0x00);              // CAT

    // Boucle d'envoi des octets d'historique
    for (i = 0; i < size_atr; i++)
    {
        sendbytet0(pgm_read_byte(atr_str + i));
    }
}

//======================================================================
// Version
//======================================================================

#define size_ver 4
const char ver_str[size_ver] PROGMEM = "2.00";

// émission de la version
// CLA = 0x81, INS = 0x00
void version(void)
{
    int i;
    // vérification de la taille
    if (p3 != size_ver)
    {
        sw1 = 0x6c;       // taille incorrecte
        sw2 = size_ver;   // taille attendue
        return;
    }
    sendbytet0(ins);      // acquittement
    // émission des données
    for (i = 0; i < p3; i++)
    {
        sendbytet0(pgm_read_byte(ver_str + i));
    }
    sw1 = 0x90;
    sw2 = 0x00;
}


//======================================================================
// Transactions anti-arrachement
//======================================================================

// nombre maximal d'opérations par transaction
#define max_ope     8
// taille maximale totale des données échangées lors d'une transaction
#define max_data    64
// définition de l'état du buffer -- plein est une valeur aléatoire
typedef enum { vide = 0, plein = 0x1c } state_t;

// la variable buffer de transaction mémorisée en eeprom
struct
{
    state_t  state;                 // état
    uint8_t  nb_ope;                // nombre d'opération dans la transaction
    uint8_t  tt[max_ope];           // table des tailles des transferts
    uint8_t* p_dst[max_ope];        // table des adresses de destination des transferts
    uint8_t  buffer[max_data];      // données à transférer
}
ee_trans EEMEM = { vide };          // l'état doit être initialisé à "vide"

// validation d'une transaction
void valide(void)
{
    state_t e;          // état
    uint8_t nb_ope;     // nombre d'opérations dans la transaction
    uint8_t *p_src;
    uint8_t *p_dst;
    uint8_t i, j;
    uint8_t tt;         // taille des données à transférer

    // lecture de l'état du buffer
    e = eeprom_read_byte((uint8_t*)&ee_trans.state);
    // s'il y a quelque chose dans le buffer, transférer les données aux destinations
    if (e == plein)     // un état non plein est interprété comme vide
    {
        // lecture du nombre d'opérations
        nb_ope = eeprom_read_byte(&ee_trans.nb_ope);
        p_src  = ee_trans.buffer;
        // boucle sur le nombre d'opérations
        for (i = 0; i < nb_ope; i++)
        {
            // lecture de la taille à transférer
            tt = eeprom_read_byte(&ee_trans.tt[i]);
            // lecture de la destination
            p_dst = (uint8_t*)eeprom_read_word((uint16_t*)&ee_trans.p_dst[i]);
            // transfert eeprom -> eeprom du buffer vers la destination
            for (j = 0; j < tt; j++)
            {
                eeprom_write_byte(p_dst++, eeprom_read_byte(p_src++));
            }
        }
    }
    eeprom_write_byte((uint8_t*)&ee_trans.state, vide);
}

// engagement d'une transaction
// appel de la forme engage(n1, p_src1, p_dst1, n2, p_src2, p_dst2, ... 0)
void engage(int tt, ...)
{
    va_list args;
    uint8_t nb_ope;
    uint8_t *p_src;
    uint8_t *p_buf;

    // mettre l'état à "vide"
    eeprom_write_byte((uint8_t*)&ee_trans.state, vide);

    va_start(args, tt);
    nb_ope = 0;
    p_buf  = ee_trans.buffer;
    while (tt != 0)
    {
        // transférer les données dans le buffer
        p_src = va_arg(args, uint8_t*);
        eeprom_write_block(p_src, p_buf, tt);
        p_buf += tt;
        // écriture de l'adresse de destination
        eeprom_write_word((uint16_t*)&ee_trans.p_dst[nb_ope],
                          (uint16_t)va_arg(args, uint8_t*));
        // écriture de la taille des données
        eeprom_write_byte(&ee_trans.tt[nb_ope], tt);
        nb_ope++;
        tt = va_arg(args, int);   // taille suivante dans la liste
    }
    // écriture du nombre de transactions
    eeprom_write_byte(&ee_trans.nb_ope, nb_ope);
    va_end(args);
    // mettre l'état à "data"
    eeprom_write_byte((uint8_t*)&ee_trans.state, plein);
}


//======================================================================
// Personnalisation + PUK généré
//======================================================================

#define MAX_PERSO 32
uint8_t ee_taille_perso EEMEM = 0;
unsigned char ee_perso[MAX_PERSO] EEMEM;


//======================================================================
// PIN / PUK + anti-rejoue + solde
//======================================================================

#define PIN_LEN      4
#define PUK_LEN      6
#define PIN_TRY_MAX  3
#define PUK_TRY_MAX  5

// PIN par défaut
#define DEFAULT_PIN0  1
#define DEFAULT_PIN1  2
#define DEFAULT_PIN2  3
#define DEFAULT_PIN3  4

// PIN/PUK stockés en EEPROM
uint8_t ee_pin[PIN_LEN] EEMEM = { DEFAULT_PIN0, DEFAULT_PIN1, DEFAULT_PIN2, DEFAULT_PIN3 };
// PUK initial, sera écrasé par intro_perso
uint8_t ee_puk[PUK_LEN] EEMEM = { '9','9','9','9','9','9' };

// Compteurs d'essais PIN/PUK
uint8_t ee_pin_tries EEMEM = PIN_TRY_MAX;
uint8_t ee_puk_tries EEMEM = PUK_TRY_MAX;

// Compteur anti-rejoue (16 bits, little endian)
uint16_t ee_ctr EEMEM = 0;

// Solde en centimes
uint16_t ee_solde EEMEM = 0;

// Flag RAM : PIN vérifié pour la prochaine opération sensible
uint8_t pin_ok = 0;


//--- utilitaires PUK --------------------------------------------------

// Génération d'un chiffre décimal à partir d'un nibble (0..15)
static uint8_t nibble_to_digit(uint8_t x)
{
    x &= 0x0F;
    if (x > 9)
        x -= 6; // mappe 10-15 dans 4-9
    return x;
}

// Génère un PUK de 6 chiffres ASCII '0'..'9' à partir des données perso
void compute_puk_from_perso(uint8_t *perso, uint8_t len, uint8_t *puk_out)
{
    uint16_t h1 = 0x1357;
    uint16_t h2 = 0x2468;
    uint8_t i;
    uint8_t b;

    for (i = 0; i < len; i++)
    {
        b = perso[i];
        h1 = (h1 + b + (uint16_t)(i * 17)) ^ ((uint16_t)b << (i & 7));
        h2 = (h2 ^ (b + (uint16_t)(i * 31))) + (h1 >> 3);
    }

    uint8_t d[PUK_LEN];
    d[0] = nibble_to_digit((uint8_t)(h1      ));
    d[1] = nibble_to_digit((uint8_t)(h1 >> 4 ));
    d[2] = nibble_to_digit((uint8_t)(h1 >> 8 ));
    d[3] = nibble_to_digit((uint8_t)(h2      ));
    d[4] = nibble_to_digit((uint8_t)(h2 >> 4 ));
    d[5] = nibble_to_digit((uint8_t)(h2 >> 8 ));

    for (i = 0; i < PUK_LEN; i++)
    {
        puk_out[i] = (uint8_t)('0' + d[i]);  // ASCII '0'..'9'
    }
}


//======================================================================
// intro_perso : perso + génération PUK + reset PIN/PUK/ctr/solde
//======================================================================

// CLA = 0x81, INS = 0x01
// APDU : 81 01 00 00 Lc [perso]
void intro_perso(void)
{
    int i;
    uint8_t perso[MAX_PERSO];
    uint8_t puk[PUK_LEN];

    // buffers pour réinitialisation de sécurité
    uint8_t def_pin[PIN_LEN] = {
        DEFAULT_PIN0,
        DEFAULT_PIN1,
        DEFAULT_PIN2,
        DEFAULT_PIN3
    };
    uint8_t pin_tries = PIN_TRY_MAX;
    uint8_t puk_tries = PUK_TRY_MAX;
    uint16_t ctr0 = 0;      // compteur anti-rejoue remis à 0
    uint16_t solde0 = 0;    // solde remis à 0

    if (p3 > MAX_PERSO)
    {
        sw1 = 0x6c;
        sw2 = MAX_PERSO;
        return;
    }

    sendbytet0(ins);   // acquittement

    // réception de la perso
    for (i = 0; i < p3; i++)
    {
        perso[i] = (uint8_t)recbytet0();
    }

    // Générer le PUK à partir de la perso reçue
    compute_puk_from_perso(perso, (uint8_t)p3, puk);

    // mémorisation de :
    //  - taille de la perso
    //  - perso
    //  - PUK
    //  - PIN par défaut
    //  - compteurs d'essais PIN / PUK
    //  - compteur anti-rejoue = 0
    //  - solde = 0
    engage(
        1,  &p3,               &ee_taille_perso,
        p3, perso,             ee_perso,
        PUK_LEN, puk,          ee_puk,
        PIN_LEN, def_pin,      ee_pin,
        1,  &pin_tries,        &ee_pin_tries,
        1,  &puk_tries,        &ee_puk_tries,
        2,  (uint8_t*)&ctr0,   (uint8_t*)&ee_ctr,
        2,  (uint8_t*)&solde0, (uint8_t*)&ee_solde,
        0
    );
    valide();

    // en RAM, pas de PIN vérifié
    pin_ok = 0;

    sw1 = 0x90;
    sw2 = 0x00;
}

// lecture perso
// CLA = 0x81, INS = 0x02
// APDU : 81 02 00 00 Lc
void lire_perso(void)
{
    int i;
    uint8_t t;

    t = eeprom_read_byte(&ee_taille_perso);
    if (p3 != t)
    {
        sw1 = 0x6c;
        sw2 = t;
        return;
    }
    sendbytet0(ins);
    for (i = 0; i < p3; i++)
    {
        sendbytet0(eeprom_read_byte(ee_perso + i));
    }
    sw1 = 0x90;
    sw2 = 0x00;
}


//======================================================================
// PIN / PUK : vérification, changement, reset par PUK
// (CLA = 0x82)
//======================================================================

uint8_t pin_est_bloque(void)
{
    uint8_t t = eeprom_read_byte(&ee_pin_tries);
    return (t == 0);
}

uint8_t puk_est_bloque(void)
{
    uint8_t t = eeprom_read_byte(&ee_puk_tries);
    return (t == 0);
}

// Vérification du PIN
// CLA = 0x82, INS = 0x04
// APDU : 82 04 00 00 04 [PIN(4 octets)]
void verifier_pin(void)
{
    uint8_t i;
    uint8_t tries;
    uint8_t ok = 1;
    uint8_t v, ref;

    if (pin_est_bloque())
    {
        sw1 = 0x69;    // PIN bloqué
        sw2 = 0x83;
        return;
    }

    if (p3 != PIN_LEN)
    {
        sw1 = 0x6C;
        sw2 = PIN_LEN;
        return;
    }

    sendbytet0(ins);  // acquittement

    tries = eeprom_read_byte(&ee_pin_tries);

    for (i = 0; i < PIN_LEN; i++)
    {
        v   = recbytet0();
        ref = eeprom_read_byte(&ee_pin[i]);
        if (v != ref)
            ok = 0;
    }

    if (ok)
    {
        pin_ok = 1;  // autorisation pour UNE prochaine opération
        eeprom_write_byte(&ee_pin_tries, PIN_TRY_MAX);
        sw1 = 0x90;
        sw2 = 0x00;
    }
    else
    {
        if (tries > 0) tries--;
        eeprom_write_byte(&ee_pin_tries, tries);
        pin_ok = 0;

        if (tries == 0)
        {
            sw1 = 0x69;   // PIN désormais bloqué
            sw2 = 0x83;
        }
        else
        {
            sw1 = 0x63;   // échec PIN, nb d’essais restants dans SW2
            sw2 = tries;
        }
    }
}

// Changement de PIN (avec ancien PIN)
// CLA = 0x82, INS = 0x05
// APDU : 82 05 00 00 08 = [old PIN(4)][new PIN(4)]
void changer_pin(void)
{
    uint8_t i;
    uint8_t ok = 1;
    uint8_t v, ref;
    uint8_t tries;
    uint8_t new_pin[PIN_LEN];

    if (pin_est_bloque())
    {
        sw1 = 0x69;
        sw2 = 0x83;
        return;
    }

    if (p3 != 2 * PIN_LEN)
    {
        sw1 = 0x6C;
        sw2 = 2 * PIN_LEN;
        return;
    }

    sendbytet0(ins);

    tries = eeprom_read_byte(&ee_pin_tries);

    // vérification ancien PIN
    for (i = 0; i < PIN_LEN; i++)
    {
        v   = recbytet0();
        ref = eeprom_read_byte(&ee_pin[i]);
        if (v != ref)
            ok = 0;
    }

    // lecture du nouveau PIN dans un buffer RAM
    for (i = 0; i < PIN_LEN; i++)
    {
        new_pin[i] = recbytet0();
    }

    if (!ok)
    {
        if (tries > 0) tries--;
        eeprom_write_byte(&ee_pin_tries, tries);
        pin_ok = 0;

        if (tries == 0)
        {
            sw1 = 0x69;
            sw2 = 0x83;
        }
        else
        {
            sw1 = 0x63;
            sw2 = tries;
        }
        return;
    }

    // ancien PIN correct -> on met à jour le PIN
    engage(PIN_LEN, new_pin, ee_pin, 0);
    valide();

    // on peut considérer que le PIN est vérifié pour UNE op (changer_pin lui-même)
    pin_ok = 0; // et on le consomme

    eeprom_write_byte(&ee_pin_tries, PIN_TRY_MAX);
    sw1 = 0x90;
    sw2 = 0x00;
}

// Reset du PIN avec le PUK
// CLA = 0x82, INS = 0x06
// APDU : 82 06 00 00 0A [PUK(6)][nouveau PIN(4)]
void reset_pin_par_puk(void)
{
    uint8_t i;
    uint8_t ok = 1;
    uint8_t v, ref;
    uint8_t tries;
    uint8_t new_pin[PIN_LEN];

    if (puk_est_bloque())
    {
        sw1 = 0x69;
        sw2 = 0x83;
        return;
    }

    if (p3 != (PUK_LEN + PIN_LEN))
    {
        sw1 = 0x6C;
        sw2 = PUK_LEN + PIN_LEN;
        return;
    }

    sendbytet0(ins);

    tries = eeprom_read_byte(&ee_puk_tries);
    if (tries == 0)
    {
        sw1 = 0x69;   // PUK bloqué
        sw2 = 0x83;
        return;
    }

    // vérification PUK
    for (i = 0; i < PUK_LEN; i++)
    {
        v   = recbytet0();
        ref = eeprom_read_byte(&ee_puk[i]);
        if (v != ref)
            ok = 0;
    }

    // lecture du nouveau PIN
    for (i = 0; i < PIN_LEN; i++)
    {
        new_pin[i] = recbytet0();
    }

    if (!ok)
    {
        if (tries > 0) tries--;
        eeprom_write_byte(&ee_puk_tries, tries);

        if (tries == 0)
        {
            sw1 = 0x69;
            sw2 = 0x83;
        }
        else
        {
            sw1 = 0x63;
            sw2 = tries;
        }
        return;
    }

    // PUK correct -> on réinitialise le PIN + essais PIN/PUK
    engage(PIN_LEN, new_pin, ee_pin, 0);
    valide();
    eeprom_write_byte(&ee_pin_tries, PIN_TRY_MAX);
    eeprom_write_byte(&ee_puk_tries, PUK_TRY_MAX);
    pin_ok = 0;   // pas de PIN “ouvert” après, il faudra faire un VERIFY

    sw1 = 0x90;
    sw2 = 0x00;
}

// petite fonction utilitaire : vérifie que PIN OK avant opérations sensibles
uint8_t check_pin_ok(void)
{
    if (!pin_ok)
    {
        sw1 = 0x69;
        sw2 = 0x82;   // security status not satisfied
        return 0;
    }
    return 1;
}

// anti-rejoue : vérifie que le compteur de transaction reçu en P1/P2
// correspond au compteur stocké en EEPROM, puis l'incrémente.
uint8_t check_and_update_ctr(void)
{
    uint16_t ctr_eep;
    uint16_t ctr_req;

    ctr_eep = eeprom_read_word(&ee_ctr);
    ctr_req = (uint16_t)p1 | ((uint16_t)p2 << 8);

    if (ctr_req != ctr_eep)
    {
        sw1 = 0x69;
        sw2 = 0x84;  // données incorrectes / anti-rejoue
        return 0;
    }

    ctr_eep++;
    eeprom_write_word(&ee_ctr, ctr_eep);
    return 1;
}


//======================================================================
// Gestion du solde (CLA 0x82)
//======================================================================

// lecture du solde
// CLA = 0x82, INS = 0x01
// APDU : 82 01 00 00 02
void lire_solde(void)
{
    uint16_t s;

    // il faut être authentifié par PIN pour CETTE opération
    if (!check_pin_ok())
        return;
    // on consomme le ticket PIN pour ne pas réutiliser l'authentification
    pin_ok = 0;

    if (p3 != 2)
    {
        sw1 = 0x6c;
        sw2 = 2;
        return;
    }
    sendbytet0(ins);
    s = eeprom_read_word(&ee_solde);
    sendbytet0(s & 0xff);   // little endian
    sendbytet0(s >> 8);
    sw1 = 0x90;
    sw2 = 0x00;
}

// crédit
// CLA = 0x82, INS = 0x02
// APDU : 82 02 P1 P2 02 [montant LSB][montant MSB]
void credit(void)
{
    uint16_t s;
    uint16_t c;

    // PIN obligatoire pour CETTE opération
    if (!check_pin_ok())
        return;
    // on consomme l'autorisation PIN
    pin_ok = 0;

    // anti-rejoue
    if (!check_and_update_ctr())
        return;

    if (p3 != 2)
    {
        sw1 = 0x6c;
        sw2 = 2;
        return;
    }
    sendbytet0(ins);
    // lire le montant à créditer (little endian)
    c  = recbytet0();
    c |= (uint16_t)recbytet0() << 8;
    s = eeprom_read_word(&ee_solde);
    s += c;
    if (s < c)
    {
        sw1 = 0x61;   // overflow
        sw2 = 0x00;
        return;
    }
    eeprom_write_word(&ee_solde, s);
    sw1 = 0x90;
    sw2 = 0x00;
}

// débit
// CLA = 0x82, INS = 0x03
// APDU : 82 03 P1 P2 02 [montant LSB][montant MSB]
void debit(void)
{
    uint16_t s;
    uint16_t d;

    // PIN obligatoire pour CETTE opération
    if (!check_pin_ok())
        return;
    // on consomme l'autorisation PIN
    pin_ok = 0;

    // anti-rejoue
    if (!check_and_update_ctr())
        return;

    if (p3 != 2)
    {
        sw1 = 0x6c;
        sw2 = 2;
        return;
    }
    sendbytet0(ins);
    d  = recbytet0();
    d |= (uint16_t)recbytet0() << 8;
    s = eeprom_read_word(&ee_solde);
    if (d > s)
    {
        sw1 = 0x61;   // solde insuffisant
        sw2 = 0x00;
        return;
    }
    s -= d;
    engage(2, (uint8_t*)&s, (uint8_t*)&ee_solde, 0);
    valide();
    sw1 = 0x90;
    sw2 = 0x00;
}

// Lecture du compteur anti-rejoue
// CLA = 0x82, INS = 0x07
// APDU : 82 07 00 00 02
void lire_compteur(void)
{
    uint16_t ctr;

    if (p3 != 2)
    {
        sw1 = 0x6C;
        sw2 = 2;
        return;
    }

    sendbytet0(ins);
    ctr = eeprom_read_word(&ee_ctr);
    sendbytet0(ctr & 0xFF);      // LSB
    sendbytet0(ctr >> 8);        // MSB
    sw1 = 0x90;
    sw2 = 0x00;
}


//======================================================================
// Programme principal
//======================================================================

int main(void)
{
    // initialisation des ports
    ACSR  = 0x80;
    PRR   = 0x87;
    PORTB = 0xff;
    DDRB  = 0xff;
    PORTC = 0xff;
    DDRC  = 0xff;
    DDRD  = 0x00;
    PORTD = 0xff;
    ASSR  = (1 << EXCLK) + (1 << AS2);

    // ATR
    atr();
    valide();
    sw2    = 0;      // pour éviter de le répéter dans toutes les commandes
    pin_ok = 0;      // PIN non vérifié au reset

    // boucle de traitement des commandes
    for (;;)
    {
        // lecture de l'entête
        cla = recbytet0();
        ins = recbytet0();
        p1  = recbytet0();
        p2  = recbytet0();
        p3  = recbytet0();
        sw2 = 0;

        switch (cla)
        {
        case 0x81:   // version / perso
            switch (ins)
            {
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
                sw1 = 0x6d; // INS inconnu
                sw2 = 0x00;
                break;
            }
            break;

        case 0x82:   // opérations sécurisées
            switch (ins)
            {
            case 0x01:
                lire_solde();
                break;
            case 0x02:
                credit();
                break;
            case 0x03:
                debit();
                break;
            case 0x04:
                verifier_pin();
                break;
            case 0x05:
                changer_pin();
                break;
            case 0x06:
                reset_pin_par_puk();
                break;
            case 0x07:
                lire_compteur();
                break;
            default:
                sw1 = 0x6d; // INS inconnu
                sw2 = 0x00;
                break;
            }
            break;

        default:
            sw1 = 0x6e; // CLA inconnue
            sw2 = 0x00;
            break;
        }

        // envoi du status word
        sendbytet0(sw1);
        sendbytet0(sw2);
    }

    return 0;
}
