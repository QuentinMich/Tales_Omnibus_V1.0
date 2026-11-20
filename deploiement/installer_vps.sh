#!/usr/bin/env bash
# ============================================================================
#  Tales Omnibus : installer (ou METTRE À JOUR) le site sur un VPS Ubuntu.
#
#  Usage, dans le terminal du VPS (en root) :
#     bash installer_vps.sh mon-domaine.fr mon-adresse@email.fr
#
#  L'adresse e-mail sert seulement à Let's Encrypt (alertes d'expiration du
#  certificat HTTPS). Relancer le script plus tard = mettre le site à jour
#  (git pull, dépendances, entretien, fichiers statiques, redémarrage) : il ne
#  recrée jamais ce qui existe déjà (clé secrète, base de données, médias).
#
#  Ce que le script installe :
#    - un utilisateur système « tales » (le site ne tourne jamais en root) ;
#    - le code dans /srv/tales-omnibus/site, son environnement Python ;
#    - settings/local.py (clé secrète NOUVELLE, domaine) : jamais dans Git ;
#    - Gunicorn en service systemd (redémarre tout seul) ;
#    - nginx (fichiers statiques, médias, SVG sans script) + HTTPS (certbot).
# ============================================================================
set -euo pipefail

DOMAINE="${1:-}"
EMAIL="${2:-}"
DEPOT="https://github.com/QuentinMich/Tales_Omnibus_V1.0.git"
DOSSIER="/srv/tales-omnibus"
SITE="$DOSSIER/site"
SERVICE="tales-omnibus"
REGLAGES="Tales_Omnibus.settings.production"

etape() { echo; echo "=== $* ==="; }
erreur() { echo "ERREUR : $*" >&2; exit 1; }

[ -n "$DOMAINE" ] && [ -n "$EMAIL" ] || erreur "usage : bash installer_vps.sh mon-domaine.fr mon-adresse@email.fr"
[ "$(id -u)" -eq 0 ] || erreur "lance ce script en root (ou avec sudo)."

# Toutes les commandes Django : en tant que « tales », réglages de PRODUCTION
django() { sudo -u tales env DJANGO_SETTINGS_MODULE="$REGLAGES" "$SITE/env/bin/python" "$SITE/manage.py" "$@"; }

etape "1/8 Paquets (Python, nginx, certbot, git)"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv nginx certbot python3-certbot-nginx git curl
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' \
    || erreur "Python 3.12 ou plus est nécessaire (Django 6.1)."

etape "2/8 Utilisateur « tales » et code du site"
id tales >/dev/null 2>&1 || adduser --system --group --home "$DOSSIER" tales
mkdir -p "$DOSSIER"
chown tales:tales "$DOSSIER"
if [ -d "$SITE/.git" ]; then
    sudo -u tales git -C "$SITE" pull --ff-only
else
    sudo -u tales git clone "$DEPOT" "$SITE"
fi
# nginx (www-data) doit pouvoir TRAVERSER ces dossiers pour lire static/ et media/
chmod 755 "$DOSSIER" "$SITE"

etape "3/8 Environnement Python"
[ -d "$SITE/env" ] || sudo -u tales python3 -m venv "$SITE/env"
sudo -u tales "$SITE/env/bin/pip" install -q --upgrade pip
sudo -u tales "$SITE/env/bin/pip" install -q -r "$SITE/requirements.txt" gunicorn

etape "4/8 Réglages du serveur (settings/local.py)"
LOCAL="$SITE/Tales_Omnibus/settings/local.py"
if [ -f "$LOCAL" ]; then
    echo "local.py existe déjà : on n'y touche pas."
else
    CLE="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
    cat > "$LOCAL" <<REGLAGES_LOCAUX
