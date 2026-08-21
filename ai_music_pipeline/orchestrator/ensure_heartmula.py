from pathlib import Path
import subprocess
import shutil
import logging
import sys

HEARTLIB_REPO = "https://github.com/HeartMuLa/heartlib.git"
HF_DOWNLOADS = [
    ("HeartMuLa/HeartMuLaGen", Path(".")),
    ("HeartMuLa/HeartMuLa-oss-3B-happy-new-year", Path("HeartMuLa-oss-3B")),
    ("HeartMuLa/HeartCodec-oss-20260123", Path("HeartCodec-oss")),
]

log = logging.getLogger("heartmula_bootstrap")

def setup_logging():
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

def run(cmd, cwd=None):
    log.info("RUN: %s", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def command_exists(name: str) -> bool:
    return shutil.which(name) is not None

def is_repo_root(p: Path) -> bool:
    return (p / "pyproject.toml").exists() or (p / "setup.py").exists() or (p / ".git").exists()

def find_repo_root(start: Path) -> Path:
    start = start.resolve()
    if is_repo_root(start):
        return start
    for parent in [start] + list(start.parents):
        if is_repo_root(parent):
            return parent
    return start

def ensure_repo_cloned(heartlib_dir: Path) -> Path:
    heartlib_dir = Path(heartlib_dir).resolve()
    if heartlib_dir.exists():
        log.info("HeartMuLa path already exists: %s", heartlib_dir)
        return find_repo_root(heartlib_dir)

    heartlib_dir.parent.mkdir(parents=True, exist_ok=True)
    if not command_exists("git"):
        raise RuntimeError("git is not installed")

    log.info("Cloning HeartMuLa repo into %s", heartlib_dir)
    run(["git", "clone", HEARTLIB_REPO, str(heartlib_dir)])
    return find_repo_root(heartlib_dir)

def install_heartlib(repo_root: Path, python_exe: str):
    repo_root = Path(repo_root).resolve()
    if not is_repo_root(repo_root):
        raise RuntimeError(f"{repo_root} does not look like heartlib repository root")

    log.info("Installing heartlib editable package from %s", repo_root)
    run([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    run([python_exe, "-m", "pip", "install", "-e", str(repo_root)])

def ckpt_complete(ckpt_dir: Path) -> bool:
    needed = [
        ckpt_dir / "HeartCodec-oss",
        ckpt_dir / "HeartMuLa-oss-3B",
        ckpt_dir / "gen_config.json",
        ckpt_dir / "tokenizer.json",
    ]
    ok = all(p.exists() for p in needed)
    log.info("Checkpoint check: %s", "OK" if ok else "missing files")
    if not ok:
        for p in needed:
            log.info("  %s: %s", p, "OK" if p.exists() else "MISSING")
    return ok

def _download_with_hf_cli(repo_id: str, target: Path):
    target.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s -> %s", repo_id, target)
    proc = subprocess.Popen(
        ["hf", "download", "--local-dir", str(target), repo_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"hf download failed for {repo_id} with code {rc}")

def download_ckpts_with_hf_cli(ckpt_dir: Path):
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    for repo_id, rel_dir in HF_DOWNLOADS:
        target = ckpt_dir if rel_dir == Path(".") else ckpt_dir / rel_dir
        _download_with_hf_cli(repo_id, target)

def download_ckpts_with_huggingface_hub(ckpt_dir: Path):
    log.info("Using huggingface_hub snapshot_download fallback")
    from huggingface_hub import snapshot_download, logging as hf_logging
    hf_logging.set_verbosity_info()

    ckpt_dir.mkdir(parents=True, exist_ok=True)
    for repo_id, rel_dir in HF_DOWNLOADS:
        target = ckpt_dir if rel_dir == Path(".") else ckpt_dir / rel_dir
        target.mkdir(parents=True, exist_ok=True)
        log.info("Downloading %s -> %s", repo_id, target)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target),
            local_dir_use_symlinks=False,
        )

def ensure_ckpts(ckpt_dir: Path):
    if ckpt_complete(ckpt_dir):
        log.info("HeartMuLa checkpoints already present in %s", ckpt_dir)
        return

    log.info("HeartMuLa checkpoints missing, starting download")
    if command_exists("hf"):
        log.info("Found hf CLI")
        download_ckpts_with_hf_cli(ckpt_dir)
    else:
        log.info("hf CLI not found, trying huggingface_hub")
        download_ckpts_with_huggingface_hub(ckpt_dir)

def ensure_heartmula(heartlib_dir: Path, python_exe: str, ckpt_dir: Path):
    setup_logging()
    log.info("Bootstrapping HeartMuLa")

    repo_root = ensure_repo_cloned(heartlib_dir)
    install_heartlib(repo_root, python_exe)
    ensure_ckpts(ckpt_dir)

    log.info("HeartMuLa bootstrap completed")
    return repo_root