#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_detection.py

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import tapo_helper as helper


VALID_TYPES = {
    "motion": "Motion",
    "person": "Person",
    "vehicle": "Vehicle",
    "pet": "Pet",
    "tamper": "Tamper",
    "linecrossing": "Linecrossing",
}


def parse_sensitivity(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        helper.error_exit("Empfindlichkeit muss eine ganze Zahl zwischen 0 und 100 sein")

    if value < 0 or value > 100:
        helper.error_exit("Empfindlichkeit muss zwischen 0 und 100 liegen")

    return value


def map_tamper_sensitivity(value: int) -> str:
    if value == 100:
        return "high"
    return "normal"


def keep_motion_fields(data: dict) -> dict:
    return {
        "enabled": helper.normalize_on_off(data.get("enabled")),
        "sensitivity": str(data.get("digital_sensitivity"))
        if data.get("digital_sensitivity") is not None else None,
    }


def keep_standard_fields(data: dict) -> dict:
    result = {
        "enabled": helper.normalize_on_off(data.get("enabled")),
    }
    if "sensitivity" in data and data.get("sensitivity") is not None:
        result["sensitivity"] = str(data.get("sensitivity"))
    return result


def call_get_detection(tapo, kind: str) -> dict:
    method_name = f"get{VALID_TYPES[kind]}Detection"
    method = getattr(tapo, method_name, None)
    if method is None:
        helper.error_exit(f"Methode {method_name} nicht vorhanden")

    try:
        data = method()
    except Exception as exc:
        helper.error_exit(f"Fehler bei {method_name}: {exc}")

    if not isinstance(data, dict):
        helper.error_exit(f"Unerwartete Rückgabe von {method_name}: {data!r}")

    if kind == "motion":
        return keep_motion_fields(data)

    return keep_standard_fields(data)


def get_status(tapo) -> dict:
    return {
        "motion": call_get_detection(tapo, "motion"),
        "person": call_get_detection(tapo, "person"),
        "vehicle": call_get_detection(tapo, "vehicle"),
        "pet": call_get_detection(tapo, "pet"),
        "tamper": call_get_detection(tapo, "tamper"),
        "linecrossing": call_get_detection(tapo, "linecrossing"),
    }


def set_detection(tapo, kind: str, value: int):
    if kind not in VALID_TYPES:
        helper.error_exit(
            "Ungültiger Typ. Erlaubt sind: motion, person, vehicle, pet, tamper, linecrossing"
        )

    method_name = f"set{VALID_TYPES[kind]}Detection"
    method = getattr(tapo, method_name, None)
    if method is None:
        helper.error_exit(f"Methode {method_name} nicht vorhanden")

    enabled = value != 0

    try:
        if kind == "linecrossing":
            result = method(enabled)
        elif kind == "tamper":
            sens = map_tamper_sensitivity(value)
            result = method(enabled, sens)
        else:
            result = method(enabled, value)
    except TypeError as exc:
        helper.error_exit(f"Falsche Parameter für {method_name}: {exc}")
    except Exception as exc:
        helper.error_exit(f"Fehler bei {method_name}: {exc}")

    return result


def usage() -> None:
    prog = Path(sys.argv[0]).name
    print(
        f"Aufruf:\n"
        f"  {prog} status\n"
        f"  {prog} motion <0-100>\n"
        f"  {prog} person <0-100>\n"
        f"  {prog} vehicle <0-100>\n"
        f"  {prog} pet <0-100>\n"
        f"  {prog} tamper <0-100>\n"
        f"  {prog} linecrossing <0-100>\n"
    )


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1].strip().lower()
    tapo = helper.create_tapo()

    if command == "status":
        if len(sys.argv) != 2:
            usage()
            sys.exit(1)

        result = get_status(tapo)
        helper.send_result(__file__, result)
        return

    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    sensitivity = parse_sensitivity(sys.argv[2])
    set_result = set_detection(tapo, command, sensitivity)

    output = {
        "action": command,
        "enabled": sensitivity != 0,
        "value": sensitivity,
        "result": set_result,
    }
    helper.send_result(__file__, output)


if __name__ == "__main__":
    main()
