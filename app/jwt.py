import jwt

def verify_token(token: str, jwt_secret: str) -> bool:
    try:
        jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return True
    except jwt.InvalidTokenError as exec:
        return False