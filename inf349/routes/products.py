from flask import Blueprint, jsonify

from ..services.products import list_products

bp = Blueprint("products", __name__)


@bp.route("/", methods=["GET"])
def get_products():
    return jsonify({"products": list_products()})
