from sentence_transformers import SentenceTransformer
from typing import List
import html
import os
import pathlib
import re
import struct
import sqlite3
import xml.etree.ElementTree as ET


# Constants
DB_PATH = pathlib.Path(os.path.dirname(__file__)) / ".." / "sqlite3" / "doxygen_sqlite3_test.db"
DEFINITION_TABLES = ["compounddef", "memberdef"]
TABLE_INDEX_BITS = 3
TABLE_INDEX_MASK = (1 << TABLE_INDEX_BITS) - 1  # 0b111
DETDESC_COL = "detaileddescription"
BRIEFDESC_COL = "briefdescription"
COMBINEDDESC_COL = "combineddescription"
PREVIEW_LIMIT = 5
BATCH_SIZE_PER_UPDATE = 1000
TEXT_EMBED_TABLE = "desc_vect_embed"
TEXT_EMBED_COL = "description_embed"
TEXT_EMBED_SIZE = 1024
SAFE_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
TAG_RE = re.compile(r'<[^>]+>')


## ----- START OF Utility functions ----- ##
def ident(name: str) -> str:
    """Quote and validate an identifier (table/column)."""
    if not SAFE_IDENT.match(name):
        raise ValueError(f'Invalid identifier: {name!r}')
    return f'"{name}"'

def normalize_ws(s: str) -> str:
    """Collapse internal whitespace to single spaces and trim."""
    single_newline_str = re.sub(r'[\n\r]+', '\n', s or '')
    return re.sub(r' +', ' ', single_newline_str or '').strip()

def simple_strip_tags(text: str) -> str:
    """Fallback for malformed XML: drop tags, decode entities, normalize spaces."""
    return normalize_ws(html.unescape(TAG_RE.sub('', text or '')))

