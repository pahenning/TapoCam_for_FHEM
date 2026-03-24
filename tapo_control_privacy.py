#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_privacy.py

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import tapo_helper as helper


def get_privacy(tapo) -> str:
    method = getattr(tapo, "getPrivacyMode", None)
    if method is None:
        helper.error_exit("Methode getPrivacyMode nicht vorhanden")

    try:
        data = method()
    except Exception as exc:
        helper.error_exit(f"Fehler bei getPrivacyMode: {exc}")

    if not isinstance(data, dict):
        helper.error_exit(f"Unerwartete Rückgabe von getPrivacyMode: {data!r}")

    return helper.normalize_on_off(data.get("enabled"))


def set_privacy(tapo, enabled: bool):
    method = getattr(tapo, "setPrivacyMode", None)
    if method is None:
        helper.error_exit("Methode setPrivacyMode nicht vorhanden")

    try:
        return method(enabled)
    except Exception as exc:
        helper.error_exit(f"Fehler bei setPrivacyMode: {exc}")


def parse_on_off(raw: str) -> bool:
    val = raw.strip().lower()
    if val == "on":
        return True
    if val == "off":
        return False
    helper.error_exit("Wert muss 'on' oder 'off' sein")


def usage() -> None:
    print(f"Usage: {Path(sys.argv[0]).name} [on|off]")


def main() -> None:
    tapo = helper.create_tapo()

    if len(sys.argv) == 1:
        helper.send_result(__file__, {
            "privacy": get_privacy(tapo)
        })
        return

    if len(sys.argv) == 2:
        desired = parse_on_off(sys.argv[1])
        set_privacy(tapo, desired)
        helper.send_result(__file__, {
            "privacy": get_privacy(tapo)
        })
        return

    usage()
    sys.exit(1)


if __name__ == "__main__":
    main()
