#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description="Valida se um backup pode ser restaurado")
parser.add_argument("backup", type=Path); args = parser.parse_args()
connection = sqlite3.connect(f"file:{args.backup}?mode=ro", uri=True)
result = connection.execute("PRAGMA integrity_check").fetchone()[0]
tables = connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
connection.close()
if result != "ok" or tables == 0: raise SystemExit(f"Backup inválido: integridade={result}, tabelas={tables}")
print(f"Restauração validada: integridade={result}, tabelas={tables}")
