import boto3
def create_security_group(ec2, vpc_id, group_name, group_description):
    
    if vpc_id is None:
        vpc_id = ec2.describe_vpcs()['Vpcs'][0]['VpcId']
        
    security_group = ec2.create_security_group(
        GroupName=group_name,
        Description=group_description,
        VpcId=vpc_id
    )
    
    ec2.authorize_security_group_ingress(
        GroupId=security_group['GroupId'],
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}] #allow ssh
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Allow FastAPI
            },
        ]
    )
    print("Security group created successfully.")
    return security_group['GroupId']