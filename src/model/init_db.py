# src/model/init_db.py

from .db import db
from .orm import Product


def init_db():
    """
    Initialise la base de données SQLite et crée les tables nécessaires.
    """
    db.connect(reuse_if_open=True)
    # crée les tables si elles n'existent pas
    db.create_tables([Product])
    db.close()