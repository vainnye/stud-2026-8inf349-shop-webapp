# Projet de session Dev Web

> L'objectif du projet de session est de développer et déployer une application Web responsable du paiement de commandes Internet.

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
