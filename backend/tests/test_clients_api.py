from conftest import create_client, create_invoice


def test_create_list_get_update_and_delete_client(client):
    response = client.post(
        "/clients",
        json={
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "company": "Johnson Design",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Alice Johnson"
    assert created["email"] == "alice@example.com"

    list_response = client.get("/clients")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/clients/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["company"] == "Johnson Design"

    update_response = client.put(
        f"/clients/{created['id']}",
        json={"company": "Johnson Creative"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["company"] == "Johnson Creative"

    delete_response = client.delete(f"/clients/{created['id']}")
    assert delete_response.status_code == 204


def test_missing_client_returns_404(client):
    response = client.get("/clients/999")

    assert response.status_code == 404


def test_delete_client_with_invoices_returns_409(client, db_session):
    db_client = create_client(db_session)
    create_invoice(db_session, db_client.id)

    response = client.delete(f"/clients/{db_client.id}")

    assert response.status_code == 409
