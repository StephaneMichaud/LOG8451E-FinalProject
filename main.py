import os
import boto3
import yaml
from ec2_utils.credentials_loading import load_credentials
from ec2_utils.generate_key_pair import generate_key_pair
from ec2_utils.create_nat_gateway import create_vpc_and_nat
from ec2_utils.create_security_group import create_security_group
from ec2_utils.ec2_instances_launcher import launch_ec2_instance
from ec2_utils.clean_up import clean_up_ressources

from ec2_assets.db_user_data import get_user_data

DEFAULT_DOTENV_PATH ='./.env'
DEFAULT_CONFIG_PATH = "./config.yaml"

def load_config(config_path=DEFAULT_CONFIG_PATH):
    with open(config_path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    return config


#setup basic thing we need
load_credentials(DEFAULT_DOTENV_PATH)
config = load_config()



private_instance_cluster0 = []
public_instance_cluster0 = []
key_pair_path = ""
group_id = None
vpc_id = None

try:
    # Create EC2 client
    ec2 = boto3.client('ec2',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
        region_name = os.environ.get('AWS_DEFAULT_REGION'),
    )

    key_pair_path = generate_key_pair(ec2, config["key_pair_name"])
    vpc_id, public_subnet_id, private_subnet_id = create_vpc_and_nat(ec2)
    group_id = create_security_group(ec2, vpc_id, config["security_group_name"], "solo security group")

    private_instance_cluster0 = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        private_subnet_id,
        config["db_instances"]["db_worker_instance_type"], 
        public_ip=False,
        user_data = get_user_data(s3_bucket_name=config["bucket_name"]), 
        tag=("STATUS", "BOOTING-UP"), 
        num_instances=1)
    print(private_instance_cluster0)

    public_instance_cluster0 = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        public_subnet_id,
        config["db_instances"]["db_worker_instance_type"], 
        public_ip=True,
        user_data = "", 
        tag=("STATUS", "BOOTING-UP"), 
        num_instances=1)
    print(public_instance_cluster0)

    input("Press any key to cleanup...")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    #cleanup ressources
    print("Cleaning up resources...")
    clean_up_ressources(ec2, private_instance_cluster0 + public_instance_cluster0, config["key_pair_name"], key_pair_path, group_id, vpc_id, "", "")




