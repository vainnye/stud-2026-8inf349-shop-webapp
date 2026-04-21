from flask import (
    Blueprint, current_app, jsonify, redirect,
    render_template, request,
)

from ..services.orders import (
    OrderNotFoundError,
    OrderValidationError,
    create_order,
    get_order,
    order_to_dict,
    update_client_info,
)
from ..services.payment import enqueue_payment, is_order_paying


def _wants_html() -> bool:
    """True when the requester prefers HTML over JSON.

    Browsers send   Accept: text/html, ...
    API / curl / test-suite sends Accept: */* or application/json.

    Listing application/json first means */* resolves to JSON,
    so all existing API tests keep working without change.
    """
    best = request.accept_mimetypes.best_match(
        ["application/json", "text/html"]
    )
    return best == "text/html"


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
    # Support both JSON (API) and HTML form submissions.
    if request.is_json:
        payload = request.get_json(silent=True) or {}
    else:
        # Form: product_id=<int>&quantity=<int>
        try:
            product_id = int(request.form.get("product_id", 0))
            quantity   = int(request.form.get("quantity", 1))
        except (TypeError, ValueError):
            product_id, quantity = 0, 0
        payload = {"product": {"id": product_id, "quantity": quantity}}

    try:
        order = create_order(payload)
    except OrderValidationError as err:
        if _wants_html():
            # Redirect back to the catalogue with an error hint.
            from ..services.products import list_products
            return render_template(
                "products.html",
                products=list_products(),
                error=err.name,
            ), 422
        return _validation_response(err)

    # 302 → browser will GET /order/<id>, which will serve HTML or JSON
    # depending on the Accept header of the follow-up request.
    return redirect(f"/order/{order.id}", code=302)


@bp.route("/order/<int:order_id>", methods=["GET"])
def get_order_detail(order_id):
    redis_url = current_app.config.get("REDIS_URL")

    if _wants_html():
        # ── HTML path ────────────────────────────────────────────────────
        if is_order_paying(order_id, redis_url):
            return render_template(
                "order.html",
                paying=True, order=None, order_id=order_id, products={},
            ), 202

        try:
            order = get_order(order_id)
        except OrderNotFoundError:
            return render_template(
                "order.html",
                paying=False, order=None, order_id=order_id, products={},
            ), 404

        from ..services.products import list_products
        products_by_id = {p["id"]: p for p in list_products()}
        return render_template(
            "order.html",
            paying=False,
            order=order_to_dict(order)["order"],
            order_id=order_id,
            products=products_by_id,
        )

    # ── JSON path (API / test suite) ─────────────────────────────────────
    if is_order_paying(order_id, redis_url):
        return jsonify({"message": "Paiement en cours"}), 202

    try:
        order = get_order(order_id)
    except OrderNotFoundError:
        return jsonify({"error": "not-found"}), 404

    return jsonify(order_to_dict(order)), 200


@bp.route("/order/<int:order_id>", methods=["PUT"])
def put_order(order_id):
    payload    = request.get_json(silent=True) or {}
    is_payment = isinstance(payload, dict) and "credit_card" in payload
    redis_url  = current_app.config.get("REDIS_URL")

    # Reject a second payment request while one is already queued.
    if is_payment and is_order_paying(order_id, redis_url):
        return jsonify({"message": "Paiement déjà en cours"}), 409

    try:
        if is_payment:
            enqueue_payment(
                order_id,
                payload,
                payment_url=current_app.config.get("PAYMENT_URL"),
                redis_url=redis_url,
            )
            # 202: the task is queued (or ran synchronously in TESTING mode).
            return jsonify({"message": "Paiement en cours de traitement"}), 202
        else:
            order = update_client_info(order_id, payload)
    except OrderNotFoundError:
        return jsonify({"error": "not-found"}), 404
    except OrderValidationError as err:
        return _validation_response(err)

    return jsonify(order_to_dict(order)), 200
