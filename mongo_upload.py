import os
import pandas as pd
from pymongo import MongoClient, UpdateOne
from datetime import datetime
import csv
import re

# MongoDB connection details
MONGO_URI = "mongodb+srv://obriensam878:____@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "metrics"

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    print("Connected to MongoDB.")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    exit(1)

# Function to parse the date from filename
def parse_date_from_filename(filename):
    """Extracts date from filenames and converts it to datetime object."""
    try:
        parts = filename.split("_")
        date_parts = parts[-6:-3]  
        month, day, year = map(int, date_parts)
        return datetime(year, month, day)
    except (ValueError, IndexError):
        print(f"Skipping file with incorrect date format: {filename}")
        return None

def extract_rat_id(filename):
    """Extracts RatID from filenames like 'metrics_rat1_stage0_session1_3_23_2023.csv'."""
    try:
        parts = filename.split("_")
        rat_id_with_prefix = parts[1]
        if rat_id_with_prefix.startswith("rat"):
            rat_id_numeric = rat_id_with_prefix[3:]
            rat_id = int(rat_id_numeric)
            print(f"Extracted RatID: {rat_id} from filename: {filename}")
            return rat_id
        else:
            print(f"Skipping file with invalid RatID format: {filename}")
            return None
    except (IndexError, ValueError):
        print(f"Skipping file with incorrect filename format: {filename}")
        return None


def process_csv(file_path, stage):
    """Reads CSV, adds metadata, and filters by date."""
    # Read CSV (handles tab/comma-separated files)
    df = pd.read_csv(file_path)
    # Extract RatID from filename
    filename = os.path.basename(file_path)
    rat_id = extract_rat_id(filename)

    # Add metadata columns
    df["Stage"] = stage
    df["RatID"] = rat_id  # Add RatID column
    file_date = parse_date_from_filename(filename)
    if not file_date:
        return []  # Skip file if date parsing fails
    
    df["Date"] = file_date

    # Filter data since August 2023
    df = df[df["Date"] >= datetime(2023, 8, 1)]

    # Check if DataFrame is empty after filtering
    if df.empty:
        print(f"Skipping file {filename}: Data out of date range.")
        return []

    # Convert DataFrame to dictionary and ensure RatID is included
    records = df.to_dict("records")
    return records

# Function to process all CSV files in the directory
def process_directory(directory):
    """Scans the directory for CSV files and processes them."""
    all_data = []
    #only allow rat ids 1-20
    rat_id_pattern = re.compile(r'rat([1-9]|1[0-9]|20)')
    
    def check_regex(pattern, string):
        if re.search(pattern, string):
            return True
        else:
            return False
        
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".csv") and file.startswith("metrics") and check_regex(rat_id_pattern, file):
                file_path = file

                # Extract stage from filename
                if "stage0" in file:
                    stage = 0
                elif "stage1" in file:
                    stage = 1
                elif "stage2" in file:
                    stage = 2
                elif "stage3" in file:
                    stage = 3
                else:
                    print(f"Skipping file without a valid stage: {file}")
                    continue  # Skip files without a stage

                # Process the file
                data = process_csv(file_path, stage)
                if data:  
                    all_data.extend(data)
    return all_data

# Function to insert data into MongoDB ensuring uniqueness
def insert_data_to_mongo(all_data):
    """Inserts the data into MongoDB ensuring uniqueness based on RatID and Date."""
    if all_data:
        # Build a list of update operations (upsert)
        operations = []
        for record in all_data:
            # Create a unique key based on RatID and Date
            filter = {"RatID": record["RatID"], "Date": record["Date"]}
            update = {"$set": record}  # If it exists, replace with the new record
            operations.append(UpdateOne(filter, update, upsert=True))

        # Execute the bulk write
        result = collection.bulk_write(operations)
        print(f"Inserted or updated {result.upserted_count} records into MongoDB.")
    else:
        print("No data to insert.")

# Main function
def main():
    """Main execution function."""
    csv_directory = r"C:\STIR"

    # Process all CSV files
    all_data = process_directory(csv_directory)

    # Insert data into MongoDB ensuring uniqueness
    insert_data_to_mongo(all_data)

if __name__ == "__main__":
    main()
