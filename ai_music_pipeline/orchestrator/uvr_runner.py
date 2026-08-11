from pathlib import Path
import subprocess
import os
import logging

log = logging.getLogger("uvr_runner")

def run_uvr(input_audio: Path, stems_dir: Path) -> Path:
    uvr_dir = Path(os.environ["UVR_CLI_DIR"])
    stems_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        os.environ["PYTHON_EXE"],
        str(uvr_dir / "separate.py"),
    ]
    env = os.environ.copy()
    env["UVR_INPUT_AUDIO"] = str(input_audio)
    env["UVR_OUTPUT_DIR"] = str(stems_dir)

    log.info("Running UVR command: %s", " ".join(cmd))
    log.info("UVR input: %s", input_audio)
    log.info("UVR output: %s", stems_dir)
    subprocess.run(cmd, cwd=str(uvr_dir), env=env, check=True)
    return stems_dir