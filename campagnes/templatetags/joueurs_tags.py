"""Pour les gabarits de l'admin : {% if request.user|est_un_joueur %}."""
from django import template

from campagnes.joueurs import est_un_joueur as _est_un_joueur

register = template.Library()


@register.filter
def est_un_joueur(utilisateur):
    return _est_un_joueur(utilisateur)
