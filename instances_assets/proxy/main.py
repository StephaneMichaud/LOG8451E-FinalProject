from fastapi import FastAPI
import uvicorn
import logging
import os
import boto3
import requests
from dotenv import load_dotenv
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create FastAPI app
app = FastAPI()



# worker info
db_manager_private_ip = None
db_workers_private_ips = []

# lb mode
VALID_MODE = [0, 1, 2]
VALID_MODE_NAMES = {    0: "MANAGER_ONLY",
                        1: "RANDOM",
                        2: "LEAST_BUSY"
                    }
lbmode = 0

@app.get("/read")
async def read_db():
    global db_manager_private_ip
    global db_workers_private_ips
    global lbmode

    if db_manager_private_ip is None:
        return {"error": "DB manager not found"}

    if lbmode == 0: # manager only
      response = requests.get(f"http://{db_manager_private_ip}/read").json()
    elif lbmode == 1: # random choice
        choice = random.randint(0, len(db_workers_private_ips)) #if we select 0, it the manger, else some worker
        if choice > 0: 
            choice = choice -1
            response = requests.get(f"http://{db_workers_private_ips[choice]}/read").json()
        else:
            response = requests.get(f"http://{db_manager_private_ip}/read").json()
    elif lbmode == 2: # least busy
        least_busy_ip = get_least_busy_ip()
        if least_busy_ip:
            response = requests.get(f"http://{least_busy_ip}/read").json()
        else:
            return {"error": "Cannot ping any db"}
    else:
        return {"error": "Invalid load balancing mode"}
    return response



def get_least_busy_ip():
    global db_manager_private_ip
    global db_workers_private_ips
    
    all_ips = [db_manager_private_ip] + db_workers_private_ips
    response_times = []
    valid_ip = []
    
    for ip in all_ips:
        try:
            response = requests.get(f"http://{ip}/ping")
            
            if response.ok:
                response_times.append(response.elapsed.total_seconds())
                valid_ip.append(ip)
            else:
                logger.warning(f"Failed to ping {ip}: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Error pinging {ip}: {str(e)}")
    
    if response_times:
        least_busy_ip_index = response_times.index(min(response_times))
        return valid_ip[least_busy_ip_index]
    else:
        logger.error("No responsive IPs found")
        return None


@app.post("/write")
async def write_db(first_name: str, last_name: str):
    global db_manager_private_ip
    global db_workers_private_ips

    if db_manager_private_ip is None:
        return {"error": "DB manager not found"}, 404
   
    response = requests.post(f"http://{db_manager_private_ip}/write", params={"first_name": first_name, "last_name": last_name})

    if response.ok:
        worker_errors = []
        for worker_ip in db_workers_private_ips:
            try:
                worker_response = requests.post(f"http://{worker_ip}/write", params={"first_name": first_name, "last_name": last_name})
                if not worker_response.ok:
                    worker_errors.append(f"Worker {worker_ip} failed to update: {worker_response.text}")
            except requests.RequestException as e:
                worker_errors.append(f"Failed to send write request to worker {worker_ip}: {str(e)}")
                logger.error(f"Failed to send write request to worker {worker_ip}: {str(e)}")
        
        if worker_errors:
            return {"error": "Some workers failed to update", "details": worker_errors}, 500
        return response.json()
    else:
        return response.json(), response.status_code
   

@app.post("/mode")
async def switch_lb_mode(mode: int):
    """
    mode: 
    0 = manager only
    1 = random
    2 = least response time
    """
    global lbmode
    if mode not in VALID_MODE:
        return {"error": "Invalid mode"}
    else:
        lbmode = mode
        return {"message": f"LB mode set to {VALID_MODE_NAMES[mode]}"}

if __name__ == "__main__":
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
    
    ec2 = boto3.client("ec2", )
    # Get private IP of first instance with the tag ROLE = DB_MANAGER
    response = ec2.describe_instances(Filters=[
        {
            'Name': 'tag:ROLE',
            'Values': ['DB_MANAGER']
        },
        {
            'Name': 'instance-state-name',
            'Values': ['running']
        }
    ])
    
    if response['Reservations']:
        db_manager_private_ip = response['Reservations'][0]['Instances'][0]['PrivateIpAddress']

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
    
    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=80)