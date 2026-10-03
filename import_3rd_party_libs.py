#!/usr/bin/env python3
"""
import_3rd_party_libs.py

Unpacks componentsearchengine / SamacSys ECAD zip archives into project-local
KiCad libraries, using a SELF-CONTAINED, ONE-FOLDER-PER-PART layout, and
registers each part in the project's library tables.

Run it from anywhere - paths are resolved relative to this file:

    python 3rd-parties-libraries/import_3rd_party_libs.py

Re-run any time you drop new .zip archives into the archive folder.

Resulting layout (one folder per part, nickname = part name):

    3rd-parties-libraries/
    |- import_3rd_party_libs.py                 (this script)
    |- 00_componentsearchengine_ZIP_archives/   (your zips - untouched)
    |- <PART>/
    |     <PART>.kicad_sym       (just this one symbol)
    |     <FOOTPRINT>.kicad_mod  (3D path rewritten to this folder)
    |     <PART>.stp             (the 3D model)

Each part is registered under its own nickname (the part name) in both
sym-lib-table and fp-lib-table, so a schematic symbol and its footprint share
one nickname, e.g. lib_id "INA226AIDGSR:INA226AIDGSR" and footprint
"INA226AIDGSR:SOP50P490X110-10N". A folder copies between projects verbatim.

The footprint library is registered as a plain folder (KiCad type), not a
".pretty" - KiCad reads .kicad_mod files from any folder given as the URI.

3D model paths are rewritten to ${KIPRJMOD}/... so the project stays portable.

PRESERVES YOUR EDITS: a part whose <PART>/ folder already exists is left
untouched - only new parts get imported. To force a re-import, delete the
part's folder and re-run.

Standard library only - runs on any Python 3 (including the one bundled with
KiCad).
"""

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
BS = chr(92)  # backslash
LIB_ROOT = Path(__file__).resolve().parent          # 3rd-parties-libraries/
PROJECT_ROOT = LIB_ROOT.parent                       # KiCad project directory
ARCHIVE_DIR = LIB_ROOT / "00_componentsearchengine_ZIP_archives"
REL = "3rd-parties-libraries"                        # ${KIPRJMOD}-relative root

SYM_TABLE = PROJECT_ROOT / "sym-lib-table"
FP_TABLE = PROJECT_ROOT / "fp-lib-table"

SYM_HEADER = ("(kicad_symbol_lib (version 20211014) "
              "(generator SamacSys_ECAD_Model)\n")
MODEL_EXTS = (".stp", ".step", ".wrl")
MODEL_RE = re.compile(r'(\(model\s+)"?[^"\s)]+"?', re.IGNORECASE)


# --------------------------------------------------------------------------- #
# S-expression helpers
# --------------------------------------------------------------------------- #
def balanced(text, start):
    """Return (block, end_index) for the balanced-paren block starting at
    `start` (a '('). Quoted strings are respected so nested parens inside
    strings don't confuse the depth count."""
    depth = 0
    in_str = False
    j = start
    n = len(text)
    while j < n:
        c = text[j]
        p = text[j - 1] if j else ''
        if c == '"' and p != BS:
            in_str = not in_str
        elif not in_str:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return text[start:j + 1], j + 1
        j += 1
    return text[start:], n


_SYM_HDR = re.compile(r"\(\s*symbol\b")
_SYM_NAME = re.compile(r'\(\s*symbol\s+"([^"]+)"')


def top_level_symbols(text):
    """{name: block} for each top-level (symbol "name" ...) in a lib file."""
    out = {}
    i, n = 0, len(text)
    while i < n:
        if text[i] == "(" and _SYM_HDR.match(text, i):
            block, end = balanced(text, i)
            m = _SYM_NAME.match(block)
            if m:
                out[m.group(1)] = block
                i = end
                continue
        i += 1
    return out


def footprint_name(block):
    """Bare footprint name from a symbol's Footprint property ('' if none)."""
    m = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', block)
    if not m:
        return ""
    val = m.group(1)
    return val.split(":", 1)[1] if ":" in val else val


def model_base(mod_text):
    m = re.search(r'\(model\s+"?([^"\s)]+)"?', mod_text)
    return m.group(1).replace(BS, "/").split("/")[-1] if m else None


# --------------------------------------------------------------------------- #
# Import one part into its own folder
# --------------------------------------------------------------------------- #
def write_symbol_lib(folder, part, block, fp):
    """Write <part>/<part>.kicad_sym containing just this symbol, with its
    Footprint property repointed to '<part>:<fp>'."""
    if fp:
        block = re.sub(r'(\(property\s+"Footprint"\s+)"[^"]*"',
                       r'\1"' + f"{part}:{fp}" + '"', block, count=1)
    body = "  " + block.replace("\n", "\n  ")
    (folder / f"{part}.kicad_sym").write_text(
        SYM_HEADER + body + "\n)\n", encoding="utf-8")


