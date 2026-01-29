import contextvars

request_id_var = contextvars.ContextVar("request_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)
persona_id_var = contextvars.ContextVar("persona_id", default=None)


def set_request_context(request_id: str | None, user_id: str | None = None, persona_id: str | None = None):
    request_id_var.set(request_id)
    user_id_var.set(user_id)
    persona_id_var.set(persona_id)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_user_id() -> str | None:
    return user_id_var.get()


def get_persona_id() -> str | None:
    return persona_id_var.get()
