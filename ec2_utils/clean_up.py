import os
import time

INSTANCE_DELETE_DELAY = 120

def terminate_instances(ec2, instance_ids):
    response = ec2.terminate_instances(InstanceIds=instance_ids)
    return response

def delete_key_pair(ec2, key_name, local_key_path = "temp/temp.pem"):
    
    
    # Check for .pem files in the specified folder and delete them
    try:
        os.remove(local_key_path)
        print(f"Deleted local key file: {local_key_path}")
    except Exception as e:
        print(f"Error deleting {local_key_path}: {str(e)}")
    
    response = ec2.delete_key_pair(KeyName=key_name)

    return response

def delete_security_group(ec2, group_id):
    response = ec2.delete_security_group(GroupId=group_id)
    return response

def clean_up_ressources(ec2, instance_ids, key_name, local_key_path, group_id):
    terminate_instances(ec2, [i[0] for i in instance_ids])
    time.sleep(INSTANCE_DELETE_DELAY)  # We wait to ensure instances are deleted
    delete_key_pair(ec2, key_name, local_key_path)
    time.sleep(60)  # Wait to ensure key pairs are deleted
    delete_security_group(ec2, group_id)  # Ensure instances are deleted before security group
    print("Cleanup completed.")
