from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import time 

folderLocation = r"C:\Users\\Pictures\Camera Roll"

#Authenticating
gauth = GoogleAuth()
gauth.LoadCredentialsFile("mycreds.txt")

if gauth.credentials is None:
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:
    gauth.Refresh()
else:
    gauth.Authorize()

gauth.SaveCredentialsFile("mycreds.txt")    

GoogleDrive = GoogleDrive(gauth)    

#look into www.blomp.com for storage of videos

def upload(file_path):
    file_name = GoogleDrive.CreateFile({'title': file_name})
    gfile.SetContentFile(file_path)
    gfile.Upload()
    print(f"Uploaded {file_path} to Google Drive.")
    