def copy_footprint(folder, part, mod_path, models):
    """Copy a .kicad_mod into the part folder, copying its referenced 3D model
    alongside and rewriting the (model ..) path to point inside the folder."""
    text = mod_path.read_text(encoding="utf-8")
    base = model_base(text)
    chosen = None
    # prefer a model named after the part, else the one the footprint names,
    # else the single model shipped in the zip
    prefer = f"{part}.stp"
    if prefer in models:
        chosen = prefer
    elif base and base in models:
        chosen = base
    elif len(models) == 1:
        chosen = next(iter(models))
    if chosen:
        shutil.copy2(models[chosen], folder / chosen)
        new_path = f'"${{KIPRJMOD}}/{REL}/{part}/{chosen}"'
        text = MODEL_RE.sub(lambda m: m.group(1) + new_path, text, count=1)
    (folder / mod_path.name).write_text(text, encoding="utf-8")
    return chosen


def import_zip(zpath, workdir):
    """Extract one archive and import each part it contains. Returns a list of
    (part, status) where status is 'imported' or 'exists'."""
    dest = workdir / zpath.stem
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(dest)

    sym_files = list(dest.rglob("KiCad/*.kicad_sym"))
    fp_files = {p.stem: p for p in dest.rglob("KiCad/*.kicad_mod")}
    models = {}
    for ext in MODEL_EXTS:
        for m in dest.rglob(f"3D/*{ext}"):
            models[m.name] = m

    results = []
    imported_parts, imported_fp_libs = [], []

    # collect every symbol across the zip's .kicad_sym file(s)
    symbols = {}
    for sf in sym_files:
        symbols.update(top_level_symbols(sf.read_text(encoding="utf-8")))

    used_fp_stems = set()
    for part, block in symbols.items():
        fp = footprint_name(block)
        # this part's footprint (match by the Footprint prop's name; if the zip
        # ships exactly one footprint, use it). Mark it used either way so the
        # footprint-only pass below never makes a stray folder for it.
        mod = fp_files.get(fp) or (next(iter(fp_files.values()))
                                   if len(fp_files) == 1 else None)
        if mod:
            used_fp_stems.add(mod.stem)
        folder = LIB_ROOT / part
        if folder.exists():
            results.append((part, "exists"))
            continue
        folder.mkdir(parents=True, exist_ok=True)
        write_symbol_lib(folder, part, block, fp)
        imported_parts.append(part)
        if mod:
            copy_footprint(folder, part, mod, models)
            imported_fp_libs.append(part)
        results.append((part, "imported"))

    # any footprint in the zip not tied to a symbol (e.g. a connector whose
    # symbol is a KiCad built-in) becomes a footprint-only library
    for stem, mod in fp_files.items():
        if stem in used_fp_stems:
            continue
        folder = LIB_ROOT / stem
        if folder.exists():
            results.append((stem, "exists"))
            continue
        folder.mkdir(parents=True, exist_ok=True)
        copy_footprint(folder, stem, mod, models)
        imported_fp_libs.append(stem)
        results.append((stem + " (footprint-only)", "imported"))

    return results, imported_parts, imported_fp_libs


# --------------------------------------------------------------------------- #
# Library-table registration (idempotent, per-part)
# --------------------------------------------------------------------------- #
def register(table_path, root_token, nick, uri, descr):
    """Add or refresh a single (lib ..) entry, leaving other entries intact."""
    entry = (f'  (lib (name "{nick}")(type "KiCad")(uri "{uri}")'
             f'(options "")(descr "{descr}"))')
    if not table_path.exists():
        table_path.write_text(f"({root_token}\n  (version 7)\n{entry}\n)\n",
                              encoding="utf-8")
        return
    text = table_path.read_text(encoding="utf-8")
    # drop any existing entry with this nickname so the uri/descr refresh
    text = re.sub(r'\n\s*\(lib \(name "' + re.escape(nick) + r'"\).*?\)\)',
                  "", text, flags=re.DOTALL)
    idx = text.rstrip().rfind(")")
    table_path.write_text(text[:idx] + entry + "\n" + text[idx:],
                          encoding="utf-8")


def register_part(nick, *, symbol, footprint):
    if symbol:
        register(SYM_TABLE, "sym_lib_table", nick,
                 f"${{KIPRJMOD}}/{REL}/{nick}/{nick}.kicad_sym",
                 f"3rd-party part {nick}")
    if footprint:
        register(FP_TABLE, "fp_lib_table", nick,
                 f"${{KIPRJMOD}}/{REL}/{nick}",
                 f"3rd-party footprints for {nick}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    print(f"Project root : {PROJECT_ROOT}")
    zips = sorted(ARCHIVE_DIR.glob("*.zip"))
    if not zips:
        sys.exit(f"No .zip archives found in {ARCHIVE_DIR}")
    print(f"Archives     : {len(zips)} found\n")

    total_new = total_exist = 0
    with tempfile.TemporaryDirectory() as tmp:
        for z in zips:
            results, sym_parts, fp_parts = import_zip(z, Path(tmp))
            for nick in sym_parts:
                register_part(nick, symbol=True, footprint=(nick in fp_parts))
            for nick in fp_parts:
                if nick not in sym_parts:            # footprint-only lib
                    register_part(nick, symbol=False, footprint=True)
            for part, status in results:
                mark = "+" if status == "imported" else "="
                print(f"  {mark} {part}  ({status})")
                total_new += status == "imported"
                total_exist += status == "exists"

    print(f"\nDone. {total_new} new part(s) imported, "
          f"{total_exist} already present (left untouched).")
    print("Reopen the project in KiCad (or rescan libraries) to see new parts.")


if __name__ == "__main__":
    main()
