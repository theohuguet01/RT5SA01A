/**
 * Machine à café Lunar White - JavaScript
 * Gestion de l'interface interactive et des sons
 * 
 * AMÉLIORATIONS :
 * - Détection automatique de carte (polling toutes les 3 secondes)
 * - Surveillance de déconnexion (toutes les 5 secondes)
 * - Protection anti-faux-positifs (3 erreurs consécutives requises)
 * - Sons sans grésillement (phases progressives)
 * - Vérification du solde avant achat
 * - Retour automatique si carte retirée avant achat
 */

// Variables globales
let currentPin = '';
let currentBalance = 0;
let selectedDrink = null;
let audioContext = null;
let cardDetectionInterval = null;
let cardConnected = false;
let isProcessing = false;
let consecutiveErrors = 0; // Compteur d'erreurs consécutives pour éviter les faux positifs

// Sons simulés avec Web Audio API
class SoundEffects {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    playBeep(frequency = 440, duration = 0.1) {
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.frequency.value = frequency;
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }

    playSuccess() {
        this.playBeep(523.25, 0.1); // C5
        setTimeout(() => this.playBeep(659.25, 0.1), 100); // E5
        setTimeout(() => this.playBeep(783.99, 0.2), 200); // G5
    }

    playError() {
        this.playBeep(200, 0.3);
    }

    playCardInsert() {
        this.playBeep(800, 0.05);
        setTimeout(() => this.playBeep(600, 0.05), 50);
    }

    playCoffeeMaking() {
        // Son réaliste de machine à café avec 5 phases
        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // Phase 1: Démarrage moteur (0-0.8s) - Bruit mécanique grave
        this.playEngineStart(now);

        // Phase 2: Montée en pression (0.8-1.5s) - Sifflement progressif
        setTimeout(() => this.playPressureBuild(now + 0.8), 800);

        // Phase 3: Percolation (1.5-3s) - Glouglou + vapeur
        setTimeout(() => this.playPercolation(now + 1.5), 1500);

        // Phase 4: Écoulement (3-3.5s) - Liquide qui coule
        setTimeout(() => this.playPour(now + 3), 3000);

        // Phase 5: Fin + bip (3.5-4s)
        setTimeout(() => {
            this.playSuccess();
        }, 4000);
    }

    playEngineStart(startTime) {
        // Bruit de moteur qui démarre - Brown noise filtré
        const duration = 0.8;
        const bufferSize = this.audioContext.sampleRate * duration;
        const buffer = this.audioContext.createBuffer(1, bufferSize, this.audioContext.sampleRate);
        const data = buffer.getChannelData(0);

        // Générer du brown noise (bruit basse fréquence)
        let lastOut = 0;
        for (let i = 0; i < bufferSize; i++) {
            const white = Math.random() * 2 - 1;
            data[i] = (lastOut + (0.02 * white)) / 1.02;
            lastOut = data[i];
            data[i] *= 0.3; // Volume modéré

            // Envelope: montée progressive
            const envelope = Math.min(1, i / (bufferSize * 0.3));
            data[i] *= envelope;
        }

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;

        // Filtre passe-bas pour le son grave du moteur
        const filter = this.audioContext.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.value = 200;
        filter.Q.value = 1;

        const gain = this.audioContext.createGain();
        gain.gain.value = 0.4;

        source.connect(filter);
        filter.connect(gain);
        gain.connect(this.audioContext.destination);

        source.start(startTime);
    }

    playPressureBuild(startTime) {
        // Sifflement de montée en pression
        const duration = 0.7;
        const osc = this.audioContext.createOscillator();
        const gain = this.audioContext.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(400, startTime);
        osc.frequency.exponentialRampToValueAtTime(800, startTime + duration);

        gain.gain.setValueAtTime(0, startTime);
        gain.gain.linearRampToValueAtTime(0.15, startTime + 0.1);
        gain.gain.linearRampToValueAtTime(0.08, startTime + duration);

        osc.connect(gain);
        gain.connect(this.audioContext.destination);

        osc.start(startTime);
        osc.stop(startTime + duration);
    }

