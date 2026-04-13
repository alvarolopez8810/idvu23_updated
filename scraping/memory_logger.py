"""
In-Memory Logger Handler
========================

Provides an in-memory logging handler for capturing log records during runtime.
Allows dumping logs to a file (using StorageManager for directory management)
and clearing the log buffer for modular logging sessions.

Author: Sports Data Campus - Lucas Bracamonte, Eduardo M. Pereira, Jaime Jimenez
Date: October 2025
"""

import os
import logging

from storage_manager import StorageManager


class InMemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def dump_to_file(self, storage_manager, log_dir, filename="session.log"):
        """
        Dumps the current log records to a file, using StorageManager for directory management.
        Supports both local and S3 storage.
        """
        storage_manager.ensure_directory(log_dir)
        log_path = os.path.join(log_dir, filename)
        log_content = "\n".join(self.records) + "\n"

        if storage_manager.storage_type == "local":
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            return log_path
        else:
            # For S3, upload the log as an object
            if not log_path.startswith("/"):
                key = log_path
            else:
                key = log_path.lstrip("/")
            storage_manager.s3_client.put_object(
                Bucket=storage_manager.s3_bucket,
                Key=key,
                Body=log_content.encode("utf-8")
            )
            return f"s3://{storage_manager.s3_bucket}/{key}"

    def clear(self):
        self.records.clear()