"""Stage 1 HTTP behavior; all booking transactions run under one state lock."""
import re
import secrets
import threading
from datetime import datetime, timedelta
from urllib.parse import parse_qs, unquote, urlsplit

from errors import email, fail, integer, required, string
from json_value import canonical
from local_time import UTC, WEEKDAYS, calendar_day, closing_instant, iso, minutes, resolve, timestamp, zone
from state import booking_values, clone_json, empty_state, fixture, import_state, occupancy, overlap, password_hash, password_matches, public

AMEND_FIELDS = ("table_id", "starts_at_local", "party_size")


def json_equal(a, b):
    """JSON booleans are distinct from numbers; object member order is irrelevant."""
    pending = [(a, b)]
    while pending:
        a, b = pending.pop()
        if type(a) is bool or type(b) is bool:
            if type(a) is not type(b) or a != b:
                return False
        elif isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                return False
            pending.extend((a[k], b[k]) for k in a)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                return False
            pending.extend(zip(a, b))
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a != b:
                return False
        elif type(a) is not type(b) or a != b:
            return False
    return True


class Service:
    def __init__(self):
        self.lock = threading.RLock()
        self.state = empty_state()

    def authenticate(self, authorization):
        match = re.fullmatch(r"Bearer ([^\s]+)", authorization or "", re.IGNORECASE)
        uid = self.state["tokens"].get(match.group(1)) if match else None
        if uid is None:
            fail(401, "unauthenticated")
        return uid

    @staticmethod
    def route(method, path):
        fixed = {("GET", "/health"), ("POST", "/_test/reset"), ("GET", "/_test/export"), ("POST", "/_test/import"),
                 ("POST", "/auth/signup"), ("POST", "/auth/login"), ("GET", "/restaurants"), ("GET", "/availability"),
                 ("POST", "/reservations"), ("GET", "/reservations"), ("POST", "/reservation-moves")}
        if (method, path) in fixed:
            return path, None
        if method == "GET" and re.fullmatch(r"/restaurants/[^/]+", path):
            return "/restaurant", unquote(path.rsplit("/", 1)[1])
        match = re.fullmatch(r"/reservations/([^/]+)(/cancel)?", path)
        if match:
            if method in ("GET", "PATCH") and not match.group(2):
                return "/reservation", unquote(match.group(1))
            if method == "POST" and match.group(2):
                return "/cancel", unquote(match.group(1))
        fail(404, "not_found")

    def dispatch(self, method, target, authorization, key, read_body):
        parsed = urlsplit(target)
        path, identifier = self.route(method, parsed.path)
        protected = path in ("/reservations", "/reservation", "/cancel", "/reservation-moves")
        # Authenticate before parsing the body. Recheck inside the transaction after
        # parsing so a concurrent reset cannot revive an old credential.
        if protected:
            with self.lock:
                self.authenticate(authorization)
        body = read_body() if method in ("POST", "PATCH") and path != "/cancel" else None
        if path == "/_test/reset":
            replacement = fixture(body)
            with self.lock:
                self.state = replacement
            return 204, None
        if path == "/_test/import":
            replacement = import_state(body)
            with self.lock:
                self.state = replacement
            return 204, None
        if path in ("/auth/signup", "/auth/login"):
            return self.auth(path, body)
        with self.lock:
            uid = self.authenticate(authorization) if protected else None
            if path == "/health":
                return 200, {"status": "ok"}
            if path == "/_test/export":
                return 200, {"track": "tablekeeper", "format_version": 1, "state": clone_json(self.state)}
            if path == "/restaurants":
                return 200, {"restaurants": [{k: r[k] for k in ("id", "name", "timezone")} for r in self.state["restaurants"].values()]}
            if path == "/restaurant":
                if len(identifier) > 64 or identifier not in self.state["restaurants"]:
                    fail(404, "not_found")
                return 200, clone_json(self.state["restaurants"][identifier])
            if path == "/availability":
                return 200, self.availability(parse_qs(parsed.query, keep_blank_values=True))
            if path == "/reservations" and method == "GET":
                rows = [b for b in self.state["reservations"].values() if b["user_id"] == uid]
                rows.sort(key=lambda b: (timestamp(b["starts_at"]), b["_order"]), reverse=True)
                return 200, {"reservations": [public(b) for b in rows]}
            if path == "/reservations":
                return self.idempotent(uid, parsed.path, key, body, lambda: self.create(uid, body))
            if path == "/reservation-moves":
                return self.idempotent(uid, parsed.path, key, body, lambda: self.moves(uid, body))
            booking = self.owned(uid, identifier)
            if path == "/cancel":
                if booking["status"] != "cancelled":
                    self.cutoff(booking)
                    booking["status"] = "cancelled"
                return 200, public(booking)
            if method == "GET":
                return 200, public(booking)
            self.changeable(booking)
            if not any(k in body for k in AMEND_FIELDS):
                return 200, public(booking)
            changed = self.amend(booking, body)
            occupancy(self.state, [changed], exclude=(identifier,))
            self.state["reservations"][identifier] = changed
            return 200, public(changed)

    def auth(self, path, body):
        required(body, ("email", "password", "display_name") if path == "/auth/signup" else ("email", "password"))
        address = email(body["email"])
        password = string(body["password"])
        if len(password) < 8:
            fail()
        if path == "/auth/signup":
            name = string(body["display_name"])
            with self.lock:
                if any(u["email"] == address for u in self.state["users"].values()):
                    fail(409, "email_taken")
            hashed = password_hash(password)
            with self.lock:
                if any(u["email"] == address for u in self.state["users"].values()):
                    fail(409, "email_taken")
                uid = self.unique_id("u_", self.state["users"])
                user = {"id": uid, "email": address, "display_name": name, "password_hash": hashed}
                self.state["users"][uid] = user
                return 201, self.session(user)
        with self.lock:
            user = next((u for u in self.state["users"].values() if u["email"] == address), None)
        if user is None or not password_matches(password, user["password_hash"]):
            fail(401, "unauthenticated")
        with self.lock:
            if self.state["users"].get(user["id"]) is not user:
                fail(401, "unauthenticated")
            return 200, self.session(user)

    def session(self, user):
        token = self.unique_id("", self.state["tokens"])
        self.state["tokens"][token] = user["id"]
        return {"user_id": user["id"], "display_name": user["display_name"], "token": token}

    @staticmethod
    def unique_id(prefix, existing):
        while True:
            value = prefix + secrets.token_hex(16)
            if value not in existing:
                return value

    def owned(self, uid, ref):
        booking = self.state["reservations"].get(ref) if len(ref) <= 64 else None
        if booking is None or booking["user_id"] != uid:
            fail(404, "not_found")
        return booking

    def cutoff(self, booking):
        restaurant = self.state["restaurants"][booking["restaurant_id"]]
        # Subtraction via a difference avoids datetime overflow for long cutoffs.
        if (timestamp(booking["starts_at"]) - datetime.now(UTC)).total_seconds() <= restaurant["cancellation_cutoff_minutes"] * 60:
            fail(409, "cutoff_passed")

    def changeable(self, booking):
        if booking["status"] == "cancelled":
            fail(409, "reservation_cancelled")
        self.cutoff(booking)

    def idempotent(self, uid, path, key, body, operation):
        if not key:
            fail(400, "missing_idempotency_key")
        if len(key) > 255:
            fail()
        stored_body = canonical(body)
        for receipt in self.state["idempotency"]:
            if (receipt["user_id"], receipt["method"], receipt["path"], receipt["key"]) == (uid, "POST", path, key):
                if receipt["body"] != stored_body:
                    fail(409, "idempotency_key_reuse")
                return 200, clone_json(receipt["response"])
        # The canonical JSON string preserves every request value without exposing
        # deep input containers or implementation-specific numeric types to export.
        response = operation()
        self.state["idempotency"].append({"user_id": uid, "method": "POST", "path": path, "key": key,
                                          "body": stored_body, "response": clone_json(response)})
        return 201, response

    def create(self, uid, body):
        values = booking_values(self.state, body)
        # All validation, including occupancy, precedes state mutation.
        occupancy(self.state, [values])
        ids = {b["reservation_id"] for b in self.state["reservations"].values()}
        rid = self.unique_id("res_", ids)
        while True:
            ref = secrets.token_hex(5).upper()
            if ref not in self.state["reservations"]:
                break
        self.state["sequence"] += 1
        booking = {**values, "reservation_id": rid, "reference": ref, "user_id": uid, "status": "confirmed",
                   "created_at": iso(datetime.now(UTC)), "_order": self.state["sequence"]}
        self.state["reservations"][ref] = booking
        return public(booking)

    def amend(self, booking, changes):
        body = {key: booking[key] for key in ("restaurant_id", *AMEND_FIELDS)}
        body.update({key: changes[key] for key in AMEND_FIELDS if key in changes})
        return {**booking, **booking_values(self.state, body)}

    def moves(self, uid, body):
        items = body.get("moves")
        if not isinstance(items, list) or not 1 <= len(items) <= 8:
            fail()
        if any(not isinstance(item, dict) or "reference" not in item for item in items):
            fail()
        # Duplicate references are a shape error even before wrong-type fields.
        refs = [item["reference"] for item in items]
        if any(json_equal(a, b) for i, a in enumerate(refs) for b in refs[:i]):
            fail()
        for item in items:
            for field in ("reference", "table_id", "starts_at_local"):
                if field in item and not isinstance(item[field], str):
                    fail(400, "malformed_request")
        for ref in refs:
            string(ref, identifier=True)
        bookings = [self.owned(uid, ref) for ref in refs]
        if len({b["restaurant_id"] for b in bookings}) != 1:
            fail()
        proposed = []
        for booking, item in zip(bookings, items):
            self.changeable(booking)
            proposed.append(self.amend(booking, item))
        occupancy(self.state, proposed, exclude=refs)
        for ref, booking in zip(refs, proposed):
            self.state["reservations"][ref] = booking
        return {"reservations": [public(b) for b in proposed]}

    def availability(self, query):
        values = {k: query.get(k, [""])[0] for k in ("restaurant_id", "date", "party_size")}
        if not all(values.values()):
            fail()
        rid = string(values["restaurant_id"], identifier=True)
        day = calendar_day(values["date"])
        if not re.fullmatch(r"[0-9]+", values["party_size"]):
            fail()
        party = int(values["party_size"])
        integer(party)
        restaurant = self.state["restaurants"].get(rid)
        if restaurant is None:
            fail(404, "not_found")
        result = {"restaurant_id": rid, "date": values["date"], "timezone": restaurant["timezone"], "slots": []}
        hours = next((h for h in restaurant["opening_hours"] if h["weekday"] == WEEKDAYS[day.weekday()]), None)
        if hours is None:
            return result
        tz = zone(restaurant["timezone"])
        closing = minutes(hours["closes"])
        close = closing_instant(datetime(day.year, day.month, day.day, closing // 60, closing % 60), tz)
        confirmed = [b for b in self.state["reservations"].values() if b["restaurant_id"] == rid and b["status"] == "confirmed"]
        for wall in range(minutes(hours["opens"]), closing, restaurant["slot_minutes"]):
            local = datetime(day.year, day.month, day.day, wall // 60, wall % 60)
            start = resolve(local, tz)
            if start is None:
                continue
            try:
                end = start + timedelta(minutes=restaurant["reservation_duration_minutes"])
            except OverflowError:
                continue
            if end > close:
                continue
            interval_values = {"restaurant_id": rid, "starts_at": iso(start, tz), "ends_at": iso(end, tz)}
            table_ids = []
            for table in restaurant["tables"]:
                if table["capacity"] >= party and not any(overlap({**interval_values, "table_id": table["id"]}, other) for other in confirmed):
                    table_ids.append(table["id"])
            result["slots"].append({"starts_at_local": local.isoformat(timespec="minutes"), "starts_at": iso(start, tz), "available_table_ids": table_ids})
        return result
