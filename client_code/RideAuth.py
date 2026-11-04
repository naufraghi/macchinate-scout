import json
import time

import anvil.server
from anvil.js.window import localStorage


_PENDING_ACTION_KEY = "m3_pending_ride_action_v1"
_PENDING_ACTION_TTL_SECONDS = 7 * 24 * 60 * 60


def request_email_access(email, pending_action=None):
    result = anvil.server.call("inizia_accesso_email", email)
    if result.get("ok") and pending_action is not None:
        save_pending_action(pending_action)
    return result


def save_pending_action(action):
    envelope = {"saved_at": int(time.time()), "action": action}
    localStorage.setItem(_PENDING_ACTION_KEY, json.dumps(envelope))


def load_pending_action():
    raw = localStorage.getItem(_PENDING_ACTION_KEY)
    if raw is None:
        return None

    try:
        envelope = json.loads(raw)
        saved_at = float(envelope["saved_at"])
        action = envelope["action"]
    except (TypeError, ValueError, KeyError):
        clear_pending_action()
        return None

    if (
        not isinstance(envelope, dict)
        or not isinstance(action, dict)
        or saved_at > time.time() + 60
        or time.time() - saved_at > _PENDING_ACTION_TTL_SECONDS
    ):
        clear_pending_action()
        return None

    return action


def clear_pending_action():
    localStorage.removeItem(_PENDING_ACTION_KEY)
