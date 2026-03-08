import pytest

pytestmark = pytest.mark.asyncio


async def test_register_user(client):
    payload = {
        "email": "user@example.com",
        "password": "strongpassword123",
    }

    response = await client.post("/register/", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["email"] == payload["email"]
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_duplicate_user_returns_400(client):
    payload = {
        "email": "user@example.com",
        "password": "strongpassword123",
    }

    first = await client.post("/register/", json=payload)
    second = await client.post("/register/", json=payload)

    assert first.status_code == 201, first.text
    assert second.status_code in (400, 409), second.text


async def test_get_token(client):
    register_payload = {
        "email": "user@example.com",
        "password": "strongpassword123",
    }

    await client.post("/register/", json=register_payload)

    token_payload = {
        "username": "user@example.com",
        "password": "strongpassword123",
    }

    response = await client.post("/token/", data=token_payload)

    assert response.status_code == 200, response.text
    data = response.json()

    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
