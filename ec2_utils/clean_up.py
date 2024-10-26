import os
import time

INSTANCE_DELETE_DELAY = 120

def terminate_instances(ec2, instance_ids):
    response = ec2.terminate_instances(InstanceIds=instance_ids)
    return response

def cleanup_vpc_and_nat(ec2, vpc_id):

    # Delete NAT Gateway
    nat_gateways = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    for nat_gateway in nat_gateways['NatGateways']:
        ec2.delete_nat_gateway(NatGatewayId=nat_gateway['NatGatewayId'])
        print(f"Deleting NAT Gateway: {nat_gateway['NatGatewayId']}")

    # Wait for NAT Gateway to be deleted
    print("Waiting for NAT Gateway to be deleted...")
    while True:
        nat_gateways = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NatGateways']
        if not nat_gateways:
            break
        
        active_nat_gateways = [ng for ng in nat_gateways if ng['State'] != 'deleted']
        if not active_nat_gateways:
            break
        
        print("NAT Gateway(s) still deleting. Waiting...")
        time.sleep(30)

    # Release Elastic IPs
    addresses = ec2.describe_addresses(Filters=[{'Name': 'domain', 'Values': ['vpc']}])
    for eip in addresses['Addresses']:
        if 'AssociationId' not in eip:
            ec2.release_address(AllocationId=eip['AllocationId'])
            print(f"Released Elastic IP: {eip['PublicIp']}")

    # Delete Subnets
    subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    for subnet in subnets['Subnets']:
        ec2.delete_subnet(SubnetId=subnet['SubnetId'])
        print(f"Deleted Subnet: {subnet['SubnetId']}")

    # Delete Route Tables
    route_tables = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    for rt in route_tables['RouteTables']:
        if not rt['Associations'] or not rt['Associations'][0]['Main']:
            ec2.delete_route_table(RouteTableId=rt['RouteTableId'])
            print(f"Deleted Route Table: {rt['RouteTableId']}")

    # Detach and Delete Internet Gateway
    igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
    for igw in igws['InternetGateways']:
        ec2.detach_internet_gateway(InternetGatewayId=igw['InternetGatewayId'], VpcId=vpc_id)
        ec2.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
        print(f"Deleted Internet Gateway: {igw['InternetGatewayId']}")

    # Delete VPC
    print("Waiting for all ressource to clean up before deleting VPC...")	
    time.sleep(30)
    ec2.delete_vpc(VpcId=vpc_id)
    print(f"Deleted VPC: {vpc_id}")

def delete_key_pair(ec2, key_name, local_key_path = "temp/temp.pem"):
    
    
    # Check for .pem files in the specified folder and delete them
    try:
        os.remove(local_key_path)
        print(f"Deleted local key file: {local_key_path}")
    except Exception as e:
        print(f"Error deleting {local_key_path}: {str(e)}")
    try:
        response = ec2.delete_key_pair(KeyName=key_name)
    except Exception as e:
        print(f"Could not find {key_name} in ec2")

    return response

def delete_security_group(ec2, group_id):
    response = ec2.delete_security_group(GroupId=group_id)
    return response


def delete_s3_bucket(s3_client, bucket_name):
    try:
        # Delete all objects in the bucket
        bucket = s3_client.Bucket(bucket_name)
        bucket.objects.all().delete()

        # Delete the bucket
        bucket.delete()

        print(f"Deleted S3 bucket: {bucket_name}")
    except Exception as e:
        print(f"Error deleting S3 bucket {bucket_name}: {str(e)}")


def clean_up_ressources(ec2, instance_ids, key_name, local_key_path, group_id, vpc_id, s3, bucket_name):
    if len(instance_ids) > 0: terminate_instances(ec2, [i[0] for i in instance_ids])
    time.sleep(INSTANCE_DELETE_DELAY)  # We wait to ensure instances are deleted
    delete_key_pair(ec2, key_name, local_key_path)
    time.sleep(60)  # Wait to ensure key pairs are deleted
    if group_id is not None: delete_security_group(ec2, group_id)  # Ensure instances are deleted before security group
    time.sleep(60)  # Wait to ensure security group are deleted
    if vpc_id is not None: cleanup_vpc_and_nat(ec2, vpc_id)
    print("Cleanup completed.")
    #delete_s3_bucket(s3, bucket_name=bucket_name)
