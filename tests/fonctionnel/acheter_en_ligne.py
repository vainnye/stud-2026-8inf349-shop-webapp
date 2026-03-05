# le script doit être run depuis à la racine du projet (cwd == racine du projet)
import os
import random
import shutil
import subprocess

from shop_webapp.globals import INSTANCE_FOLDER
from shop_webapp.util import http_get, http_post

"""
init-db
POST /order
PUT shipping
PUT payment
GET order
Vérifier tout le workflow
"""


# préparer repartir à 0 pour la BD
if os.path.exists(INSTANCE_FOLDER):
    shutil.rmtree(INSTANCE_FOLDER)
os.makedirs(INSTANCE_FOLDER)


my_env = os.environ.copy()
my_env["API_PRODUCTS_LOCATION"] = "./res/data/products.json"
my_env["API_USE_MOCKS"] = "True"
my_env["FLASK_DEBUG"] = "True"
my_env["FLASK_APP"] = "shop_webapp"

HOST = "127.0.0.1"
PORT = 5000

ADDRESS = f"http://{HOST}:{PORT}"

# 1. Start the api
proc = subprocess.Popen(
    ["flask", "run", f"--host={HOST}--port={PORT}"],
    env=my_env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    # shell=False,
    # text=True,
)


def check_and_get_response_json(resp):
    try:
        resp.raise_for_status()
        return resp.json()
    except Exception as err:
        print(f"{err!r}")
        print("GET /api/products/")
        print(f"STATUS {resp.status_code}")
        print(resp.text)
        exit(1)


# TODO: ajouter la commande init-db

# 2. lister les produits:

resp = http_get(ADDRESS + "/api/products/")
resp_json = check_and_get_response_json(resp)
products = resp_json["products"]

print(f"liste des produits récupérée ({len(products)} produits)")
idx = random.randint(0, len(products) - 1)
print("nous en sélectionnons 1 au hasard")
print(f"products[{idx}]: {products[idx]}")

qty = random.randint(1, 10)
print(f"nous en prendrons {qty}")

# 3. passer commande

resp = http_post(
    ADDRESS + "/api/order/",
    {"product": {"id": products[idx]["id"], "quantity": qty}},
)

resp_json = check_and_get_response_json(resp)
print("Commande passée avec succès !")
print("Réponse de la commande :", resp_json)

# 4. renseigner les coordonnées
