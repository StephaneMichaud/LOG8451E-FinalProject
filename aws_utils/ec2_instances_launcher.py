import time
"""Script to launch EC2 instances."""
def launch_ec2_instance(ec2, 
                    key_pair_name, 
                    security_group_id,
                    subnet_id,
                    instance_type:str = "t2.micro", 
                    num_instances:int = 1, 
                    image_id:str =  "ami-0e86e20dae9224db8",
                    public_ip:bool = False,
                    user_data = "",
                    tags:list[tuple[str,str]] = None,
                    enable_detailed_monitoring:bool = False,
                    ):
    # Create EC2 client
    # Specify instance parameters
    instance_params = {
        'ImageId': image_id, 
        'InstanceType': instance_type,
        'MinCount': num_instances,
        'MaxCount': num_instances,
        'KeyName': key_pair_name,
        'NetworkInterfaces': [{
            'AssociatePublicIpAddress': public_ip,
            'DeviceIndex': 0,
            'Groups': [security_group_id]
        }],
        'Monitoring': {'Enabled': enable_detailed_monitoring},
    }
    if subnet_id is not None:
        instance_params["NetworkInterfaces"][0]["SubnetId"] = subnet_id

    if tags is not None:
        tag_params = []
        for tag in tags:
            tag_params.append({"Key": tag[0], "Value": tag[1]})

        instance_params["TagSpecifications"] = [
            {"ResourceType": "instance", "Tags": tag_params}]

    # Launch the instance
    response = ec2.run_instances(UserData=user_data, **instance_params)

    # Get the instance ID
    instances_id_and_ip = []
    for instance in response['Instances']:
        instance_id = instance['InstanceId']
        if not public_ip:
            instances_id_and_ip.append((instance_id, instance["PrivateIpAddress"], None))
        else:
            instances_id_and_ip.append((instance_id, instance["PrivateIpAddress"], instance["PublicDnsName"]))

    # Wait for the instance to be running
    time.sleep(10)
    #ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
    print(f"Launched {num_instances} EC2 instances of type {instance_type} with ID and ip: {instances_id_and_ip}")

    return instances_id_and_ip