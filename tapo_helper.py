#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_helper.py

import json
import sys
import os
import urllib.parse
import urllib.request

from tapo_credentials import CAMERA_IP, USERNAME, PASSWORD, FHEMIP, FHEMPORT, FHEMCSRF, FHEMDEVICE


def get_tapo_class():
    try:
        from pytapo import Tapo
        return Tapo
    except ImportError:
        print(json.dumps({"error": "Python-Modul 'pytapo' nicht gefunden"}))
        sys.exit(1)


def create_tapo():
    Tapo = get_tapo_class()
    try:
        return Tapo(CAMERA_IP, USERNAME, PASSWORD)
    except Exception as exc:
        error_exit(f"Verbindung zur Kamera fehlgeschlagen: {exc}")


def normalize_on_off(value):
    if isinstance(value, bool):
        return "on" if value else "off"
    if value is None:
        return None
    return str(value).lower()


def print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False))


def error_exit(message: str, script_name: str = None):
    """
    Sendet einen Fehler an FHEM und beendet das Skript.
    """
    if script_name is None:
        script_name = sys.argv[0]

    payload = {
        "result": "error",
        "message": message
    }

    try:
        return_FHEM(script_name, payload)
    except Exception:
        print(f"ERROR: {message}")

    sys.exit(1)


def return_FHEM(script_name: str, data):
    base = os.path.basename(script_name)

    if base.startswith("tapo_control_") and base.endswith(".py"):
        command = base[len("tapo_control_"):-3]
    else:
        command = os.path.splitext(base)[0]

    json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    # Für Perl-String escapen
    json_escaped = json_str.replace("\\", "\\\\").replace('"', '\\"')

    perl_cmd = f'{{ TapoReturnHandler("{FHEMDEVICE}","{command}","{json_escaped}") }}'

    query = urllib.parse.urlencode({
        "fwcsrf": FHEMCSRF,
        "cmd": perl_cmd,
        "XHR": "1",
    })

    url = f"http://{FHEMIP}:{FHEMPORT}/fhem?{query}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Fehler beim Rückruf an FHEM: {e}")
        return None


def send_result(script_name: str, payload: dict):
    if isinstance(payload, dict):
        if "error" in payload and not payload["error"]:
            payload.pop("error")

    return return_FHEM(script_name, payload)
