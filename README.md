# Shop 8INF349

Application Web de commandes et paiement — Travail de session, cours 8INF349, UQAC.

---

## Stack technique

- **Backend** : Python 3.11 · Flask · Peewee ORM
- **Base de données** : PostgreSQL 12
- **Cache / file de tâches** : Redis 5 · RQ (Redis Queue)
- **Frontend** : HTML · Jinja2 · JavaScript (vanilla)

---

## Prérequis

- Python 3.11+
- PostgreSQL 12+
- Redis 5+
- Docker + Docker Compose (optionnel, pour lancer Postgres et Redis)

---

## Installation

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Variables d'environnement

| Variable | Description | Exemple |
|---|---|---|
| `FLASK_APP` | Nom du package Flask | `api8inf349` |
| `FLASK_ENV` | Environnement (`development` / `production`) | `development` |
| `DB_HOST` | Hôte PostgreSQL | `localhost` |
| `DB_USER` | Utilisateur PostgreSQL | `user` |
| `DB_PASSWORD` | Mot de passe PostgreSQL | `pass` |
| `DB_PORT` | Port PostgreSQL | `5432` |
| `DB_NAME` | Nom de la base | `api8inf349` |
| `REDIS_URL` | URL Redis | `redis://localhost:6379/0` |
| `PRODUCTS_URL` | URL du catalogue distant | *(défaut : dimensweb.uqac.ca)* |
| `PAYMENT_URL` | URL du service de paiement distant | *(défaut : dimensweb.uqac.ca)* |

---

## Lancement rapide (avec Docker Compose)

**1. Démarrer PostgreSQL et Redis :**

```bash
docker-compose up -d
```

**2. Configurer les variables d'environnement :**

```bash
# Windows (PowerShell)
$env:FLASK_APP     = "api8inf349"
$env:FLASK_ENV     = "development"
$env:DB_HOST       = "localhost"
$env:DB_USER       = "user"
$env:DB_PASSWORD   = "pass"
$env:DB_PORT       = "5432"
$env:DB_NAME       = "api8inf349"
$env:REDIS_URL     = "redis://localhost:6379/0"

# Linux / macOS
export FLASK_APP=api8inf349
export FLASK_ENV=development
export DB_HOST=localhost
export DB_USER=user
export DB_PASSWORD=pass
export DB_PORT=5432
export DB_NAME=api8inf349
export REDIS_URL=redis://localhost:6379/0
```

**3. Initialiser la base de données :**

```bash
flask init-db
```

**4. Lancer le serveur Flask (terminal 1) :**

```bash
flask run
```

L'application est disponible sur [http://localhost:5000](http://localhost:5000).

**5. Lancer le worker RQ (terminal 2) :**

```bash
flask worker
```

Le worker traite les paiements en arrière-plan. Sans lui, les paiements s'exécutent de façon synchrone (mode développement sans Redis).

---

## Lancement avec Docker (image Flask)

```bash
# Build
docker build -t api8inf349 .

# Run (Postgres et Redis démarrés via docker-compose)
docker run -p 5000:5000 \
  -e DB_HOST=host.docker.internal \
  -e DB_USER=user \
  -e DB_PASSWORD=pass \
  -e DB_PORT=5432 \
  -e DB_NAME=api8inf349 \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  api8inf349
```

---

## Commandes Flask

| Commande | Description |
|---|---|
| `flask init-db` | Crée les tables en base de données |
| `flask seed-products` | Charge le catalogue produits depuis le service distant |
| `flask worker` | Démarre le worker RQ pour le traitement des paiements |

---

## API REST

### `GET /`
Liste tous les produits du catalogue.

### `POST /order`
Crée une nouvelle commande.

```json
// Multi-produits
{ "products": [{ "id": 1, "quantity": 2 }, { "id": 2, "quantity": 1 }] }

// Mono-produit (rétrocompatibilité)
{ "product": { "id": 1, "quantity": 2 } }
```

Réponse : `302` → `GET /order/<id>`

### `GET /order/<id>`
Retourne l'état d'une commande.

- `200` — commande trouvée
- `202` — paiement en cours de traitement
- `404` — commande introuvable

### `PUT /order/<id>`
Met à jour une commande (infos client ou paiement).

**Infos client :**
```json
{
  "order": {
    "email": "jdoe@example.com",
    "shipping_information": {
      "country": "Canada", "address": "125 rue Gagnon",
      "postal_code": "G7X 3Y5", "city": "Chicoutimi", "province": "QC"
    }
  }
}
```

**Paiement :**
```json
{
  "credit_card": {
    "name": "John Doe", "number": "4242424242424242",
    "expiration_year": 2026, "expiration_month": 9, "cvv": "123"
  }
}
```

- `202` — paiement mis en file d'attente
- `409` — un paiement est déjà en cours
- `422` — erreur de validation

---

## Tests

```bash
# Tous les tests
pytest -q

# Par catégorie
pytest tests/unit/
pytest tests/functional/
pytest tests/integration/
```

Les tests utilisent SQLite en mémoire et désactivent Redis (`REDIS_URL=None`).

---

## Structure du projet

```
api8inf349/
├── __init__.py          # App factory (create_app)
├── config.py            # Config / DevConfig / TestConfig
├── db.py                # DatabaseProxy (SQLite ↔ PostgreSQL)
├── cli.py               # flask init-db, seed-products, worker
├── clients/
│   ├── products.py      # Client HTTP catalogue distant
│   └── payment.py       # Client HTTP service de paiement
├── models/
│   └── __init__.py      # Product, Order, OrderProduct, JSONField
├── routes/
│   ├── products.py      # GET /
│   └── orders.py        # POST/GET/PUT /order
├── services/
│   ├── orders.py        # Logique commandes + cache Redis
│   ├── payment.py       # Paiement async (RQ), process_payment
│   ├── pricing.py       # Calculs prix, taxes, expédition
│   └── products.py      # Gestion catalogue
└── templates/
    ├── base.html
    ├── products.html
    └── order.html

tests/
├── unit/
├── functional/
└── integration/

Dockerfile
docker-compose.yml
requirements.txt
CODES-PERMANENTS
```
