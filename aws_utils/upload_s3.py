
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
