
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from collections import Counter

MONGO_URI = "mongodb+srv://:@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "Raw_Data"
SUMMARY_COLLECTION_NAME = "Daily summarys"
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

        # HH variables
        if record['Stage'] == 0:
            record['Max_HH'] = max(session_df['HH time'])
            record['Timeouts'] = sum(1 for latency in session_df['Latency to corr sample'] if latency == 0)
            record['S_Odor_FP'] = None
            record['M_Odor_FP'] = None

        # Stage 1 variables
        elif record['Stage'] == 1:
            record['S_Odor_FP'] = None
            record['M_Odor_FP'] = None


            record['FP'] = record.get('False pos inc sample', 0) if record['Latency to corr sample'] != 0 else 0
            record['Timeouts'] = sum(1 for latency in session_df['Latency to corr sample'] if latency == 0)
            record['Odor_FP'] = "Blank" if record['FP'] > 0 else None
            record['TP'] = int(record['False pos inc sample'] == 0 and record['Latency to corr sample'] != 0)

        # Stage 2 and 3 variables
        elif record['Stage'] in [2, 3]:
            record.update({
                'TP': 0, 'FP': 0, 'S_FP': 0, 'M_FP': 0, 'Timeout': 1,
                'S_Odor_FP': None, 'M_Odor_FP': None
            })

            # If the sample trial was completed, but timed out on the match trial
            if record['Latency to corr sample'] != 0 and record['Latency to corr match'] == 0:
                record['FP'] = sum([
                    record.get('False pos inc sample', 0),
                    record.get('False pos inc match 1', 0),
                    record.get('False pos inc match 2', 0)
                ])
                record['S_FP'], record['M_FP'] = record.get('False pos inc sample', 0), record['FP'] - record['S_FP']
                record['TP'] += int(record['Time in corr sample'] >= 4)
                record['S_Odor_FP'] = "Blank" if record['S_FP'] >= 1 else None
                
                false_pos_odors = [
                    record.get(f'Inc match {i} odor name') 
                    for i in [1, 2] 
                    if record.get(f'False pos inc match {i}', 0) > 0
                ]
                record['M_Odor_FP'] = max(set(false_pos_odors), key=false_pos_odors.count) if false_pos_odors else None

            # Now check what the results were if there were no timeouts:
            elif record['Latency to corr sample'] != 0 and record['Latency to corr match'] != 0:
                record['FP'] = sum([
                    record.get('False pos inc sample', 0),
                    record.get('False pos inc match 1', 0),
                    record.get('False pos inc match 2', 0)
                ])
                record['S_FP'], record['M_FP'] = record.get('False pos inc sample', 0), record['FP'] - record['S_FP']
                record['TP'] += int(record['Time in corr sample'] >= 4) + int(record['Time in corr match'] >= 4)
                record['S_Odor_FP'] = "Blank" if record['S_FP'] >= 1 else None
                
                false_pos_odors = [
                    record.get(f'Inc match {i} odor name') 
                    for i in [1, 2] 
                    if record.get(f'False pos inc match {i}', 0) > 0
                ]
                record['M_Odor_FP'] = max(set(false_pos_odors), key=false_pos_odors.count) if false_pos_odors else None
                record['Timeout'] -= 1

    return data_dict


def averages(data_dict):
    from collections import Counter

    def most_common(lst):
        cleaned_lst = [item for item in lst if item and item != '']  # Ignore None and empty strings
        return Counter(cleaned_lst).most_common(1)[0][0] if cleaned_lst else None

    include = ['Date', 'RatID', 'Stage', 'HH Time', 'Latency to corr sample',
               'Latency to corr match', 'Num pokes corr sample', 'Time in corr sample', 
               'Num pokes inc sample', 'Time in inc sample', 'Num pokes corr match', 
               'Time in corr match']

    df = pd.DataFrame(data_dict)

    available_columns = [col for col in include[3:] if col in df.columns]
    
    # HH Time doesn't matter after stage 0
    df.loc[df['Stage'] > 0, 'HH Time'] = pd.NA

    # Calculate daily averages for only available columns
    daily_avg = df.groupby(['Date', 'RatID', 'Stage'])[available_columns].mean().reset_index()
    daily_avg.columns = ['Date', 'RatID', 'Stage'] + [f'{col}_avg' for col in available_columns]

    # Calculate totals
    total_columns = ['FP', 'S_FP', 'M_FP', 'TP', 'Timeout']
    available_totals = [col for col in total_columns if col in df.columns]

    daily_totals = df.groupby(['Date', 'RatID', 'Stage'])[available_totals].sum().reset_index()
    daily_totals.columns = ['Date', 'RatID', 'Stage'] + [f'{col}_total' for col in available_totals]

    # Collect the most common Sample and Match Odors that had False Positives
    odor_fp_df = df.groupby(['Date', 'RatID', 'Stage']).agg({
        'S_Odor_FP': lambda x: most_common(
            [item for sublist in x.dropna() for item in (sublist if isinstance(sublist, list) else [sublist])]
        ) if 'S_Odor_FP' in df.columns else None,
        'M_Odor_FP': lambda x: most_common(
            [item for sublist in x.dropna() for item in (sublist if isinstance(sublist, list) else [sublist])]
        ) if 'M_Odor_FP' in df.columns else None
    }).reset_index()

    # Merge all summaries
    summary_df = daily_avg.merge(daily_totals, on=['Date', 'RatID', 'Stage'], how='left').merge(odor_fp_df, on=['Date', 'RatID', 'Stage'], how='left')

    return summary_df


#Summarize dat data
def add_summary(data_dict):
    summary_df = averages(data_dict)
    summary_dict = {
        'daily_summary': summary_df.to_dict(orient='records')
    }
    return summary_dict


#upload mongo
def upload(folder_location):
    for file_name in os.listdir(folder_location):
        if file_name.startswith("metrics"):
            file_path = os.path.join(folder_location, file_name)
            data_dict = make_dict(file_path)
            summary = add_summary(data_dict)

            if data_dict:
                collection.insert_many(data_dict)
            if summary:
                summary_collection.insert_one(summary)

            print(f"Uploaded {file_name}")
                

upload(folder_location)

#upload single to mongo
def upload_new_file(file_name):
    if file_name.startswith("metrics"):
        file_path = os.path.join(folder_location, file_name)
        data_dict = make_dict(file_path)
        summary = add_summary(data_dict)

        if data_dict:
            collection.insert_many(data_dict)
        if summary:
            summary_collection.insert_one(summary)

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
