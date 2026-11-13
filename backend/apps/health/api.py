from django.db import connection
from ninja import Router

from apps.health.schemas import HealthOut

router = Router(tags=["health"])


@router.get("/health", response=HealthOut)
def health(request) -> HealthOut:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return HealthOut(status="ok")
