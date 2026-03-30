import pytest

pytestmark = pytest.mark.asyncio


async def register_and_login(
    client, email="user@example.com", password="strongpassword123"
):
    await client.post(
        "/register/",
        json={"email": email, "password": password},
    )

    token_response = await client.post(
        "/token/",
        data={"username": email, "password": password},
    )
    token_data = token_response.json()
    return token_data["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_order(client, token: str):
    payload = {
        "items": [
            {
                "sku": "sku-1",
                "name": "Test Item",
                "qty": 2,
                "price": 100,
            }
        ]
    }

    response = await client.post(
        "/orders/",
        json=payload,
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    return response.json()


async def test_create_order(client):
    token = await register_and_login(client)

    response = await client.post(
        "/orders/",
        json={
            "items": [
                {
                    "sku": "sku-1",
                    "name": "Test Item",
                    "qty": 1,
                    "price": 50,
                }
            ]
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201, response.text
    data = response.json()

    assert "id" in data
    assert data["user_id"] == 1
    assert data["status"] == "PENDING"
    assert data["total_price"] == 50


async def test_get_order_by_id(client):
    token = await register_and_login(client)
    created = await create_order(client, token)

    response = await client.get(
        f"/orders/{created['id']}/",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == created["id"]
    assert data["user_id"] == created["user_id"]
    assert data["total_price"] == 200


async def test_update_order_status(client):
    token = await register_and_login(client)
    created = await create_order(client, token)

    response = await client.patch(
        f"/orders/{created['id']}/",
        json={"status": "PAID"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == created["id"]
    assert data["status"] == "PAID"
    assert data["total_price"] == 200


async def test_get_orders_by_user(client):
    token = await register_and_login(client)
    await create_order(client, token)
    await create_order(client, token)

    response = await client.get(
        "/orders/user/1/",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2
    assert all(order["user_id"] == 1 for order in data)
    assert all(order["total_price"] == 200 for order in data)


async def test_get_nonexistent_order_returns_404(client):
    token = await register_and_login(client)

    response = await client.get(
        "/orders/00000000-0000-0000-0000-000000000000/",
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text


async def test_cannot_access_other_user_order(client):
    token_user_1 = await register_and_login(
        client,
        email="user1@example.com",
        password="password123",
    )
    token_user_2 = await register_and_login(
        client,
        email="user2@example.com",
        password="password123",
    )

    created = await create_order(client, token_user_1)

    response = await client.get(
        f"/orders/{created['id']}/",
        headers=auth_headers(token_user_2),
    )

    assert response.status_code == 403, response.text
