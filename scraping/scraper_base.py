"""
Base Scraper
============

Provides a base class for all scraper classes, encapsulating common setup,
session management, headers, storage abstraction, and utility methods.

Author: Sports Data Campus - Lucas Bracamonte, Eduardo M. Pereira, Jaime Jimenez
Date: October 2025
"""

import os
import json
import time
import random
import logging
import requests
from typing import Optional

from utils import get_env_variable
from storage_manager import StorageManager


class BaseScraper:
    """
    Base class for all scraper classes, providing common setup and utilities.
    """

    def __init__(
        self, 
        base_url: str = "https://www.scoresway.com",
        storage_type: str = "local",
        s3_bucket: Optional[str] = None,
        data_dir: str = "data",
        schema_dir: str = "schema",
        log_dir: str = "logs",
        log_level: str = "INFO",
        verbose: bool = True
    ) -> None:
        self.base_url = base_url
        self.data_dir = data_dir
        self.schema_dir = schema_dir
        self.log_dir = log_dir
        self.log_level = log_level.upper()
        self.verbose = verbose

        if storage_type == "auto":
            storage_type = get_env_variable('STORAGE_TYPE', 'local')
        self.storage = StorageManager(storage_type=storage_type, s3_bucket=s3_bucket)

        # Ensure all managed directories exist using StorageManager
        self.storage.ensure_directory(self.data_dir)
        self.storage.ensure_directory(self.schema_dir)
        self.storage.ensure_directory(self.log_dir)

        # Setup logging (only for local storage, otherwise print to stdout)
        if self.storage.storage_type == "local":
            os.makedirs(self.log_dir, exist_ok=True)
            log_file = os.path.join(self.log_dir, "scraper.log")
            logging.basicConfig(
                filename=log_file,
                level=getattr(logging, self.log_level, logging.INFO),
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            self.logger = logging.getLogger()
            if self.verbose:
                print(f"[{self.__class__.__name__}] Logging to {log_file} at level {self.log_level}")
        else:
            # For S3 or other storage, fallback to stdout logging
            self.logger = logging.getLogger()
            if self.verbose:
                print(f"[{self.__class__.__name__}] Logging to STDOUT at level {self.log_level} (cloud mode)")

        # self.headers = {
        #     "Host": "www.scoresway.com",
        #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7",
        #     "Accept-Encoding": "gzip, deflate, br, zstd",
        #     "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        #     "Cache-Control": "no-cache",
        #     "Cookie": "ga=GA1.1.666883386.1751465023; OptanonAlertBoxClosed=2025-09-19T18:35:29.983Z; eupubconsent-v2=CQX_8fgQX_8fgAcABBESB8FsAP_gAEPgACiQLmtR_GbWlr-b73aftkeYxP9_hr7sQxBgbJk24FzLvW_JwXx2E5NAzatqIKmRIAu3TBIQNlHJDURVCgKIgVryDMaEyUoTNKJ6BkiFMRI2NYCFxvm4pjeQCY5vr99lc1mB-N7dr82dzyy6hHn3a5_2S1WJCdIYetDfv8ZBKT-9IEd_x8v4v4_F7pE2-eS1n_pGvp6D9-Yns_dBmx9_baffzPnrl_e7X_vf_n37v943H77v__f-7_-C5gAJhoVEEZZECIRKBhBAgAUFYQAUCAIAAEgaICAEwYFOQMAF1hMgBACgAGCAEAAIMAAQAACQAIRABQAQCAACAQKAAMACAICABgYAAwAWIgEAAIDoGKYEEAgWACRmVQaYEoACQQEtlQgkAwIK4QhFngEECImCgAABAAKAgAAeCwEJJASsSCALiCaAAAgAACiBAgRSNmAIKAzRaC8GT6MjTAMHzBMkpkGQBMEZGSbEJvwmHjkKIUEOQGxSzAAAA.f_wACHwAAAAA; OptanonConsent=isGpcEnabled=0&datestamp=Sat+Oct+04+2025+07%3A54%3A48+GMT-0300+(Argentina+Standard+Time)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=3aea9760-108d-4551-a221-5897ac42ce3e&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&groups=C0004%3A1%2CC0002%3A1%2CC0001%3A1%2CV2STACK42%3A1&intType=1&geolocation=AR%3BS&AwaitingReconsent=false; _ga_7T677PWWJ1=GS2.1.s1759575288$o13$g0$t1759575663$j60$l0$h0; _ga_SQ24F7Q7YW=GS2.1.s1759575288$o12$g0$t1759575663$j60$l0$h0; _ga_K2ECMCJBFQ=GS2.1.s1759575289$o12$g0$t1759575663$j60$l0$h0; ak_bmsc=2ECEC4E130BAC5B20F08F35A6089AD16~000000000000000000000000000000~YAAQ1fcSAj+I74CZAQAAs+Lhrh2YPxK77E7qLFZQQuUebu8S0QfESbLbXxUf+GBQYg1VDTAbYpqkpZDI8yGwzACCEALkrWskMm5uYnzHod+pAGWM63Wd809k9bgU465O9y1iGHBRyU6BYhpIDR58GC1IHZckBUKMfrOpX5vpxRhdZyxDbiNrqy8BQ7ZrpGZ2QRKsLZLEpg2ubVfna7Iq3j67+IQjyAD8niyPPvMGf1PEGrCLDyt0NW2D1Zpxxd2epGIhDmvYpYQScZmHTwWq8cQs5rzrfYV9GnYpmkDWxEJQBpO9qNcNd7fOy25RM/4ViEc6VfmL7jE4n4+5ojvrqfoOFTxAFNYimypmRem1BjLFWBy5Xeh8y1h9epVd+fUNt7knN3ZDMmZpouwku1fNUCjIgzbAilqHxc4ZfymZUpTu3Ls40cYHID9ZI797B0SuLaLlTyUErgXKBux+DRpL1ZD18Fw=",
        #     "Pragma": "no-cache",
        #     "Priority": "u=0, i",
        #     "Referer": "https://www.scoresway.com/en_GB/soccer/competitions",
        #     "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
        #     "sec-ch-ua-mobile": "?1",
        #     "sec-ch-ua-platform": "\"Android\"",
        #     "Sec-Fetch-Dest": "document",
        #     "Sec-Fetch-Mode": "navigate",
        #     "Sec-Fetch-Site": "same-origin",
        #     "Upgrade-Insecure-Requests": "1",
        #     "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
        # }

        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'es-ES,es;q=0.9',
            'priority': 'u=0, i',
            'referer': 'https://www.scoresway.com/en_GB/soccer/competitions',
            'cache-control': 'no-cache',  # Forzamos a que no use caché
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
            'Cookie': '_ga=GA1.1.558066127.1772281928; _ga_7T677PWWJ1=GS2.1.s1772309810$o3$g0$t1772309810$j60$l0$h0; ak_bmsc=F5884D48868D2B6961250D11D360A937~000000000000000000000000000000~YAAQHbsUAhMiNmKdAQAA3OrFgh8cWJBjQA6eQnP2nlysC4SdGfFCvaVJqMHV9oAY9C0X/4V4+i/Ge7+flQ2t4xTkQMmV0gqBzaVXJSXH6tq4ttHYHhkWuckZfBYpI7hxiiWr/DGYCPFwNfJAUAEhQzTCCuLSLL7fDSyePIsnOI4B8rnMwfWFjbKKbs7eId7XZyQWOF/kJ0biC3GU8Meogy/wyyX0hrb2CxUAftWhoxIp/oAPdPcCCrSUXMffssFEKv4nDRcIstzY8Qzk+qwfIRKCAi7KuuJc5qlbeJFY6ROCvadQ/vprdFqLHqYPvLbJg3Dgb+taZLCamBcAbrwBEt928Ht6gXMgc+KyYR65cy69broVosHtG/wCE+gbNnzndJrIyyybem9FkH/FcIBfbVJNoBJINViyDoO/Nb7ocamOXNFCwwlqYK3OK4fhJt2uebtPSVx97bqw7cr5e3e3fs8Gbov4cgnRUD5Xr28S80EBYK7E5xzfkOqXGCg=',
        }
        self.min_delay = 1.0
        self.max_delay = 3.0

        self._log(f"Initialized {self.__class__.__name__} with storage_type={storage_type}, data_dir={self.data_dir}, schema_dir={self.schema_dir}, log_dir={self.log_dir}")

    def set_delay_range(self, min_delay: float, max_delay: float) -> None:
        """
        Set the minimum and maximum delay (in seconds) for random sleep between requests.

        Args:
            min_delay (float): Minimum delay in seconds.
            max_delay (float): Maximum delay in seconds.
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._log(f"Set delay range: min_delay={min_delay}, max_delay={max_delay}")

    def random_sleep(self) -> None:
        """
        Sleep for a random duration between min_delay and max_delay seconds.
        """
        delay = random.uniform(self.min_delay, self.max_delay)
        self._log(f"Sleeping for {delay:.2f} seconds...", level="DEBUG")
        if self.verbose:
            print(f"[{self.__class__.__name__}] Sleeping for {delay:.2f} seconds...")
        time.sleep(delay)

    def _log(self, message: str, level: str = "INFO") -> None:
        """
        Internal logging helper.

        Args:
            message (str): Message to log.
            level (str): Logging level ('INFO', 'DEBUG', 'WARNING', 'ERROR').
        """
        if hasattr(self.logger, level.lower()):
            getattr(self.logger, level.lower())(message)
        else:
            self.logger.info(message)
        if self.verbose and level in ("INFO", "WARNING", "ERROR"):
            print(f"[{self.__class__.__name__}] {level}: {message}")