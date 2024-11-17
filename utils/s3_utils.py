import boto3
from django.conf import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
)


def generate_presigned_url(key, expiration=86400):
    """
    Generates a pre-signed URL to access a file in S3 with an expiration time.

    :param key: The key (filename) of the file in S3.
    :param expiration: Time in seconds for the link to remain valid (default is 1 day).
    :return: The pre-signed URL as a string.
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f'Failed to generate pre-signed URL: {e}')
        return None


def upload_file_to_s3(file, key):
    """
    Uploads a file to the specified S3 bucket using the provided key.

    :param file: The file object to upload.
    :param key: The key (filename) to use in S3.
    :return: The URL of the uploaded file.
    """
    try:
        s3_client.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            key,
            ExtraArgs={'ContentType': file.content_type}
        )
        return generate_presigned_url(key)
    except Exception as e:
        print(f'Failed to upload file to S3: {e}')
        return None

def delete_file_from_s3(key):
    """
    Deletes a file from the specified S3 bucket using the provided key.

    :param key: The key (filename) of the file in S3 to delete.
    :return: True if the file was deleted successfully, False otherwise.
    """
    try:
        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )
        return True
    except Exception as e:
        print(f'Failed to delete file from S3: {e}')
        return False