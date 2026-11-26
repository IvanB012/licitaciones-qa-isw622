from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Sin autenticación (contrato §5)."""
    return {"status": "ok"}
