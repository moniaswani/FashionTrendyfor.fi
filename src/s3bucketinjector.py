import os
import boto3
from botocore.exceptions import ClientError

# AWS config
bucket_name = "runwayimages"
region = "eu-west-2"  # change if needed

# Initialize S3 client
s3 = boto3.client("s3", region_name=region)

def file_exists_in_s3(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise

def upload_images_to_s3(local_base="images"):
    for root, dirs, files in os.walk(local_base):
        for filename in files:
            local_path = os.path.join(root, filename)

            # S3 key = folder structure after "images/"
            relative_path = os.path.relpath(local_path, local_base)
            s3_key = relative_path.replace("\\", "/")  # For Windows paths

            if file_exists_in_s3(bucket_name, s3_key):
                print(f"Skipped (already exists): {s3_key}")
                continue

            try:
                s3.upload_file(local_path, bucket_name, s3_key)
                print(f"Uploaded: {local_path} → s3://{bucket_name}/{s3_key}")
            except Exception as e:
                print(f"Error uploading {local_path}: {e}")

if __name__ == "__main__":
    upload_images_to_s3()
