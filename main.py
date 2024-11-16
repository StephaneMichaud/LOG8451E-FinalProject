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
private_instance_dbworkers = None
private_instance_proxy = None
private_instance_trusted_host = None
public_instance_gatekeeper = None


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
        instance_type=config["instances"]["db_instances"]["db_worker_instance_type"],
        image_id=config["instances"]["db_instances"]["db_worker_instance_ami"],
        public_ip=False,
        user_data = get_db_user_data(s3_bucket_name=config["s3_bucket_name"], benchmark_upload_path=config["benchmarks_s3_path"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "DB_MANAGER")], 
        num_instances=1)[0]
    print("Creating DB_WORKER...")
    private_instance_dbworkers = launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        private_subnet_id,
        instance_type=config["instances"]["db_instances"]["db_worker_instance_type"],
        image_id=config["instances"]["db_instances"]["db_worker_instance_ami"],
        public_ip=False,
        user_data = get_db_user_data(s3_bucket_name=config["s3_bucket_name"], benchmark_upload_path=config["benchmarks_s3_path"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "DB_WORKER")], 
        num_instances=config["instances"]["db_instances"]["n_workers"])
    
    

    print("Creating PROXY...")
    private_instance_proxy= launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        private_subnet_id,
        instance_type=config["instances"]["proxy_instance"]["proxy_instance_type"],
        image_id=config["instances"]["proxy_instance"]["proxy_instance_ami"],
        public_ip=False,
        user_data = get_proxy_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "PROXY")], 
        num_instances=1)[0]
    
    print("Creating Trusted Host...")
    private_instance_trusted_host= launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        private_subnet_id,
        instance_type=config["instances"]["gatekeeper_instances"]["trusted_host"]["trusted_host_instance_type"],
        image_id=config["instances"]["gatekeeper_instances"]["trusted_host"]["trusted_host_instance_ami"],
        public_ip=False,
        user_data = get_trusted_host_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "TRUSTED-HOST")], 
        num_instances=1)[0]

    print("Creating Gatekeeper...")
    public_instance_gatekeeper= launch_ec2_instance(
        ec2, 
        config["key_pair_name"], 
        group_id,
        public_subnet_id,
        instance_type=config["instances"]["gatekeeper_instances"]["gatekeeper"]["gatekeeper_instance_type"],
        image_id=config["instances"]["gatekeeper_instances"]["gatekeeper"]["gatekeeper_instance_ami"],
        public_ip=True,
        user_data = get_trusted_host_data(s3_bucket_name=config["s3_bucket_name"]), 
        tags=[("STATUS", "BOOTING-UP"), ("ROLE", "GATEKEEPER")], 
        num_instances=1)[0]

    print("Waiting for DB_MANAGER to be ready...")
    wait_for_tag_value(ec2, private_instance_dbmanager[0], "STATUS", "READY")
    print("Waiting for DB_WORKERS to be ready...")
    for instance in private_instance_dbworkers:
        wait_for_tag_value(ec2, instance[0], "STATUS", "READY")
    
    print("Downloading benchmarks from S3...")
    download_folder_from_s3(s3_client, config["s3_bucket_name"], config["benchmarks_s3_path"], config["benchmarks_download_local_path"])

    print("Waiting for PROXY to be ready...")
    wait_for_tag_value(ec2, private_instance_proxy[0], "STATUS", "READY")
    print("Waiting for Trusted-Host to be ready...")
    wait_for_tag_value(ec2, private_instance_trusted_host[0], "STATUS", "READY")
    print("Waiting for Gatekeeper to be ready...")
    wait_for_tag_value(ec2, public_instance_gatekeeper[0], "STATUS", "READY")

    print("=================================================================")
    print("All instances are ready!")
    print("Press any key to run benchmarks!")

    gatekeeper_instance = ec2.describe_instances(InstanceIds=[public_instance_gatekeeper[0]])['Reservations'][0]['Instances'][0]
    gatekeeper_public_ip = gatekeeper_instance['PublicIpAddress']
    print(f"Gatekeeper public IP: {gatekeeper_public_ip}")

    benchmarks_cluster(gatekeeper_public_ip, config["cluster_benchmark"]["wait_time_s"])
    db_instances_dict = {
        "db_manager": private_instance_dbmanager[0],
    }
    worker_id = 1
    for worker in private_instance_dbworkers:
        db_instances_dict[f"db_worker_{worker_id}"] = worker[0]
        worker_id += 1
    
    cloudwatch = boto3.client('cloudwatch',
                            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                            aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
                            region_name=default_region)
    
    current_time = datetime.datetime.now(datetime.timezone.utc)
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Current UTC time and date: {formatted_time}")
    
    print("Collecting stats from cloudwatch...")
    metrics = get_instance_metrics(
         db_instances_dict, 
         cloudwatch, 
         current_time - datetime.timedelta( seconds = config["cluster_benchmark"]["wait_time_s"] * 10), 
         current_time, 
         config["cluster_benchmark"]["period_s"], 
         True, True, True, True, False)
    plot_metrics(metrics, out_folder = config["benchmarks_download_local_path"])
    print(f"Stats collected and saved at {config["benchmarks_download_local_path"]}")



    input("Press any key to cleanup...")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    #cleanup ressources
    print("=================================================================")
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
    if private_instance_trusted_host:
            instances_to_clean_up.append(private_instance_trusted_host)
    if public_instance_gatekeeper:
            instances_to_clean_up.append(public_instance_gatekeeper)

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




