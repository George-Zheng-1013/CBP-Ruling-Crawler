"""Seed sample data into the CBP crawler SQLite DB, but only if it is empty.

This protects any real crawled data: if `rulings` already has rows, we skip.
Run automatically by start.bat before launching the backend.

Paths are resolved relative to this script (project root = cbp-ruling-explorer/),
so no hard-coded Chinese path literals are needed.
"""
import sqlite3
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
DB_PATH = ROOT.parent / "cbp-crawler" / "data" / "db" / "cbp_rulings.db"
SEED_PATH = ROOT / "docs" / "seed_sample.sql"


def main():
    if not SEED_PATH.exists():
        print(f"[seed] ERROR: seed file not found: {SEED_PATH}")
        sys.exit(1)

    # Make sure the DB directory exists (e.g. fresh checkout).
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Count existing rows; tolerate a missing DB file or missing table.
    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            n = conn.execute("SELECT COUNT(*) FROM rulings").fetchone()[0]
        except sqlite3.OperationalError:
            n = 0
        finally:
            conn.close()
    except Exception as e:
        print(f"[seed] ERROR reading DB ({e}); skipping seed.")
        sys.exit(0)

    if n > 0:
        print(f"[seed] rulings already has {n} row(s); skipping to protect your data.")
        return

    print(f"[seed] rulings is empty -> injecting sample data into {DB_PATH}")
    sql = SEED_PATH.read_text(encoding="utf-8")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(sql)
        conn.commit()
        inserted = conn.execute("SELECT COUNT(*) FROM rulings").fetchone()[0]
        conn.close()
        print(f"[seed] done. {inserted} sample ruling(s) inserted.")
    except Exception as e:
        print(f"[seed] ERROR during seeding: {e}")
        print("[seed] Hint: ensure the crawler DB schema exists (run the crawler once, or check storage.py).")
        sys.exit(0)


if __name__ == "__main__":
    main()
