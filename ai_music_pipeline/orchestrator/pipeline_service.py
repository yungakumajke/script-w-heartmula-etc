from flask import Flask, request, jsonify
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import logging
import sys

from ensure_heartmula import ensure_heartmula
from heartmula_runner import run_heartmula
from uvr_runner import run_uvr
from reaper_mixer import create_reaper_project_from_stems

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("pipeline")

app = Flask(__name__)

BASE_DIR = Path(os.getenv("BASE_DIR", str(Path.home() / "ai_music_pipeline"))).expanduser().resolve()
JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

HEARTLIB_DIR = Path(os.environ["HEARTLIB_DIR"]).expanduser().resolve()
HEARTLIB_PYTHON = os.environ["HEARTLIB_PYTHON"]
HEARTLIB_CKPT = Path(os.environ["HEARTLIB_CKPT"]).expanduser().resolve()

def safe_name(s: str) -> str:
    s = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in s.strip())
    return s[:120] or "untitled"

def save_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def rename_stems(stems_dir: Path):
    mapping = {
        "vocals": ["vocals", "vocal"],
        "drums": ["drums", "drum"],
        "bass": ["bass"],
        "other": ["other", "instrumental", "music"],
    }
    found = {}
    for p in stems_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".wav":
            low = p.stem.lower()
            for target, keys in mapping.items():
                if any(k in low for k in keys):
                    found[target] = p
    return found

@app.post("/generate")
def generate():
    body = request.get_json(force=True)
    prompt = (body.get("prompt") or "").strip()
    tags = (body.get("tags") or "cinematic,modern,epic").strip()
    name = safe_name(body.get("name") or datetime.now().strftime("%Y%m%d_%H%M%S"))

    if not prompt:
        return jsonify({"status": "error", "error": "prompt is empty"}), 400

    job_dir = JOBS_DIR / name
    source_dir = job_dir / "source"
    stems_dir = job_dir / "stems"
    mixed_dir = job_dir / "mixed"
    source_dir.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)
    mixed_dir.mkdir(parents=True, exist_ok=True)

    log.info("New job: %s", name)
    log.info("Prompt: %s", prompt)
    log.info("Tags: %s", tags)
    log.info("Job dir: %s", job_dir)

    save_text(job_dir / "prompts.txt", f"tags: {tags}\nprompt: {prompt}\n")
    save_json(job_dir / "meta.json", {
        "name": name,
        "prompt": prompt,
        "tags": tags,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    })

    try:
        repo_root = ensure_heartmula(HEARTLIB_DIR, HEARTLIB_PYTHON, HEARTLIB_CKPT)

        log.info("Running HeartMuLa from repo root: %s", repo_root)
        source_audio = run_heartmula(repo_root, job_dir, prompt, tags)

        log.info("Running UVR stem separation")
        run_uvr(source_audio, stems_dir)

        found = rename_stems(stems_dir)

        log.info("Found stems: %s", list(found.keys()))

        output_mix_path = mixed_dir / "mix.wav"
        try:
            create_reaper_project_from_stems(stems_dir, output_mix_path)
        except Exception as e:
            log.warning("REAPER integration failed: %s", e)
            log.warning("Continuing without REAPER mix")
            output_mix_path = None

        meta = {
            "name": name,
            "prompt": prompt,
            "tags": tags,
            "created_at": datetime.now().isoformat(),
            "status": "ok",
            "source_audio": str(source_audio),
            "stems_dir": str(stems_dir),
            "found_stems": {k: str(v) for k, v in found.items()},
            "mix_path": str(output_mix_path) if output_mix_path else None,
        }
        save_json(job_dir / "meta.json", meta)

        return jsonify({
            "status": "ok",
            "job": name,
            "dir": str(job_dir),
            "found_stems": meta["found_stems"],
            "mix_path": meta["mix_path"],
        })

    except Exception as e:
        log.exception("Job failed: %s", name)
        save_json(job_dir / "meta.json", {
            "name": name,
            "prompt": prompt,
            "tags": tags,
            "created_at": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        })
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    log.info("Starting pipeline service on 127.0.0.1:5055")
    log.info("BASE_DIR = %s", BASE_DIR)
    log.info("HEARTLIB_DIR = %s", HEARTLIB_DIR)
    log.info("HEARTLIB_CKPT = %s", HEARTLIB_CKPT)
    app.run(host="127.0.0.1", port=5055, debug=False)