def test_single_account_setup_can_only_initialize_once(auth_client):
    first_response = auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert first_response.status_code == 201
    assert first_response.json()["username"] == "owner"
    assert "password_hash" not in first_response.json()

    second_response = auth_client.post(
        "/api/auth/setup",
        json={"username": "second", "password": "another secure password"},
    )
    assert second_response.status_code == 409


def test_login_returns_bearer_token_and_me_accepts_it(auth_client):
    auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    login_response = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    assert login_response.status_code == 200
    token_body = login_response.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["access_token"]

    me_response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_body['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "owner"


def test_invalid_credentials_return_401(auth_client):
    auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    response = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "wrong password"},
    )

    assert response.status_code == 401


def test_me_requires_valid_bearer_token(auth_client):
    response = auth_client.get("/api/auth/me")

    assert response.status_code == 401
