#!/usr/bin/env python3
"""
Clean up Doxygen-like XML fragments in two SQLite TEXT columns.

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

- Makes a safety backup unless --no-backup.
- Has a --dry-run preview.
"""

import argparse
import html
import os
import pathlib
import re
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET

SAFE_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
TAG_RE = re.compile(r'<[^>]+>')

def ident(name: str) -> str:
    """Quote and validate an identifier (table/column)."""
    if not SAFE_IDENT.match(name):
        raise ValueError(f'Invalid identifier: {name!r}')
    return f'"{name}"'

def normalize_ws(s: str) -> str:
    """Collapse internal whitespace to single spaces and trim."""
    return re.sub(r'\s+', ' ', s or '').strip()

def simple_strip_tags(text: str) -> str:
    """Fallback for malformed XML: drop tags, decode entities, normalize spaces."""
    return normalize_ws(html.unescape(TAG_RE.sub('', text or '')))

def render_with_kind(elem: ET.Element) -> str:
    """
    Recursively render an Element:
      - Interleave .text, children, and child .tail in document order.
      - If the current element has a 'kind' attribute and non-empty text result,
        prefix "(kind) " before the rendered content of this element.
    """
    parts = []
    if elem.text and normalize_ws(elem.text):
        parts.append(normalize_ws(elem.text))

    for child in elem:
        child_txt = render_with_kind(child)
        if child_txt:
            parts.append(child_txt)
        if child.tail and normalize_ws(child.tail):
            parts.append(normalize_ws(child.tail))

    content = " ".join(parts).strip()
    kind = elem.attrib.get('kind')
    if kind and content:
        content = f"({kind}) {content}"
    return content

def extract_text(elem: ET.Element) -> str:
    """Flatten all text under element with whitespace normalization."""
    return normalize_ws("".join(elem.itertext()))

def format_paramlist_element(plist: ET.Element) -> str:
    """
    Turn a <parameterlist kind="...">...</parameterlist> into:

    (kind)
    name: description
    ...
    """
    kind = plist.attrib.get("kind", "param")
    lines = [f"({kind})"]
    for pitem in plist.findall("parameteritem"):
        # names (often single)
        names = [extract_text(nn) for nn in pitem.findall("parameternamelist/parametername")]
        name = ", ".join(n for n in names if n)

        # description
        desc_elems = pitem.findall("parameterdescription")
        desc = " ".join(extract_text(d) for d in desc_elems if extract_text(d))

        # Only add meaningful lines
        if name or desc:
            if name and desc:
                lines.append(f"{name}: {desc}")
            elif name:
                lines.append(f"{name}:")
            else:
                lines.append(desc)
    # Only return a section if it has more than the header
    return "\n".join(lines) if len(lines) > 1 else ""

def format_fragment(text: str) -> str:
    """
    Full formatter for a fragment:
      - If it contains any <parameterlist>, render those sections pretty,
        and render other siblings with the general rules. Join chunks with blank lines.
      - Otherwise, render the whole thing with general rules.
      - On parse error, fall back to a simple tag strip.
    """
    if not text:
        return ""
    wrapped = f"<root>{text}</root>"
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        return simple_strip_tags(text)

    has_pl = any(root.iter("parameterlist"))
    if not has_pl:
        # No parameter lists: render the whole thing normally.
        # Include root.text and children in document order.
        return render_with_kind(root)

    # Mixed content with parameter lists: build chunks, preserving their formatting.
    chunks = []
    if root.text and normalize_ws(root.text):
        chunks.append(normalize_ws(root.text))

    for child in root:
        if child.tag == "parameterlist":
            block = format_paramlist_element(child)
            if block:
                chunks.append(block)
        else:
            rendered = render_with_kind(child)
            if rendered:
                chunks.append(rendered)
        if child.tail and normalize_ws(child.tail):
            chunks.append(normalize_ws(child.tail))

    # Join chunks with a blank line to keep param blocks readable.
    out = "\n\n".join(c for c in chunks if c)
    # Light cleanup: collapse >2 consecutive blank lines to just one.
    out = re.sub(r'\n{3,}', '\n\n', out).strip()
    return out

