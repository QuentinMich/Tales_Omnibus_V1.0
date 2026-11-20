/*
 * Compte à rebours de la prochaine session (accueil, pages/includes/annonces.html).
 *
 * L'élément porte deux dates ISO (avec le fuseau) : le début de la session
 * et sa fin. Avant : « Dans 2 jours et 3 h ». Pendant : « En ce moment ! ».
 * Après : la ligne disparaît (au prochain chargement, l'annonce aussi).
 * La date en clair est écrite par le serveur : ce script n'est qu'un plus,
 * d'où l'attribut hidden retiré seulement ici.
 * Mise à jour toutes les 30 secondes : la minute suffit, inutile de
 * réveiller le navigateur chaque seconde.
 */
(function () {
    "use strict";

    function pluriel(n, mot) {
        return n + " " + mot + (n > 1 ? "s" : "");
    }

    function texte(ms) {
        const minutes = Math.floor(ms / 60000);
        const jours = Math.floor(minutes / 1440);
        const heures = Math.floor((minutes % 1440) / 60);
        const reste = minutes % 60;
        if (jours >= 1) {
            return "Dans " + pluriel(jours, "jour") + (heures ? " et " + heures + " h" : "");
        }
        if (heures >= 1) {
            return "Dans " + heures + " h" + (reste ? " " + String(reste).padStart(2, "0") + " min" : "");
        }
        if (minutes >= 1) {
            return "Dans " + pluriel(minutes, "minute");
        }
        return "Dans moins d'une minute";
    }

    function mettreAJour(element) {
        const debut = new Date(element.dataset.compteARebours).getTime();
        const fin = new Date(element.dataset.fin).getTime();
        const maintenant = Date.now();
        if (Number.isNaN(debut) || maintenant >= fin) {
            element.hidden = true;
            return false;
        }
        const enCours = maintenant >= debut;
        element.textContent = enCours ? "En ce moment !" : texte(debut - maintenant);
        element.classList.toggle("is-live", enCours);
        element.hidden = false;
        return true;
    }

    document.querySelectorAll("[data-compte-a-rebours]").forEach(function (element) {
        if (!mettreAJour(element)) {
            return;
        }
        const minuterie = setInterval(function () {
            if (!mettreAJour(element)) {
                clearInterval(minuterie);
            }
        }, 30000);
    });
})();
