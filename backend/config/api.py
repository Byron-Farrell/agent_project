from ninja import NinjaAPI

from apps.health.api import router as health_router

api = NinjaAPI(title="Agent project API", urls_namespace="api")
api.add_router("", health_router)