    playPercolation(startTime) {
        // Glouglou de percolation - Son bouillonnant
        const duration = 1.5;

        // Créer plusieurs oscillateurs pour le glouglou
        for (let i = 0; i < 15; i++) {
            const delay = Math.random() * duration;
            const freq = 100 + Math.random() * 150;
            const bubbleDuration = 0.08 + Math.random() * 0.12;

            const osc = this.audioContext.createOscillator();
            const gain = this.audioContext.createGain();

            osc.type = 'sine';
            osc.frequency.value = freq;

            const bubbleStart = startTime + delay;
            gain.gain.setValueAtTime(0, bubbleStart);
            gain.gain.linearRampToValueAtTime(0.12, bubbleStart + bubbleDuration * 0.3);
            gain.gain.linearRampToValueAtTime(0, bubbleStart + bubbleDuration);

            osc.connect(gain);
            gain.connect(this.audioContext.destination);

            osc.start(bubbleStart);
            osc.stop(bubbleStart + bubbleDuration);
        }

        // Bruit de vapeur continu
        const bufferSize = this.audioContext.sampleRate * duration;
        const buffer = this.audioContext.createBuffer(1, bufferSize, this.audioContext.sampleRate);
        const data = buffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i++) {
            data[i] = (Math.random() * 2 - 1) * 0.08;
            // Envelope
            const t = i / bufferSize;
            const envelope = Math.sin(t * Math.PI); // Monte puis descend
            data[i] *= envelope;
        }

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;

        const filter = this.audioContext.createBiquadFilter();
        filter.type = 'highpass';
        filter.frequency.value = 2000;

        source.connect(filter);
        filter.connect(this.audioContext.destination);

        source.start(startTime);
    }

    playPour(startTime) {
        // Son de liquide qui coule
        const duration = 0.5;
        const bufferSize = this.audioContext.sampleRate * duration;
        const buffer = this.audioContext.createBuffer(1, bufferSize, this.audioContext.sampleRate);
        const data = buffer.getChannelData(0);

        // White noise filtré pour simuler l'écoulement
        for (let i = 0; i < bufferSize; i++) {
            data[i] = (Math.random() * 2 - 1) * 0.15;

            // Envelope: décroissant
            const t = i / bufferSize;
            const envelope = 1 - (t * 0.7);
            data[i] *= envelope;
        }

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;

        // Filtre pour le son d'eau
        const filter = this.audioContext.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.value = 1500;
        filter.Q.value = 0.5;

        source.connect(filter);
        filter.connect(this.audioContext.destination);

        source.start(startTime);
    }

    playInsufficientFunds() {
        // Son d'erreur pour solde insuffisant
        this.playBeep(150, 0.2);
        setTimeout(() => this.playBeep(120, 0.2), 200);
        setTimeout(() => this.playBeep(100, 0.3), 400);
    }

    playButtonClick() {
        this.playBeep(600, 0.05);
    }
}

// Initialiser les sons
const sounds = new SoundEffects();

// Démarrer la détection automatique de carte
function startCardDetection() {
    if (cardDetectionInterval) {
        clearInterval(cardDetectionInterval);
    }

    updateScreen(`
        <div class="screen-title">En attente de carte...</div>
        <p style="text-align: center; margin-top: 20px; animation: pulse 2s infinite;">
            📇 Veuillez insérer votre carte à puce
        </p>
        <p style="text-align: center; margin-top: 30px; color: #00ff88; font-size: 0.9em;">
            ⚡ Détection automatique active
        </p>
    `);

    // Masquer le panneau de contrôle
    document.querySelector('.control-section').style.display = 'none';

    // Vérifier toutes les 3 secondes (réduit pour éviter les erreurs)
    cardDetectionInterval = setInterval(async () => {
        if (!cardConnected && !isProcessing) {
            await checkCardPresence();
        }
    }, 3000);
}

// Vérifier la présence de la carte
async function checkCardPresence() {
    try {
        const response = await fetch('/api/check_card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success && !cardConnected) {
            // Carte détectée !
            cardConnected = true;
            consecutiveErrors = 0; // Réinitialiser le compteur
            clearInterval(cardDetectionInterval);
            cardDetectionInterval = null;

            sounds.playCardInsert();
            document.getElementById('card-visual').classList.add('inserted');

            updateScreen(`
                <div class="screen-title">Carte détectée ✓</div>
                <p style="text-align: center; margin-top: 20px; color: #00ff88;">
                    Veuillez saisir votre code PIN
                </p>
            `);

            // Afficher le panneau de contrôle
            document.querySelector('.control-section').style.display = 'block';
            showStep('step-pin');
            document.getElementById('pin-input').focus();

            // Démarrer la surveillance de déconnexion
            startDisconnectionMonitoring();
        }
    } catch (error) {
        // Carte pas encore présente ou erreur, on continue à attendre
    }
}

// Surveiller la déconnexion de la carte
function startDisconnectionMonitoring() {
    if (cardDetectionInterval) {
        clearInterval(cardDetectionInterval);
    }

    // Vérifier toutes les 5 secondes si la carte est toujours présente (réduit pour éviter les faux positifs)
    cardDetectionInterval = setInterval(async () => {
        if (cardConnected && !isProcessing) {
            await checkCardStillPresent();
        }
    }, 5000);
}

