import boto3
from django.conf import settings
from botocore.exceptions import ClientError

# Validate AWS settings
if not all([
    getattr(settings, 'AWS_ACCESS_KEY_ID', None),
    getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
    getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
]):
    raise ValueError(
        "AWS credentials not properly configured. Please ensure AWS_ACCESS_KEY_ID, "
        "AWS_SECRET_ACCESS_KEY, and AWS_STORAGE_BUCKET_NAME are set in settings."
    )

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def generate_presigned_url(key, expiration=86400):
    """
    Generate a presigned URL for an S3 object.

    Args:
        key (str): The S3 object key
        expiration (int): URL expiration time in seconds

    Returns:
        str or None: Presigned URL if successful, None otherwise
    """
    if not key:
        print("Error: Key cannot be empty")
        return None

    try:
        # Check if the object exists
        s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )

        # Generate pre-signed URL if the object exists
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=expiration,
        )
        return url

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')

        if error_code == "404":
            print(f"File with key {key} does not exist.")
        else:
            print(f"Failed to generate pre-signed URL: {e}")
        return None

    except Exception as e:
        print(f"Unexpected error generating presigned URL: {e}")
        return None


def upload_file_to_s3(file, key):
    """
    Upload a file to S3.

    Args:
        file: File object to upload
        key (str): The S3 object key

    Returns:
        str or None: Presigned URL if successful, None otherwise
    """
    if not file or not key:
        print("Error: Both file and key are required")
        return None

    try:
        s3_client.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": file.content_type},
        )
        return generate_presigned_url(key)

    except Exception as e:
        print(f"Failed to upload file to S3: {e}")
        return None


def delete_file_from_s3(key):
    """
    Delete a file from S3.

    Args:
        key (str): The S3 object key

    Returns:
        bool: True if successful, False otherwise
    """
    if not key:
        print("Error: Key cannot be empty")
        return False

    try:
        # Check if the object exists first
        s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )

        # Delete the object
        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )
        return True

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')

        if error_code == "404":
            print(f"File with key {key} does not exist.")
        else:
            print(f"Failed to delete file from S3: {e}")
        return False

    except Exception as e:
        print(f"Unexpected error deleting file: {e}")
        return False