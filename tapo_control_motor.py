#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_motor.py

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import tapo_helper as helper

STEP = 10
VALID_DIRECTIONS = {"left", "right", "up", "down"}


def parse_value(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        helper.error_exit("Wert muss eine ganze Zahl zwischen 0 und 359 sein")

    if value < 0 or value >= 360:
        helper.error_exit("Wert muss zwischen 0 und 359 liegen")

    return value


def parse_preset(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        helper.error_exit("Preset muss eine ganze Zahl sein")

    if value < 1:
        helper.error_exit("Preset muss >= 1 sein")

    return value


def normalize_preset_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        helper.error_exit("Preset-Name darf nicht leer sein")
    return name


def move_motor(tapo, direction: str, value: int):
    method = getattr(tapo, "moveMotor", None)
    if method is None:
        helper.error_exit("Methode moveMotor nicht vorhanden")

    if direction == "left":
        dx, dy = -value, 0
    elif direction == "right":
        dx, dy = value, 0
    elif direction == "up":
        dx, dy = 0, value
    elif direction == "down":
        dx, dy = 0, -value
    else:
        helper.error_exit("Ungültige Richtung")

    try:
        method(dx, dy)
        return {"result": "ok"}
    except Exception as exc:
        msg = str(exc)
        if "MOTOR_LOCKED_ROTOR" in msg or "-64304" in msg:
            return {"result": "error max range"}
        return {"result": f"error {msg}"}


def calibrate_motor(tapo):
    method = getattr(tapo, "calibrateMotor", None)
    if method is None:
        helper.error_exit("Methode calibrateMotor nicht vorhanden")

    try:
        method()
        return {"result": "ok"}
    except Exception as exc:
        return {"result": f"error {exc}"}


def get_presets(tapo):
    method = getattr(tapo, "getPresets", None)
    if method is None:
        helper.error_exit("Methode getPresets nicht vorhanden")

    try:
        presets = method()
    except Exception as exc:
        return {"result": f"error {exc}", "presets": {}}

    if not isinstance(presets, dict):
        return {"result": "error invalid presets response", "presets": {}}

    normalized = {str(k): str(v) for k, v in presets.items()}
    return {"result": "ok", "presets": normalized}


def goto_preset(tapo, preset: int):
    method = getattr(tapo, "setPreset", None)
    if method is None:
        helper.error_exit("Methode setPreset nicht vorhanden")

    try:
        method(str(preset))
        return {"result": "ok"}
    except Exception as exc:
        return {"result": f"error {exc}"}


def save_preset(tapo, preset: int, name: str):
    method = getattr(tapo, "savePreset", None)
    if method is None:
        helper.error_exit("Methode savePreset nicht vorhanden")

    try:
        method(str(preset), name)
        return {"result": "ok"}
    except Exception as exc:
        return {"result": f"error {exc}"}


def delete_preset(tapo, preset: int):
    method = getattr(tapo, "deletePreset", None)
    if method is None:
        helper.error_exit("Methode deletePreset nicht vorhanden")

    try:
        method(str(preset))
        return {"result": "ok"}
    except Exception as exc:
        return {"result": f"error {exc}"}


def usage() -> None:
    prog = Path(sys.argv[0]).name
    print(
        f"Aufruf:\n"
        f"  {prog} left\n"
        f"  {prog} right\n"
        f"  {prog} up\n"
        f"  {prog} down\n"
        f"  {prog} left <0-359>\n"
        f"  {prog} right <0-359>\n"
        f"  {prog} up <0-359>\n"
        f"  {prog} down <0-359>\n"
        f"  {prog} calibrate\n"
        f"  {prog} presets\n"
        f"  {prog} goto <preset>\n"
        f"  {prog} save <preset> <name>\n"
        f"  {prog} delete <preset>\n"
    )


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1].strip().lower()
    tapo = helper.create_tapo()

    if command == "calibrate":
        if len(sys.argv) != 2:
            usage()
            sys.exit(1)

        result = calibrate_motor(tapo)
        helper.send_result(__file__, {
            "action": "calibrate",
            "result": result["result"]
        })
        return

    if command == "presets":
        if len(sys.argv) != 2:
            usage()
            sys.exit(1)

        result = get_presets(tapo)
        helper.send_result(__file__, {
            "action": "presets",
            "result": result["result"],
            "presets": result["presets"]
        })
        return

    if command == "goto":
        if len(sys.argv) != 3:
            usage()
            sys.exit(1)

        preset = parse_preset(sys.argv[2])
        result = goto_preset(tapo, preset)
        helper.send_result(__file__, {
            "action": "goto",
            "preset": str(preset),
            "result": result["result"]
        })
        return

    if command == "save":
        if len(sys.argv) < 4:
            usage()
            sys.exit(1)

        preset = parse_preset(sys.argv[2])
        name = normalize_preset_name(" ".join(sys.argv[3:]))

        result = save_preset(tapo, preset, name)
        helper.send_result(__file__, {
            "action": "save",
            "preset": str(preset),
            "name": name,
            "result": result["result"]
        })
        return

    if command == "delete":
        if len(sys.argv) != 3:
            usage()
            sys.exit(1)

        preset = parse_preset(sys.argv[2])
        result = delete_preset(tapo, preset)
        helper.send_result(__file__, {
            "action": "delete",
            "preset": str(preset),
            "result": result["result"]
        })
        return

    if command not in VALID_DIRECTIONS:
        usage()
        sys.exit(1)

    if len(sys.argv) == 3:
        value = parse_value(sys.argv[2])
    elif len(sys.argv) == 2:
        value = STEP
    else:
        usage()
        sys.exit(1)

    result = move_motor(tapo, command, value)
    helper.send_result(__file__, {
        "action": command,
        "value": value,
        "result": result["result"]
    })


if __name__ == "__main__":
    main()
