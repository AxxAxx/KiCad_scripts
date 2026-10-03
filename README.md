# KiCad_scripts

A drop-in toolkit for standing up a new KiCad project and pulling in 3rd-party
parts from [componentsearchengine.com](https://componentsearchengine.com)
(SamacSys ECAD archives).

## Contents

| File | Purpose |
|------|---------|
| `kicad_create_filestructure.py` | Bootstraps a new project's folder tree and deploys the importer. Run once per project. |
| `import_3rd_party_libs.py` | Unpacks componentsearchengine zips into one self-contained library folder per part and registers each part in the project's library tables. Run whenever you add parts. |
| `README.md` | This file. |

## Quick start

1. **Drop this whole `KiCad_scripts` folder into your (empty) KiCad project
   directory** — next to your `*.kicad_pro` file.

2. **Create the folder structure.** From inside the folder:
   ```
   cd KiCad_scripts
   python kicad_create_filestructure.py
   ```
   This creates the standard project subfolders and deploys the importer to
   `3rd-parties-libraries/00_import_3rd_party_libs.py`.

3. **Add parts.** Download components from componentsearchengine in **KiCad**
   format and drop the `.zip` files into:
   ```
   3rd-parties-libraries/00_componentsearchengine_ZIP_archives/
   ```

4. **Import them.** From the project root:
   ```
   python 3rd-parties-libraries/00_import_3rd_party_libs.py
   ```

5. **Open (or reopen) the project in KiCad.** Each part appears as its own
   library (nicknamed after the part, e.g. `INA226AIDGSR`) in both the symbol
   and footprint choosers — the importer registers them in the project's
   `sym-lib-table` / `fp-lib-table` ("Project Specific Libraries") automatically,
   with footprints and 3D models already attached.

You can delete the `KiCad_scripts` folder from the project afterwards if you
like — only the deployed importer under `3rd-parties-libraries/` is needed to
add more parts later.

## Folder structure created

```
<project>/
├─ 3rd-parties-libraries/
│  ├─ 00_import_3rd_party_libs.py            the importer (deployed)
│  ├─ 00_componentsearchengine_ZIP_archives/ drop your .zip downloads here
│  └─ <PART>/                                one folder per part (generated)
│     ├─ <PART>.kicad_sym                    the symbol
│     ├─ <FOOTPRINT>.kicad_mod               the footprint
│     └─ <PART>.stp                          the 3D model
├─ board-dimensions/
├─ bom/
├─ datasheets/
├─ fabrication/
├─ images/
├─ logos/
├─ pcb_render/
└─ schematic_pdf/
```

The `sym-lib-table` and `fp-lib-table` files (which tell KiCad where the
libraries live — the "Project Specific Libraries" in KiCad's library managers)
are created and updated in the project root by the importer.

## One library per part

Each imported part gets its own self-contained folder and its own library
nickname (the part name):

- **Symbol** goes to `<PART>/<PART>.kicad_sym`, registered in `sym-lib-table`.
- **Footprint** goes to `<PART>/<FOOTPRINT>.kicad_mod`, registered in
  `fp-lib-table` (as a plain folder — KiCad reads `.kicad_mod` files from any
  folder given as the URI, no `.pretty` needed). Its 3D `(model …)` path is
  rewritten to `${KIPRJMOD}/…` so the project is **portable** — no absolute
  paths, no changes to KiCad's global settings.
- **3D model** is copied into the same folder.
- The symbol's `Footprint` field is repointed to `<PART>:<FOOTPRINT>` so the
  footprint (and its 3D model) auto-associates when you place the symbol.
- A footprint that ships without a symbol (e.g. a connector whose symbol is a
  KiCad built-in) becomes a footprint-only library.

Because symbol, footprint, and 3D model live together under one nickname, a
part folder copies between projects verbatim.

**Registration happens at import time.** If you remove a part's entry from the
library tables but keep its folder, re-running the importer will not re-add
the entry — delete the part's folder and re-run to re-import and re-register.

## Preserving your edits

A part whose `<PART>/` folder already exists is **left untouched** — each run
only imports parts that are not yet present, so tweaks you make in KiCad
survive re-runs.

To force a part to be re-imported fresh from its zip, delete the part's folder
and re-run the importer.

## Requirements

- Python 3 (the interpreter bundled with KiCad works — no extra packages).
- KiCad 6 or newer (the archives ship modern `.kicad_sym` / `.kicad_mod`
  files; tested against a KiCad 10 project).

## Notes

- Both scripts are **idempotent** — safe to re-run.
- Only the KiCad assets are used. The Altium / OrCAD / Allegro files and the
  legacy `.lib` / `.dcm` / `.mod` files in each archive are ignored.
- If a zip contains a `.wrl` 3D model it is imported too; these archives ship
  `.stp`.
