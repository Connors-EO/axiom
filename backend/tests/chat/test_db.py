import os
from unittest.mock import MagicMock, patch

from backend.src.shared.db import get_connection


def test_get_connection_reads_env_vars() -> None:
    env = {
        "DB_HOST": "myhost",
        "DB_PORT": "5433",
        "DB_NAME": "mydb",
        "DB_USER": "myuser",
        "DB_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123:secret:test",
    }
    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {"SecretString": "password123"}

    with (
        patch.dict(os.environ, env),
        patch("backend.src.shared.db.boto3.client", return_value=mock_sm),
        patch("backend.src.shared.db.psycopg2.connect") as mock_connect,
    ):
        get_connection()

    mock_connect.assert_called_once_with(
        host="myhost",
        port=5433,
        dbname="mydb",
        user="myuser",
        password="password123",
    )


def test_get_connection_secret_arn() -> None:
    secret_arn = "arn:aws:secretsmanager:us-east-1:289921858159:secret:axiom-staging-db-password"
    env = {
        "DB_HOST": "proxy.host",
        "DB_PORT": "5432",
        "DB_NAME": "axiom",
        "DB_USER": "axiom",
        "DB_SECRET_ARN": secret_arn,
    }
    mock_sm = MagicMock()
    mock_sm.get_secret_value.return_value = {"SecretString": "secretpass"}

    with (
        patch.dict(os.environ, env),
        patch("backend.src.shared.db.boto3.client", return_value=mock_sm),
        patch("backend.src.shared.db.psycopg2.connect"),
    ):
        get_connection()

    mock_sm.get_secret_value.assert_called_once_with(SecretId=secret_arn)
