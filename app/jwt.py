import jwt
from app.logger import logger


def verify_token(token: str, jwt_secret: str) -> bool:
    try:
        jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
        return True
    except jwt.InvalidTokenError as ex:
        logger.debug(str(ex))
        return False