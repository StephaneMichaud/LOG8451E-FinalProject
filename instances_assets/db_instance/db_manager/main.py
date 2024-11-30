from threading import Lock
from fastapi import FastAPI, HTTPException
import uvicorn
import logging
from pymysql import connect
import boto3
import os
from dotenv import load_dotenv
from ec2_metadata import ec2_metadata
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create FastAPI app
app = FastAPI()
# Database connection details
DB_NAME = "sakila"
connection = None
instance_id = ec2_metadata.instance_id
db_workers_private_ips = []

@app.get("/ping")
async def ping():
    return {"message": f"!"}

@app.get("/read")
async def read_db():
    message = f"Instance {instance_id} reading now:"
    logger.info(message)

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
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# Create a global mutex for write operations
write_mutex = Lock()

@app.post("/write")
async def write_db(first_name: str, last_name: str):
    global db_workers_private_ips
    message = f"Instance {instance_id} is writing now:"
    logger.info(message)

    try:
        with write_mutex:  # Acquire the mutex before writing
            with connection.cursor() as cursor:
                sql = "INSERT INTO actor (first_name, last_name) VALUES (%s, %s)"
                cursor.execute(sql, (first_name, last_name))
            connection.commit()
            message += f"\nSuccessfully added new actor: {first_name} {last_name}"
            logger.info(f"New actor added: {first_name} {last_name}")
            worker_errors= []

            #replicate write on workers
            for worker_ip in db_workers_private_ips:
                try:
                    worker_response = requests.post(f"http://{worker_ip}/write", params={"first_name": first_name, "last_name": last_name})
                    if not worker_response.ok:
                        worker_errors.append(f"Worker {worker_ip} failed to update: {worker_response.text}")
                except requests.RequestException as e:
                    worker_errors.append(f"Failed to send write request to worker {worker_ip}: {str(e)}")
                    logger.error(f"Failed to send write request to worker {worker_ip}: {str(e)}")
            
            if worker_errors:
                raise HTTPException(status_code=400, detail=f"Some workers failed to update: {worker_errors}")
    
    except Exception as e:
        logger.error(f"Error writing to database: {str(e)}")
        message += f"\nError occurred while writing to database: {str(e)}"
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}
if __name__ == "__main__":
    # Run the FastAPI app
     # Create EC2 client

    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get AWS credentials from environment variables
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')
    aws_region = os.getenv('AWS_DEFAULT_REGION')

    
    # Create EC2 client with loaded credentials
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token = aws_session_token,
        region_name=aws_region
    )
    # Connect to the database
     # Get private IPs of all instances with the tag ROLE = DB_WORKER
    response = ec2.describe_instances(Filters=[
        {
            'Name': 'tag:ROLE',
            'Values': ['DB_WORKER']
        },
        {
            'Name': 'instance-state-name',
            'Values': ['running']
        }
    ])
    if response['Reservations']:
        db_workers_private_ips = [res["PrivateIpAddress"] for res in response["Reservations"][0]["Instances"]]
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