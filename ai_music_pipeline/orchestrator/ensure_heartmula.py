from pathlib import Path
import subprocess
import os
import logging

log = logging.getLogger("heartmula_runner")

def validate_ckpt_dir(ckpt_dir: Path):
    required = [
        ckpt_dir / "HeartCodec-oss",
        ckpt_dir / "HeartMuLa-oss-3B",
        ckpt_dir / "gen_config.json",
        ckpt_dir / "tokenizer.json",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        raise RuntimeError(
            "HeartMuLa checkpoint structure is incomplete:\n" +
            "\n".join(f"- missing: {p}" for p in missing)
        )

def run_heartmula(repo_root: Path, job_dir: Path, prompt: str, tags: str) -> Path:
    heartlib_python = os.environ["HEARTLIB_PYTHON"]
    ckpt_dir = Path(os.environ["HEARTLIB_CKPT"]).expanduser().resolve()

    if not ckpt_dir.exists():
        raise RuntimeError(f"Checkpoint directory not found: {ckpt_dir}")

    validate_ckpt_dir(ckpt_dir)

    assets_dir = Path(repo_root) / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    lyrics_path = assets_dir / "lyrics.txt"
    tags_path = assets_dir / "tags.txt"
    output_path = job_dir / "source" / "output.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lyrics_path.write_text(prompt, encoding="utf-8")
    tags_path.write_text(tags, encoding="utf-8")

    script_path = Path(repo_root) / "examples" / "run_music_generation.py"
    if not script_path.exists():
        raise RuntimeError(f"run_music_generation.py not found: {script_path}")

    cmd = [
        heartlib_python,
        str(script_path),
        "--model_path", str(ckpt_dir),
        "--version", "3B",
        "--lyrics", str(lyrics_path),
        "--tags", str(tags_path),
        "--save_path", str(output_path),
        "--lazy_load", "true",
    ]

    log.info("Running HeartMuLa command: %s", " ".join(cmd))
    log.info("cwd = %s", repo_root)
    log.info("model_path = %s", ckpt_dir)

    subprocess.run(cmd, cwd=str(repo_root), check=True)
    return output_path