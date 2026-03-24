#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_alarm.py

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import tapo_helper as helper


def get_alarm_status(tapo) -> dict:
    method = getattr(tapo, "getAlarm", None)
    if method is None:
        helper.error_exit("Methode getAlarm nicht vorhanden")

    try:
        data = method()
    except Exception as exc:
        helper.error_exit(f"Fehler bei getAlarm: {exc}")

    if not isinstance(data, dict):
        helper.error_exit(f"Unerwartete Rückgabe von getAlarm: {data!r}")

    alarm_mode = data.get("alarm_mode") or []
    if not isinstance(alarm_mode, list):
        alarm_mode = []

    sound_on = ("sound" in alarm_mode) or ("siren" in alarm_mode)
    light_on = "light" in alarm_mode

    return {
        "status": helper.normalize_on_off(data.get("enabled")),
        "sound": "on" if sound_on else "off",
        "light": "on" if light_on else "off",
        "volume": str(data.get("alarm_volume")) if data.get("alarm_volume") is not None else None,
        "duration": str(data.get("alarm_duration")) if data.get("alarm_duration") is not None else None,
    }


def parse_on_off(raw: str) -> bool:
    value = raw.strip().lower()
    if value == "on":
        return True
    if value == "off":
        return False
    helper.error_exit("Wert muss on oder off sein")


def parse_duration(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        helper.error_exit("duration muss eine ganze Zahl sein")
    if value < 0:
        helper.error_exit("duration muss >= 0 sein")
    return value


def parse_volume(raw: str) -> str:
    value = raw.strip().lower()
    if value not in ("low", "medium", "high"):
        helper.error_exit("volume muss low, medium oder high sein")
    return value


def set_alarm(
    tapo,
    enabled,
    sound_enabled=True,
    light_enabled=True,
    alarm_volume=None,
    alarm_duration=None,
):
    method = getattr(tapo, "setAlarm", None)
    if method is None:
        helper.error_exit("Methode setAlarm nicht vorhanden")

    try:
        method(
            enabled,
            soundEnabled=sound_enabled,
            lightEnabled=light_enabled,
            alarmVolume=alarm_volume,
            alarmDuration=alarm_duration,
        )
    except Exception as exc:
        helper.error_exit(f"Fehler bei setAlarm: {exc}")


def usage() -> None:
    prog = Path(sys.argv[0]).name
    print(
        f"Aufruf:\n"
        f"  {prog} status\n"
        f"  {prog} on\n"
        f"  {prog} off\n"
        f"  {prog} light on|off\n"
        f"  {prog} sound on|off\n"
        f"  {prog} volume low|medium|high\n"
        f"  {prog} duration <zahl>\n"
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
        helper.send_result(__file__, get_alarm_status(tapo))
        return

    current = get_alarm_status(tapo)

    status_enabled = current["status"] == "on"
    sound_enabled = current["sound"] == "on"
    light_enabled = current["light"] == "on"
    alarm_volume = current["volume"]
    alarm_duration = current["duration"]

    if command in ("on", "off"):
        if len(sys.argv) != 2:
            usage()
            sys.exit(1)

        set_alarm(
            tapo,
            command == "on",
            sound_enabled=sound_enabled,
            light_enabled=light_enabled,
            alarm_volume=alarm_volume,
            alarm_duration=alarm_duration,
        )
        helper.send_result(__file__, get_alarm_status(tapo))
        return

    if not status_enabled:
        helper.error_exit("Alarm ist ausgeschaltet; Parameteränderung nur bei eingeschaltetem Alarm möglich")

    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    if command == "light":
        new_light = parse_on_off(sys.argv[2])
        if not new_light and not sound_enabled:
            helper.error_exit("Mindestens sound oder light muss aktiv bleiben")
        light_enabled = new_light

    elif command == "sound":
        new_sound = parse_on_off(sys.argv[2])
        if not new_sound and not light_enabled:
            helper.error_exit("Mindestens sound oder light muss aktiv bleiben")
        sound_enabled = new_sound

    elif command == "volume":
        alarm_volume = parse_volume(sys.argv[2])

    elif command == "duration":
        alarm_duration = parse_duration(sys.argv[2])

    else:
        usage()
        sys.exit(1)

    set_alarm(
        tapo,
        True,
        sound_enabled=sound_enabled,
        light_enabled=light_enabled,
        alarm_volume=alarm_volume,
        alarm_duration=alarm_duration,
    )

    helper.send_result(__file__, get_alarm_status(tapo))


if __name__ == "__main__":
    main()