# Réglages PROPRES À CE SERVEUR (jamais dans Git). Créé par installer_vps.sh.
SECRET_KEY = "$CLE"
ALLOWED_HOSTS = ["$DOMAINE", "www.$DOMAINE"]
CSRF_TRUSTED_ORIGINS = ["https://$DOMAINE", "https://www.$DOMAINE"]
WAGTAILADMIN_BASE_URL = "https://$DOMAINE"
# Pas encore de serveur d'envoi : les e-mails sont écrits dans le journal
# (sudo journalctl -u $SERVICE). Les messages restent lisibles dans l'admin.
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
REGLAGES_LOCAUX
    chown tales:tales "$LOCAL"
    chmod 640 "$LOCAL"
    echo "local.py créé (clé secrète nouvelle, non affichée)."
fi

etape "5/8 Base de données et fichiers statiques"
sudo -u tales mkdir -p "$SITE/media"
if [ -f "$SITE/db.sqlite3" ]; then
    django entretien          # mise à jour : sauvegarde de la base, migrations, rangement
else
    django migrate --noinput  # première installation : base neuve
fi
django collectstatic --noinput -v 0
django check --deploy

etape "6/8 Service Gunicorn"
cat > "/etc/systemd/system/$SERVICE.service" <<SERVICE_SYSTEMD
[Unit]
Description=Tales Omnibus (Gunicorn)
After=network.target

[Service]
User=tales
Group=www-data
WorkingDirectory=$SITE
Environment=DJANGO_SETTINGS_MODULE=$REGLAGES
RuntimeDirectory=$SERVICE
ExecStart=$SITE/env/bin/gunicorn --workers 3 --bind unix:/run/$SERVICE/gunicorn.sock Tales_Omnibus.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE_SYSTEMD
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null 2>&1
systemctl restart "$SERVICE"

etape "7/8 nginx"
CONF="/etc/nginx/sites-available/$SERVICE"
if [ ! -f "$CONF" ]; then
    # Première installation seulement : ensuite, certbot y a ajouté le HTTPS
    cat > "$CONF" <<CONF_NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAINE www.$DOMAINE;
    server_tokens off;
    client_max_body_size 20M;

    location /static/ { alias $SITE/static/; }

    # Un SVG peut contenir du JavaScript : servi SANS droit d'exécuter un script
    location ~* ^/media/.+\.svg\$ {
        root $SITE;
        add_header Content-Security-Policy "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox" always;
        add_header X-Content-Type-Options "nosniff" always;
    }

    location /media/ { alias $SITE/media/; }

    location / {
        proxy_pass http://unix:/run/$SERVICE/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
CONF_NGINX
fi
ln -sf "$CONF" "/etc/nginx/sites-enabled/$SERVICE"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

etape "8/8 HTTPS (Let's Encrypt)"
if [ -d "/etc/letsencrypt/live/$DOMAINE" ]; then
    echo "Certificat déjà présent : renouvelé automatiquement par certbot."
else
    certbot --nginx -d "$DOMAINE" -d "www.$DOMAINE" --redirect --agree-tos -m "$EMAIL" --non-interactive
fi

etape "Vérifications"
sleep 2
echo "-- https://$DOMAINE/ (attendu : 200 ou 302, avec Strict-Transport-Security)"
curl -sI "https://$DOMAINE/" | grep -iE "^HTTP|strict-transport" || true
echo "-- http://$DOMAINE/ (attendu : 301 vers https)"
curl -sI "http://$DOMAINE/" | grep -iE "^HTTP|^location" || true
echo "-- page inexistante (attendu : 404)"
curl -s -o /dev/null -w "%{http_code}\n" "https://$DOMAINE/nimporte-quoi/"
echo "-- service (attendu : active)"
systemctl is-active "$SERVICE"

echo
echo "Terminé ! Si c'est la PREMIÈRE installation, crée ton compte administrateur :"
echo "  cd $SITE && sudo -u tales env DJANGO_SETTINGS_MODULE=$REGLAGES env/bin/python manage.py createsuperuser"
echo "puis ouvre https://$DOMAINE/admin/"
