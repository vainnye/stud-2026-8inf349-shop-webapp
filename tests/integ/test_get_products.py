def test_get_products(client):

    response = client.get("/api/products/")

    assert response.status_code == 200

    data = response.get_json()

    assert "products" in data
    assert isinstance(data["products"], list)