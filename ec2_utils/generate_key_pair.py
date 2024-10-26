import os
from pathlib import Path

# Generate a key pair
def generate_key_pair(ec2_client, key_pair_name, out_path = "temp"):
    key_pair_path = Path(os.path.join(out_path, f'{key_pair_name}.pem'))

    try:
        ec2_client.describe_key_pairs(KeyNames=[key_pair_name])
        if key_pair_path.exists():
            print(f"Key pair '{key_pair_name}' already exists.")
            return key_pair_path
        else:
            print(f"Key pair '{key_pair_name}' exists on EC2 but not locally. Recreating...")
    except ec2_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            if key_pair_path.exists():
                print(f"Key pair '{key_pair_name}' exists locally but not on EC2. Deleting local file...")
                key_pair_path.unlink()
        else:
            raise

    response = ec2_client.create_key_pair(KeyName=key_pair_name)
    # Save the private key to a file
    private_key = response['KeyMaterial']
    Path(out_path).mkdir(exist_ok=True)
    with open(key_pair_path, 'w') as key_file:
        key_file.write(private_key)

    print(f"Key pair '{key_pair_name}' has been created and saved to {key_pair_name}.pem")

    return key_pair_path