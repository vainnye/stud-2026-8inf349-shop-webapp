def test_app_boots(client):

    resp = client.get("/api/products/")

    assert resp.status_code == 200