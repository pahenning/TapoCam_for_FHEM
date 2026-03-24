#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_light.py

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import tapo_helper as helper


def normalize_light_status(value) -> str:
    if value in (1, "1", True, "on"):
        return "on"
    return "off"


def map_night_mode_from_camera(value: str) -> str:
    mapping = {
        "inf_night_vision": "ir",
        "wtl_night_vision": "white",
        "md_night_vision": "auto",
    }
    return mapping.get(str(value), str(value))


def map_night_mode_to_camera(value: str) -> str:
    value = value.strip().lower()
    mapping = {
        "ir": "inf_night_vision",
        "white": "wtl_night_vision",
        "auto": "md_night_vision",
    }
    if value not in mapping:
        helper.error_exit("night muss ir, white oder auto sein")
    return mapping[value]

# Beispiel-Rückgabe von tapo.getWhitelampConfig()
# (aktuell genutzt:)
#   wtl_intensity_level  -> intensity
#   wtl_force_time       -> time
#
# (weitere verfügbare Felder – derzeit keine set-Methoden in pytapo:)
# {
#   "schedule_end_time": "64800",
#   "schedule_start_time": "21600",
#   "clear_licence_plate_mode": "off",
#   "switch_mode": "common",
#   "rotate_type": "off",
#   "flip_type": "off",
#   "ldc": "off",
#   "night_vision_mode": "inf_night_vision",
#   "full_color_people_enhance": "off",
#   "full_color_min_keep_time": "5",
#   "wtl_intensity_level": "47",
#   "wtl_force_time": "300",
#   "overexposure_people_suppression": "off",
#   "best_view_distance": "0",
#   "image_scene_mode": "normal",
#   "image_scene_mode_common": "normal",
#   "image_scene_mode_shedday": "normal",
#   "image_scene_mode_shednight": "normal",
#   "image_scene_mode_autoday": "normal",
#   "image_scene_mode_autonight": "normal"
# }

def get_whitelamp_config_status(tapo) -> dict:
    method = getattr(tapo, "getWhitelampConfig", None)
    if method is None:
        helper.error_exit("Methode getWhitelampConfig nicht vorhanden")

    try:
        data = method()
    except Exception as exc:
        helper.error_exit(f"Fehler bei getWhitelampConfig: {exc}")

    if not isinstance(data, dict):
        helper.error_exit(f"Unerwartete Rückgabe von getWhitelampConfig: {data!r}")

    return {
        "intensity": str(data.get("wtl_intensity_level")) if data.get("wtl_intensity_level") is not None else None,
        "time": str(data.get("wtl_force_time")) if data.get("wtl_force_time") is not None else None,
        "night": map_night_mode_from_camera(data.get("night_vision_mode")),
    }


def get_light_status(tapo) -> dict:
    method = getattr(tapo, "getWhitelampStatus", None)
    if method is None:
        helper.error_exit("Methode getWhitelampStatus nicht vorhanden")

    try:
        data = method()
    except Exception as exc:
        helper.error_exit(f"Fehler bei getWhitelampStatus: {exc}")

    if not isinstance(data, dict):
        helper.error_exit(f"Unerwartete Rückgabe von getWhitelampStatus: {data!r}")

    return {
        "status": normalize_light_status(data.get("status")),
        "time_remain": int(data.get("rest_time", 0)),
    }


def get_led_status(tapo) -> dict:
    method = getattr(tapo, "getLED", None)
    if method is None:
        helper.error_exit("Methode getLED nicht vorhanden")

    try:
        data = method()
    except Exception as exc:
        helper.error_exit(f"Fehler bei getLED: {exc}")

    if not isinstance(data, dict):
        helper.error_exit(f"Unerwartete Rückgabe von getLED: {data!r}")

    return {
        "led": helper.normalize_on_off(data.get("enabled")),
    }


def get_full_status(tapo) -> dict:
    result = {}
    result.update(get_whitelamp_config_status(tapo))
    result.update(get_light_status(tapo))
    result.update(get_led_status(tapo))
    return result


def parse_on_off(raw: str) -> bool:
    value = raw.strip().lower()
    if value == "on":
        return True
    if value == "off":
        return False
    helper.error_exit("Wert muss on oder off sein")


