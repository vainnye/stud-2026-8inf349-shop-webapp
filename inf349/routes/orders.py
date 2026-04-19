from flask import Blueprint, jsonify, redirect, request

from ..services.orders import OrderValidationError, create_order

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