def render_with_kind(elem: ET.Element) -> str:
    """
    Recursively render an Element:
      - Interleave .text, children, and child .tail in document order. E.g., turn `<root>Start <a>link</a> mid <b>x</b>end</root>` into

        root.text = "Start "
        a.text = "link"
        a.tail = " mid "
        b.text = "x"
        b.tail = "end"
      - If the current element has a 'kind' attribute and non-empty text result,
        prefix "(kind) " before the rendered content of this element.
    """
    parts = []
    if elem.text and normalize_ws(elem.text):
        parts.append(normalize_ws(elem.text))

    for child in elem:
        if child.tag == "parameterlist":
            block = format_paramlist_element(child)
            if block:
                parts.append(f"\n{block}\n")
        else:
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
    Turn a `<parameterlist kind="...">...</parameterlist>` into:

    (kind)
    name: description
    ...
    """
    kind = plist.attrib.get("kind", "param")
    lines = [f"({kind})"]
    for pitem in plist.findall("parameteritem"):
        # param names (often single)
        names = [extract_text(nn) for nn in pitem.findall("parameternamelist/parametername")]
        name = ", ".join(n for n in names if n)

        # description
        desc_elems = pitem.findall("parameterdescription")
        desc = " ".join(extract_text(d) for d in desc_elems if extract_text(d))

        # Only add meaningful lines
        if name and desc:
            lines.append(f"{name}: {desc}")
        elif name:
            lines.append(f"{name}:")
        elif desc:
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

    return render_with_kind(root)

def get_table_columns(conn, table):
    cursor = conn.execute(f"PRAGMA table_info({ident(table)})")
    return {row[1].lower() for row in cursor.fetchall()}

def backup_db(src_path: pathlib.Path, dst_path: pathlib.Path):
    with sqlite3.connect(src_path) as src, sqlite3.connect(dst_path) as dst:
        src.backup(dst)

def preview_changes(conn, table: str, col_names: List[str], limit: int=5):
    desc_col_str = ", ".join(ident(c) for c in col_names)
    desc_col_like_str = " OR ".join([f"{ident(c)} LIKE '%<%'" for c in col_names])
    # Get `limit` rows from table
    query = (
        f"SELECT rowid, {desc_col_str} FROM {ident(table)} "
        f"WHERE ({desc_col_like_str}) "
        f"LIMIT ?"
    )
    print(f"\nPreviewing up to {limit} rows with XML-like content…\n")
    for row in conn.execute(query, (limit,)):
        rowid = row[0]
        desc_vals = row[1:]
        print(f"rowid={rowid}")

        full_raw_desc = ""
        full_clean_desc = ""
        for cname, desc in zip(col_names, desc_vals):
            before_desc = desc or ""
            full_raw_desc += before_desc + "\n"
            after_desc = format_fragment(before_desc)
            if after_desc:
                full_clean_desc += after_desc + "\n"

        print(f"  [{cname}] BEFORE:\n{full_raw_desc}\n  [{cname}] AFTER:\n{full_clean_desc}\n")

def run_update(conn, table: str, col_names: List[str], new_col: str, embed_model: SentenceTransformer, batch_size: int=1000):
    """
    Stream through rows that look like they contain tags and update in batches.
    Returns number of rows changed.
    """
    desc_col_str = ", ".join(ident(c) for c in col_names)
    desc_col_like_str = " OR ".join([f"{ident(c)} LIKE '%<%'" for c in col_names])
    select_q = (
        f"SELECT rowid, {desc_col_str} "
        f"FROM {ident(table)} "
        f"WHERE {desc_col_like_str};"
    )

    # Make sure the new column exists
    exist_cols = get_table_columns(conn, table)
    if new_col.lower() not in exist_cols:
        ddl = f"ALTER TABLE {ident(table)} ADD COLUMN {ident(new_col)} TEXT DEFAULT ''"
        conn.execute(ddl)

    # Create the vector embedding table if it does not exist
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {ident(TEXT_EMBED_TABLE)} USING vec0({ident(TEXT_EMBED_COL)} float[{TEXT_EMBED_SIZE}])")

    changed = 0
    batch_params = []
    upd_q = (
        f"UPDATE {ident(table)} SET {new_col}=? "
        f"WHERE rowid=?"
    )

    conn.execute("BEGIN")
    try:
        for row in conn.execute(select_q):
            rowid = row[0]
            desc_vals = row[1:]

            full_clean_desc = ""
            for cname, desc in zip(col_names, desc_vals):
                before_desc = desc or ""
                after_desc = format_fragment(before_desc)
                if after_desc:
                    full_clean_desc += after_desc + "\n"

            if full_clean_desc:
                batch_params.append((full_clean_desc, rowid))
                changed += 1

            if len(batch_params) >= batch_size:
                # Execute batch update
                conn.executemany(upd_q, batch_params)
                insert_text_embed_table(embed_model, conn, table, batch_params)
                batch_params.clear()

        if batch_params:
            conn.executemany(upd_q, batch_params)
            insert_text_embed_table(embed_model, conn, table, batch_params)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return changed

def insert_text_embed_table(embed_model: SentenceTransformer, conn: sqlite3.Connection, table: str, batch_params: List[tuple]):
    # Embed the descriptions into vector embeddings
    query_embeddings = embed_model.encode([param[0] for param in batch_params], prompt_name="query")
    for bparam, vect_emb in zip(batch_params, query_embeddings):
        table_idx = DEFINITION_TABLES.index(table)
        embed_idx = encode_rowid(table_idx, bparam[1])
        conn.execute(
            f"INSERT INTO {ident(TEXT_EMBED_TABLE)}(rowid, {ident(TEXT_EMBED_COL)}) VALUES (?, ?)",
            [embed_idx, serialize_f32(vect_emb)],
        )

def serialize_f32(vector: List[float]) -> bytes:
    """serializes a list of floats into a compact "raw bytes" format"""
    return struct.pack("%sf" % len(vector), *vector)

def encode_rowid(table_index: int, table_rowid: int) -> int:
    """
    Pack table_index (3 bits) and table_rowid into a single rowid.

    :param table_index: Table index (0-7).
    :param table_rowid: Row ID within the table.
    :return: Combined integer rowid.
    """
    if not (0 <= table_index <= TABLE_INDEX_MASK):
        raise ValueError(f"table_index must fit in {TABLE_INDEX_BITS} bits (0-{TABLE_INDEX_MASK})")

    return (table_rowid << TABLE_INDEX_BITS) | table_index

def decode_rowid(rowid: int) -> tuple[int, int]:
    """
    Unpack a rowid into table_index and table_rowid.

    :param rowid: The combined integer rowid.
    :return: (table_index, table_rowid)
    """
    table_index = rowid & TABLE_INDEX_MASK
    table_rowid = rowid >> TABLE_INDEX_BITS
    return table_index, table_rowid

## ------ END OF Utility functions ------ ##
