import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

MONGO_URI = "mongodb+srv://____:___@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "metrics"
folder_location = r"C:\Users\obrie\OneDrive\Desktop\Documents\Local_Python\Williams Data Science Project\DBs" #replace for lab computers:

#connect to MongoDB:
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    print("Connected to MongoDB.")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    exit(1)



#parse all necessary info from csv names:
def parse_filename(filename):
    parts = filename.split("_")
    dates = parts[4:7]
    month, day = int(dates[0]), int(dates[1])
    year = int(dates[2].split(".")[0])

    if int(parts[1][3:]) > 0 and int(parts[1][3:]) < 20:
        rat_id = int(parts[1][3:])

    session = int(parts[3][7:])
    stage = int(parts[2][5:])

    metadata = [rat_id, session, stage, month, day, year]
    return metadata



#read in each csv file and add metadata:
def make_dict(file_path):
        df = pd.read_csv(file_path)

        metadata = parse_filename(os.path.basename(file_path))
        df['RatID'] = metadata[0]
        df['Session'] = metadata[1]
        df['Stage'] = metadata[2]
        df['Date'] = datetime(metadata[5], metadata[3], metadata[4])

        df = df[df["Date"] >= datetime(2023,1 ,8 )] 
        data_dict = df.to_dict(orient="records")
        return data_dict
#TODO: calculate false positives, true positives, etc. and add to dictionary

#upload mongo
def upload(folder_location):
    for file_name in os.listdir(folder_location):
        if file_name.startswith("metrics"):
            dict = make_dict(file_name)
            collection.insert_many(dict)
            print(f"Uploaded {file_name}")
                

upload(folder_location)

#upload single to mongo
def upload_new_file(file_name):
    if file_name.startswith("metrics"):
            dict = make_dict(file_name)
            collection.insert_many(dict)
            print(f"Uploaded the single file: {file_name}")

#watch for anyone new who shows up:

def watch_and_upload():
    class FileWatcher(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory or not event.src_path.endswith(".csv"):
                return
            print(f"New CSV detected: {event.src_path}")
            upload_new_file(os.path.basename(event.src_path))  # Call the function to upload the file
    observer = Observer()
    observer.schedule(FileWatcher(), path=folder_location, recursive=False)
    observer.start()
    print(f"Watching folder: {folder_location}")

    try:
        while True:
            time.sleep(1)  
    except KeyboardInterrupt:
        observer.stop()
        print("Stopping file watcher...")
    observer.join()

watch_and_upload()
