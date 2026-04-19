from flask import Blueprint, jsonify, redirect, request

from ..services.orders import (
    OrderNotFoundError,
    OrderValidationError,
    create_order,
    get_order,
    order_to_dict,
)

bp = Blueprint("orders", __name__)


@bp.route("/order", methods=["POST"])
def post_order():
    payload = request.get_json(silent=True) or {}
    try:
        order = create_order(payload)
    except OrderValidationError as err:
        return (
            jsonify({
                "errors": {
                    err.field: {
                        "code": err.code,
                        "name": err.name,
                    }
                }
            }),
            422,
        )
    return redirect(f"/order/{order.id}", code=302)


@bp.route("/order/<int:order_id>", methods=["GET"])
def get_order_detail(order_id):
    try:
        order = get_order(order_id)
    except OrderNotFoundError:
        return jsonify({"error": "not-found"}), 404
    return jsonify(order_to_dict(order)), 200
