"""Lossless JSON numbers and canonical request values for portable retries."""
import json
from decimal import Decimal


def reject_constant(_):
    raise ValueError("Non-JSON numeric constant")


def loads(raw):
    # Decimal preserves huge finite exponents and distinguishes float literals
    # from JSON integer literals for the party_size rule.
    return json.loads(raw, parse_float=Decimal, parse_constant=reject_constant)


def number(value):
    sign, digits, exponent = Decimal(value).as_tuple()
    digits = list(digits)
    if not any(digits):
        return "0e0"
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    return ("-" if sign else "") + "".join(map(str, digits)) + "e" + str(exponent)


def canonical(value):
    """Return valid JSON with sorted keys and normalized numbers, iteratively."""
    pieces = []
    pending = [(False, value)]
    while pending:
        literal, value = pending.pop()
        if literal:
            pieces.append(value)
        elif isinstance(value, dict):
            pieces.append("{")
            entries = sorted(value.items())
            pending.append((True, "}"))
            for index in range(len(entries) - 1, -1, -1):
                key, child = entries[index]
                pending.append((False, child))
                pending.append((True, json.dumps(key, ensure_ascii=True) + ":"))
                if index:
                    pending.append((True, ","))
        elif isinstance(value, list):
            pieces.append("[")
            pending.append((True, "]"))
            for index in range(len(value) - 1, -1, -1):
                pending.append((False, value[index]))
                if index:
                    pending.append((True, ","))
        elif type(value) is int or isinstance(value, Decimal):
            pieces.append(number(value))
        else:
            pieces.append(json.dumps(value, ensure_ascii=True, allow_nan=False))
    return "".join(pieces)
