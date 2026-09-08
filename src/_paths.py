"""Repo-root-anchored paths, so every module works from any working directory."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]      # repo root
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"
CLEAN_DIR = DATA / "clean"
OUT_DIR = DATA / "output"


def crypto_dir(ccy: str, kind: str) -> pathlib.Path:
    """kind in {'raw', 'clean', 'output'}"""
    return DATA / "crypto" / ccy.upper() / kind
