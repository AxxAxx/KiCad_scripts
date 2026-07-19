import zipfile
import os
import shutil

folder_structure = [['3rd-parties-libraries', '00_componentsearchengine_ZIP_archives'], ['board-dimensions'], ['bom'], ['datasheets'], ['fabrication'], ['images'], ['logos'], ['pcb_render'], ['schematic_pdf']]

currentpath = os.path.dirname(os.getcwd())

for folders in folder_structure:
	tempfolderpath = os.path.join(currentpath, folders[0])	
	if not os.path.exists(tempfolderpath):
		os.makedirs(tempfolderpath)
	if len(folders) > 1:
		for sub_folders in folders[1:]:
			tempsubfolderpath = os.path.join(tempfolderpath, sub_folders)
			if not os.path.exists(tempsubfolderpath):
				os.makedirs(tempsubfolderpath)
				
# Deploy the 3rd-party library import script into 3rd-parties-libraries/.
# It consolidates componentsearchengine zips into merged symbol / footprint /
# 3D-model libraries and registers them in the project's library tables.
source_script = os.path.join(os.getcwd(), 'import_3rd_party_libs.py')
deployed_script = os.path.join(currentpath, '3rd-parties-libraries', '00_import_3rd_party_libs.py')
if not os.path.isfile(deployed_script):
	shutil.copyfile(source_script, deployed_script)
