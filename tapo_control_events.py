#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_events.py

import json
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import tapo_helper as helper

DEFAULT_WINDOW_SECONDS = 600
CACHE_FILE = "/tmp/tapo_control_events_cache.json"
CLIP_DIR = Path("/tmp/tapo_recordings/clips")

EVENT_TYPE_MAP = {
    2: "motion",
    4: "person",
    5: "area_intrusion",
    6: "person",
    8: "vehicle",
    9: "pet",
}

def cleanup_clips(debug: bool = False) -> None:
    if not CLIP_DIR.exists():
        return

    try:
        for p in CLIP_DIR.iterdir():
            if p.is_file():
                try:
                    p.unlink()
                    if debug:
                        helper.error_exit(f"Deleted clip: {p}")
                except Exception as exc:
                    if debug:
                        helper.error_exit(f"Could not delete {p}: {exc}")
    except Exception as exc:
        if debug:
            helper.error_exit(f"Error while cleaning clip directory: {exc}")


def map_event_type(alarm_type) -> str:
    try:
        num = int(alarm_type)
    except Exception:
        return f"unknown_{alarm_type}"
    return EVENT_TYPE_MAP.get(num, f"unknown_{num}")


def ts_to_display(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).astimezone().strftime("%H:%M:%S %Y-%m-%d")
    except Exception:
        return "invalid_timestamp"


def ts_to_daystring(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).astimezone().strftime("%Y%m%d")
    except Exception:
        return ""


def parse_window(raw: str) -> int:
    try:
        val = int(raw.strip())
    except Exception:
        helper.error_exit("Zeitfenster muss eine ganze Zahl in Sekunden sein")

    if val <= 0:
        helper.error_exit("Zeitfenster muss > 0 sein")

    return val


def parse_number(raw: str) -> int:
    try:
        val = int(raw.strip())
    except Exception:
        helper.error_exit("Nummer muss eine ganze Zahl sein")

    if val <= 0:
        helper.error_exit("Nummer muss > 0 sein")

    return val


def save_cache(cache_data: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        helper.error_exit(f"Cache konnte nicht geschrieben werden: {exc}")


def load_cache() -> dict:
    if not CACHE_FILE.exists():
        helper.error_exit("Kein Event-Cache vorhanden. Bitte zuerst 'events' aufrufen.")

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        helper.error_exit(f"Cache konnte nicht gelesen werden: {exc}")


def flatten_recording_item(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None

    for _, value in item.items():
        if isinstance(value, dict):
            return value

    return None


def get_events(tapo, window_seconds: int) -> dict:
    cleanup_clips()
    method = getattr(tapo, "getEvents", None)
    if method is None:
        helper.error_exit("Methode getEvents nicht vorhanden")

    now_ts = int(time.time())
    start_ts = now_ts - window_seconds

    try:
        data = method(start_ts, now_ts)
    except TypeError:
        try:
            data = method()
        except Exception as exc:
            helper.error_exit(f"Fehler bei getEvents: {exc}")
    except Exception as exc:
        helper.error_exit(f"Fehler bei getEvents: {exc}")

    if not isinstance(data, list):
        helper.error_exit(f"Unerwartete Rückgabe von getEvents: {data!r}")

    events = []
    seen = set()

    for event in data:
        if not isinstance(event, dict):
            continue

        start_time = event.get("start_time")
        alarm_type = event.get("alarm_type")

        try:
            start_ts_event = int(start_time)
        except Exception:
            continue

        if start_ts_event < start_ts or start_ts_event > now_ts:
            continue

        eventtype = map_event_type(alarm_type)
        dedup_key = (eventtype, start_ts_event)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        events.append({
            "timestamp": start_ts_event,
            "event_type": eventtype,
            "display_time": ts_to_display(start_ts_event),
            "day": ts_to_daystring(start_ts_event),
        })

    # neueste zuerst
    events.sort(key=lambda x: x["timestamp"], reverse=True)

    lines = []
    cached_events = []

    for idx, event in enumerate(events, start=1):
        event["number"] = idx
        lines.append(f"{idx} {event['display_time']} {event['event_type']}")
        cached_events.append(event)

    cache_data = {
        "generated_at": ts_to_display(now_ts),
        "events_window": window_seconds,
        "events_start": ts_to_display(start_ts),
        "events": cached_events,
    }
    save_cache(cache_data)

    return {
        "events_window": window_seconds,
        "events_start": ts_to_display(start_ts),
        "events_count": len(cached_events),
        "events_list": "\n".join(lines),
    }

def usage() -> None:
    print(f"Usage: {Path(sys.argv[0]).name} events [window_seconds]")


def main() -> None:
    tapo = helper.create_tapo()

    if len(sys.argv) == 2 and sys.argv[1] == "events":
        helper.send_result(__file__, get_events(tapo, DEFAULT_WINDOW_SECONDS))
        return

    if len(sys.argv) == 3 and sys.argv[1] == "events":
        window_seconds = parse_window(sys.argv[2])
        helper.send_result(__file__, get_events(tapo, window_seconds))
        return

    usage()
    sys.exit(1)


if __name__ == "__main__":
    main()
