import os
import boto3
import yaml
from aws_utils.credentials_loading import load_credentials
from aws_utils.generate_key_pair import generate_key_pair
from aws_utils.create_nat_gateway import create_vpc_and_nat
from aws_utils.create_security_group import create_security_group
from aws_utils.ec2_instances_launcher import launch_ec2_instance
from aws_utils.clean_up import clean_up_ressources
from aws_utils.create_s3_bucket import create_s3_bucket
from aws_utils.upload_s3 import upload_folder_to_s3
from aws_utils.instance_sync import wait_for_tag_value

from instances_assets.db_instance.db_user_data import get_db_user_data
from instances_assets.proxy.proxy_user_data import get_proxy_data

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

ec2 = None
s3_client = None
default_region = config["default_region"]

private_instance_dbmanager = None
private_instance_dbworkers = None
private_instance_proxy = None


try:
    # Create S3 bucket
    s3_client = boto3.client('s3',
                             aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                             aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                             aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
                             region_name = default_region,
                             )
    create_s3_bucket(s3_client, config["s3_bucket_name"], default_region)
    upload_folder_to_s3(s3_client, config["s3_bucket_name"], config["instances_assets_local_path"])


    # Create EC2 client
    ec2 = boto3.client('ec2',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
        region_name = default_region,
    )

    key_pair_path = generate_key_pair(ec2, config["key_pair_name"])
    vpc_id, public_subnet_id, private_subnet_id = create_vpc_and_nat(ec2)
    group_id = create_security_group(ec2, vpc_id, config["security_group_name"], "solo security group")

    print("Creating DB_MANAGER...")
    private_instance_dbmanager = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        private_subnet_id,
        config["db_instances"]["db_worker_instance_type"], 
        public_ip=False,
        user_data = get_db_user_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "DB_MANAGER")], 
        num_instances=1)[0]
    print("Creating DB_WORKER...")
    private_instance_dbworkers = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        private_subnet_id,
        config["db_instances"]["db_worker_instance_type"], 
        public_ip=False,
        user_data = get_db_user_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "DB_WORKER")], 
        num_instances=1)
    
    

    print("Creating PROXY...")
    private_instance_proxy= launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        public_subnet_id,
        config["db_instances"]["db_worker_instance_type"], 
        public_ip=True,
        user_data = get_proxy_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "PROXY")], 
        num_instances=1)[0]


    print("Waiting for DB_MANAGER to be ready...")
    wait_for_tag_value(ec2, private_instance_dbmanager[0], "STATUS", "READY")
    print("Waiting for DB_WORKERS to be ready...")
    for instance in private_instance_dbworkers:
        wait_for_tag_value(ec2, instance[0], "STATUS", "READY")
    #TODO DOWNLOAD FROM BUCKET BENCHMARKS
    print("Waiting for PROXY to be ready...")
    wait_for_tag_value(ec2, private_instance_proxy[0], "STATUS", "READY")



    input("Press any key to cleanup...")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    #cleanup ressources
    print("Cleaning up resources...")
    s3_ressource = boto3.resource('s3',
                        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                        aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
                        region_name = default_region,
                        )
    instances_to_clean_up = []
    if private_instance_dbmanager:
        instances_to_clean_up.append(private_instance_dbmanager)
    if private_instance_dbworkers:
        instances_to_clean_up.extend(private_instance_dbworkers)
    if private_instance_proxy:
        instances_to_clean_up.append(private_instance_proxy)

    clean_up_ressources(
        ec2, 
        instances_to_clean_up, 
        config["key_pair_name"], 
        key_pair_path, 
        group_id, 
        vpc_id, 
        s3_ressource, 
        config["s3_bucket_name"]
    )




