#!/usr/bin/env python3
"""
Clean up Doxygen-like XML fragments in two SQLite TEXT columns, concat the cleaned text into a new column.

Rules:
- Pretty-print <parameterlist kind="..."> into:
  (param)
  s: Full name
  n: Employee ID
  ...
- For all other XML:
  * Strip all tags.
  * If an element has attribute kind="X", prefix with "(X) " before that element's rendered text.
    Example:
      <simplesect kind="note"><para>Requires initialization.</para></simplesect>
      -> (note) Requires initialization.
- If the column contains XML-like content, move the cleaned text to a new column. The new column is added if it does not exist.

Notes:
- Makes a safety backup unless --no-backup.
- Has a --dry-run preview.
"""

from sentence_transformers import SentenceTransformer
import argparse
import sqlite_vec
import sqlite3
import sys
import time

from common_utils import *


def main():
    ap = argparse.ArgumentParser(
        description="Normalize Doxygen-like XML in two SQLite TEXT columns. "
                    "Formats <parameterlist> blocks and prefixes (kind) for elements with kind='...'."
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    ap.add_argument("--no-backup", action="store_true", help="Skip automatic backup")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    if not args.no_backup:
        # Perform a backup before making changes
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_path = DB_PATH.with_suffix(DB_PATH.suffix + f".pre-clean-{ts}.sqlite")
        print(f"Creating backup: {backup_path}")
        backup_db(DB_PATH, backup_path)

    print(f"Connect to database: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        # Load sqlite-vec SQL functions into a SQLite connection.
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        tbl_cols = [BRIEFDESC_COL, DETDESC_COL]

        # Load the model
        embed_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
        # embed_model = SentenceTransformer(
        #     "Qwen/Qwen3-Embedding-4B",
        #     model_kwargs={"attn_implementation": "flash_attention_2", "device_map": "auto"},
        #     tokenizer_kwargs={"padding_side": "left"},
        # )

        for table in DEFINITION_TABLES:
            print(f"Processing table '{table}' with columns {tbl_cols}...")
            if args.dry_run:
                preview_changes(conn, table, tbl_cols, limit=PREVIEW_LIMIT)
                print("Dry run only; no changes written.")
                return

            changed = run_update(conn, table, tbl_cols, COMBINEDDESC_COL, embed_model, batch_size=BATCH_SIZE_PER_UPDATE)
            print(f"Rows updated for table '{table}': {changed}")


if __name__ == "__main__":
    main()
