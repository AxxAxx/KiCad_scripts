import zipfile
import os
import shutil

# Function to remove a folder
def remove(path):
    """ param <path> could either be relative or absolute. """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(path))

currentpath = os.getcwd()
zipfolders = os.getcwd() + "/00_componentsearchengine_ZIP_archives"

# make temp folder for unzipping components
tempfolderpath = os.path.join(currentpath, "temp")
os.makedirs(tempfolderpath, exist_ok=True)
print("temp directory created %s" % tempfolderpath)


for filename in os.listdir(zipfolders):
    f = os.path.join(zipfolders, filename)
    # checking if it is a .zip file
    if f.endswith('.zip'):
        # unzip
        with zipfile.ZipFile(f, 'r') as zip_ref:
            zip_ref.extractall(tempfolderpath)
            
            try:
                componentfolderpath = os.path.join(currentpath,f.split('LIB_')[1].strip(".zip")) 
                if not os.path.exists(componentfolderpath):
                    os.makedirs(componentfolderpath)
                # Move 3D model to component folder
                file = f.split('LIB_')[1].strip(".zip")+"/3D"
                for filename in os.listdir(tempfolderpath + "/" + file):
                    if not os.path.isfile(componentfolderpath + filename):
                        os.replace(os.path.join(tempfolderpath + "/" + file, filename), os.path.join(componentfolderpath + "/" + filename))
                        print("moving file %s" % filename)
                    else:
                        print("%s did already exist!" % filename)
                
                # Move footprint and symbol to component folder                
                file = f.split('LIB_')[1].strip(".zip")+"/KiCad"
                for filename in os.listdir(tempfolderpath + "/" + file):
                    if (filename.endswith('.kicad_mod') or filename.endswith('.kicad_sym')):
                        if not os.path.isfile(componentfolderpath + filename):
                            os.replace(os.path.join(tempfolderpath + "/" + file, filename), os.path.join(componentfolderpath + "/" + filename))
                            print("moving file %s" % filename)
                        else:
                            print("%s did already exist!" % filename)
                        
            except Exception as e: print(e)
remove(tempfolderpath)