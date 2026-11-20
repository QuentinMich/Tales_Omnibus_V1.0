"""
Réglages de PRODUCTION (le site en ligne).

Les SECRETS et ce qui est propre à UN serveur (clé secrète, adresse du site,
e-mail…) vont dans settings/local.py, sur le serveur, jamais dans Git.
local.py est lu EN DERNIER : il peut tout remplacer.

Ce fichier pose des valeurs SÛRES PAR DÉFAUT : l'outil est distribué, et un
MJ qui l'installe ne doit pas avoir à connaître ces réglages pour être
protégé. (Vérification : manage.py check --deploy.)
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# ManifestStaticFilesStorage : chaque fichier CSS / JS a une empreinte dans
# son nom, le navigateur ne garde jamais une vieille version en cache.
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"  # noqa: F405

# --- HTTPS ---------------------------------------------------------------------
# Cookies de session (connexion à l'admin) et anti-CSRF envoyés UNIQUEMENT
# en HTTPS : sur un Wi-Fi public, personne ne peut les lire au passage.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS : le navigateur retient que le site est en HTTPS et refuse ensuite
# toute connexion non chiffrée. 30 jours pour commencer (prudent : si le
# certificat cassait, le site serait inaccessible pendant ce temps). Pas
# d'includeSubDomains : le domaine peut appartenir à quelqu'un d'autre
# (sous-domaine de la formation, par exemple).
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

# Derrière nginx, Django reçoit les visites en HTTP « interne » : c'est nginx
# qui lui dit, par l'en-tête X-Forwarded-Proto, que le visiteur était en HTTPS.
# Sans ça, Django se croit en HTTP et n'envoie jamais l'en-tête HSTS.
# Sûr parce que notre nginx ÉCRASE cet en-tête (proxy_set_header, voir
# deploiement/installer_vps.sh) : un visiteur ne peut pas le falsifier.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# La redirection http -> https est faite par nginx (certbot), avant même
# Django : pas de SECURE_SSL_REDIRECT ici. L'activer sans que nginx transmette
# X-Forwarded-Proto ferait une boucle de redirections.
# W005 / W021 : includeSubDomains et preload VOLONTAIREMENT absents (voir HSTS).
SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W005", "security.W021"]

# --- Réglages propres au serveur -------------------------------------------------
try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass

# Une clé secrète absente ou de développement en ligne = sessions et liens
# de réinitialisation de mot de passe falsifiables. On refuse de démarrer.
if not globals().get("SECRET_KEY") or SECRET_KEY.startswith("django-insecure"):  # noqa: F405
    raise ImproperlyConfigured(
        "SECRET_KEY manquante dans settings/local.py. Pour en générer une : "
        "python -c \"from django.core.management.utils import get_random_secret_key; "
        "print(get_random_secret_key())\""
    )
