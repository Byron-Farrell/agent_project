import json

import allure
import pytest
from django.db import connection
from django.db.utils import OperationalError
from django.test import Client


@allure.epic("API")
@allure.feature("Health")
@allure.story("Readiness")
class HealthTests:
    @allure.title("Health route reports that the API is ready")
    @allure.description(
        "What: GET /api/health returns HTTP 200 and a body of "
        '{"status": "ok"}.\n\n'
        "Why: this route proves Compose, migrations, and Postgres are "
        "working. If it fails, the API is not ready for traffic."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.django_db
    def test_route_reports_the_api_is_ready(self) -> None:
        with allure.step("Request the health route"):
            response = Client().get("/api/health")

        with allure.step("Expect HTTP 200"):
            assert response.status_code == 200

        with allure.step("Expect the body to report status ok"):
            allure.attach(
                response.content,
                name="response body",
                attachment_type=allure.attachment_type.JSON,
            )
            assert json.loads(response.content) == {"status": "ok"}

    @allure.title("Unknown API paths are not reported as ready")
    @allure.description(
        "What: a path under /api/ that has no route returns HTTP 404.\n\n"
        "Why: readiness is one specific route. A catch-all that answered "
        "200 would hide a missing router and make the check meaningless."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_unknown_path_is_not_reported_as_ready(self) -> None:
        with allure.step("Request a path that has no route"):
            response = Client().get("/api/not-a-route")

        with allure.step("Expect the path to be missing"):
            assert response.status_code == 404

    @allure.title("A database outage is not reported as ready")
    @allure.description(
        "What: when the database probe raises, the health route does not "
        'return {"status": "ok"}.\n\n'
        "Why: swallowing a database error would tell Compose the API is "
        "ready when it cannot use Postgres."
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.django_db
    def test_database_outage_is_not_reported_as_ready(self) -> None:
        client = Client(raise_request_exception=False)

        def unavailable(*args, **kwargs):
            raise OperationalError("database unavailable")

        with allure.step("Simulate a database outage during the probe"):
            original = connection.cursor
            connection.cursor = unavailable
            try:
                response = client.get("/api/health")
            finally:
                connection.cursor = original

        with allure.step("Expect the outage to surface instead of status ok"):
            allure.attach(
                str(response.status_code),
                name="status code",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert response.status_code == 500
            assert response.content != b'{"status": "ok"}'
