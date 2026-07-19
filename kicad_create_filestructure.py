#!/usr/bin/env python3
"""
kicad_create_filestructure.py

Bootstraps a new KiCad project's directory layout.

Usage
-----
Drop this whole `KiCad_scripts` folder into a fresh (empty) KiCad project
directory, then run this script *from inside that folder*:

    cd KiCad_scripts
    python kicad_create_filestructure.py

It does two things:

1. Creates the standard project subfolders (see FOLDER_STRUCTURE below) in the
   PARENT directory - i.e. the project root that contains this KiCad_scripts
   folder.
2. Deploys the 3rd-party library importer into
   3rd-parties-libraries/00_import_3rd_party_libs.py so it is ready to run.

After bootstrapping: drop componentsearchengine .zip archives into
3rd-parties-libraries/00_componentsearchengine_ZIP_archives/ and run the
deployed importer to build the "00_CSE" libraries. See README.md for the full
workflow.

Standard library only - runs on any Python 3 (including the one bundled with
KiCad).
"""

import os
import shutil

# Project subfolders to create. Each entry is a list: the first item is a
# top-level folder, any following items are subfolders created inside it.
FOLDER_STRUCTURE = [
    ["3rd-parties-libraries", "00_componentsearchengine_ZIP_archives"],
    ["board-dimensions"],
    ["bom"],
    ["datasheets"],
    ["fabrication"],
    ["images"],
    ["logos"],
    ["pcb_render"],
    ["schematic_pdf"],
]

# The project root is the PARENT of this script's folder. This assumes the
# script is run from within the KiCad_scripts folder (cwd = KiCad_scripts),
# which sits directly inside the project directory.
script_dir = os.getcwd()
project_root = os.path.dirname(script_dir)

# --- 1. Create the folder tree (idempotent - skips folders that exist) -------
for entry in FOLDER_STRUCTURE:
    top_folder = os.path.join(project_root, entry[0])
    if not os.path.exists(top_folder):
        os.makedirs(top_folder)

    # Create any subfolders listed after the first item.
    for sub_folder in entry[1:]:
        sub_path = os.path.join(top_folder, sub_folder)
        if not os.path.exists(sub_path):
            os.makedirs(sub_path)

# --- 2. Deploy the 3rd-party library importer --------------------------------
# Copy import_3rd_party_libs.py (sitting next to this script) into
# 3rd-parties-libraries/ as 00_import_3rd_party_libs.py. The "00_" prefix keeps
# it sorted next to the archive folder. The importer consolidates
# componentsearchengine zips into merged symbol / footprint / 3D-model libraries
# and registers them in the project's library tables.
source_script = os.path.join(script_dir, "import_3rd_party_libs.py")
deployed_script = os.path.join(
    project_root, "3rd-parties-libraries", "00_import_3rd_party_libs.py"
)

# Don't clobber an already-deployed importer (it may carry your local tweaks).
if not os.path.isfile(deployed_script):
    shutil.copyfile(source_script, deployed_script)
    print(f"Deployed importer -> {deployed_script}")
else:
    print(f"Importer already present -> {deployed_script} (left untouched)")

print(f"Project structure ready in {project_root}")
