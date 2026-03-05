def test_put_order_add_shipping(client):

    resp = client.post("/api/order/", json={"product": {"id": 1, "quantity": 1}})
    order_url = resp.headers["Location"]

    payload = {
        "order": {
            "email": "test@uqac.ca",
            "shipping_information": {
                "country": "Canada",
                "address": "201 rue Kennedy",
                "postal_code": "G7X3Y7",
                "city": "Chicoutimi",
                "province": "QC"
            }
        }
    }

    resp2 = client.put(order_url, json=payload)

    assert resp2.status_code == 200