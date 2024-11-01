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

#proxy
proxy_private_ip = None


@app.get("/read")
async def read_db():
   if proxy_private_ip is None:
       return {"message": "Proxy instance not found"}, 404
   return requests.get(f"http://{proxy_private_ip}/read").json()

@app.post("/write")
async def write_db(first_name: str, last_name: str):
    if proxy_private_ip is None:
        return {"message": "Proxy instance not found"}, 404
    return requests.post(f"http://{proxy_private_ip}/write", params={"first_name": first_name, "last_name": last_name}).json()

if __name__ == "__main__":
    # Run the FastAPI app# Create EC2 client
    ec2 = boto3.client("ec2")
    
    response = ec2.describe_instances(Filters=[
            {
                'Name': 'tag:ROLE',
                'Values': ['PROXY']
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ])
        
    proxy_private_ip = response['Reservations'][0]['Instances'][0]['PrivateIpAddress']

    uvicorn.run(app, host="0.0.0.0", port=80)