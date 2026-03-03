import shutil
import os
import time

source = r"c:\Users\signa\OneDrive\Desktop\AQI Folder"
destination = r"c:\Users\signa\OneDrive\Desktop\AQI_Central_Command\Legacy_Archives\AQI Folder"

print(f"Attempting to move {source} to {destination}")

if os.path.exists(source):
    try:
        shutil.move(source, destination)
        print("SUCCESS: Moved folder.")
    except Exception as e:
        print(f"FAILURE: {e}")
else:
    print("Source folder not found (maybe already moved?)")
