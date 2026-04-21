from flask import Blueprint, jsonify, render_template, request

from ..services.products import list_products

bp = Blueprint("products", __name__)


@bp.route("/", methods=["GET"])
def get_products():
    products = list_products()
    # Browsers send Accept: text/html; API clients / test suite send */* or
    # application/json. Listing application/json first means */* resolves to
    # JSON, preserving all existing API tests.
    best = request.accept_mimetypes.best_match(
        ["application/json", "text/html"]
    )
    if best == "text/html":
        return render_template("products.html", products=products)
    return jsonify({"products": products})
