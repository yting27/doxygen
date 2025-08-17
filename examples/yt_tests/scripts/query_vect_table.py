from sentence_transformers import SentenceTransformer
import sqlite_vec
import sqlite3
import sys

from common_utils import *


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        # Load sqlite-vec SQL functions into a SQLite connection.
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        query = "Show vintage port details. For example, nickname and year."
        print(f"Query: {query}")

        # Encode query string
        embed_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
        query_embed = embed_model.encode(query)

        # Find similar rows in the TEXT_EMBED_TABLE
        rows = conn.execute(
            f"""
            SELECT
                rowid,
                distance
            FROM {TEXT_EMBED_TABLE}
            WHERE {ident(TEXT_EMBED_COL)} MATCH ?
            ORDER BY distance
            LIMIT 3
            """,
            [serialize_f32(query_embed)],
        ).fetchall()
        for rowid, distance in rows:
            table_index, table_rowid = decode_rowid(rowid)
            print(f"Row ID: {rowid}, Table Index: {table_index}, Table Row ID: {table_rowid}, Distance: {distance}")


if __name__ == "__main__":
    main()
