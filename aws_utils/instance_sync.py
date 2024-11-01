
import boto3
import time


DELAY_CHECK_S = 30
def wait_for_tag_value(ec2, instance_id, tag_key, tag_value):
    ec2 = boto3.client('ec2')
    
    while True:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        tags = instance.get('Tags', [])
        status_tag = next((tag for tag in tags if tag['Key'] == tag_key), None)
        
        if status_tag and status_tag['Value'] == tag_value:
            print(f"Instance {instance_id} is {tag_value}")
            break
        elif status_tag:
            print(f"Instance {instance_id} is {status_tag['Value']}. Waiting...")
        else:
            print(f"Instance {instance_id} is not tagged. Waiting...")
        time.sleep(DELAY_CHECK_S)  # Wait for 30 seconds before checking again
