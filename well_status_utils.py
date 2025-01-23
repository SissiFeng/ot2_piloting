#from lambda_mongo_utils import send_data_to_mongodb
from pymongo import MongoClient
from prefect import task
import pandas as pd
#import os

#MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")

MONGODB_PASSWORD = "84Zcbnk8oF9nRKVj"

# Connection string obtained via MongoDB Atlas "Connect" button
blinded_connection_string = "mongodb+srv://Neil-YL:<db_password>@lcm-ot2-sdl.4wik0.mongodb.net/?retryWrites=true&w=majority&appName=LCM-OT2-SDL"

# Replace <password> with the MongoDB password (where again, the connection
# string and password would normally be kept private)
connection_string = blinded_connection_string.replace("<db_password>", MONGODB_PASSWORD)

@task
def generate_empty_well():
    dbclient = MongoClient(connection_string)
    db = dbclient["LCM-OT-2-SLD"]  
    collection = db["wells"] 
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    columns = [str(i) for i in range(1, 13)]
    for row in rows:
        for col in columns:
            well = f"{row}{col}"
            metadata = {
                "well": well,
                "status": "empty",
                "project": "OT2"
            }

            #send_data_to_mongodb(collection="wells", data=metadata)
            query = {"well": well}
            update_data = {"$set": metadata}  
            result = collection.update_one(query, update_data, upsert=True)
            
    # close connection
    dbclient.close()

@task 
def update_used_wells(used_wells):
    dbclient = MongoClient(connection_string)
    db = dbclient["LCM-OT-2-SLD"]  
    collection = db["wells"] 

    for well in used_wells:
        metadata = {
            "well": well,
            "status": "used",
            "project": "OT2"
        }
        #send_data_to_mongodb(collection="wells", data=metadata)
        query = {"well": well}
        update_data = {"$set": metadata}  
        result = collection.update_one(query, update_data, upsert=True)
        
    # close connection
    dbclient.close()

@task
def find_unused_wells():
    dbclient = MongoClient(connection_string)
    db = dbclient["LCM-OT-2-SLD"]  
    collection = db["wells"] 
    query = {"status": "empty"}
    response = list(collection.find(query))  
    df = pd.DataFrame(response)

    # Extract the "well" column as a list
    if "well" not in df.columns:
        raise ValueError("The returned data does not contain the 'well' field.")
    # Sort obtained list
    def well_sort_key(well):
        row = well[0]  # A, B, C, ...
        col = int(well[1:])  # 1, 2, ..., 12
        return (row, col)

    empty_wells = sorted(df["well"].tolist(), key=well_sort_key)
    #print(empty_wells)
    
    # close connection
    dbclient.close()

    # Check if there are any empty wells
    if len(empty_wells) == 0:
        raise ValueError("No empty wells found")
    #print(empty_wells)
    return empty_wells
    


if __name__ == "__main__":
    generate_empty_well()
    #find_unused_wells()
       
    