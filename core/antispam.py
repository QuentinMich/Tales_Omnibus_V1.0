"""
ANTI-SPAM des formulaires (Contact, fiche d'un héros) : le « pot de miel ».

Un champ « Site internet » est ajouté au formulaire, mais CACHÉ aux humains
(placé hors de l'écran par le CSS, sauté au clavier). Un robot qui remplit
tout ce qu'il trouve le remplit : on le reconnaît, et on fait semblant
d'avoir reçu son message (rien n'est enregistré, rien n'est envoyé). S'il
voyait une erreur, il apprendrait à contourner le piège.

Pourquoi pas un CAPTCHA ? Il gêne tous les visiteurs, et les plus connus
(reCAPTCHA) envoient des données chez Google : le site n'en envoie aucune.

Hors de l'écran et pas display: none : certains robots sautent les champs
invisibles. Le libellé dit quoi faire si un lecteur d'écran le lit quand même.
"""
from django import forms

NOM_DU_PIEGE = "site_internet"


def champ_piege():
    return forms.CharField(
        required=False,
        label="Laissez ce champ vide",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )


def est_un_robot(donnees):
    """Le champ piège a été rempli : c'est un robot."""
    return bool((donnees.get(NOM_DU_PIEGE) or "").strip())
