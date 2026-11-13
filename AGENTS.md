# Agent project

Business logic follows the [Django Styleguide](https://github.com/HackSoftware/Django-Styleguide). This API uses Django Ninja: an endpoint validates input, calls a service or selector, and returns. It does not hold business logic.

## Where logic lives

- **Services** — writes, in `services.py`, named `<entity>_<action>`.
- **Selectors** — reads, in `selectors.py`, with the same naming style. List filters stay inside the selector.
- **Models** — simple properties, and `Model.clean` for checks on non-relational fields.

Logic does not belong in Ninja endpoints, schemas, `Model.save`, custom managers, or signals.

## Ninja

One function per operation, with Pydantic input and output schemas. Import the service module so the endpoint name does not shadow the service:

```python
from apps.users import services

user = services.user_create(email=payload.email, name=payload.name)
```

Domain code lives in `backend/apps/<name>/` as `models.py`, `services.py`, `selectors.py`, `api.py`, and `schemas.py`. Register the router from `backend/config/api.py`.

File-specific rules are in `.cursor/rules/`.
