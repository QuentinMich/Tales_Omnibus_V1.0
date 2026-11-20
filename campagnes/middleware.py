"""
L'espace du joueur, côté ADRESSES : un compte qui n'est QUE joueur ne peut
pas ouvrir les écrans qui listent tout le site, même en tapant l'adresse.

Le menu les cache déjà (core/wagtail_hooks.menu_du_joueur), mais la
recherche de l'admin montrait les titres de TOUTES les pages, brouillons
compris : les fiches que le MJ prépare en secret (spoilers !). Ici, ces
adresses renvoient simplement à l'accueil du joueur.
Les droits de Wagtail protègent déjà le reste (modifier, publier, réglages).
"""
from django.shortcuts import redirect
from django.urls import reverse

from campagnes.joueurs import est_un_joueur

# Les écrans de LISTE du site (les sélecteurs d'images restent permis :
# le joueur choisit le portrait de son héros)
ECRANS_INTERDITS = (
    "wagtailadmin_pages:search",   # recherche de l'admin (titres des brouillons)
    "wagtailadmin_explore_root",   # explorateur de pages
    "wagtailimages:index",         # médiathèque complète
    "wagtaildocs:index",           # documents
)


class EspaceDuJoueurMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in {reverse(nom) for nom in ECRANS_INTERDITS} and est_un_joueur(request.user):
            return redirect("wagtailadmin_home")
        return self.get_response(request)
