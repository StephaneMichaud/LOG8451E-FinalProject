from fastapi import FastAPI
import uvicorn
import logging
import os
import boto3
import requests

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

    if lbmode == 0:
      response = requests.get(f"http://{db_manager_private_ip}/read").json()
    else:
      response = {"error": "Not implemented yet!"}, 400
    return response

@app.post("/write")
async def write_db(first_name: str, last_name: str):
    global db_manager_private_ip
    global db_workers_private_ips
   
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
    ec2 = boto3.client("ec2")
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

    db_workers_private_ips = [res["PrivateIpAddress"] for res in response["Reservations"][0]["Instances"]]
    
    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=80)