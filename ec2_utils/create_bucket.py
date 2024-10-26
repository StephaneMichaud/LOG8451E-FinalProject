
import boto3

def create_bucket(bucket_name):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' created successfully.")
        return response
    except Exception as e:
        print(f"Error creating bucket '{bucket_name}': {str(e)}")
        return None
