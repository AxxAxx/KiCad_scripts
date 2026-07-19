# KiCad_scripts

A drop-in toolkit for standing up a new KiCad project and pulling in 3rd-party
parts from [componentsearchengine.com](https://componentsearchengine.com)
(SamacSys ECAD archives).

## Contents

| File | Purpose |
|------|---------|
| `kicad_create_filestructure.py` | Bootstraps a new project's folder tree and deploys the importer. Run once per project. |
| `import_3rd_party_libs.py` | Consolidates componentsearchengine zips into a single KiCad library set and registers it. Run whenever you add parts. |
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

5. **Open (or reopen) the project in KiCad.** The parts are available under the
   `00_CSE` library in both the symbol and footprint choosers, with footprints
   and 3D models already attached.

You can delete the `KiCad_scripts` folder from the project afterwards if you
like — only the deployed importer under `3rd-parties-libraries/` is needed to
add more parts later.

## Folder structure created

```
<project>/
├─ 3rd-parties-libraries/
│  ├─ 00_import_3rd_party_libs.py            the importer (deployed)
│  ├─ 00_componentsearchengine_ZIP_archives/ drop your .zip downloads here
│  ├─ symbols/     cse.kicad_sym             all symbols, merged (generated)
│  ├─ footprints/  cse.pretty/*.kicad_mod    all footprints (generated)
│  └─ 3dmodels/    *.stp                      all 3D models (generated)
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
libraries live) are created in the project root.

## The `00_CSE` library

All imported parts land in one library nicknamed **`00_CSE`**. The leading
`00_` sorts it to the top of KiCad's library lists.

- **Symbols** are merged into `symbols/cse.kicad_sym`.
- **Footprints** are copied into `footprints/cse.pretty/`. Each footprint's 3D
  `(model …)` path is rewritten to `${KIPRJMOD}/…/3dmodels/…` so the project is
  **portable** — no absolute paths, no changes to KiCad's global settings.
- **3D models** are copied into `3dmodels/`.
- Each symbol's `Footprint` field is prefixed with `00_CSE:` so the footprint
  (and its 3D model) auto-associates when you place the symbol.

## Preserving your edits

The importer **never overwrites a symbol, footprint, or 3D model that already
exists** in the generated libraries. Each run only imports parts that are not
yet present, so tweaks you make in KiCad survive re-runs.

To force a part to be re-imported fresh from its zip, delete it first, then
re-run the importer:

- **Footprint:** delete `footprints/cse.pretty/<name>.kicad_mod`
- **3D model:** delete `3dmodels/<name>.stp`
- **Symbol:** delete its `(symbol "<name>" …)` block from
  `symbols/cse.kicad_sym` (or delete the whole file to rebuild every symbol)

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
