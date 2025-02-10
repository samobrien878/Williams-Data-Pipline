import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import chardet  # Added for encoding detection
from collections import Counter

MONGO_URI = "mongodb+srv://____:____@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "Raw_Data"
SUMMARY_COLLECTION_NAME = "Daily summarys"
folder_location = r"C:\Senior Thesis\DBs"

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    summary_collection = db[SUMMARY_COLLECTION_NAME]
    print("Connected to MongoDB.")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    exit(1)


# Parse all necessary info from filenames
def parse_filename(filename):
    parts = filename.split("_")
    dates = parts[4:7]
    month, day = int(dates[0]), int(dates[1])
    year = int(dates[2].split(".")[0])

    rat_id = int(parts[1][3:]) if 0 < int(parts[1][3:]) < 20 else None
    session = int(parts[3][7:])
    stage = int(parts[2][5:])

    return [rat_id, session, stage, month, day, year]


# Function to detect encoding dynamically
def detect_encoding(file_path, num_bytes=10000):
    """Detect the encoding of a file by reading a sample of bytes."""
    with open(file_path, "rb") as f:
        raw_data = f.read(num_bytes)  # Read first `num_bytes` of the file
    result = chardet.detect(raw_data)  # Detect encoding
    return result["encoding"]  # Return detected encoding


# Function to load CSV or Excel file dynamically
def load_data(file_path):
    """Load CSV or Excel file dynamically, ensuring proper encoding detection for CSVs."""
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == ".csv":
            encoding = detect_encoding(file_path)  # Detect encoding dynamically
            df = pd.read_csv(file_path, encoding=encoding)  # Removed 'errors' argument for compatibility

        elif file_ext in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path, engine="openpyxl")  # Read Excel files properly

        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None  # Return None to prevent further processing of the file

    return df


# Function to process data into a dictionary format for MongoDB
def make_dict(file_path):
    df = load_data(file_path)  # Uses new load_data function with encoding detection
    if df is None:
        return []

    metadata = parse_filename(os.path.basename(file_path))
    df['RatID'] = metadata[0]
    df['Session'] = metadata[1]
    df['Stage'] = metadata[2]
    df['Date'] = datetime(metadata[5], metadata[3], metadata[4])

    # Filter data based on date
    df = df[df["Date"] >= datetime(2023, 1, 8)]
    data_dict = df.to_dict(orient="records")

    for record in data_dict:
        session_df = df[df['Session'] == record['Session']]

        # Initialize default values
        record['TP'], record['FP'], record['S_FP'], record['M_FP'], record['Timeout'] = 0, 0, 0, 0, 1
        record['S_Odor_FP'], record['M_Odor_FP'] = None, None

        # HH variables (Stage 0)
        if record['Stage'] == 0:
            record['Max_HH'] = max(session_df['HH time'])

    return data_dict


# Function to compute daily averages for each rat
def averages(data_dict):
    def most_common(lst):
        cleaned_lst = [item for item in lst if item and item != '']  # Ignore None and empty strings
        return Counter(cleaned_lst).most_common(1)[0][0] if cleaned_lst else None

    include = ['Date', 'RatID', 'Stage', 'HH Time', 'Latency to corr sample',
               'Latency to corr match', 'Num pokes corr sample', 'Time in corr sample', 
               'Num pokes inc sample', 'Time in inc sample', 'Num pokes corr match', 
               'Time in corr match']

    df = pd.DataFrame(data_dict)
    available_columns = [col for col in include[3:] if col in df.columns]

    df.loc[df['Stage'] > 0, 'HH Time'] = pd.NA

    daily_avg = df.groupby(['Date', 'RatID', 'Stage'])[available_columns].mean().reset_index()
    daily_avg.columns = ['Date', 'RatID', 'Stage'] + [f'{col}_avg' for col in available_columns]

    return daily_avg


# Function to add summary data
def add_summary(data_dict):
    summary_df = averages(data_dict)
    summary_dict = {'daily_summary': summary_df.to_dict(orient='records')}
    return summary_dict


# Upload function to MongoDB
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


# Function to upload a single new file
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


# Watchdog to monitor folder for new files
def watch_and_upload():
    class FileWatcher(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory or not event.src_path.lower().endswith((".csv", ".xls", ".xlsx")):
                return
            print(f"New file detected: {event.src_path}")
            upload_new_file(os.path.basename(event.src_path))

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


# Run initial upload
upload(folder_location)

# Start watching for new files
watch_and_upload()
