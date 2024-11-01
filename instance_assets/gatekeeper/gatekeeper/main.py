from fastapi import FastAPI
import uvicorn
import logging
import boto3
import requests


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create FastAPI app
app = FastAPI()

#proxy
trusted_host_private_ip = None


@app.get("/read")
async def read_db():
   if trusted_host_private_ip is None:
       return {"message": "Proxy instance not found"}, 404
   return requests.get(f"http://{trusted_host_private_ip}/read").json()

@app.post("/write")
async def write_db(first_name: str, last_name: str):
    if trusted_host_private_ip is None:
        return {"message": "Proxy instance not found"}, 404
    
    # Validate input
    if not first_name or not last_name:
        return {"message": "First name and last name are required"}, 400
    
    # Check for SQL injection
    sql_patterns = ["'", '"', ';', '--', '/*', '*/']
    if any(pattern in first_name or pattern in last_name for pattern in sql_patterns):
        return {"message": "Invalid input detected"}, 400
    
    # Additional validation (e.g., length, allowed characters)
    if not all(name.replace(' ', '').isalpha() for name in [first_name, last_name]):
        return {"message": "Names should only contain letters and spaces"}, 400
    
    if len(first_name) > 50 or len(last_name) > 50:
        return {"message": "Names should not exceed 50 characters"}, 400
    
    # If all validations pass, proceed with the request
    return requests.post(f"http://{trusted_host_private_ip}/write", params={"first_name": first_name, "last_name": last_name}).json()

@app.post("/mode")
async def switch_lb_mode(mode: int):
    if trusted_host_private_ip is None:
        return {"message": "Proxy instance not found"}, 404

    # Validate input
    if mode not in [0, 1, 2]:
        return {"message": "Invalid mode"}, 400

    # If all validations pass, proceed with the request
    return requests.post(f"http://{trusted_host_private_ip}/mode", params={"mode": mode}).json()

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
        
    trusted_host_private_ip = response['Reservations'][0]['Instances'][0]['PrivateIpAddress']

    uvicorn.run(app, host="0.0.0.0", port=80)