// Vérifier si la carte est toujours présente
async function checkCardStillPresent() {
    try {
        const response = await fetch('/api/check_card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (!data.success || data.disconnected) {
            // Incrémenter le compteur d'erreurs
            consecutiveErrors++;

            // Si carte déconnectée explicitement, déconnecter immédiatement
            if (data.disconnected) {
                consecutiveErrors = 3; // Forcer la déconnexion
            }

            // Seulement déconnecter après 3 erreurs consécutives
            if (consecutiveErrors >= 3) {
                handleCardDisconnection();
            }
        } else {
            // Réinitialiser le compteur si la carte répond
            consecutiveErrors = 0;
        }
    } catch (error) {
        // Incrémenter le compteur d'erreurs
        consecutiveErrors++;

        // Seulement déconnecter après 3 erreurs consécutives
        if (consecutiveErrors >= 3) {
            handleCardDisconnection();
        }
    }
}

// Gérer la déconnexion de la carte
function handleCardDisconnection() {
    if (!cardConnected) return;

    sounds.playError();
    cardConnected = false;
    consecutiveErrors = 0; // Réinitialiser le compteur

    updateScreen(`
        <div class="screen-title" style="color: #ff4444;">⚠️ Carte retirée</div>
        <p style="text-align: center; margin-top: 20px; color: #ff8888;">
            La carte a été retirée
        </p>
        <p style="text-align: center; margin-top: 20px; color: #ffdd00;">
            Retour au menu principal...
        </p>
    `);

    setTimeout(() => {
        reset();
        startCardDetection();
    }, 2000);
}

// Afficher une étape
function showStep(stepId) {
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById(stepId).classList.add('active');
}

// Afficher un message sur l'écran de la machine
function updateScreen(html) {
    const screen = document.getElementById('screen-display');
    const preparing = document.getElementById('preparing-animation');

    screen.style.display = 'block';
    preparing.classList.remove('active');
    screen.innerHTML = html;
}

// Afficher l'animation de préparation
function showPreparingAnimation() {
    const screen = document.getElementById('screen-display');
    const preparing = document.getElementById('preparing-animation');

    // Mettre à jour l'emoji de la boisson dans l'animation
    if (selectedDrink && selectedDrink.emoji) {
        const cupAnimation = preparing.querySelector('.cup-animation');
        if (cupAnimation) {
            cupAnimation.textContent = selectedDrink.emoji;
        }
    }

    screen.style.display = 'none';
    preparing.classList.add('active');
}

// Insérer la carte
async function insertCard() {
    sounds.playButtonClick();
    sounds.playCardInsert();

    // Animation visuelle de la carte
    document.getElementById('card-visual').classList.add('inserted');

    updateScreen(`
        <div class="screen-title">Connexion à la carte...</div>
        <p style="text-align: center; margin-top: 20px;">
            Vérification en cours...
        </p>
    `);

    try {
        const response = await fetch('/api/check_card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            sounds.playSuccess();
            updateScreen(`
                <div class="screen-title">Carte détectée ✓</div>
                <p style="text-align: center; margin-top: 20px; color: #00ff88;">
                    Veuillez saisir votre code PIN
                </p>
            `);
            showStep('step-pin');
            document.getElementById('pin-input').focus();
        } else {
            sounds.playError();
            updateScreen(`
                <div class="screen-title" style="color: #ff4444;">Erreur</div>
                <p style="text-align: center; margin-top: 20px; color: #ff8888;">
                    ${data.error}
                </p>
                <p style="text-align: center; margin-top: 20px;">
                    Réessayez dans quelques instants
                </p>
            `);
        }
    } catch (error) {
        sounds.playError();
        updateScreen(`
            <div class="screen-title" style="color: #ff4444;">Erreur de connexion</div>
            <p style="text-align: center; margin-top: 20px; color: #ff8888;">
                ${error.message}
            </p>
        `);
    }
}

