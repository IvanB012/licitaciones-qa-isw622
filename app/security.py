"""Hash de contraseñas con argon2 (nunca se guardan en claro)."""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# Hash de relleno para igualar el tiempo de respuesta cuando el usuario no existe.
DUMMY_HASH = _hasher.hash("relleno-no-es-una-contrasena")
