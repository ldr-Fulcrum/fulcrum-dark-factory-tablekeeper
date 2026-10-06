"""Portable JSON state, hashed credentials and transactional fixture validation."""
import hashlib
import hmac
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from errors import APIError, email, fail, integer, reference, required, string
from json_value import canonical, loads
from local_time import UTC, WEEKDAYS, interval, iso, local_datetime, minutes, timestamp, zone

PUBLIC_FIELDS = ("reservation_id", "reference", "restaurant_id", "table_id", "party_size", "status", "starts_at_local", "starts_at", "ends_at", "created_at")
SCRYPT_N = 2048


def clone_json(value):
    """Copy JSON containers without consuming Python's recursion stack."""
    if not isinstance(value, (dict, list)):
        return value
    root = {} if isinstance(value, dict) else []
    pending = [(value, root)]
    while pending:
        source, target = pending.pop()
        entries = source.items() if isinstance(source, dict) else enumerate(source)
        for key, child in entries:
            copied = ({} if isinstance(child, dict) else []) if isinstance(child, (dict, list)) else child
            if isinstance(target, dict):
                target[key] = copied
            else:
                target.append(copied)
            if isinstance(child, (dict, list)):
                pending.append((child, copied))
    return root


def empty_state():
    return {"version": 1, "users": {}, "restaurants": {}, "tokens": {}, "reservations": {}, "idempotency": [], "sequence": 0}


def password_hash(password: str):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=8, p=1, dklen=32)
    return {"salt": salt.hex(), "digest": digest.hex()}


def password_matches(password: str, stored: dict):
    actual = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(stored["salt"]), n=SCRYPT_N, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual.hex(), stored["digest"])


def public(booking: dict):
    return {key: booking[key] for key in PUBLIC_FIELDS}


def overlap(first: dict, second: dict):
    return (first["restaurant_id"] == second["restaurant_id"] and first["table_id"] == second["table_id"]
            and timestamp(first["starts_at"]) < timestamp(second["ends_at"])
            and timestamp(second["starts_at"]) < timestamp(first["ends_at"]))


def occupancy(state: dict, proposed: list, exclude=()):
    remaining = [b for ref, b in state["reservations"].items() if ref not in exclude and b["status"] == "confirmed"]
    for booking in proposed:
        if any(overlap(booking, other) for other in remaining):
            fail(409, "table_unavailable")
        remaining.append(booking)


def fields(body: dict):
    required(body, ("restaurant_id", "table_id", "starts_at_local", "party_size"))
    string(body["restaurant_id"], identifier=True)
    string(body["table_id"], identifier=True)
    local_datetime(body["starts_at_local"])
    integer(body["party_size"])


def booking_values(state: dict, body: dict):
    fields(body)
    restaurant = state["restaurants"].get(body["restaurant_id"])
    if restaurant is None:
        fail(404, "not_found")
    start, end = interval(restaurant, body["table_id"], body["starts_at_local"], body["party_size"])
    tz = zone(restaurant["timezone"])
    return {"restaurant_id": body["restaurant_id"], "table_id": body["table_id"], "starts_at_local": body["starts_at_local"],
            "party_size": body["party_size"], "starts_at": iso(start, tz), "ends_at": iso(end, tz)}


def restaurant_record(raw):
    if not isinstance(raw, dict):
        fail()
    required(raw, ("id", "name", "timezone", "slot_minutes", "reservation_duration_minutes", "cancellation_cutoff_minutes", "opening_hours", "tables"))
    record = {k: raw[k] for k in ("id", "name", "timezone", "slot_minutes", "reservation_duration_minutes", "cancellation_cutoff_minutes")}
    string(record["id"], identifier=True)
    string(record["name"])
    string(record["timezone"])
    zone(record["timezone"])
    integer(record["slot_minutes"])
    integer(record["reservation_duration_minutes"])
    integer(record["cancellation_cutoff_minutes"], 0)
    if not isinstance(raw["opening_hours"], list) or not isinstance(raw["tables"], list):
        fail()
    record["opening_hours"], record["tables"] = [], []
    days, table_ids = set(), set()
    for item in raw["opening_hours"]:
        if not isinstance(item, dict):
            fail()
        required(item, ("weekday", "opens", "closes"))
        day = string(item["weekday"])
        if day not in WEEKDAYS or day in days or minutes(item["opens"]) >= minutes(item["closes"]):
            fail()
        days.add(day)
        record["opening_hours"].append({k: item[k] for k in ("weekday", "opens", "closes")})
    for item in raw["tables"]:
        if not isinstance(item, dict):
            fail()
        required(item, ("id", "label", "capacity"))
        table_id = string(item["id"], identifier=True)
        string(item["label"])
        integer(item["capacity"])
        if table_id in table_ids:
            fail()
        table_ids.add(table_id)
        record["tables"].append({k: item[k] for k in ("id", "label", "capacity")})
    return record