// Vérifier le PIN
async function verifyPin() {
    const pinInput = document.getElementById('pin-input');
    const pin = pinInput.value;

    if (pin.length !== 4) {
        showError('pin-error', 'Le PIN doit contenir 4 chiffres');
        sounds.playError();
        return;
    }

    sounds.playButtonClick();
    currentPin = pin;

    document.getElementById('pin-error').innerHTML = '';
    document.getElementById('loading-spinner').classList.add('active');

    updateScreen(`
        <div class="screen-title">Vérification du PIN...</div>
        <p style="text-align: center; margin-top: 20px;">
            Authentification en cours...
        </p>
    `);

    try {
        const response = await fetch('/api/verify_pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: pin })
        });

        const data = await response.json();
        document.getElementById('loading-spinner').classList.remove('active');

        if (data.success) {
            sounds.playSuccess();
            currentBalance = data.solde;

            updateScreen(`
                <div class="screen-title">Bienvenue ! ✓</div>
                <div class="balance">Solde: ${data.solde_euros}€</div>
                <p style="text-align: center; color: #00ff88;">
                    Choisissez votre boisson
                </p>
            `);

            document.getElementById('balance-display').textContent = data.solde_euros;
            showStep('step-select-drink');
        } else {
            // Vérifier si c'est une déconnexion
            if (data.disconnected) {
                document.getElementById('loading-spinner').classList.remove('active');
                handleCardDisconnection();
                return;
            }

            sounds.playError();
            updateScreen(`
                <div class="screen-title" style="color: #ff4444;">PIN incorrect</div>
                <p style="text-align: center; margin-top: 20px; color: #ff8888;">
                    ${data.error}
                </p>
            `);
            showError('pin-error', data.error);
            pinInput.value = '';
            pinInput.focus();
        }
    } catch (error) {
        sounds.playError();
        document.getElementById('loading-spinner').classList.remove('active');
        showError('pin-error', `Erreur: ${error.message}`);
    }
}

// Sélectionner une boisson
function selectDrink(id, name, emoji) {
    sounds.playButtonClick();

    // Convertir l'ID en nombre si c'est une chaîne
    const drinkId = typeof id === 'string' ? parseInt(id) : id;

    // Vérifier le solde AVANT de sélectionner
    const PRIX_BOISSON = 20; // 20 centimes

    if (currentBalance < PRIX_BOISSON) {
        // Solde insuffisant
        sounds.playInsufficientFunds();

        updateScreen(`
            <div class="screen-title" style="color: #ff4444;">⚠️ Solde insuffisant</div>
            <p style="text-align: center; font-size: 3em; margin: 20px 0; opacity: 0.3;">
                ${emoji}
            </p>
            <p style="text-align: center; font-size: 1.3em; color: #ff8888;">
                ${name}
            </p>
            <div class="balance" style="color: #ff4444;">
                Solde actuel: ${(currentBalance / 100).toFixed(2)}€
            </div>
            <p style="text-align: center; margin-top: 20px; color: #ff8888;">
                Prix de la boisson: 0.20€<br>
                Il vous manque: ${((PRIX_BOISSON - currentBalance) / 100).toFixed(2)}€
            </p>
            <p style="text-align: center; margin-top: 20px; color: #ffdd00;">
                Veuillez recharger votre carte
            </p>
        `);

        showError('drink-error', `❌ Solde insuffisant (${(currentBalance / 100).toFixed(2)}€). Rechargez votre carte.`);
        return;
    }

    // Solde suffisant, continuer
    selectedDrink = { id: drinkId, name, emoji };

    updateScreen(`
        <div class="screen-title">✓ Confirmation</div>
        <p style="text-align: center; font-size: 3em; margin: 20px 0;">
            ${emoji}
        </p>
        <p style="text-align: center; font-size: 1.3em; color: #ffdd00;">
            ${name}
        </p>
        <p style="text-align: center; margin-top: 20px;">
            Prix: 0.20€
        </p>
        <p style="text-align: center; margin-top: 10px; color: #00ff88;">
            Préparation en cours...
        </p>
    `);

    // Confirmer et lancer la préparation
    setTimeout(() => {
        prepareDrink();
    }, 1000);
}

