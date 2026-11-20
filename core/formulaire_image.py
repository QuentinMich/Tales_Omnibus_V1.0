"""
Envoi d'images : le SVG est réservé aux administrateurs (le MJ).

Un SVG n'est pas une simple image : c'est du XML qui peut contenir du
JavaScript. Ouvert directement (son adresse dans /media/), ce script
s'exécuterait AVEC LE SITE COMME ORIGINE, donc avec les droits de la
personne connectée. Les comptes joueurs ont le droit d'envoyer des images
(leur portrait) : un joueur malveillant, ou un compte volé, pourrait piéger
un SVG et attendre que le MJ l'ouvre.

Deux protections, l'une n'excuse pas l'autre :
  - ici : un joueur ne peut envoyer que des images « classiques » (PNG,
    JPG, WebP…), jamais un SVG ;
  - sur le serveur : nginx sert /media/*.svg avec une Content-Security-Policy
    qui interdit tout script (voir README, « Mise en ligne »), comme
    core/middleware.py le fait en développement.

Branché par WAGTAILIMAGES_IMAGE_FORM_BASE (settings/base.py) : TOUS les
formulaires d'envoi de Wagtail (médiathèque, envoi multiple, sélecteur
d'image d'une fiche) héritent de cette classe.
"""
import os

from django.core.exceptions import ValidationError
from wagtail.images.forms import BaseImageForm


class FormulaireImage(BaseImageForm):
    def __init__(self, *args, **kwargs):
        # Wagtail passe l'utilisateur (« user ») pour choisir les dossiers
        # autorisés ; on le garde avant que la classe parente ne le retire.
        self.utilisateur = kwargs.get("user")
        super().__init__(*args, **kwargs)

    def clean_file(self):
        fichier = self.cleaned_data.get("file")
        envoye = "file" in self.changed_data
        extension = os.path.splitext(getattr(fichier, "name", "") or "")[1].lower()
        # Sans utilisateur (démo, commande) : c'est le code du site qui envoie
        if envoye and extension == ".svg" and self.utilisateur is not None \
                and not self.utilisateur.is_superuser:
            raise ValidationError(
                "Les images SVG sont réservées à l'administrateur du site "
                "(elles peuvent contenir du code). Envoie un PNG, un JPG ou un WebP."
            )
        return fichier
