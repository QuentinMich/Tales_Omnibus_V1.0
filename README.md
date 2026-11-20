# Tales Omnibus

Un site pour les maîtres du jeu de jeu de rôle : campagnes (héros, cartes
interactives, chronologie), encyclopédie de l'univers filtrable, page
Univers, contact et prestations. Tout se gère depuis l'administration, sans
écrire une ligne de code. Six thèmes graphiques au choix.

Construit avec [Wagtail](https://wagtail.org/) 8.1 (Django 6.1).

> Version 0.9-a : l'outil fonctionne, l'installeur « clé en main » est à venir.

## Installer (Windows, Python 3.12 ou plus récent)

Dans ce dossier (celui qui contient `manage.py`) :

```bash
python -m venv env
```

```bash
env\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
```

```bash
python manage.py createsuperuser
```

```bash
python manage.py runserver
```

Puis ouvrir http://127.0.0.1:8000/admin/ : la page **Bien démarrer** crée la
structure du site en un clic, et peut ajouter une campagne de démonstration
complète.

Sous Linux ou macOS : `source env/bin/activate` à la place de la deuxième
commande.

## Après chaque mise à jour du code

```bash
python manage.py entretien
```

Une seule commande : sauvegarde de la base, migrations, rangement des
contenus, index de recherche. `--simulation` pour voir sans rien changer.

## Ce qui n'est pas dans le dépôt

La base de données (`db.sqlite3`) et les fichiers envoyés (`media/`) : chaque
installation a les siens. Les réglages secrets d'un serveur vont dans
`Tales_Omnibus/settings/local.py`, lui aussi exclu.

## Mettre en ligne sur un VPS Ubuntu (deux commandes)

Dans le terminal du VPS, en root :

```bash
curl -fsSL https://raw.githubusercontent.com/QuentinMich/Tales_Omnibus_V1.0/main/deploiement/installer_vps.sh -o installer_vps.sh
```

```bash
bash installer_vps.sh mon-domaine.fr mon-adresse@email.fr
```

Le domaine doit déjà pointer vers l'adresse IP du VPS (enregistrement DNS
**A**). Le script installe tout (utilisateur dédié, Python, Gunicorn, nginx,
HTTPS) et affiche des vérifications à la fin. **Relancé plus tard, il met le
site à jour** (`git pull`, dépendances, entretien, redémarrage) sans toucher à
la base, aux médias ni à la clé secrète.

## Mise en ligne : sécurité côté serveur

`Tales_Omnibus/settings/production.py` pose des réglages sûrs par défaut
(cookies réservés au HTTPS, HSTS). Sur le serveur, `settings/local.py` doit
au minimum contenir la clé secrète et l'adresse du site : sans clé secrète,
le site refuse de démarrer.

```python
SECRET_KEY = "…"            # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
ALLOWED_HOSTS = ["mon-site.fr"]
CSRF_TRUSTED_ORIGINS = ["https://mon-site.fr"]
```

C'est **nginx** qui sert les fichiers envoyés (`/media/`), pas Django. Deux
lignes à ajouter dans le bloc `server { … }` du site :

```nginx
server_tokens off;   # ne pas afficher la version de nginx

# Un SVG peut contenir du JavaScript : servi SANS droit d'exécuter un script
location ~* ^/media/.+\.svg$ {
    # Le dossier qui CONTIENT media/ : si « location /media/ » a
    # « alias /home/moi/app/media/; », écrire ici « root /home/moi/app; »
    root /chemin/vers/le/projet;
    add_header Content-Security-Policy "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

Puis `sudo nginx -t` (vérifie la configuration) et `sudo systemctl reload nginx`.
Vérification : `curl -I https://mon-site.fr/media/images/<une-icone>.svg`
doit afficher la ligne `Content-Security-Policy`.
