#!/usr/bin/env python3
import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def backup(source: Path, target: Path):
    target.mkdir(parents=True, exist_ok=True)
    integrity = sqlite3.connect(source).execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok": raise RuntimeError(f"Falha de integridade: {integrity}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = target / f"filial-bsb-{stamp}.sqlite3"
    src = sqlite3.connect(source); dst = sqlite3.connect(destination); src.backup(dst); dst.close(); src.close()
    copies = sorted(target.glob("filial-bsb-*.sqlite3"), reverse=True)
    for old in copies[35:]: old.unlink()
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup consistente do SQLite")
    parser.add_argument("database", type=Path); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); print(backup(args.database, args.directory))
