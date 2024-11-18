import boto3
from django.conf import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
)


def generate_presigned_url(key, expiration=86400):
    try:
        # Check if the object exists
        s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        # Generate pre-signed URL if the object exists
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except s3_client.exceptions.ClientError as e:
        # If the error is '404 Not Found', the object does not exist
        if e.response['Error']['Code'] == '404':
            print(f'File with key {key} does not exist.')
            return None
        # Other errors
        print(f'Failed to generate pre-signed URL: {e}')
        return None


def upload_file_to_s3(file, key):
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
    try:
        response = s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )
        print("response: ", response)

        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key
        )
        return True
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f'File with key {key} does not exist.')
            return False

        print(f'Failed to delete file from S3: {e}')
        return False
