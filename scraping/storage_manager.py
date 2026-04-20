"""
Storage Manager
==============

Abstraction for storage operations supporting both local filesystem and S3.

Author: Sports Data Campus - Lucas Bracamonte, Eduardo M. Pereira, Jaime Jimenez
Date: October 2025
"""

import os
import io
import boto3
import pandas as pd
from typing import Optional, Union
from botocore.exceptions import ClientError
from utils import get_aws_credentials


class StorageManager:
    """
    Storage manager supporting operations on local filesystem and Amazon S3.
    """

    def __init__(self, storage_type: str = "local", s3_bucket: Optional[str] = None) -> None:
        """
        Initialize the storage manager.

        Args:
            storage_type (str): Type of storage ('local' or 's3').
            s3_bucket (Optional[str]): S3 bucket name (optional, uses AWS_BUCKET env if not provided).

        Raises:
            ValueError: If storage_type is invalid or S3 bucket is missing in S3 mode.
        """
        self.storage_type: str = storage_type.lower()

        if self.storage_type not in ("local", "s3"):
            raise ValueError("storage_type must be 'local' or 's3'.")

        self.s3_bucket: Optional[str] = None
        self.s3_client: Optional[boto3.client] = None

        if self.storage_type == "s3":
            aws_creds = get_aws_credentials()
            bucket = s3_bucket or aws_creds["bucket"]

            if bucket and bucket.startswith("arn:aws:s3:::"):
                bucket = bucket.split(":", 5)[-1]
            self.s3_bucket = bucket

            if not self.s3_bucket:
                raise ValueError("S3 bucket is required for 's3' storage mode.")

            if aws_creds["access_key"] and aws_creds["secret_key"]:
                self.s3_client = boto3.client(
                    "s3",
                    region_name=aws_creds["region"],
                    aws_access_key_id=aws_creds["access_key"],
                    aws_secret_access_key=aws_creds["secret_key"],
                )
            else:
                self.s3_client = boto3.client("s3")

            print(f"✅ StorageManager initialized in S3 mode with bucket: {self.s3_bucket}")

    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            file_path (str): Path to the file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        if self.storage_type == "local":
            return os.path.exists(file_path)
        else:
            assert self.s3_client is not None
            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=file_path)
                return True
            except ClientError:
                return False

    def ensure_directory(self, dir_path: str) -> None:
        """
        Ensure a directory exists.

        Args:
            dir_path (str): Path to the directory.
        """
        if self.storage_type == "local":
            os.makedirs(dir_path, exist_ok=True)
        else:
            # S3 does not require explicit directory creation,
            # but we can create an empty object to simulate a directory.
            if not dir_path.endswith("/"):
                dir_path += "/"
            if not self.file_exists(dir_path):
                assert self.s3_client is not None
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=dir_path,
                    Body=""
                )

    def save_dataframe_csv(self, df: pd.DataFrame, file_path: str) -> str:
        """
        Save a DataFrame as a CSV file.

        Args:
            df (pd.DataFrame): DataFrame to save.
            file_path (str): Path where to save the CSV.

        Returns:
            str: Full path where the file was saved.
        """
        if self.storage_type == "local":
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            df.to_csv(file_path, index=False)
            return file_path
        else:
            assert self.s3_client is not None
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=file_path,
                Body=csv_buffer.getvalue()
            )
            return f"s3://{self.s3_bucket}/{file_path}"

    def load_dataframe_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load a DataFrame from a CSV file.

        Args:
            file_path (str): Path to the CSV file.

        Returns:
            pd.DataFrame: Loaded DataFrame.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if self.storage_type == "local":
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            return pd.read_csv(file_path)
        else:
            assert self.s3_client is not None
            try:
                obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=file_path)
                return pd.read_csv(io.BytesIO(obj["Body"].read()))
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise FileNotFoundError(f"File not found in S3: {file_path}")
                raise