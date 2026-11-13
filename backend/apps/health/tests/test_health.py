import json

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_route() -> None:
    response = Client().get("/api/health")

    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "ok"}
