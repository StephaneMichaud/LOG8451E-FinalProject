DB_USER_DATA = """#!/bin/bash
cd /home/ubuntu
# Update instance status
sudo snap install aws-cli --classic
sudo apt install amazon-ec2-utils -y

instance_id=$(ec2metadata --instance-id)
aws configure set aws_access_key_id {aws_access_key_id}
aws configure set aws_secret_access_key {aws_secret_access_key}
aws configure set aws_session_token {aws_session_token}
aws configure set region {region}

# Save AWS credentials in .env format
cat << EOF > .env
AWS_ACCESS_KEY_ID={aws_access_key_id}
AWS_SECRET_ACCESS_KEY={aws_secret_access_key}
AWS_SESSION_TOKEN={aws_session_token}
AWS_DEFAULT_REGION={region}
EOF

sudo apt-get update && sudo apt-get upgrade -y

# Install Python and pip
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:PYTHON
sudo apt-get update -y
sudo apt-get install python3 python3-pip -y

# Install Python libraries
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:PYTHON-LIBS
aws s3 cp s3://{s3_bucket_name}/instances_assets/proxy/requirements.txt ./requirements.txt
sudo pip3 install -r requirements.txt


# Run flask
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=READY
aws s3 cp s3://{s3_bucket_name}/instances_assets/proxy/main.py ./main.py
sudo python3 main.py
"""

import os
def get_proxy_data(s3_bucket_name):
    return DB_USER_DATA.format(
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
        region = os.environ.get('AWS_DEFAULT_REGION'),
        s3_bucket_name = s3_bucket_name,

    )