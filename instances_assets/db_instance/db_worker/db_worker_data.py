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


aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:MY-SQL


sudo apt-get update && sudo apt-get upgrade -y

# Install MySQL
sudo apt-get install mysql-server mysql-client -y
sudo apt-get update && sudo apt-get upgrade -y
sudo mysql_secure_installation <<EOF

N
N
N
N
N
EOF

# Execute the script to install Sakila
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:Sakila
#   Download MySQL tar from the web
wget https://downloads.mysql.com/docs/sakila-db.tar.gz
#   Unzip the downloaded file
tar -xvzf sakila-db.tar.gz
sudo mysql -u root --password="" < sakila-db/sakila-schema.sql
sudo mysql -u root --password="" < sakila-db/sakila-data.sql



#run mysql benchmark
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:SQL-BENCHMARK
sudo apt-get install sysbench -y
sudo sysbench --test=oltp_read_write --table-size=10000 --mysql-db=sakila --mysql-user=root --mysql-password="" prepare
sudo sysbench oltp_read_write --table-size=10000 --mysql-db=sakila --db-driver=mysql --mysql-user=root --num-threads=6 --max-time=60 --max-requests=0 run > standaloneBenchmark-_$instance_id.txt
sudo sysbench oltp_read_write --table-size=10000 --mysql-db=sakila --db-driver=mysql --mysql-user=root cleanup
aws s3 cp standaloneBenchmark-_$instance_id.txt s3://{s3_bucket_name}/{benchmark_upload_path}/standaloneBenchmark_$instance_id.txt

#create user for fastapi app
sudo mysql -u root --password="" <<EOF
CREATE USER 'log8415e'@'localhost' IDENTIFIED BY 'log8415e';
GRANT ALL ON *.* TO 'log8415e'@'localhost';
FLUSH PRIVILEGES;
EOF



# Install Python and pip
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:PYTHON
sudo apt-get update -y
sudo apt-get install python3 python3-pip -y

# Install Python libraries
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=INSTALL:PYTHON-LIBS
aws s3 cp s3://{s3_bucket_name}/instances_assets/db_instance/db_worker/requirements.txt ./requirements.txt
sudo pip3 install -r requirements.txt


# Run flask application
aws ec2 create-tags --region {region} --resources $instance_id --tags Key=STATUS,Value=READY
aws s3 cp s3://{s3_bucket_name}/instances_assets/db_instance/db_worker/main.py ./main.py
sudo python3 main.py
"""

import os
def get_db_worker_data(s3_bucket_name, benchmark_upload_path):
    return DB_USER_DATA.format(
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN'),
        region = os.environ.get('AWS_DEFAULT_REGION'),
        s3_bucket_name = s3_bucket_name,
        benchmark_upload_path = benchmark_upload_path

    )