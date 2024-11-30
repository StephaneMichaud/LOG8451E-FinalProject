from fastapi import FastAPI, HTTPException
import uvicorn
import logging
from threading import Lock
from pymysql import connect
from ec2_metadata import ec2_metadata

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create FastAPI app
app = FastAPI()
# Database connection details
DB_NAME = "sakila"
connection = None
instance_id = ec2_metadata.instance_id


@app.get("/ping")
async def ping():
    return {"message": f"!"}

@app.get("/read")
async def read_db():
    message = f"Instance {instance_id} reading now:"
    logger.info(message)
    response_type = 200

    try:
        with connection.cursor() as cursor:
            # Example query to read data from the 'actor' table
            sql = "SELECT actor_id, first_name, last_name FROM actor ORDER BY last_update DESC LIMIT 5"
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # Format the result
            actors = [f"Actor ID: {row[0]}, Name: {row[1]} {row[2]}" for row in result]
            message += f" Read {len(actors)} actors from the database: " + "| ".join(actors)
    except Exception as e:
        logger.error(f"Error reading from database: {str(e)}")
        message += f"\nError occurred while reading from database: {str(e)}"
        response_type = 400
    if response_type == 400:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

write_mutex = Lock()
@app.post("/write")
async def write_db(first_name: str, last_name: str):
    with write_mutex:
        message = f"Instance {instance_id} is writing now:"
        logger.info(message)
        response_type = 200
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO actor (first_name, last_name) VALUES (%s, %s)"
                cursor.execute(sql, (first_name, last_name))
            connection.commit()
            message += f"\nSuccessfully added new actor: {first_name} {last_name}"
            logger.info(f"New actor added: {first_name} {last_name}")
        except Exception as e:
            logger.error(f"Error writing to database: {str(e)}")
            message += f"\nError occurred while writing to database: {str(e)}"
            response_type = 400
        
    if response_type == 400:
        raise HTTPException(status_code=400, detail=message)
        
    return {"message": message}

if __name__ == "__main__":
    # Run the FastAPI app
# Connect to the database
    try:
        connection = connect(
            user='log8415e',
            password='log8415e',
            database=DB_NAME
        )
        logger.info(f"Successfully connected to {DB_NAME} database")
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

    uvicorn.run(app, host="0.0.0.0", port=80)