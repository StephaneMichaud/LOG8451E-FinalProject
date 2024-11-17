import os
import boto3
import yaml
import asyncio
import time
from aws_utils.credentials_loading import load_credentials
from aws_utils.generate_key_pair import generate_key_pair
from aws_utils.create_nat_gateway import create_vpc_and_nat
from aws_utils.create_security_group import create_security_group
from aws_utils.ec2_instances_launcher import launch_ec2_instance
from aws_utils.clean_up import clean_up_ressources
from aws_utils.create_s3_bucket import create_s3_bucket
from aws_utils.upload_download_s3 import upload_folder_to_s3, download_folder_from_s3
from aws_utils.instance_sync import wait_for_tag_value

from instances_assets.db_instance.db_user_data import get_db_user_data
from instances_assets.proxy.proxy_user_data import get_proxy_data
from instances_assets.gatekeeper.trusted_host.trusted_host_user_data import get_trusted_host_data
from benchmarks_utils.benchmarking import benchmarks_cluster
from aws_utils.cloudwatch_metrics import get_instance_metrics, plot_metrics
import datetime

import os

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
#private_instance_dbworkers = None
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
    print("Creating Db manager...")
    key_pair_path = generate_key_pair(ec2, config["key_pair_name"])
    vpc_id, public_subnet_id, private_subnet_id = None, None, None#create_vpc_and_nat(ec2)
    group_id = create_security_group(ec2, vpc_id, config["security_group_name"], "solo security group")
    private_instance_dbmanager = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        None,
        instance_type=config["instances"]["db_instances"]["db_worker_instance_type"],
        image_id=config["instances"]["db_instances"]["db_worker_instance_ami"],
        public_ip=True,
        user_data = get_db_user_data(s3_bucket_name=config["s3_bucket_name"], benchmark_upload_path=config["benchmarks_s3_path"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "DB_MANAGER")], 
        num_instances=1,
        enable_detailed_monitoring = True)[0]
    
    print("Creating DB_WORKER...")
    private_instance_dbworkers = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        None,
        instance_type=config["instances"]["db_instances"]["db_worker_instance_type"],
        image_id=config["instances"]["db_instances"]["db_worker_instance_ami"],
        public_ip=True,
        user_data = get_db_user_data(s3_bucket_name=config["s3_bucket_name"], benchmark_upload_path=config["benchmarks_s3_path"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "DB_WORKER")], 
        num_instances=config["instances"]["db_instances"]["n_workers"],
        enable_detailed_monitoring = True)
    
    

    print("Creating PROXY...")
    private_instance_proxy= launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        None,
        instance_type=config["instances"]["proxy_instance"]["proxy_instance_type"],
        image_id=config["instances"]["proxy_instance"]["proxy_instance_ami"],
        public_ip=True,
        user_data = get_proxy_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "PROXY")], 
        num_instances=1)[0]
    
    public_instance_cluster0 = [private_instance_proxy, private_instance_dbmanager] + private_instance_dbworkers
    wait_for_tag_value(ec2, private_instance_proxy[0], "STATUS", "READY")
    wait_for_tag_value(ec2, private_instance_dbmanager[0], "STATUS", "READY")
    for instance in private_instance_dbworkers:
        wait_for_tag_value(ec2, instance[0], "STATUS", "READY")
    input("Press Enter to continue...")
except Exception as e:
    print(f"Error : {e}")
finally:
    clean_up_ressources(
        ec2, 
        public_instance_cluster0, 
        config["key_pair_name"], 
        key_pair_path, 
        group_id, 
        vpc_id, 
        None, 
        None
    )