def get_table_columns(conn, table):
    cursor = conn.execute(f"PRAGMA table_info({ident(table)})")
    return {row[1].lower() for row in cursor.fetchall()}

def backup_db(src_path: pathlib.Path, dst_path: pathlib.Path):
    with sqlite3.connect(src_path) as src, sqlite3.connect(dst_path) as dst:
        src.backup(dst)

def preview_changes(conn, table, col_names, limit=5):
    cols = ", ".join(ident(c) for c in col_names)
    q = (
        f"SELECT rowid, {cols} FROM {ident(table)} "
        f"WHERE ({ident(col_names[0])} LIKE '%<%' OR {ident(col_names[1])} LIKE '%<%') "
        f"LIMIT ?"
    )
    print(f"\nPreviewing up to {limit} rows with XML-like content…\n")
    for row in conn.execute(q, (limit,)):
        rowid = row[0]
        vals = row[1:]
        print(f"rowid={rowid}")
        for cname, val in zip(col_names, vals):
            before = val or ""
            after = format_fragment(before)
            if before != after:
                print(f"  [{cname}] BEFORE:\n{before}\n  [{cname}] AFTER:\n{after}\n")
            else:
                print(f"  [{cname}] (no change)\n")

def run_update(conn, table, col_names, new_col, batch_size=1000):
    """
    Stream through rows that look like they contain tags and update in batches.
    Returns number of rows changed.
    """
    select_q = (
        f"SELECT rowid, {ident(col_names[0])}, {ident(col_names[1])} "
        f"FROM {ident(table)} "
        f"WHERE {ident(col_names[0])} LIKE '%<%' OR {ident(col_names[1])} LIKE '%<%';"
    )

    # Make sure the new column exists
    exist_cols = get_table_columns(conn, table)
    if new_col.lower() not in exist_cols:
        ddl = f"ALTER TABLE {ident(table)} ADD COLUMN {ident(new_col)} TEXT DEFAULT ''"
        conn.execute(ddl)

    changed = 0
    batch_params = []
    upd_q = (
        f"UPDATE {ident(table)} SET {new_col}=? "
        f"WHERE rowid=?"
    )

    conn.execute("BEGIN")
    try:
        for rowid, col1, col2 in conn.execute(select_q):
            new1 = format_fragment(col1 or "")
            new2 = format_fragment(col2 or "")
            if new1 != (col1 or "") or new2 != (col2 or ""):
                concat_new = f"{new1}\n{new2}".strip()
                batch_params.append((concat_new, rowid))
                changed += 1

            if len(batch_params) >= batch_size:
                conn.executemany(upd_q, batch_params)
                batch_params.clear()

        if batch_params:
            conn.executemany(upd_q, batch_params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return changed

def main():
    ap = argparse.ArgumentParser(
        description="Normalize Doxygen-like XML in two SQLite TEXT columns. "
                    "Formats <parameterlist> blocks and prefixes (kind) for elements with kind='...'."
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    ap.add_argument("--no-backup", action="store_true", help="Skip automatic backup")
    args = ap.parse_args()

    # Get current file directory
    current_dir = os.path.abspath(os.path.dirname(__file__))

    db_path = pathlib.Path(current_dir, "..", "sqlite3", "doxygen_sqlite3_test.db")
    compounddef_table = "compounddef"
    detdesc_col = "detaileddescription"
    briefdesc_col = "briefdescription"
    combineddesc_col = "combineddescription"
    preview_limit = 5
    batch_size_per_update = 1000

    if not db_path.exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if not args.no_backup:
        # Perform a backup before making changes
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_suffix(db_path.suffix + f".pre-clean-{ts}.sqlite")
        print(f"Creating backup: {backup_path}")
        backup_db(db_path, backup_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        tbl_cols = [detdesc_col, briefdesc_col]

        if args.dry_run:
            preview_changes(conn, args.table, tbl_cols, limit=preview_limit)
            print("Dry run only; no changes written.")
            return

        changed = run_update(conn, compounddef_table, tbl_cols, combineddesc_col, batch_size=batch_size_per_update)
        print(f"Rows updated: {changed}")


if __name__ == "__main__":
    main()
