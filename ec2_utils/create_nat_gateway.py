import time
def create_vpc_and_nat(ec2):
    
    # Create VPC
    public_subnet_id = None
    private_subnet_id = None
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    print(f"VPC created: {vpc_id}")
    try:
        # Create Internet Gateway
        igw = ec2.create_internet_gateway()
        igw_id = igw['InternetGateway']['InternetGatewayId']
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        print(f"Internet Gateway created and attached: {igw_id}")
        
        # Create public subnet
        public_subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
        public_subnet_id = public_subnet['Subnet']['SubnetId']
        print(f"Public subnet created: {public_subnet_id}")
        
        # Create and configure route table for public subnet
        public_route_table = ec2.create_route_table(VpcId=vpc_id)
        public_route_table_id = public_route_table['RouteTable']['RouteTableId']
        ec2.create_route(RouteTableId=public_route_table_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
        ec2.associate_route_table(RouteTableId=public_route_table_id, SubnetId=public_subnet_id)
        print(f"Public route table created and configured: {public_route_table_id}")
        
        # Create private subnet
        private_subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.2.0/24')
        private_subnet_id = private_subnet['Subnet']['SubnetId']
        print(f"Private subnet created: {private_subnet_id}")
        
        # Create NAT Gateway
        eip = ec2.allocate_address(Domain='vpc')
        nat_gateway = ec2.create_nat_gateway(AllocationId=eip['AllocationId'], SubnetId=public_subnet_id)
        nat_gateway_id = nat_gateway['NatGateway']['NatGatewayId']
        print(f"NAT Gateway created: {nat_gateway_id}")
        
        # Wait for NAT Gateway to be available
        print("Waiting for NAT Gateway to be available...")
        while True:
            nat_gateway_state = ec2.describe_nat_gateways(NatGatewayIds=[nat_gateway_id])['NatGateways'][0]['State']
            if nat_gateway_state == 'available':
                break
            time.sleep(10)
        
        # Create and configure route table for private subnet
        private_route_table = ec2.create_route_table(VpcId=vpc_id)
        private_route_table_id = private_route_table['RouteTable']['RouteTableId']
        ec2.create_route(RouteTableId=private_route_table_id, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gateway_id)
        ec2.associate_route_table(RouteTableId=private_route_table_id, SubnetId=private_subnet_id)
        print(f"Private route table created and configured: {private_route_table_id}")
    except  Exception as e:
        print(f"An error occurred: {e}")
    
    return vpc_id, public_subnet_id, private_subnet_id