def fixture(raw: dict):
    """Construct independently; callers swap it in only after full validation."""
    result = empty_state()
    try:
        arrays = [raw.get(k, []) for k in ("users", "restaurants", "reservations")]
        if any(not isinstance(a, list) for a in arrays):
            fail()
        users, restaurants, bookings = arrays
        addresses, ids = set(), set()
        credentials = []
        for item in users:
            if not isinstance(item, dict):
                fail()
            required(item, ("id", "email", "password", "display_name"))
            uid = string(item["id"], identifier=True)
            address = email(item["email"])
            name = string(item["display_name"])
            password = string(item["password"])
            # The 8-character minimum is a signup rule; fixture passwords may be any non-empty string.
            if uid in result["users"] or address in addresses:
                fail()
            addresses.add(address)
            result["users"][uid] = {"id": uid, "email": address, "display_name": name}
            credentials.append((uid, password))
        for item in restaurants:
            record = restaurant_record(item)
            if record["id"] in result["restaurants"]:
                fail()
            result["restaurants"][record["id"]] = record
        created = iso(datetime.now(UTC))
        for item in bookings:
            if not isinstance(item, dict):
                fail()
            required(item, ("id", "reference", "user_id"))
            rid = string(item["id"], identifier=True)
            ref = reference(item["reference"])
            uid = string(item["user_id"], identifier=True)
            if uid not in result["users"] or rid in ids or ref in result["reservations"]:
                fail()
            values = booking_values(result, item)
            result["sequence"] += 1
            booking = {**values, "reservation_id": rid, "reference": ref, "user_id": uid, "status": "confirmed", "created_at": created, "_order": result["sequence"]}
            occupancy(result, [booking])
            result["reservations"][ref] = booking
            ids.add(rid)
        # scrypt releases the GIL. Two bounded workers use the two allowed CPUs,
        # preserving independent random salts without serializing a large seed.
        with ThreadPoolExecutor(max_workers=2) as pool:
            hashed = pool.map(password_hash, (password for _, password in credentials))
            for (uid, _), digest in zip(credentials, hashed):
                result["users"][uid]["password_hash"] = digest
        return result
    except (APIError, ValueError, TypeError, KeyError, OverflowError):
        fail()


def validate_public(state, item):
    if not isinstance(item, dict):
        fail()
    required(item, PUBLIC_FIELDS)
    string(item["reservation_id"], identifier=True)
    reference(item["reference"])
    if item["status"] not in ("confirmed", "cancelled"):
        fail()
    values = booking_values(state, item)
    if any(item[k] != v for k, v in values.items()):
        fail()
    timestamp(item["created_at"])


def import_state(envelope: dict):
    try:
        if envelope.get("track") != "tablekeeper" or type(envelope.get("format_version")) is not int or envelope["format_version"] != 1:
            fail()
        state = envelope.get("state")
        if not isinstance(state, dict) or set(state) != set(empty_state()):
            fail()
        if type(state["version"]) is not int or state["version"] != 1:
            fail()
        integer(state["sequence"], 0)
        if any(not isinstance(state[k], dict) for k in ("users", "restaurants", "tokens", "reservations")) or not isinstance(state["idempotency"], list):
            fail()
        addresses = set()
        for uid, user in state["users"].items():
            string(uid, identifier=True)
            if not isinstance(user, dict) or set(user) != {"id", "email", "display_name", "password_hash"} or user.get("id") != uid:
                fail()
            address = email(user["email"])
            string(user["display_name"])
            if address != user["email"] or address in addresses:
                fail()
            addresses.add(address)
            hashed = user["password_hash"]
            if not isinstance(hashed, dict) or set(hashed) != {"salt", "digest"}:
                fail()
            for key, length in (("salt", 16), ("digest", 32)):
                string(hashed[key])
                if len(hashed[key]) != length * 2 or len(bytes.fromhex(hashed[key])) != length or hashed[key].lower() != hashed[key]:
                    fail()
        for rid, restaurant in state["restaurants"].items():
            if restaurant_record(restaurant) != restaurant or rid != restaurant["id"]:
                fail()
        for token, uid in state["tokens"].items():
            string(token)
            if not isinstance(uid, str) or uid not in state["users"]:
                fail()
        ids, orders = set(), set()
        confirmed = []
        for ref, booking in state["reservations"].items():
            validate_public(state, booking)
            uid = booking["user_id"]
            integer(booking["_order"])
            if (ref != booking["reference"] or not isinstance(uid, str) or uid not in state["users"]
                    or booking["reservation_id"] in ids or booking["_order"] in orders or booking["_order"] > state["sequence"]):
                fail()
            ids.add(booking["reservation_id"])
            orders.add(booking["_order"])
            if booking["status"] == "confirmed":
                if any(overlap(booking, other) for other in confirmed):
                    fail()
                confirmed.append(booking)
        keys = set()
        for receipt in state["idempotency"]:
            if not isinstance(receipt, dict) or set(receipt) != {"user_id", "method", "path", "key", "body", "response"}:
                fail()
            uid, key = receipt["user_id"], receipt["key"]
            string(key)
            if len(key) > 255 or not isinstance(uid, str) or uid not in state["users"] or receipt["method"] != "POST" or not isinstance(receipt["body"], str):
                fail()
            request = loads(receipt["body"])
            if not isinstance(request, dict) or canonical(request) != receipt["body"]:
                fail()
            if receipt["path"] not in ("/reservations", "/reservation-moves"):
                fail()
            identity = (uid, receipt["method"], receipt["path"], key)
            if identity in keys:
                fail()
            keys.add(identity)
            if receipt["path"] == "/reservations":
                responses = [receipt["response"]]
            else:
                response = receipt["response"]
                if not isinstance(response, dict) or set(response) != {"reservations"} or not isinstance(response["reservations"], list) or not 1 <= len(response["reservations"]) <= 8:
                    fail()
                responses = response["reservations"]
            seen = set()
            for response in responses:
                validate_public(state, response)
                original = state["reservations"].get(response["reference"])
                if (original is None or original["user_id"] != uid or original["reservation_id"] != response["reservation_id"]
                        or original["created_at"] != response["created_at"] or response["reference"] in seen):
                    fail()
                seen.add(response["reference"])
        return clone_json(state)
    except (APIError, ValueError, TypeError, KeyError, ArithmeticError, RecursionError):
        fail()
