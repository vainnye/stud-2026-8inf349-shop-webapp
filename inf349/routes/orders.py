from flask import Blueprint, current_app, jsonify, redirect, request

from ..services.orders import (
    OrderNotFoundError,
    OrderValidationError,
    create_order,
    get_order,
    order_to_dict,
    update_client_info,
)
from ..services.payment import pay_order


def _validation_response(err: OrderValidationError):
    payload = {
        err.field: {
            "code": err.code,
            "name": err.name,
        }
    }
    # Errors relayed verbatim from the remote payment service (card-declined
    # and similar) are emitted literally, without the `errors` wrapper, per
    # the PDF example on page 10.
    if not err.remote_relay:
        payload = {"errors": payload}
    return jsonify(payload), 422

bp = Blueprint("orders", __name__)


@bp.route("/order", methods=["POST"])
def post_order():
    payload = request.get_json(silent=True) or {}
    try:
        order = create_order(payload)
    except OrderValidationError as err:
        return _validation_response(err)
    return redirect(f"/order/{order.id}", code=302)


@bp.route("/order/<int:order_id>", methods=["GET"])
def get_order_detail(order_id):
    try:
        order = get_order(order_id)
    except OrderNotFoundError:
        return jsonify({"error": "not-found"}), 404
    return jsonify(order_to_dict(order)), 200


@bp.route("/order/<int:order_id>", methods=["PUT"])
def put_order(order_id):
    payload = request.get_json(silent=True) or {}
    is_payment = isinstance(payload, dict) and "credit_card" in payload
    try:
        if is_payment:
            order = pay_order(
                order_id,
                payload,
                payment_url=current_app.config.get("PAYMENT_URL"),
            )
        else:
            order = update_client_info(order_id, payload)
    except OrderNotFoundError:
        return jsonify({"error": "not-found"}), 404
    except OrderValidationError as err:
        return _validation_response(err)
    return jsonify(order_to_dict(order)), 200
