"""Configuración de la aplicación desde variables de entorno (ver .env.example)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_DATABASE_URL = "sqlite:///./licitaciones.db"
DEFAULT_SECRET_KEY = "cambiar-esta-clave-de-ejemplo-solo-desarrollo"  # ejemplo, NO es un secreto real
DEFAULT_ENV = "dev"
DEFAULT_EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/USD"


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable. Los tests construyen su propia instancia (BD limpia por prueba)."""

    database_url: str = DEFAULT_DATABASE_URL
    secret_key: str = DEFAULT_SECRET_KEY
    env: str = DEFAULT_ENV  # dev | test | prod
    exchange_rate_url: str = DEFAULT_EXCHANGE_RATE_URL  # solo lo usa HttpExchangeRateProvider (app real)

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"


def get_settings() -> Settings:
    """Lee DATABASE_URL, SECRET_KEY, ENV y EXCHANGE_RATE_URL del entorno (y de .env si existe)."""
    load_dotenv()  # no pisa variables ya definidas en el entorno
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        secret_key=os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
        env=os.getenv("ENV", DEFAULT_ENV),
        exchange_rate_url=os.getenv("EXCHANGE_RATE_URL", DEFAULT_EXCHANGE_RATE_URL),
    )
