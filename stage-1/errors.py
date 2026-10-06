"""Public API failures and small, shared validators."""
import re


class APIError(Exception):
    def __init__(self, status: int, code: str):
        self.status = status
        self.code = code
        super().__init__(code)


def fail(status: int = 422, code: str = "validation_failed"):
    raise APIError(status, code)


def string(value, *, identifier=False, nonempty=True):
    if not isinstance(value, str):
        fail(400, "malformed_request")
    if (nonempty and not value) or (identifier and len(value) > 64):
        fail()
    # Lone JSON surrogates are not Unicode scalar values.
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        fail()
    return value


def integer(value, minimum=1):
    if type(value) is not int or value < minimum:
        fail()
    return value


def required(body: dict, fields):
    if any(field not in body for field in fields):
        fail()


def email(value):
    string(value)
    if value.count("@") != 1 or any(c.isspace() for c in value):
        fail()
    local, domain = value.split("@")
    if not local or not domain:
        fail()
    return value.casefold()


def reference(value):
    string(value, identifier=True)
    if not re.fullmatch(r"[A-Z0-9]{6,12}", value):
        fail()
    return value