// Préparer la boisson
async function prepareDrink() {
    if (!selectedDrink) return;

    isProcessing = true; // Marquer comme en traitement
    showStep('step-preparing');
    showPreparingAnimation();

    // Jouer le son de la machine à café
    sounds.playCoffeeMaking();

    try {
        const response = await fetch('/api/acheter_boisson', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                boisson_id: selectedDrink.id,
                pin: currentPin
            })
        });

        const data = await response.json();

        // Attendre la fin de l'animation (4 secondes)
        await new Promise(resolve => setTimeout(resolve, 4000));

        isProcessing = false; // Fin du traitement

        if (data.success) {
            updateScreen(`
                <div class="screen-title" style="color: #00ff88;">Boisson servie ! ✓</div>
                <p style="text-align: center; font-size: 3em; margin: 20px 0;">
                    ${selectedDrink.emoji}
                </p>
                <p style="text-align: center; font-size: 1.3em; color: #00ff88;">
                    ${data.boisson}
                </p>
                <div class="balance">Nouveau solde: ${data.nouveau_solde_euros}€</div>
                <p style="text-align: center; margin-top: 20px;">
                    Merci et bonne dégustation !
                </p>
                <p style="text-align: center; margin-top: 15px; color: #ffdd00; font-size: 0.9em;">
                    Retour à l'accueil dans 3 secondes...
                </p>
            `);

            document.getElementById('success-msg').innerHTML = `
                ✅ Votre ${data.boisson} est prêt(e) ! Bonne dégustation !
            `;
            document.getElementById('new-balance').textContent = data.nouveau_solde_euros;
            showStep('step-done');

            // Retour automatique à l'accueil après 3 secondes
            setTimeout(() => {
                reset();
                startCardDetection();
            }, 3000);
        } else {
            // Vérifier si c'est une déconnexion
            if (data.disconnected) {
                isProcessing = false;
                handleCardDisconnection();
                return;
            }

            sounds.playError();
            isProcessing = false;
            updateScreen(`
                <div class="screen-title" style="color: #ff4444;">Transaction refusée</div>
                <p style="text-align: center; margin-top: 20px; color: #ff8888;">
                    ${data.error}
                </p>
            `);
            showError('drink-error', data.error);
            showStep('step-select-drink');
        }
    } catch (error) {
        sounds.playError();
        isProcessing = false;
        updateScreen(`
            <div class="screen-title" style="color: #ff4444;">Erreur</div>
            <p style="text-align: center; margin-top: 20px; color: #ff8888;">
                ${error.message}
            </p>
        `);
        setTimeout(() => {
            showStep('step-select-drink');
        }, 3000);
    }
}

// Afficher une erreur
function showError(elementId, message) {
    const errorDiv = document.getElementById(elementId);
    errorDiv.innerHTML = `<div class="error-message">${message}</div>`;

    setTimeout(() => {
        errorDiv.innerHTML = '';
    }, 5000);
}

// Annuler la transaction
function cancelTransaction() {
    sounds.playButtonClick();

    // Réinitialiser toutes les variables
    currentPin = '';
    currentBalance = 0;
    selectedDrink = null;
    cardConnected = false;
    isProcessing = false;
    consecutiveErrors = 0;

    // Arrêter les intervalles existants
    if (cardDetectionInterval) {
        clearInterval(cardDetectionInterval);
        cardDetectionInterval = null;
    }

    // Réinitialiser l'interface
    document.getElementById('pin-input').value = '';
    document.getElementById('card-visual').classList.remove('inserted');

    // Masquer le panneau de contrôle
    document.querySelector('.control-section').style.display = 'none';

    // Retour à l'écran d'accueil
    updateScreen(`
        <div class="screen-title">🔍 En attente de carte...</div>
        <p style="text-align: center; margin-top: 25px; animation: pulse 2s infinite; font-size: 1.1em;">
            📇 Veuillez insérer votre carte à puce
        </p>
        <p style="text-align: center; margin-top: 35px; color: #00ff88; font-size: 0.95em; opacity: 0.8;">
            ⚡ Détection automatique active
        </p>
    `);

    // Redémarrer la détection de carte
    startCardDetection();
}

// Réinitialiser
function reset() {
    sounds.playButtonClick();

    currentPin = '';
    currentBalance = 0;
    selectedDrink = null;
    cardConnected = false;
    isProcessing = false;
    consecutiveErrors = 0; // Réinitialiser le compteur d'erreurs

    if (cardDetectionInterval) {
        clearInterval(cardDetectionInterval);
        cardDetectionInterval = null;
    }

    document.getElementById('pin-input').value = '';
    document.getElementById('card-visual').classList.remove('inserted');

    // Masquer le panneau de contrôle
    document.querySelector('.control-section').style.display = 'none';

    updateScreen(`
        <div class="screen-title">Machine à café Lunar White</div>
        <p style="text-align: center; margin-top: 20px;">
            Système réinitialisé
        </p>
    `);
}

// Écouter la touche Entrée sur le champ PIN
document.addEventListener('DOMContentLoaded', () => {
    const pinInput = document.getElementById('pin-input');
    if (pinInput) {
        pinInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                verifyPin();
            }
        });

        // Filtrer uniquement les chiffres
        pinInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
    }

    // Démarrer la détection automatique de carte au chargement
    startCardDetection();
});

// Export pour utilisation globale
window.verifyPin = verifyPin;
window.selectDrink = selectDrink;
window.cancelTransaction = cancelTransaction;
window.reset = reset;
window.startCardDetection = startCardDetection;