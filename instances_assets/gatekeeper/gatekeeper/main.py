from fastapi import FastAPI, HTTPException
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

#trusted_host
host_private_ip = None


@app.get("/read")
async def read_db():
   if host_private_ip is None:
         raise HTTPException(status_code = 404, detail= "Proxy instance not found")
   return requests.get(f"http://{host_private_ip}/read").json()

@app.post("/write")
async def write_db(first_name: str, last_name: str):
   if host_private_ip is None:
      raise HTTPException(status_code = 404, detail= "Proxy instance not found")

   # Validate first_name and last_name
   if not first_name or not last_name:
      raise HTTPException(status_code = 400, detail= "First name and last name cannot be empty")
   
   if len(first_name) > 50 or len(last_name) > 50:
      raise HTTPException(status_code = 400, detail= "First name and last name must be 50 characters or less")
   
   # Simple SQL injection check
   sql_patterns = ["'", '"', ';', '--', '/*', '*/']
   if any(pattern in first_name or pattern in last_name for pattern in sql_patterns):
      raise HTTPException(status_code = 400, detail= "Invalid characters detected in name fields")
   
   # If all validations pass, proceed with the request
   
   return requests.post(f"http://{host_private_ip}/write", params={"first_name": first_name, "last_name": last_name}).json()

@app.post("/mode")
async def switch_lb_mode(mode: int):
   if host_private_ip is None:
      raise HTTPException(status_code = 404, detail="Proxy instance not found")
   if mode not in [0, 1, 2]:
         raise HTTPException(status_code = 400, detail="Invalid mode. Mode must be 0, 1 or 2.")
   response = requests.post(f"http://{host_private_ip}/mode", params={"mode": mode})
   return response.json()

if __name__ == "__main__":
   # Run the FastAPI app# Create EC2 client
   ec2 = boto3.client("ec2")
   
   response = ec2.describe_instances(Filters=[
         {
               'Name': 'tag:ROLE',
               'Values': ['TRUSTED-HOST']
         },
         {
               'Name': 'instance-state-name',
               'Values': ['running']
         }
      ])
   if response['Reservations']:
      host_private_ip = response['Reservations'][0]['Instances'][0]['PrivateIpAddress']

   uvicorn.run(app, host="0.0.0.0", port=80)