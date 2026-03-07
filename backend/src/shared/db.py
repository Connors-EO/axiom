import os

import boto3
import psycopg2


def get_connection() -> psycopg2.extensions.connection:
    secret_arn = os.environ["DB_SECRET_ARN"]
    sm_client = boto3.client(
        "secretsmanager",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    response = sm_client.get_secret_value(SecretId=secret_arn)
    password: str = response["SecretString"]

    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=password,
    )
