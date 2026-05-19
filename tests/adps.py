import time

import board
import requests
import adafruit_apds9960.apds9960


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://127.0.0.1:8000"

STUDENT_ID = "1234567"

TIMEOUT_HTTP = 2.0

PERIODE_LECTURE = 0.5

DUREE_STABLE_REQUISE = 3.0

DELTA_STABILITE = 10

PERIODE_MIN_ENTRE_POSTS = 5.0

TAILLE_HISTORIQUE = 16


# =============================================================================
# PHASE 1 : Acquisition I2C
# =============================================================================


def initialiser_capteur():

    i2c = board.I2C()

    capteur = adafruit_apds9960.apds9960.APDS9960(i2c)

    return capteur


def lire_capteur(capteur):

    proximite = float(capteur.proximity)

    rouge, vert, bleu, clair = capteur.color_data

    return proximite, clair


# =============================================================================
# PHASE 2 : Client REST
# =============================================================================


def verifier_sante(base_url):

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


def envoyer_mesure(base_url, valeur, duree_stable, luminosite):

    payload = {

        "valeur": valeur,

        "duree_stable": duree_stable,

        "luminosite": luminosite,

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
# PHASE 3 : Stabilite
# =============================================================================


def est_stable(historique, delta_max):

    if len(historique) < 2:

        return False

    return max(historique) - min(historique) <= delta_max


def afficher(proximite, luminosite, duree_stable, derniere_decision):

    print(
        f"\rP= {proximite:.1f}",
        f"| L= {luminosite:.1f}",
        f"| stable= {duree_stable:.1f} s",
        f"| decision= {derniere_decision}",
        end=""
    )


def boucle_principale(capteur, base_url):

    historique = []

    dernier_temps_lecture = 0

    dernier_post = 0

    derniere_decision = ""

    while True:

        maintenant = time.monotonic()

        if maintenant - dernier_temps_lecture >= PERIODE_LECTURE:

            dernier_temps_lecture = maintenant

            proximite, luminosite = lire_capteur(capteur)

            historique.append(proximite)

            if len(historique) > TAILLE_HISTORIQUE:

                historique.pop(0)

            stable = est_stable(
                historique,
                DELTA_STABILITE
            )

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
                    proximite,
                    duree_stable,
                    luminosite
                )

                dernier_post = maintenant

            afficher(
                proximite,
                luminosite,
                duree_stable,
                derniere_decision
            )

        time.sleep(0.01)


# =============================================================================
# MAIN
# =============================================================================


def main():

    capteur = initialiser_capteur()

    if verifier_sante(BASE_URL) == False:

        print("Serveur inaccessible")

        return

    print("Serveur OK")

    try:

        boucle_principale(
            capteur,
            BASE_URL
        )

    except KeyboardInterrupt:

        print("\nArret du programme")


if __name__ == "__main__":

    main()