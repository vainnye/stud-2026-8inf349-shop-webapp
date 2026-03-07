def test_post_order_creates_order(client):

    payload = {
        "product": {
            "id": 1,
            "quantity": 1
        }
    }

    response = client.post("/api/order/", json=payload)

    assert response.status_code == 302
    assert "Location" in response.headers