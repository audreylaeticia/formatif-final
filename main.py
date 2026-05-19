"""
Formatif FINAL-AHT20 -- Mini-examen blanc, capteur AHT20 + REST
Cours 243-413-SH

Variante FORMATIVE de l'examen FINAL-AHT20. Meme architecture
(lecture I2C, client REST, boucle non-bloquante a time.monotonic)
mais **sujet variant** pour eviter le copier-coller :

* Valeur principale envoyee au serveur : **humidite relative** (%)
  au lieu de la temperature.
* Endpoint serveur : **/evaluer** au lieu de /decider.
* Decisions : **"sec" | "confort" | "humide"** au lieu de
  chaud/normal/froid.

Interaction physique
--------------------
Soufflez doucement sur le capteur AHT20 ; l'humidite mesuree monte.
Eloignez-vous pour la voir redescendre. Apres stabilisation, le
serveur renvoie une categorie d'humidite.

Contrat REST (resume)
---------------------
* GET  `<BASE_URL>/sante`     -> `{"ok": true, ...}`
* POST `<BASE_URL>/evaluer`   -> payload :
    `{"valeur": float, "duree_stable": float, "temperature": float,
      "student_id": str}`
  reponse :
    `{"decision": "sec"|"confort"|"humide", ...}`

Contraintes (identiques au sommatif)
------------------------------------
* Aucun `time.sleep` superieur a 50 ms dans `boucle_principale`.
* Timeout obligatoire sur chaque appel `requests`.
* Gestion d'erreurs reseau (la boucle ne plante pas).
* Anti-rebond entre POST consecutifs.

Aide (`aide.pyc`)
-----------------
Module compile Python 3.11 fourni ; usage penalise. Voir
GRILLE_EVALUATION.md fournie par l'instructeur.
"""

import time

import board
import adafruit_ahtx0
import requests


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://127.0.0.1:8000"
STUDENT_ID = "202345413"                    # Votre numero d'etudiant (7 chiffres)
TIMEOUT_HTTP = 2.0

PERIODE_LECTURE = 0.5
DUREE_STABLE_REQUISE = 3.0
DELTA_STABILITE = 1.5            # amplitude humidite max-min toleree (%)
PERIODE_MIN_ENTRE_POSTS = 5.0
TAILLE_HISTORIQUE = 16


# =============================================================================
# PHASE 1 : Acquisition I2C (25 pts)
# =============================================================================


def initialiser_capteur():
    i2c = board.I2C()
    capteur = adafruit_ahtx0.AHTx0(i2c)
    return capteur
    


def lire_capteur(capteur):
    humidite = float(capteur.relative_humidity)

    temperature = float(capteur.temperature)

    return humidite, temperature


# =============================================================================
# PHASE 2 : Client REST (35 pts)
# =============================================================================


def verifier_sante(base_url):

    #on verifie si le serveur est joignable ou pas 
    try:
        response = requests.get(
            base_url + "/sante",
            timeout=TIMEOUT_HTTP
        )

        if response.status_code == 200:
            data = response.json()
            return data["ok"]

        return False

    except requests.RequestException:
        return False


def envoyer_mesure(base_url, valeur, duree_stable, temperature):
    """POST /evaluer avec payload JSON."""

    payload = {
        "valeur": valeur,
        "duree_stable": duree_stable,
        "temperature": temperature,
        "student_id": STUDENT_ID
    }

    try:
        response = requests.post(
            base_url + "/evaluer",
            json=payload,
            timeout=TIMEOUT_HTTP
        )

        if response.status_code == 200:
            data = response.json()
            return data["decision"]

        return None

    except requests.RequestException:
        return None


# =============================================================================
# PHASE 3 : Minuteur + stabilite (40 pts)
# =============================================================================


def est_stable(historique, delta_max):
    if len(historique) < 2:
        return False

    return max(historique) - min(historique) <= delta_max
  


def afficher(humidite, temperature, duree_stable, derniere_decision):
    """Affiche une ligne console (rafraichie avec \\r).

    Format suggere :
        H= 48.5 % | T= 24.8 C | stable= 1.5 s | decision= confort
    """
    print(
        f"\rH= {humidite:.1f} % | "
        f"T= {temperature:.1f} C | "
        f"stable= {duree_stable:.1f} s | "
        f"decision= {derniere_decision}",
        end=""
    )


def boucle_principale(capteur, base_url):
    """Boucle non-bloquante a `time.monotonic()`."""

    historique = []

    dernier_temps_lecture = 0
    dernier_post = 0

    derniere_decision = ""

    while True:

        maintenant = time.monotonic()

        if maintenant - dernier_temps_lecture >= PERIODE_LECTURE:

            dernier_temps_lecture = maintenant

            humidite, temperature = lire_capteur(capteur)

            historique.append(humidite)

            if len(historique) > TAILLE_HISTORIQUE:
                historique.pop(0)

            stable = est_stable(historique, DELTA_STABILITE)

            if stable:
                duree_stable = DUREE_STABLE_REQUISE
            else:
                duree_stable = 0

            if (
                stable
                and maintenant - dernier_post >= PERIODE_MIN_ENTRE_POSTS
            ):

                derniere_decision = envoyer_mesure(
                    base_url,
                    humidite,
                    duree_stable,
                    temperature
                )

                dernier_post = maintenant

            afficher(
                humidite,
                temperature,
                duree_stable,
                derniere_decision
            )

        time.sleep(0.01)


# =============================================================================
# POINT D'ENTREE
# =============================================================================


def main():
    """Init capteur + verif serveur + boucle. Arret propre sur Ctrl+C."""

    capteur = initialiser_capteur()

    if verifier_sante(BASE_URL) == False:
        print("Serveur inaccessible")
        return

    print("Serveur OK")

    try:
        boucle_principale(capteur, BASE_URL)

    except KeyboardInterrupt:
        print("\nArret du programme")

if __name__ == "__main__":
    main()