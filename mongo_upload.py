import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

MONGO_URI = "mongodb+srv://____:____@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "metrics"
SUMMARY_COLLECTION_NAME = "summary"
folder_location = r"C:\Users\obrie\OneDrive\Desktop\Documents\Local_Python\Williams Data Science Project\DBs" #replace for lab computers:

#connect to MongoDB:
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    summary_collection = db[SUMMARY_COLLECTION_NAME]
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
    
    # Making some key metrics and turning df into dict for each trial
    metadata = parse_filename(os.path.basename(file_path))
    df['RatID'] = metadata[0]
    df['Session'] = metadata[1]
    df['Stage'] = metadata[2]
    df['Date'] = datetime(metadata[5], metadata[3], metadata[4])
    df = df[df["Date"] >= datetime(2023, 1, 8)]
    data_dict = df.to_dict(orient="records")
    
    for record in data_dict:
        session_df = df[df['Session'] == record['Session']]
        
        #HH variables
        if record['Stage'] == 0:
            record['Max_HH'] = max(session_df['HH Time'])
            record['Timeouts'] = sum(1 for latency in session_df['Latency to corr sample'] if latency == 0)
    
        # Stage 1 variables
        elif record['Stage'] == 1:
            record['Total_FP'] = record.get('False pos inc sample', 0) if record['Latency to corr sample'] != 0 else 0
            record['Timeouts'] = sum(1 for latency in session_df['Latency to corr sample'] if latency == 0)
            record['Odor_FP'] = "Blank" if record['Total_FP'] > 0 else None
            record['True_Positives'] = 1 if record['False pos inc sample'] == 0 and  record['Latency to corr sample'] != 0 else 0
    
        # Stage 2 and 3 variables
        elif record['Stage'] in [2, 3]:
            if record['Latency to corr sample'] != 0 and record['Latency to corr match'] != 0:
                record['Total_FP'] = sum([
                    record.get('False pos inc sample', 0),
                    record.get('False pos inc match 1', 0),
                    record.get('False pos inc match 2', 0)
                ]) 
                record['Sample_FP'] = record.get('False pos inc sample', 0)
                record['Match_FP'] = sum([
                    record.get('False pos inc match 1', 0),
                    record.get('False pos inc match 2', 0)
                ]) 
                record['Odor_FP'] = "Blank" if record.get('False pos inc sample', 0) >= 1 else [
                    record.get(f'Inc match {i} odor name') for i in [1, 2] if record.get(f'False pos inc match {i}') >= 1
                ]
                
                record['TP'] = 0
                if record['Time in corr sample'] >= 4 and record['Time in corr match'] >= 4:
                    record['TP'] = record['TP'] + 2
                # did we want this to increment 3 if the time in corr sample was above 4 secs? 
                if record['Time in corr sample'] >= 4:
                    record['TP'] = record['TP'] + 1
                    
            else:
                record['Odor_FP'] = None
                record['Timeouts'] = 1

    return data_dict

def averages(data_dict):
    include = ['Date', 'RatID', 'Stage', 'HH Time', 'Latency to corr sample', 
               'Latency to corr match', 'Num pokes corr sample', 'Time in corr sample', 
               'Num pokes inc sample','Time in inc sample', 'Num pokes corr match', 'Time in corr match']
    df = pd.DataFrame(data_dict)

    #HH Time doesn't matter after stage 0
    df.loc[df['Stage'] > 0, 'HH Time'] = pd.NA

    daily_avg = df.groupby(df['Date'])[include[3:]].mean().reset_index()
    daily_avg.columns = ['Date'] + ['RatID'] + ['Stage'] + [f'{col}_avg' for col in include[3:]]
    return daily_avg

def add_summary(data_dict):
    daily_avg = averages(data_dict)
    df = pd.DataFrame(data_dict)
    summary_dict = {
        'daily_avg': daily_avg.to_dict(orient='records')
    }
    return summary_dict

a = make_dict(r"Test_data\metrics_rat1_stage2_session15_11_29_2023_13_45_50.csv")
#C:\Users\obrie\OneDrive\Desktop\Documents\Local_Python\Williams Data Science Project\DBs\metrics_rat1_stage2_session15_11_29_2023_13_45_50.csv
print(add_summary(a))



#upload mongo
# def upload(folder_location):
#     for file_name in os.listdir(folder_location):
#         if file_name.startswith("metrics"):
#             dict = make_dict(file_name)
#             summary = add_summary(data_dict)
#             collection.insert_many(dict)
#             summary_collection.insert_one(summary)
#             print(f"Uploaded {file_name}")
                

# upload(folder_location)

#upload single to mongo
# def upload_new_file(file_name):
#     if file_name.startswith("metrics"):
#             dict = make_dict(file_name)
#             collection.insert_many(dict)
#             print(f"Uploaded the single file: {file_name}")

# #watch for anyone new who shows up:

# def watch_and_upload():
#     class FileWatcher(FileSystemEventHandler):
#         def on_created(self, event):
#             if event.is_directory or not event.src_path.endswith(".csv"):
#                 return
#             print(f"New CSV detected: {event.src_path}")
#             upload_new_file(os.path.basename(event.src_path))  # Call the function to upload the file
#     observer = Observer()
#     observer.schedule(FileWatcher(), path=folder_location, recursive=False)
#     observer.start()
#     print(f"Watching folder: {folder_location}")

#     try:
#         while True:
#             time.sleep(1)  
#     except KeyboardInterrupt:
#         observer.stop()
#         print("Stopping file watcher...")
#     observer.join()

# watch_and_upload()
