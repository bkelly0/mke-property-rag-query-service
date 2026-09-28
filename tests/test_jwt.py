import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-bytes")

from app import main
from app.jwt import verify_token

TEST_SECRET = "test-secret-that-is-at-least-32-bytes"


def _make_token(secret: str = TEST_SECRET) -> str:
    return jwt.encode(
        {
            "sub": "test-user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def test_verify_token_accepts_valid_token() -> None:
    assert verify_token(_make_token(), TEST_SECRET)


@pytest.mark.parametrize(
    ("token", "secret"),
    [
        ("not-a-jwt", TEST_SECRET),
        (_make_token("different-secret-that-is-long-enough"), TEST_SECRET),
        (_make_token(), "wrong-secret-that-is-also-at-least-32"),
    ],
)
def test_verify_token_rejects_invalid_token(token: str, secret: str) -> None:
    assert not verify_token(token, secret)


def test_verify_token_rejects_expired_token() -> None:
    token = jwt.encode(
        {
            "sub": "test-user",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    assert not verify_token(token, TEST_SECRET)


@pytest.mark.parametrize("claims", [{"sub": "test-user"}, {"exp": 2_000_000_000}])
def test_verify_token_rejects_missing_required_claims(claims: dict) -> None:
    token = jwt.encode(claims, TEST_SECRET, algorithm="HS256")

    assert not verify_token(token, TEST_SECRET)


def test_authorize_accepts_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(jwt_secret_key=TEST_SECRET),
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=_make_token(),
    )

    assert main._authorize(credentials) is None


def test_authorize_rejects_invalid_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(jwt_secret_key=TEST_SECRET),
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="not-a-jwt",
    )

    with pytest.raises(HTTPException) as error:
        main._authorize(credentials)

    assert error.value.status_code == 401
