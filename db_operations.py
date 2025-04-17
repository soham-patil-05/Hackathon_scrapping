
import json
import asyncio
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor

# Create an executor that can be used across your application
executor = ThreadPoolExecutor()

async def update_hackathon_data(json_file_path, db_url):
    """
    Async wrapper for MongoDB operations using executor
    """
    # Define the synchronous function that will run in the executor
    def _update_in_thread():
        client = None
        results = {
            "deleted_count": 0,
            "inserted_count": 0,
            "success": False,
            "message": ""
        }
        
        try:
            # Connect to the database
            client = MongoClient(db_url)
            db = client["HOC_Users"]
            hackathons_collection = db["hackathons"]
            
            # Delete previous hackathons data
            deleted = hackathons_collection.delete_many({})
            results["deleted_count"] = deleted.deleted_count
            
            # Load new hackathon data from JSON file
            with open(json_file_path, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            
            # Insert new data
            if isinstance(new_data, list) and new_data:
                result = hackathons_collection.insert_many(new_data)
                results["inserted_count"] = len(result.inserted_ids)
                results["success"] = True
                results["message"] = f"Successfully updated hackathon data: deleted {results['deleted_count']} records and inserted {results['inserted_count']} new records."
            else:
                results["message"] = "No valid data found in the JSON file."
            
        except Exception as e:
            results["success"] = False
            results["message"] = f"Error updating hackathon data: {str(e)}"
        
        finally:
            # Close the connection
            if client:
                client.close()
            
            return results
    
    # Run the synchronous function in a thread pool
    return await asyncio.get_event_loop().run_in_executor(executor, _update_in_thread)
