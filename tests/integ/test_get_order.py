def test_get_order_after_creation(client):

    resp = client.post("/api/order/", json={"product": {"id": 1, "quantity": 1}})
    order_url = resp.headers["Location"]

    resp2 = client.get(order_url)

    assert resp2.status_code == 200

    data = resp2.get_json()

    assert "order" in data