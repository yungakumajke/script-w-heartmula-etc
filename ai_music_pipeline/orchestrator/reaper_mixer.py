from pathlib import Path
import logging
import reapy

log = logging.getLogger("reaper_mixer")

def ensure_reaper_connection():
    if not reapy.is_inside_reaper():
        try:
            reapy.connect()
            log.info("Connected to REAPER via reapy")
        except Exception as e:
            log.warning("Could not connect to REAPER: %s", e)
            log.warning("Make sure REAPER is running and reapy server is enabled")
            raise

def create_reaper_project_from_stems(stems_dir: Path, output_mix_path: Path):
    ensure_reaper_connection()

    stem_mapping = {
        "vocals": ["vocals", "vocal"],
        "drums": ["drums", "drum"],
        "bass": ["bass"],
        "other": ["other", "instrumental", "music"],
    }

    found = {}
    for p in stems_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".wav":
            low = p.stem.lower()
            for target, keys in stem_mapping.items():
                if any(k in low for k in keys):
                    if target not in found:
                        found[target] = p

    if not found:
        raise RuntimeError("No stems found to import into REAPER")

    project = reapy.Project()
    project.name = f"Mix_{stems_dir.parent.name}"

    track_order = ["vocals", "drums", "bass", "other"]
    tracks = {}

    for stem_type in track_order:
        if stem_type not in found:
            continue
        track = project.add_track(name=stem_type.capitalize())
        tracks[stem_type] = track

        audio_path = found[stem_type]
        log.info("Adding %s stem: %s", stem_type, audio_path)
        item = track.add_media_item(str(audio_path))
        item.start = 0.0

    project.cursor_position = 0.0
    project.length = max(
        item.end for track in tracks.values() for item in track.items
    )

    output_mix_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Rendering mix to %s", output_mix_path)

    project.render(
        str(output_mix_path),
        render_stems=False,
        render_fx=True,
        render_master=True,
    )

    log.info("Mix rendered successfully")
    return output_mix_path