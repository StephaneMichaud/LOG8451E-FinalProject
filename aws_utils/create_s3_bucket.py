
import boto3
import time
from botocore.exceptions import ClientError

def create_s3_bucket(s3_client, bucket_name, region):
    """
    Create an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket_name: Bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :return: True if bucket created, else False
    """
    if region == "us-east-1": #do this or api fail https://stackoverflow.com/questions/31092056/how-to-create-a-s3-bucket-using-boto3
        s3_client.create_bucket(Bucket=bucket_name)
    else:
        location = {'LocationConstraint': region}
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration=location)
    
    waiter = s3_client.get_waiter('bucket_exists')
    waiter.wait(Bucket=bucket_name)
    time.sleep(10)


def delete_s3_bucket(s3_client, bucket_name):
    """
    Clean up and delete an S3 bucket

    :param s3_client: Boto3 S3 client
    :param bucket_name: Name of the bucket to delete
    :return: True if bucket deleted, else False
    """
    try:
        # Delete all objects in the bucket
        bucket = s3_client.Bucket(bucket_name)
        bucket.objects.all().delete()

        # Delete all versions if versioning is enabled
        bucket.object_versions.delete()

        # Delete the bucket
        bucket.delete()

        print(f"Bucket {bucket_name} has been deleted")
        return True
    except ClientError as e:
        print(f"Error deleting bucket {bucket_name}: {e}")
        return False

