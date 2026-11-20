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
