# Projet de session Dev Web

> L'objectif du projet de session est de développer et déployer une application Web responsable du paiement de commandes Internet.

## Dispclaimers

- toute l'api tourne sous l'url "/api/"
- l'endpoint de la liste des produits se trouve à "/api/produtcs/" au lieu de "/api/" dans le pdf du cours


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

## Le projet

Le projet consiste à développer une application Web responsable de prendre des commandes Internet. Cette application devra répondre à une API REST, mais devra également être utilisée à travers des pages HTMLs.  
Le projet est séparé en deux. Les informations pour la première remise sont disponibles dans cet énoncé. La section pour la deuxième remise sera disponible plus tard.
Il s'agit de remises incrémentielles sur le même projet. Pour la deuxième remise, vous continuerez à utiliser le projet décrit ci-dessous.

## Specs

- language: Python 3.13
- cadriciel dev. Web: Flask
- ORM: Peewee
- Base de données: SQLite3
- dépendances de production: flask, pytest, pytest-flask, peewee, requests
- dépendances de développement: types-peewee (pour le type checking)

## Lancer l'app

## commandes qui fonctionnent

```bash
FLASK_APP=shop_webapp flask run --debug
```

Autres variables d'environnement dispnibles pour configurer l'app
`API_PRODUCTS_LOCATION`: url ou chemin vers un fichier json contenant tous les produits en  
`API_USE_MOCKS`: si "True" notre API utilise un endpoint mock '/api/mocks/' qui reproduit le comportement de l'endpoint du professeur 

```bash
API_PRODUCTS_LOCATION="./res/data/products.json" API_USE_MOCKS=True flask run --debug
```

## commandes qui fonctionnent pas

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

- [ ] modifier le nom de l'app flask pour la lancer avec FLASK_APP=inf349 plutôt que FLASK_APP=shop_webapp
- [ ] contraintes logique métiers (ex: prix > 0, qté > 0, ...) 
- [ ] standardisation des erreurs 
- [ ] standardisation de la validation des données (in et out) de l'API 
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
