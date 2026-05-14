import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    redis_url: str
    rabbitmq_url: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def sync_database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


def load_config() -> Config:
    return Config(
        bot_token=os.environ.get("BOT_TOKEN", ""),
        db_host=os.environ.get("DB_HOST", "localhost"),
        db_port=int(os.environ.get("DB_PORT", "5432")),
        db_user=os.environ.get("DB_USER", "postgres"),
        db_password=os.environ.get("DB_PASSWORD", "postgres"),
        db_name=os.environ.get("DB_NAME", "dating_bot"),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        rabbitmq_url=os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        s3_endpoint=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        s3_access_key=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        s3_secret_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        s3_bucket=os.environ.get("S3_BUCKET", "profiles"),
    )
