"""
Raccourcis dans la barre latérale de l'admin : un menu "Univers" qui liste
directement toutes les campagnes, héros, lieux et événements (toutes
campagnes confondues), sans passer par l'explorateur de pages.
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from wagtail import hooks
from wagtail.images import get_image_model
from wagtail.admin.ui.tables import Column
from wagtail.admin.viewsets.base import ViewSetGroup
from wagtail.admin.viewsets.pages import PageListingViewSet
from wagtail.admin.ui.components import Component

from .models import CampagnePage, EvenementPage, HeroPage, LieuPage


class CampagneListingViewSet(PageListingViewSet):
    model = CampagnePage
    icon = "globe"
    menu_label = "Campagnes"
    columns = PageListingViewSet.columns + [
        Column("status", label="Statut", sort_key="status"),
    ]


class HeroListingViewSet(PageListingViewSet):
    model = HeroPage
    icon = "user"
    menu_label = "Héros"
    columns = PageListingViewSet.columns + [
        Column("joueur_nom", label="Joué par", sort_key="joueur_nom"),
    ]


class LieuListingViewSet(PageListingViewSet):
    model = LieuPage
    icon = "site"
    menu_label = "Lieux"
    columns = PageListingViewSet.columns + [
        Column("categorie", label="Catégorie"),
    ]


class EvenementListingViewSet(PageListingViewSet):
    model = EvenementPage
    icon = "date"
    menu_label = "Événements"
    columns = PageListingViewSet.columns + [
        Column("date_affichage", label="Date", sort_key="date_ordre"),
    ]


class UniversViewSetGroup(ViewSetGroup):
    """Regroupe les 4 listes sous un seul menu "Univers"."""
    menu_label = "Univers"
    menu_icon = "folder-open-inverse"
    menu_order = 150  # juste sous "Pages" dans la barre latérale
    items = (
        CampagneListingViewSet("liste_campagnes"),
        HeroListingViewSet("liste_heros"),
        LieuListingViewSet("liste_lieux"),
        EvenementListingViewSet("liste_evenements"),
    )


@hooks.register("register_admin_viewset")
def register_univers_menu():
    return UniversViewSetGroup()


def image_de_carte(request, pk):
    """
    Pour l'éditeur de carte (editeur_carte.js) : l'adresse de l'image de la
    carte en width-1400, LA MÊME version que sur le site (jamais recadrée),
    pour que les % cliqués dans l'admin tombent au même endroit sur le site.
    """
    image = get_object_or_404(get_image_model(), pk=pk)
    return JsonResponse({"url": image.get_rendition("width-1400").url})


@hooks.register("register_admin_urls")
def urls_de_l_editeur_de_carte():
    # Les URLs d'admin sont déjà protégées par Wagtail (connexion obligatoire)
    return [path("carte-image/<int:pk>/", image_de_carte, name="image_de_carte")]


# --- L'ESPACE DU JOUEUR -------------------------------------------------------
# Un compte qui n'est QUE joueur (campagnes/joueurs.est_un_joueur) voit une
# admin réduite : « Ma fiche » et « Mes messages » dans le menu (rangé par
# core/wagtail_hooks.organiser_le_menu), et un accueil qui ne parle que de
# lui. Les droits, eux, n'ont pas changé : c'est l'affichage qui suit.

@hooks.register("register_admin_urls")
def urls_de_l_espace_joueur():
    from .admin_joueur import mes_messages
    return [path("mes-messages/", mes_messages, name="mes_messages")]


class AccueilDuJoueur(Component):
    """Le tableau de bord d'un joueur : ses fiches et ses messages non lus."""
    template_name = "campagnes/admin/accueil_joueur.html"
    order = 10

    def __init__(self, utilisateur):
        self.utilisateur = utilisateur

    def get_context_data(self, parent_context=None):
        from .joueurs import fiches_du_joueur, messages_visibles_par
        return {
            'fiches': fiches_du_joueur(self.utilisateur),
            'non_lus': messages_visibles_par(self.utilisateur).filter(lu=False).count(),
        }


@hooks.register("construct_homepage_panels", order=1000)
def accueil_du_joueur(request, panels):
    from .joueurs import est_un_joueur
    if est_un_joueur(request.user):
        # Pas de « modifications récentes » ni de pages verrouillées du site :
        # seulement ce qui le concerne
        panels[:] = [AccueilDuJoueur(request.user)]


@hooks.register("construct_homepage_summary_items", order=1000)  # APRÈS ceux de Wagtail, qui ajoutent les leurs
def pas_de_resume_du_site_pour_un_joueur(request, summary_items):
    from .joueurs import est_un_joueur
    if est_un_joueur(request.user):
        summary_items[:] = []  # « 120 pages, 45 images » : rien à voir pour lui
