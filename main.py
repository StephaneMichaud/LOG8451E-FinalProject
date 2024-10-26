import os
import boto3
import yaml
from ec2_utils.credentials_loading import load_credentials
from ec2_utils.generate_key_pair import generate_key_pair
from ec2_utils.create_security_group import create_security_group
from ec2_utils.ec2_instances_launcher import launch_ec2_instance
from ec2_utils.clean_up import clean_up_ressources


DEFAULT_DOTENV_PATH ='./.env'
DEFAULT_CONFIG_PATH = "./config.yaml"

def load_config(config_path=DEFAULT_CONFIG_PATH):
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    return config


config = load_config()


# Create EC2 client
ec2 = boto3.client('ec2',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
    region_name = os.environ.get('AWS_DEFAULT_REGION'),
)

#setup basic thing we need
load_credentials(DEFAULT_DOTENV_PATH)
key_pair_path = generate_key_pair(ec2, config["key_pair_name"])
group_id = create_security_group(ec2, config["security_group_name"], "solo security group")


private_instance_cluster0 = launch_ec2_instance(
    ec2, 
    config["key_pair_name"], 
    group_id, 
    config["db_instances"]["t2.micro"], 
    public_ip=False,
    user_data = "", 
    tag=("STATUS", "BOOTING-UP"), 
    num_instances=1)
print(private_instance_cluster0)

public_instance_cluster0 = launch_ec2_instance(
    ec2, 
    config["key_pair_name"], 
    group_id, 
    "t2.micro", 
    public_ip=True,
    user_data = "", 
    tag=("STATUS", "BOOTING-UP"), 
    num_instances=1)
print(public_instance_cluster0)

input("Press any key to cleanup...")

#cleanup ressources
clean_up_ressources(ec2, private_instance_cluster0 + public_instance_cluster0, config["key_pair_name"], key_pair_path, group_id)




