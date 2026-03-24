#!/opt/fhem/tapo/.venv/bin/python3
# /opt/fhem/tapo/tapo_control_download.py

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pytapo import Tapo
from pytapo.media_stream.downloader import Downloader

import tapo_helper as helper
import tapo_credentials as credentials


CACHE_FILE = Path("/tmp/tapo_control_events_cache.json")
DOWNLOAD_DIR = Path("/tmp/tapo_recordings/clips")
PUBLIC_LINK = Path("/opt/fhem/www/images/TapoClip.mp4")

DEFAULT_USERNAME = "admin"
DEFAULT_DEBUG = 0


def debug_print(enabled: bool, msg: str) -> None:
    if enabled:
        print(msg)


def ts_to_display(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).astimezone().strftime("%H:%M:%S %Y-%m-%d")
    except Exception:
        return "invalid_timestamp"


def parse_number(raw: str) -> int:
    try:
        val = int(raw.strip())
    except Exception:
        helper.error_exit("Nummer muss eine ganze Zahl sein")

    if val <= 0:
        helper.error_exit("Nummer muss > 0 sein")

    return val


def parse_debug(raw: str) -> int:
    raw = raw.strip()
    if raw not in ("0", "1"):
        helper.error_exit("DEBUG muss 0 oder 1 sein")
    return int(raw)


def ensure_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        helper.error_exit(f"Verzeichnis konnte nicht angelegt werden: {exc}")


def load_cache() -> dict:
    if not CACHE_FILE.exists():
        helper.error_exit("Kein Event-Cache vorhanden. Bitte zuerst tapo_control_events.py events aufrufen.")

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        helper.error_exit(f"Cache konnte nicht gelesen werden: {exc}")


def create_tapo_instance(child_id=None):
    host = str(getattr(credentials, "CAMERA_IP", "")).strip()
    password = str(getattr(credentials, "PASSWORD", ""))
    username = str(getattr(credentials, "USERNAME", DEFAULT_USERNAME)).strip() or DEFAULT_USERNAME

    if not host:
        helper.error_exit("CAMERA_IP fehlt in tapo_credentials.py")
    if not password:
        helper.error_exit("PASSWORD fehlt in tapo_credentials.py")

    try:
        if child_id:
            return Tapo(
                host,
                username,
                password,
                password,
                childID=child_id,
                printDebugInformation=False,
            )
        return Tapo(
            host,
            username,
            password,
            password,
            printDebugInformation=False,
        )
    except Exception as exc:
        helper.error_exit(f"Verbindung zur Kamera fehlgeschlagen: {exc}")


def flatten_recording_item(item: dict):
    if not isinstance(item, dict):
        return None, None

    for key, value in item.items():
        if isinstance(value, dict):
            return key, value

    return None, None


def update_public_symlink(target_file: Path, debug: bool = False) -> str:
    try:
        ensure_directory(PUBLIC_LINK.parent)

        if PUBLIC_LINK.is_symlink() or PUBLIC_LINK.exists():
            PUBLIC_LINK.unlink()

        PUBLIC_LINK.symlink_to(target_file)
        debug_print(debug, f"Symlink gesetzt: {PUBLIC_LINK} -> {target_file}")
        return str(PUBLIC_LINK)
    except Exception as exc:
        helper.error_exit(f"Symlink konnte nicht gesetzt werden: {exc}")


async def create_tapo_instance_async(child_id=None, debug: bool = False):
    debug_print(debug, f"Erzeuge Tapo-Instanz{' für Child ' + str(child_id) if child_id else ''}...")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, create_tapo_instance, child_id)


async def get_recordings_async(tapo, date: str, debug: bool = False):
    debug_print(debug, f"Hole Recordings für {date}...")
    loop = asyncio.get_running_loop()
    recordings = await loop.run_in_executor(None, tapo.getRecordings, date)
    debug_print(debug, f"Recordings geholt: {len(recordings) if isinstance(recordings, list) else 'ungültig'}")
    return recordings


async def get_time_correction_async(tapo, debug: bool = False):
    debug_print(debug, "Hole TimeCorrection...")
    loop = asyncio.get_running_loop()
    time_correction = await loop.run_in_executor(None, tapo.getTimeCorrection)
    debug_print(debug, f"TimeCorrection: {time_correction}")
    return time_correction


