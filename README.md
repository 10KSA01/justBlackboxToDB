# justBlackboxToDB

An ETL script that runs in the background that extracts data from a CSV file, transforms the necessary data and finally loads the data to a database (in this case PostgreSQL).

For linux, edit config.json:
"find_log_file_path": "~/blackbox-cpp/logs/<filename>.csv",
"save_local_file_path": "./logs/<filename>.csv"

For windows, edit config.json:
"find_log_file_path": "FYP-Full-Stack-PyroInsight\\blackbox-db\\logs\\<filename>.csv",
"save_local_file_path": "FYP-Full-Stack-PyroInsight\\blackbox-db\\logs\\<filename>.csv",
    
