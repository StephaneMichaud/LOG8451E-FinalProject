DB_USER_DATA = """#!/bin/bash

# Update instance status
instance_id=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
region=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)




aws ec2 create-tags --region $region --resources $instance_id --tags Key=STATUS,Value=INSTALL:MY-SQL
sudo apt-get update && sudo apt-get upgrade -y

# Install MySQL
sudo apt-get install mysql-server
sudo mysql_secure_installation


# Download MySQL tar from the web
wget https://downloads.mysql.com/docs/sakila-db.tar.gz

# Unzip the downloaded file
tar -xvzf sakila-db.tar.gz

aws ec2 create-tags --region $region --resources $instance_id --tags Key=STATUS,Value=INSTALL:Sakila

# Execute the script to install Sakila
mysql -u root -p < sakila-db/sakila-schema.sql
mysql -u root -p < sakila-db/sakila-data.sql
aws ec2 create-tags --region $region --resources $instance_id --tags Key=STATUS,Value=INSTALL:PYTHON
# Install Python and pip
sudo apt-get update
sudo apt-get install python3 python3-pip -y

aws ec2 create-tags --region $region --resources $instance_id --tags Key=STATUS,Value=INSTALL:PYTHON-FASTAPI
sudo pip3 install fastapi uvicorn requests boto3 --break-system-packages

"""