
import os

def upload_folder_to_s3(s3_client, bucket_name, path):
    """
    Upload a folder to the root of an S3 bucket.

    Args:
    path (str): Local path of the folder to upload.
    s3_client (boto3.client): Initialized S3 client.
    bucket_name (str): Name of the S3 bucket.
    """
    folder_name = os.path.basename(path)
    for root, dirs, files in os.walk(path):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, path)
            s3_path = relative_path.replace("\\", "/")  # Ensure forward slashes for S3 keys

            s3_client.upload_file(local_path, bucket_name, os.path.join(folder_name, s3_path))

    print(f"Folder upload complete: {path} -> s3://{bucket_name}/")

def download_folder_from_s3(s3_client, bucket_name, bucket_path, local_path):
    """
    Download a folder from an S3 bucket to the local filesystem.

    Args:
    s3_client (boto3.client): Initialized S3 client.
    bucket_name (str): Name of the S3 bucket.
    bucket_path (str): Path of the folder in the S3 bucket.
    local_path (str): Local path where the folder will be downloaded.
    """
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=bucket_path):
        for obj in page.get('Contents', []):
            s3_path = obj['Key']
            if not s3_path.endswith('/'):  # Skip folders
                relative_path = os.path.relpath(s3_path, bucket_path)
                local_file_path = os.path.join(local_path, relative_path)
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                s3_client.download_file(bucket_name, s3_path, local_file_path)

    print(f"Folder download complete: s3://{bucket_name}/{bucket_path} -> {local_path}")
