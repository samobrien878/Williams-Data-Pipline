from pymongo import MongoClient
from datetime import datetime
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import chardet  # Added for encoding detection
from collections import Counter
import pandas as pd

MONGO_URI = "mongodb+srv://obriensam878:1234@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "Raw_Data"
SUMMARY_COLLECTION_NAME = "Daily summaries"
folder_location = r"C:\Users\obrie\OneDrive\Desktop\Documents\Local_Python\Williams Data Science Project\DBs"

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


# Parse filename metadata
def parse_filename(filename):
    parts = filename.split("_")
    dates = parts[4:7]
    month, day = int(dates[0]), int(dates[1])
    year = int(dates[2].split(".")[0])

    rat_id = int(parts[1][3:]) if 0 < int(parts[1][3:]) < 20 else None
    session = int(parts[3][7:])
    stage = int(parts[2][5:])

    return [rat_id, session, stage, month, day, year]


# Detect encoding for CSV files
def detect_encoding(file_path, num_bytes=10000):
    """Detect the encoding of a file by reading a sample of bytes."""
    with open(file_path, "rb") as f:
        raw_data = f.read(num_bytes)
    result = chardet.detect(raw_data)
    return result["encoding"]


# Load data dynamically (CSV or Excel)
def load_data(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()

    try:
        if file_ext == ".csv":
            encoding = detect_encoding(file_path)  
            df = pd.read_csv(file_path, encoding=encoding)

        elif file_ext in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path, engine="openpyxl")

        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None  

    return df


# Convert DataFrame to dictionary format for MongoDB
def make_dict(file_path):
    df = load_data(file_path)
    if df is None:
        return []

    metadata = parse_filename(os.path.basename(file_path))
    file_date = datetime(metadata[5], metadata[3], metadata[4])
    cutoff_date = datetime(2024, 8, 1)
    # Only process files later than the cutoff date
    if file_date < cutoff_date:
        print(f"Skipping file {file_path} as its date {file_date.date()} is before cutoff {cutoff_date.date()}.")
        return []

    df["RatID"] = metadata[0]
    df["Session"] = metadata[1]
    df["Stage"] = metadata[2]
    df["Date"] = file_date

    df = df[df["Date"] >= datetime(2024, 8, 1)]
    data_dict = df.to_dict(orient="records")

    for record in data_dict:
        session_df = df[df["Session"] == record["Session"]]

        # Default values
        record["TP"], record["FP"], record["S_FP"], record["M_FP"], record["Timeout"] = 0, 0, 0, 0, 1
        record["S_Odor_FP"], record["M_Odor_FP"] = None, None

        # **Stage-specific processing**
        if record["Stage"] == 0:
            record["Max_HH"] = max(session_df["HH time"])

        elif record["Stage"] == 1:
            record["S_FP"] = record.get("False pos inc sample", 0) if record["Latency to corr sample"] != 0 else 0
            record["FP"] = record["S_FP"]
            record["TP"] = int(record["False pos inc sample"] == 0 and record["Latency to corr sample"] != 0)

        elif record["Stage"] in [2, 3]:
            if record["Latency to corr sample"] != 0 and record["Latency to corr match"] == 0:
                record["S_FP"] = record.get("False pos inc sample", 0)
                record["M_FP"] = sum([record.get("False pos inc match 1", 0), record.get("False pos inc match 2", 0)])
                record["FP"] = record["S_FP"] + record["M_FP"]
                record["TP"] += int(record["Time in corr sample"] >= 4)

            elif record["Latency to corr sample"] != 0 and record["Latency to corr match"] != 0:
                record["S_FP"] = record.get("False pos inc sample", 0)
                record["M_FP"] = sum([record.get("False pos inc match 1", 0), record.get("False pos inc match 2", 0)])
                record["FP"] = record["S_FP"] + record["M_FP"]
                record["TP"] += int(record["Time in corr sample"] >= 4) + int(record["Time in corr match"] >= 4)
                record["Timeout"] -= 1 

    return data_dict


def add_summary(data_dict):
    # Added check to exit early if data_dict is empty or missing expected columns
    if not data_dict:
        return {}
    df = pd.DataFrame(data_dict)
    if df.empty or "Stage" not in df.columns:
        return {}
    
    include = ["Date", "RatID", "Stage", "TP", "FP", "S_FP", "M_FP", "Latency to corr sample",
               "Latency to corr match", "Num pokes corr sample", "Time in corr sample", 
               "Num pokes inc sample", "Time in inc sample", "Num pokes corr match", 
               "Time in corr match"]

    available_columns = [col for col in include if col in df.columns]

    df.loc[df["Stage"] > 0, "HH Time"] = pd.NA  # Nullify HH Time for stages > 0

    # summing false and true positives, everything else avg
    agg_dict = {col: "mean" for col in available_columns if col not in ["Date", "RatID", "Stage", "TP", "FP"]}
    agg_dict.update({"TP": "sum", "FP": "sum", "S_FP": "sum", "M_FP": "sum"})  # Summing these values

    # groups by date, ratid, and stage so that there is only 1 entry per summary in the db
    daily_avg = df.groupby(["Date", "RatID", "Stage"], as_index=False).agg(agg_dict)

    # renaming for some clarity
    renamed_columns = {col: f"{col}_avg" for col in available_columns if col not in ["Date", "RatID", "Stage", "TP", "FP", "S_FP", "M_FP"]}
    renamed_columns.update({"TP": "TP_total", "FP": "FP_total", "S_FP": "S_FP_total", "M_FP": "M_FP_total"})  # Rename summed values
    daily_avg.rename(columns=renamed_columns, inplace=True)

    # dict so that it can go to mongo
    return {"daily_summary": daily_avg.to_dict(orient="records")}



# Upload files to MongoDB
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


# Upload single file
def upload_new_file(file_name):
    if file_name.startswith("metrics"):
        file_path = os.path.join(folder_location, file_name)
        data_dict = make_dict(file_path)
        summary = add_summary(data_dict)

        if data_dict:
            collection.insert_many(data_dict)
        if summary:
            summary_collection.insert_one(summary)

        print(f"Uploaded: {file_name}")


# Watchdog to monitor folder
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


upload(folder_location)
watch_and_upload()
