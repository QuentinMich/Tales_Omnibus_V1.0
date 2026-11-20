"""
L'espace du joueur dans l'admin : « Mes messages ».

Les messages laissés par les visiteurs sur la fiche d'un héros
(MessageAuHeros). Le joueur ne voit QUE ceux de ses héros ; un
administrateur les voit tous. Les ouvrir les marque comme lus ; la
suppression passe par un formulaire en POST (jamais par un simple lien).
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from campagnes.joueurs import est_un_joueur, messages_visibles_par


def peut_lire_des_messages(utilisateur):
    return utilisateur.is_superuser or est_un_joueur(utilisateur)


def mes_messages(request):
    if not peut_lire_des_messages(request.user):
        raise PermissionDenied
    visibles = messages_visibles_par(request.user)

    if request.method == 'POST':
        # get_object_or_404 DANS les messages visibles : impossible de
        # supprimer celui d'un autre joueur en changeant le numéro
        message = get_object_or_404(visibles, pk=request.POST.get('supprimer'))
        message.delete()
        messages.success(request, f"Message de {message.nom} supprimé.")
        return redirect('mes_messages')  # Post/Redirect/Get

    liste = list(visibles)
    nouveaux = {m.pk for m in liste if not m.lu}
    # Affichés = lus. La pastille « Nouveau » reste pour CET affichage.
    visibles.filter(pk__in=nouveaux).update(lu=True)
    return TemplateResponse(request, "campagnes/admin/mes_messages.html", {
        'liste': liste,
        'nouveaux': nouveaux,
        'tous_les_heros': request.user.is_superuser,
    })
