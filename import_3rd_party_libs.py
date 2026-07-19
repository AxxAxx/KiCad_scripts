#!/usr/bin/env python3
"""
import_3rd_party_libs.py

Unpacks componentsearchengine / SamacSys ECAD zip archives and consolidates the
KiCad assets (schematic symbols, footprints, 3D models) into a single set of
project-local libraries, then registers them in the project's library tables.

This script lives in (and operates on) the 3rd-parties-libraries folder. Run it
from anywhere - paths are resolved relative to this file:

    python 3rd-parties-libraries/import_3rd_party_libs.py

Re-run any time you drop new .zip archives into the archive folder.

PRESERVES YOUR EDITS: if a symbol / footprint / 3D model is already present in
the generated libraries, it is left untouched. Only parts that are not yet
loaded get imported. So if you tweak a symbol or footprint in KiCad, a re-run
will not clobber your changes. To force a part to be re-imported from its zip,
delete it from the generated library first (or delete the symbol block from
cse.kicad_sym) and re-run.

Resulting layout:

    3rd-parties-libraries/
    |- import_3rd_party_libs.py                 (this script)
    |- 00_componentsearchengine_ZIP_archives/   (your zips - untouched)
    |- symbols/     cse.kicad_sym               (all symbols, merged)
    |- footprints/  cse.pretty/*.kicad_mod      (all footprints, 3D paths fixed)
    |- 3dmodels/    *.stp/.step/.wrl            (all 3D models)

Library nickname registered in sym-lib-table / fp-lib-table: "00_CSE"
(the leading "00_" sorts it to the top of KiCad's library lists).

3D model paths are rewritten to ${KIPRJMOD}/... so the project stays portable.

Standard library only - runs on any Python 3 (including the one bundled with
KiCad).
"""

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LIB_ROOT = Path(__file__).resolve().parent          # 3rd-parties-libraries/
PROJECT_ROOT = LIB_ROOT.parent                        # KiCad project directory
ARCHIVE_DIR = LIB_ROOT / "00_componentsearchengine_ZIP_archives"

SYMBOLS_DIR = LIB_ROOT / "symbols"
FOOTPRINTS_DIR = LIB_ROOT / "footprints" / "cse.pretty"
MODELS_DIR = LIB_ROOT / "3dmodels"

MERGED_SYM = SYMBOLS_DIR / "cse.kicad_sym"

# Library nickname shown in KiCad. The leading "00_" sorts it to the top of
# the (alphabetically sorted) library lists.
LIB_NICKNAME = "00_CSE"

# Paths (relative to the project dir) that footprints and lib tables point at,
# via the ${KIPRJMOD} KiCad environment variable (= the project directory).
REL_MODELS = "3rd-parties-libraries/3dmodels"
REL_SYMBOLS = "3rd-parties-libraries/symbols/cse.kicad_sym"
REL_FOOTPRINTS = "3rd-parties-libraries/footprints/cse.pretty"

MODEL_EXTS = (".stp", ".step", ".wrl")

# ---------------------------------------------------------------------------
# S-expression helpers
# ---------------------------------------------------------------------------


def extract_top_level_blocks(text, token):
    """Return the list of balanced-paren '(token ...)' blocks that sit at the
    top level *inside* the root s-expression of `text`."""
    blocks = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "(":
            m = re.match(r"\(\s*([A-Za-z0-9_]+)", text[i:])
            if m and m.group(1) == token:
                depth = 0
                start = i
                in_str = False
                while i < n:
                    c = text[i]
                    if c == '"' and text[i - 1] != "\\":
                        in_str = not in_str
                    elif not in_str:
                        if c == "(":
                            depth += 1
                        elif c == ")":
                            depth -= 1
                            if depth == 0:
                                blocks.append(text[start : i + 1])
                                i += 1
                                break
                    i += 1
                continue
        i += 1
    return blocks


def symbol_name(block):
    m = re.match(r'\(\s*symbol\s+"([^"]+)"', block)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def find_archives():
    zips = sorted(ARCHIVE_DIR.glob("*.zip"))
    if not zips:
        sys.exit(f"No .zip archives found in {ARCHIVE_DIR}")
    return zips


