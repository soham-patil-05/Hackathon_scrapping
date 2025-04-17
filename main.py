import os
import asyncio
from fastapi import FastAPI, HTTPException
from scrapper import scrape_hackathons
from db_operations import update_hackathon_data
from dotenv import load_dotenv
load_dotenv()


app = FastAPI()

@app.get("/run")
async def run_hackathon_pipeline():
    
    # Ensure Mongo URL is provided
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        raise HTTPException(status_code=500, detail="MONGO_URL environment variable not set")

    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            # 1) Scrape hackathons and write hackathon_data.json
            await scrape_hackathons()

            # 2) Update database
            result = await update_hackathon_data(
                json_file_path="./hackathon_data.json",
                db_url=mongo_url
            )

            if result.get("success"):
                return {"message": "Scrapped hackathons and updated hackathons"}
            else:
                # Prepare to retry
                last_error = result.get("message", "Unknown error during DB update")
                raise RuntimeError(last_error)

        except Exception as e:
            last_error = str(e)
            # If this was the last attempt, raise HTTPException
            if attempt == max_retries:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed after {max_retries} attempts: {last_error}"
                )
            # Otherwise, wait briefly and retry
            await asyncio.sleep(5)  # small delay before retry

# If run directly, start Uvicorn server
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)