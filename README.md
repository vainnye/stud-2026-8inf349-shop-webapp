# Projet de session Dev Web

> L'objectif du projet de session est de développer et déployer une application Web responsable du paiement de commandes Internet.

## Le projet

Le projet consiste à développer une application Web responsable de prendre des commandes Internet. Cette application devra répondre à une API REST, mais devra également être utilisée à travers des pages HTMLs.  
Le projet est séparé en deux. Les informations pour la première remise sont disponibles dans cet énoncé. La section pour la deuxième remise sera disponible plus tard.
Il s'agit de remises incrémentielles sur le même projet. Pour la deuxième remise, vous continuerez à utiliser le projet décrit ci-dessous.

## Specs

- language: Python 3.13
- cadriciel dev. Web: Flask
- ORM: Peewee
- Base de données: SQLite3
- dépendances de production: flask, pytest, pytest-flask, peewee
- dépendances de développement: types-peewee (pour le type checking)

## Disclaimers

- toute l'api tourne sous l'url "/api/"
- l'endpoint de la liste des produits se trouve à "/api/produtcs/" au lieu de "/api/" dans le pdf du cours
- Les consignes du TP ne font pas la différence entre les erreurs de type "field manquant" et "field existant mais valeur incorrecte" dans les données reçues par l'API. Notre code ne fait pas non plus la différence, bien qu'on l'ait codé de façon à pouvoir différencier ces erreurs avec les Exceptions `ValidationError`, `ValidationMissingField`, `ValidationIncorrectValue`.
- pour des raisons de rapididté / simplicité / traçabilité du code, toutes les contraintes métier sur la base de données autre que le type de données et ses relations (ex: Check x > 0) sont actuellement gérées par l'API et non par l'ORM (peewee), il se peut que l'on change cela dans le futur avec l'augmentation de la taille de la codebase pour favoriser la maintenabilité long terme.

## liste de tous les endpoints

### API
- GET /api/products/
- POST /api/order/
- GET /api/order/<int:id>
- PUT /api/order/<int:id>
- POST /api/mocks/shops/pay/ *(si API_USE_MOCKS=True)*

### Autre
- GET /
- GET /favicon.ico
- GET /static/favicon.ico

## Lancer l'app

### commandes qui fonctionnent

```bash
FLASK_APP=shop_webapp flask run --debug
```

Autres variables d'environnement dispnibles pour configurer l'app
`API_PRODUCTS_LOCATION`: url ou chemin vers un fichier json contenant tous les produits en  
`API_USE_MOCKS`: si "True" notre API utilise un endpoint mock '/api/mocks/' qui reproduit le comportement de l'endpoint du professeur 

```bash
API_PRODUCTS_LOCATION="./res/data/products.json" API_USE_MOCKS=True flask run --debug
```

#### sur windows

**en full local**
```powershell
<<<<<<< HEAD
$env:API_PRODUCTS_LOCATION="./res/data/products.json"; $env:API_USE_MOCKS="True"; $env:FLASK_DEBUG="False"; $env:FLASK_APP="shop_webapp"; flask run;
=======
$env:API_PRODUCTS_LOCATION="./res/data/products.json"; $env:API_USE_MOCKS="True"; $env:FLASK_APP="shop_webapp"; flask run --debug;
>>>>>>> origin/Frantxa
```

**si t'as de la connexion internet**
```powershell
<<<<<<< HEAD
$env:API_PRODUCTS_LOCATION=""; $env:API_USE_MOCKS=""; $env:FLASK_DEBUG="False"; $env:FLASK_APP="shop_webapp"; flask run;
=======
$env:API_PRODUCTS_LOCATION=""; $env:API_USE_MOCKS="False"; $env:FLASK_APP="shop_webapp"; flask run --debug;
>>>>>>> origin/Frantxa
```

### commandes qui fonctionnent pas

initialiser la base de données
```bash
FLASK_DEBUG=True FLASK_APP=inf349 flask init-db
```

lancer l'app web
```bash
FLASK_DEBUG=True FLASK_APP=inf349 flask run
```

## TODO

### refactoring

- [X] contraintes logique métiers mentionnées dans le pdf (ex: qté > 0, ...) 
- [X] utiliser `urllib` (lib std python) plutôt que `requests` car le prof ne l'a pas mentionnée
- [ ] standardisation de la validation des données (in et out) de l'API (ça aurait été bien de pouvoir utiliser qqc comme pydantic mais le prof ne nous laisse pas utiliser d'autre librairies que celles mentionnées plus haut) 
- [ ] modifier le nom de l'app flask pour la lancer avec FLASK_APP=inf349 plutôt que FLASK_APP=shop_webapp **(à faire en dernier pour minimiser les git diffs et merge)**
- [ ] contraintes logique métiers non mentionnées dans le pdf (ex: prix > 0, , ...) 
- [ ] standardisation des erreurs 
- [ ] standardisation du mapping des données de la BD à celles de l'API sur les requêtes GET  

## Développement

**Cloner le repo**

**Préparer l'environnement**

```bash
uv sync
```

**ça y est vous pouvez coder**

svp utilisez [uv](<README#Installer uv>) plutôt que pip, ça sera plus simple pour tout le monde

**run le projet (l'app flask)**
en debug mode (avec hot reload):
```bash
flask --app shop_webapp --debug run
```

**run un fichier faisant appel au projet**
exemple:
```bash
uv run .\tests\fiddle\fetch_products.py
```

### répertoire 

- `res`: fichiers utilisées pour le développement qui ne doivent pas être utilisées en production
- `instance`: fichiers créés par l'app ou api, ex: database.db
- `static`: fichiers servis à l'adresse /static/ 
- `src/nom_du_projet/`: code source
- `tests/unit/`: tests unitaires
- `tests/use_case/`: tests de cas d'utilisation
- `tests/fiddle/`: tests et expérimentations en tout genre, éphémères

### bonnes pratiques

**logging**  
Toujours utiliser le logger lié à flask si le code tourne en mm temps que l'app flask.  
utiliser `app.logger` quand vous pouvez accéder à la variable `app`  
sinon utiliser `flask.current_app.logger`

## Installer uv

**sur Windows**
dans powershell :
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**sur MacOs ou Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
