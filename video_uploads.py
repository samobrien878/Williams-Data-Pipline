from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import time 
folderLocation = r"C:\Users\\Pictures\Camera Roll"