def parse_intensity(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        helper.error_exit("Intensity muss eine ganze Zahl zwischen 0 und 100 sein")

    if value < 0 or value > 100:
        helper.error_exit("Intensity muss zwischen 0 und 100 liegen")

    return value


def parse_time(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        helper.error_exit("Time muss eine ganze Zahl zwischen 0 und 3600 sein")

    if value < 0 or value > 3600:
        helper.error_exit("Time muss zwischen 0 und 3600 liegen")

    return value


def set_led_status(tapo, enabled: bool) -> dict:
    method = getattr(tapo, "setLEDEnabled", None)
    if method is None:
        helper.error_exit("Methode setLEDEnabled nicht vorhanden")

    try:
        method(enabled)
    except Exception as exc:
        helper.error_exit(f"Fehler bei setLEDEnabled: {exc}")

    return get_led_status(tapo)


def set_light_status(tapo, enabled: bool) -> dict:
    current = get_light_status(tapo)
    current_enabled = current.get("status") == "on"

    if current_enabled != enabled:
        method = getattr(tapo, "reverseWhitelampStatus", None)
        if method is None:
            helper.error_exit("Methode reverseWhitelampStatus nicht vorhanden")

        try:
            method()
        except Exception as exc:
            helper.error_exit(f"Fehler bei reverseWhitelampStatus: {exc}")

    return get_light_status(tapo)


def set_intensity(tapo, value: int) -> dict:
    method = getattr(tapo, "setWhitelampConfig", None)
    if method is None:
        helper.error_exit("Methode setWhitelampConfig nicht vorhanden")

    try:
        method(False, value)
    except Exception as exc:
        helper.error_exit(f"Fehler bei setWhitelampConfig(False, {value}): {exc}")

    return get_whitelamp_config_status(tapo)


def set_time_value(tapo, value: int) -> dict:
    method = getattr(tapo, "setWhitelampConfig", None)
    if method is None:
        helper.error_exit("Methode setWhitelampConfig nicht vorhanden")

    try:
        method(value, False)
    except Exception as exc:
        helper.error_exit(f"Fehler bei setWhitelampConfig({value}, False): {exc}")

    return get_whitelamp_config_status(tapo)


def set_night_mode(tapo, value: str) -> dict:
    method = getattr(tapo, "setNightVisionModeConfig", None)
    if method is None:
        helper.error_exit("Methode setNightVisionModeConfig nicht vorhanden")

    mode = map_night_mode_to_camera(value)

    try:
        method(mode)
    except Exception as exc:
        helper.error_exit(f"Fehler bei setNightVisionModeConfig: {exc}")

    return get_whitelamp_config_status(tapo)


def usage() -> None:
    prog = Path(sys.argv[0]).name
    print(
        f"Aufruf:\n"
        f"  {prog} status\n"
        f"  {prog} light\n"
        f"  {prog} light on|off\n"
        f"  {prog} led\n"
        f"  {prog} led on|off\n"
        f"  {prog} intensity <0-100>\n"
        f"  {prog} time <0-3600>\n"
        f"  {prog} night ir|white|auto\n"
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
        helper.send_result(__file__, get_full_status(tapo))
        return

    if command == "light":
        if len(sys.argv) == 2:
            helper.send_result(__file__, get_light_status(tapo))
            return
        if len(sys.argv) == 3:
            enabled = parse_on_off(sys.argv[2])
            helper.send_result(__file__, set_light_status(tapo, enabled))
            return
        usage()
        sys.exit(1)

    if command == "led":
        if len(sys.argv) == 2:
            helper.send_result(__file__, get_led_status(tapo))
            return
        if len(sys.argv) == 3:
            enabled = parse_on_off(sys.argv[2])
            helper.send_result(__file__, set_led_status(tapo, enabled))
            return
        usage()
        sys.exit(1)

    if command == "intensity":
        if len(sys.argv) != 3:
            usage()
            sys.exit(1)
        value = parse_intensity(sys.argv[2])
        helper.send_result(__file__, set_intensity(tapo, value))
        return

    if command == "time":
        if len(sys.argv) != 3:
            usage()
            sys.exit(1)
        value = parse_time(sys.argv[2])
        helper.send_result(__file__, set_time_value(tapo, value))
        return

    if command == "night":
        if len(sys.argv) != 3:
            usage()
            sys.exit(1)
        helper.send_result(__file__, set_night_mode(tapo, sys.argv[2]))
        return

    usage()
    sys.exit(1)


if __name__ == "__main__":
    main()