def ensure_dirs():
    for d in (SYMBOLS_DIR, FOOTPRINTS_DIR, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def collect_from_archives(zips, workdir):
    """Extract each zip and return (symbol_files, footprint_files, model_files)."""
    sym_files, fp_files, model_files = [], [], []
    for z in zips:
        dest = workdir / z.stem
        with zipfile.ZipFile(z) as zf:
            zf.extractall(dest)
        sym_files += list(dest.rglob("KiCad/*.kicad_sym"))
        fp_files += list(dest.rglob("KiCad/*.kicad_mod"))
        for ext in MODEL_EXTS:
            model_files += list(dest.rglob(f"3D/*{ext}"))
    return sym_files, fp_files, model_files


def prefix_footprint_property(block):
    """Rewrite the symbol's Footprint field to '<nickname>:<name>' so KiCad
    auto-associates the footprint. Leaves already-qualified ('lib:fp') values
    alone."""

    def repl(m):
        value = m.group(2)
        if not value or ":" in value:
            return m.group(0)
        return f'{m.group(1)}"{LIB_NICKNAME}:{value}"'

    return re.sub(
        r'(\(property\s+"Footprint"\s+)"([^"]*)"', repl, block, count=1
    )


def load_existing_symbols():
    """Ordered {name: block} of symbols already in the merged library."""
    existing = {}
    if MERGED_SYM.exists():
        text = MERGED_SYM.read_text(encoding="utf-8")
        for block in extract_top_level_blocks(text, "symbol"):
            name = symbol_name(block)
            if name:
                existing[name] = block
    return existing


def merge_symbols(sym_files):
    """Add not-yet-loaded symbols to the merged library, preserving existing
    ones verbatim. Returns (added, preserved)."""
    result = load_existing_symbols()      # preserve existing edits
    preserved = len(result)
    added = 0
    for f in sym_files:
        text = f.read_text(encoding="utf-8")
        for block in extract_top_level_blocks(text, "symbol"):
            name = symbol_name(block)
            if name is None or name in result:
                continue
            result[name] = prefix_footprint_property(block)
            added += 1

    header = "(kicad_symbol_lib (version 20211014) (generator SamacSys_ECAD_Model)\n"
    body = "\n".join("  " + b.replace("\n", "\n  ") for b in result.values())
    MERGED_SYM.write_text(header + body + "\n)\n", encoding="utf-8")
    return added, preserved


MODEL_RE = re.compile(r'\(model\s+"?([^"\s)]+)"?', re.IGNORECASE)


def rewrite_model_path(match):
    base = Path(match.group(1).replace("\\", "/")).name
    return f'(model "${{KIPRJMOD}}/{REL_MODELS}/{base}"'


def copy_footprints(fp_files):
    """Copy not-yet-loaded footprints (3D path rewritten). Returns (added, kept)."""
    added = kept = 0
    for f in fp_files:
        dest = FOOTPRINTS_DIR / f.name
        if dest.exists():
            kept += 1
            continue
        text = MODEL_RE.sub(rewrite_model_path, f.read_text(encoding="utf-8"))
        dest.write_text(text, encoding="utf-8")
        added += 1
    return added, kept


def copy_models(model_files):
    """Copy not-yet-loaded 3D models. Returns (added, kept)."""
    added = kept = 0
    for f in model_files:
        dest = MODELS_DIR / f.name
        if dest.exists():
            kept += 1
            continue
        shutil.copy2(f, dest)
        added += 1
    return added, kept


# ---------------------------------------------------------------------------
# Library-table registration (idempotent)
# ---------------------------------------------------------------------------


def register_lib(table_path, root_token, uri):
    entry = (
        f'  (lib (name "{LIB_NICKNAME}")(type "KiCad")'
        f'(uri "{uri}")(options "")(descr "componentsearchengine 3rd-party parts"))'
    )

    if not table_path.exists():
        table_path.write_text(
            f"({root_token}\n  (version 7)\n{entry}\n)\n", encoding="utf-8"
        )
        return "created"

    text = table_path.read_text(encoding="utf-8")

    # Drop any existing entry with our nickname so we can rewrite it cleanly.
    text = re.sub(
        r'\n\s*\(lib \(name "' + re.escape(LIB_NICKNAME) + r'"\).*?\)\)',
        "",
        text,
        flags=re.DOTALL,
    )

    idx = text.rstrip().rfind(")")
    text = text[:idx] + entry + "\n" + text[idx:]
    table_path.write_text(text, encoding="utf-8")
    return "updated"


def register_tables():
    s = register_lib(
        PROJECT_ROOT / "sym-lib-table",
        "sym_lib_table",
        "${KIPRJMOD}/" + REL_SYMBOLS,
    )
    f = register_lib(
        PROJECT_ROOT / "fp-lib-table",
        "fp_lib_table",
        "${KIPRJMOD}/" + REL_FOOTPRINTS,
    )
    return s, f


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print(f"Project root : {PROJECT_ROOT}")
    zips = find_archives()
    print(f"Archives     : {len(zips)} found")

    ensure_dirs()

    with tempfile.TemporaryDirectory() as tmp:
        sym_files, fp_files, model_files = collect_from_archives(zips, Path(tmp))
        sym_added, sym_kept = merge_symbols(sym_files)
        fp_added, fp_kept = copy_footprints(fp_files)
        mod_added, mod_kept = copy_models(model_files)

    sym_state, fp_state = register_tables()

    print("\nDone. (existing parts preserved, not overwritten)")
    print(f"  Symbols    : +{sym_added} new, {sym_kept} preserved  -> {MERGED_SYM}")
    print(f"  Footprints : +{fp_added} new, {fp_kept} preserved  -> {FOOTPRINTS_DIR}")
    print(f"  3D models  : +{mod_added} new, {mod_kept} preserved  -> {MODELS_DIR}")
    print(f"  sym-lib-table : {sym_state} (nickname '{LIB_NICKNAME}')")
    print(f"  fp-lib-table  : {fp_state} (nickname '{LIB_NICKNAME}')")
    print(f"\nOpen (or reopen) the project in KiCad - the '{LIB_NICKNAME}' libraries are ready.")


if __name__ == "__main__":
    main()
