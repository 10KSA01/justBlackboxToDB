import os
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy as sa
from constants import *
from clock import Clock
from datetime import datetime
import json

class BlackboxToDB:
    def __init__(self):
        self.df = pd.DataFrame()
        self.last_timestamp = self.read_last_timestamp()
        self.load_config()
        
    def find_config(self):
        # Get the current directory
        current_directory = os.path.dirname(os.path.abspath(__file__))

        # Construct the file path to config.json
        config_file_path = os.path.join(current_directory, 'config.json')

        return config_file_path
        
    def load_config(self):         
        with open(self.find_config(), 'r') as config_file:
            config_data = json.load(config_file)
        
        # Azure details    
        self.host = config_data["host"]
        self.dbname = config_data["dbname"]
        self.user = config_data["user"]
        self.password = config_data["password"]
        self.tablename = config_data["tablename"]
        
        # Others
        self.log_file_path = config_data["log_file_path"]
        self.timestamp = datetime.strptime(config_data["timestamp"], "%Y-%m-%d %H:%M:%S")
        self.cooldown = config_data["cooldown"]
        self.save_local = config_data["save_local"]
        self.local_file_path = config_data["local_file_path"]
        
        return self
    
    def read_last_timestamp(self):
        return self.load_config().timestamp

    def save_last_timestamp(self):
        with open(self.find_config(), 'r') as config_file:
            config_data = json.load(config_file)
        
        # Update the "timestamp" value in the JSON data     
        config_data["timestamp"] = str(self.current_timestamp())
        
        # Write the updated JSON data back to the config.json file
        with open(self.find_config(), 'w') as config_file:
            config_file.write(json.dumps(config_data, indent=4))
            
        print("saved " , self.load_config().timestamp)
    
    def current_timestamp(self):
         return self.df['datetime'].max()
    
    def loading(self):
        print("Loading \n") 
        # read csv file into DataFrame
        self.df = pd.read_csv(self.log_file_path)
        
        # Convert timestamp column to datetime format
        self.df["datetime"] = pd.to_datetime(self.df['datetime'], format='%a %b %d %H:%M:%S %Y')
        
    def analysing(self):
        print("Analysing \n")            
        # Filter data from the last timestamp onwards
        self.df = self.df[self.df['datetime'] > self.last_timestamp]

        # Update the last timestamp with the latest datetime
        if not self.df.empty:
            self.last_timestamp = self.current_timestamp()

        # Remove duplicates
        self.df = self.df.drop_duplicates()

        # Remove rows with all null values
        self.df.dropna(how='all', inplace=True)

        # Replace empty values to appropriate values
        self.df.fillna(column_na_defaults, inplace=True)

        # Replacing string values with error code
        self.df['logical_point_zone'] = self.df['logical_point_zone'].replace('Zone N/A', error400)
        self.df['point_number'] = self.df['point_number'].replace('No Physical Address Provided', error400)
        self.df['point_number'] = self.df['point_number'].replace('All', all300)

        # Convert float64 columns to int64
        self.df[float_to_int64] = self.df[float_to_int64].astype('Int64')
             
        # Creating unique id column
        self.df['id'] = self.df[unique_id].astype(str).apply(lambda x: '_'.join(x).zfill(3), axis=1)
        
        # Moving column 'id' to the first column
        column_id = self.df.pop('id')
        self.df.insert(0, 'id', column_id)

        # # Reset the index of the result DataFrame
        self.df.reset_index(drop=True, inplace=True)

        # Remove duplicates
        self.df = self.df.drop_duplicates()
                
    def uploading(self):        
        print("Uploading \n")
        
        # create connection string
        # conn_string = "postgresql://{0}:{1}@{2}:5432/{3}?sslmode=require".format(self.user, self.password, self.host, self.dbname)
        conn_string = f"postgresql://{self.user}:{self.password}@{self.host}:5432/{self.dbname}?sslmode=require"
        # create engine
        engine = create_engine(conn_string)

        # Define the column data types
        dtypes = {
            'id':                   sa.String(length=50),
            'datetime':             sa.TIMESTAMP(),
            'reply_status':         sa.String(length=10),
            'node':                 sa.Integer(),
            'channel_address':      sa.Integer(),
            'point_number':         sa.String(length=50),
            'logical_point_number': sa.Integer(),
            'logical_point_zone':   sa.String(length=20),
            'device_type':          sa.String(length=50),
            'dirtiness':            sa.Integer(),
        }

        # write DataFrame to table
        self.df[columns_to_upload].to_sql(self.tablename, engine, if_exists='append', index=False, dtype=dtypes) 
        
    def saving_locally(self):
        # Save the last timestamp to the file
        """
            Moved it here instead of analysing, 
            incase something goes wrong with the uploading stage, 
            then there is no point of saving the timestamp
        """
        self.save_last_timestamp()
        
        # if save_local is set to false, it will not save locally
        # save_local & local_file_path can be configured in the config.json file
        if (self.save_local):
            print("Saving locally\n")
            
        with open(self.local_file_path, 'a') as f:
            # Append to the file and write header only if file is empty
            self.df.to_csv(f, index=False, header=f.tell() == 0) 
        
        print(self.df)
        
    def return_df(self):
        return self.df
    

def main():
    clock = Clock(start=True)
    blackbox_to_db = BlackboxToDB()
    
    while True:
        if clock.time_elapsed(blackbox_to_db.cooldown):
            blackbox_to_db.loading()
            
            print(blackbox_to_db.current_timestamp())
            print(blackbox_to_db.last_timestamp) 
            print("\n")
            
            # Only run the following code if there are new data to process
            if blackbox_to_db.current_timestamp() > blackbox_to_db.last_timestamp:
                blackbox_to_db.analysing()
                blackbox_to_db.uploading()
                blackbox_to_db.saving_locally()
                
                print("Completed \n")

if __name__ == "__main__":
    main()