async def get_event_and_clip_from_cache(number: int, debug: bool = False) -> dict:
    cache = load_cache()
    events = cache.get("events")

    if not isinstance(events, list):
        helper.error_exit("Event-Cache ist ungültig")

    selected_event = None
    for event in events:
        if isinstance(event, dict) and int(event.get("number", 0)) == number:
            selected_event = event
            break

    if selected_event is None:
        helper.error_exit(f"Keine Event-Nummer {number} im Cache gefunden")

    event_ts = selected_event.get("timestamp")
    event_day = selected_event.get("day")
    event_type = selected_event.get("event_type")
    event_display = selected_event.get("display_time")

    if not isinstance(event_ts, int) or not event_day:
        helper.error_exit("Gewähltes Event im Cache ist unvollständig")

    debug_print(debug, f"Cache-Event gefunden: Nr. {number}")
    debug_print(debug, f"  Event-Typ: {event_type}")
    debug_print(debug, f"  Event-Zeit: {event_display}")
    debug_print(debug, f"  Event-Timestamp: {event_ts}")
    debug_print(debug, f"  Event-Tag: {event_day}")
    debug_print(debug, "Hole passende Recordings von der Kamera...")

    tapo = await create_tapo_instance_async(debug=debug)
    recordings = await get_recordings_async(tapo, event_day, debug)

    if not isinstance(recordings, list):
        helper.error_exit(f"Unerwartete Rückgabe von getRecordings: {recordings!r}")

    debug_print(debug, f"Anzahl Recordings für {event_day}: {len(recordings)}")

    matching_clip = None

    for item in recordings:
        rec_key, rec = flatten_recording_item(item)
        if not isinstance(rec, dict):
            continue

        try:
            start_ts = int(rec.get("startTime"))
            end_ts = int(rec.get("endTime"))
        except Exception:
            continue

        debug_print(
            debug,
            f"Prüfe Clip {rec_key}: {ts_to_display(start_ts)} - {ts_to_display(end_ts)}"
        )

        if start_ts <= event_ts <= end_ts:
            matching_clip = {
                "clip_key": rec_key,
                "clip_start_ts": start_ts,
                "clip_end_ts": end_ts,
                "clip_start": ts_to_display(start_ts),
                "clip_end": ts_to_display(end_ts),
                "clip_type": rec.get("vedio_type"),
                "clip_recording": rec,
                "clip_recording_raw": item,
            }
            break

    if matching_clip is None:
        helper.error_exit(
            f"Kein passender Clip für Event {number} ({event_display} {event_type}) gefunden"
        )

    debug_print(debug, "Passender Clip gefunden:")
    debug_print(debug, f"  Key: {matching_clip['clip_key']}")
    debug_print(debug, f"  Start: {matching_clip['clip_start']}")
    debug_print(debug, f"  Ende: {matching_clip['clip_end']}")
    debug_print(debug, f"  Typ: {matching_clip['clip_type']}")

    return {
        "event_number": number,
        "event_type": event_type,
        "event_time": event_display,
        "event_timestamp": event_ts,
        "event_day": event_day,
        **matching_clip,
    }


async def download_single_clip(
    tapo,
    output_dir: Path,
    start_time: int,
    end_time: int,
    file_name: str,
    debug: bool = False,
) -> str:
    debug_print(debug, "Starte Einzelclip-Download...")
    debug_print(debug, f"  Clip-Start: {ts_to_display(start_time)}")
    debug_print(debug, f"  Clip-Ende : {ts_to_display(end_time)}")
    debug_print(debug, f"  Datei     : {file_name}")

    ensure_directory(output_dir)
    target_file = output_dir / file_name

    if target_file.exists() and target_file.stat().st_size > 0:
        debug_print(debug, f"Datei bereits vorhanden, kein neuer Download: {target_file}")
        return str(target_file)

    time_correction = await get_time_correction_async(tapo, debug)

    date = datetime.fromtimestamp(start_time).astimezone().strftime("%Y%m%d")

    # wichtig: direkter getRecordings-Aufruf vor downloadFile()
    await get_recordings_async(tapo, date, debug)

    downloader = Downloader(
        tapo,
        start_time,
        end_time,
        time_correction,
        str(output_dir) + "/",
        0,
        None,
        None,
        file_name,
    )

    result = await downloader.downloadFile(None)

    if debug:
        print(f"downloadFile result: {result}")

    real_file = None
    if isinstance(result, dict):
        real_file = result.get("fileName")

    if not real_file:
        real_file = str(target_file)

    debug_print(debug, f"Einzelclip fertig: {real_file}")
    return real_file


async def download_clip_by_number(number: int, debug: bool = False):
    ensure_directory(DOWNLOAD_DIR)
    debug_print(debug, f"Zielverzeichnis: {DOWNLOAD_DIR}")

    clip_info = await get_event_and_clip_from_cache(number, debug)

    tapo = await create_tapo_instance_async(debug=debug)

    file_name = (
        f"event_{number:03d}_"
        f"{clip_info['clip_start_ts']}-{clip_info['clip_end_ts']}.mp4"
    )

    downloaded_file = await download_single_clip(
        tapo,
        DOWNLOAD_DIR,
        clip_info["clip_start_ts"],
        clip_info["clip_end_ts"],
        file_name,
        debug,
    )

    public_link = update_public_symlink(Path(downloaded_file), debug)

    return {
        "event_number": clip_info["event_number"],
        "event_type": clip_info["event_type"],
        "event_time": clip_info["event_time"],
        "event_timestamp": clip_info["event_timestamp"],
        "event_day": clip_info["event_day"],
        "clip_key": clip_info["clip_key"],
        "clip_start_ts": clip_info["clip_start_ts"],
        "clip_end_ts": clip_info["clip_end_ts"],
        "clip_start": clip_info["clip_start"],
        "clip_end": clip_info["clip_end"],
        "clip_type": clip_info["clip_type"],
        "clip_recording": clip_info["clip_recording"],
        "clip_recording_raw": clip_info["clip_recording_raw"],
        "download_dir": str(DOWNLOAD_DIR),
        "download_file": str(downloaded_file),
        "public_link": public_link,
    }


def usage() -> None:
    prog = Path(sys.argv[0]).name
    print(f"Usage: {prog} clip <number> [DEBUG]")
    print("DEBUG: 0 oder 1, default 0")


def main() -> None:
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        usage()
        sys.exit(1)

    if sys.argv[1] != "clip":
        usage()
        sys.exit(1)

    number = parse_number(sys.argv[2])
    debug = DEFAULT_DEBUG

    if len(sys.argv) == 4:
        debug = parse_debug(sys.argv[3])

    try:
        result = asyncio.run(download_clip_by_number(number, bool(debug)))
    except Exception as exc:
        helper.error_exit(f"Clip-Download fehlgeschlagen: {exc}")

    helper.send_result(__file__, result)


if __name__ == "__main__":
    main()
