import aioboto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        self.session = aioboto3.Session()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name

    async def init_bucket(self):
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket_name)
            except ClientError:
                await s3.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Bucket {self.bucket_name} created")

    async def upload_photo(self, user_id: int, photo_bytes: bytes, filename: str) -> str:
        key = f"user_{user_id}/{filename}"
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=photo_bytes,
                ContentType="image/jpeg"
            )
            return key

    async def get_photo_url(self, key: str) -> str:
        # For Minio in local dev, we might need a public URL or proxy
        # Here we just return the internal URL for simplicity or pre-signed URL
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=3600
            )
            return url
            
    async def download_photo(self, key: str) -> bytes:
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key)
            async with response["Body"] as stream:
                return await stream.read()
