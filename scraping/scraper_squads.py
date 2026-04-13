"""
Squads Scraper
==============

This module provides the ScraperSquads class for scraping squads (team rosters)
from the ScoresWay API, organizing and saving JSON data using a consistent
storage abstraction and modular, pythonic practices.

Author: Sports Data Campus
Date: October 2025
"""

import os
import json
import time
import random
import requests
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple

from urllib.parse import quote
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from scraper_base import BaseScraper
from storage_manager import StorageManager
from utils import (
    get_season_name_from_url,
    get_tournament_id,
    sanitize_dir_name,
    normalize_season_string,
    extend_dataframe_with_unique_rows
)

class ScraperSquads(BaseScraper):
    """
    Scraper for downloading squads (team rosters) from the ScoresWay API.
    Inherits from BaseScraper for session, logging, and storage management.
    """

    def __init__(
        self,
        sdapi_outlet_key: str = 'ft1tiv1inq7v1sk3y9tv12yh5',
        callback_id: str = 'W3e14cbc3e4b2577e854bf210e5a3c7028c7409678',
        base_url: str = "https://www.scoresway.com",
        storage_type: str = "local",
        s3_bucket: Optional[str] = None,
        data_dir: str = "data",
        schema_dir: str = "schema",
        log_dir: str = "logs",
        log_level: str = "INFO",
        verbose: bool = True,
    ) -> None:
        """
        Initialize the ScraperSquads.

        Args:
            sdapi_outlet_key (str): API outlet key.
            callback_id (str): Callback ID for JSONP.
            base_url (str): Base URL of the website.
            storage_type (str): Storage type ('local' or 's3').
            s3_bucket (Optional[str]): S3 bucket name if using S3.
            data_dir (str): Directory for data files.
            schema_dir (str): Directory for schema files.
            log_dir (str): Directory for logs.
            log_level (str): Logging level.
            verbose (bool): Verbose output.
        """
        super().__init__(
            base_url=base_url,
            storage_type=storage_type,
            s3_bucket=s3_bucket,
            data_dir=data_dir,
            schema_dir=schema_dir,
            log_dir=log_dir,
            log_level=log_level,
            verbose=verbose,
        )
        self.sdapi_outlet_key = sdapi_outlet_key
        self.callback_id = callback_id
        self.api_base_url = "https://api.performfeeds.com/soccerdata/squads"
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36'
        }
        self.session = self._create_session_with_retries()
        self.page_size = 50
        self.page_number = 1
        self.detailed = True
        self.reset_stats()

    def _create_session_with_retries(self) -> requests.Session:
        """
        Create a requests session with retry strategy.

        Returns:
            requests.Session: Configured session.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def set_api_credentials(self, sdapi_outlet_key: str, callback_id: str) -> None:
        """
        Update API credentials.

        Args:
            sdapi_outlet_key (str): New outlet key.
            callback_id (str): New callback ID.
        """
        self.sdapi_outlet_key = sdapi_outlet_key
        self.callback_id = callback_id
        self._log("API credentials updated.", "INFO")

    def set_pagination_config(self, page_size: int = 50, page_number: int = 1, detailed: bool = True) -> None:
        """
        Set pagination parameters for the API.

        Args:
            page_size (int): Number of items per page.
            page_number (int): Page number to fetch.
            detailed (bool): Whether to fetch detailed info.
        """
        self.page_size = page_size
        self.page_number = page_number
        self.detailed = detailed
        self._log(f"Pagination set: {page_size} per page, page {page_number}, detailed: {detailed}", "INFO")

    def reset_stats(self) -> None:
        """Reset download statistics."""
        self.success = 0
        self.errors = 0
        self.skipped = 0
        self.processed = 0

    def fetch_squads_json(self, tournament_id: str, competition_name: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch squads data from the API.

        Args:
            tournament_id (str): Tournament ID.
            competition_name (str): Competition name.
            referer (Optional[str]): Referer URL.

        Returns:
            Dict[str, Any]: Squads data as JSON.

        Raises:
            Exception: On request or parsing error.
        """
        try:
            if not referer:
                referer_base = f'{self.base_url}/en_GB/soccer/'
                safe_competition_name = quote(competition_name)
                referer = f"{referer_base}{safe_competition_name}/{tournament_id}/fixtures"

            api_url = (
                f"{self.api_base_url}/{self.sdapi_outlet_key}/"
                f"?_rt=c&tmcl={tournament_id}&_pgSz={self.page_size}&_pgNm={self.page_number}"
                f"&detailed={'yes' if self.detailed else 'no'}"
                f"&_lcl=en&_fmt=jsonp&sps=widgets&_clbk={self.callback_id}"
            )

            headers = self.headers.copy()
            headers['Referer'] = referer

            self._log(f"Requesting API URL: {api_url}", "INFO")
            response = self.session.get(api_url, headers=headers)
            response.raise_for_status()

            content = response.text
            json_start = content.find('(') + 1
            json_end = content.rfind(')')
            if json_start <= 0 or json_end <= json_start:
                raise Exception("Could not extract JSON from JSONP response.")

            squads_data = json.loads(content[json_start:json_end])
            return squads_data

        except requests.RequestException as e:
            raise Exception(f"Request error: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON parsing error: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")

    def save_squads_json(self, season_row: pd.Series, skip_existing: bool = True) -> Optional[Dict[str, Any]]:
        """
        Download and save squads JSON for a season.

        Args:
            season_row (pd.Series): Row from the seasons DataFrame.
            skip_existing (bool): Skip if file already exists.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        print(season_row)
        try:
            tournament_id = get_tournament_id(season_row['season_url'])
            if not tournament_id:
                self._log(f"Could not extract tournament_id from: {season_row['season_url']}", "WARNING")
                return False

            season_name = get_season_name_from_url(season_row['results_url'])
            if not season_name:
                self._log(f"Could not extract season_name from: {season_row['results_url']}", "WARNING")
                return False

            competition = str(season_row['competition']).replace('/', '_')
            continent_dir = sanitize_dir_name(season_row["continent"])
            country_dir = sanitize_dir_name(season_row["country"])
            competition_dir = sanitize_dir_name(season_row['competition'])
            competition_id = str(season_row['competition_id'])
            season_name = normalize_season_string(season_name)
            dir_path = os.path.join(
                self.data_dir,
                continent_dir,
                country_dir,
                competition_dir,
                competition_id,
                season_name
            )

            self.storage.ensure_directory(dir_path)
            json_path = os.path.join(dir_path, 'squads.json')

            if skip_existing and self.storage.file_exists(json_path):
                self._log(f"File already exists, skipping: {json_path}", "INFO")
                self.skipped += 1
                return True

            squads_data = self.fetch_squads_json(
                tournament_id=tournament_id,
                competition_name=competition,
                referer=season_row['season_url']
            )

            if self.storage.storage_type == 'local':
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(squads_data, f, ensure_ascii=False, indent=2)
                self._log(f"Squads saved: {json_path}", "INFO")
            else:
                json_str = json.dumps(squads_data, ensure_ascii=False, indent=2)
                self.storage.s3_client.put_object(
                    Bucket=self.storage.s3_bucket,
                    Key=json_path,
                    Body=json_str.encode('utf-8')
                )
                self._log(f"Squads saved to S3: s3://{self.storage.s3_bucket}/{json_path}", "INFO")

            self.success += 1
            self.random_sleep()
            return self._build_squad_summary(season_row, json_path, has_squads=True)

        except Exception as e:
            self._log(f"Error processing {season_row.get('season', 'N/A')}: {str(e)}", "ERROR")
            self.errors += 1
            return None
        
    def _build_squad_summary(self, season_row: pd.Series, file_path: str, has_squads: bool) -> Dict[str, Any]:
        return {
            'continent': season_row.get('continent'),
            'country': season_row.get('country'),
            'competition': season_row.get('competition'),
            'competition_id': season_row.get('competition_id'),
            'season': season_row.get('season'),
            'season_url': season_row.get('season_url'),
            'results_url': season_row.get('results_url'),
            'file_path': file_path,
            'has_squads': has_squads
        }

    def process_seasons(
        self,
        df_seasons: pd.DataFrame,
        filters: Optional[Dict[str, Any]] = None,
        skip_existing: bool = True,
        start_index: int = 0,
        limit: Optional[int] = None,
        save_consolidated: bool = True,
        consolidated_filename: str = "all_squads.csv"
    ) -> Dict[str, Any]:
        """
        Process multiple seasons to download squads.

        Args:
            df_seasons (pd.DataFrame): DataFrame with seasons.
            filters (Optional[Dict[str, Any]]): Filters to apply.
            skip_existing (bool): Skip existing files.
            start_index (int): Start index.
            limit (Optional[int]): Limit of seasons to process.

        Returns:
            Dict[str, Any]: Processing statistics.
        """
        self.reset_stats()
        start_time = time.time()
        df_filtered = self._apply_filters(df_seasons, filters)
        end_index = len(df_filtered)
        if limit:
            end_index = min(start_index + limit, end_index)
        df_to_process = df_filtered.iloc[start_index:end_index]

        self._log(f"Starting squads download: {len(df_to_process)} seasons", "INFO")
        stats = {
            'total_seasons': len(df_to_process),
            'processed': 0,
            'success': 0,
            'skipped': 0,
            'errors': 0,
            'start_time': start_time
        }
        all_squads: List[Dict[str, Any]] = []

        for idx, (_, row) in enumerate(df_to_process.iterrows()):
            try:
                self._log(f"Processing {idx + 1}/{len(df_to_process)}: {row.get('competition', 'N/A')} - {row.get('season', 'N/A')}", "INFO")
                summary = self.save_squads_json(row, skip_existing)
                self.processed += 1
                stats['processed'] += 1
                if summary:
                    all_squads.append(summary)
                    if skip_existing and self.storage.file_exists(self._get_json_path(row)):
                        stats['skipped'] += 1
                    else:
                        stats['success'] += 1
                else:
                    stats['errors'] += 1
                if (idx + 1) % 10 == 0:
                    self._print_progress(stats, idx + 1, len(df_to_process))
            except KeyboardInterrupt:
                self._log("Processing interrupted by user.", "WARNING")
                break
            except Exception as e:
                self._log(f"Unexpected error in season {idx}: {e}", "ERROR")
                stats['errors'] += 1

        stats['duration'] = time.time() - stats['start_time']
        self._print_final_summary(stats)

        # Save consolidated CSV
        if save_consolidated and all_squads:
            df_squads = pd.DataFrame(all_squads)
            self.save_squads_dataframe(df_squads, filename=consolidated_filename)

        return stats

    def _apply_filters(self, df: pd.DataFrame, filters: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply filters to the seasons DataFrame.

        Args:
            df (pd.DataFrame): Original DataFrame.
            filters (Optional[Dict[str, Any]]): Filters to apply.

        Returns:
            pd.DataFrame: Filtered DataFrame.
        """
        if not filters:
            return df
        df_filtered = df.copy()
        for column, value in filters.items():
            if column in df_filtered.columns:
                if isinstance(value, list):
                    df_filtered = df_filtered[df_filtered[column].isin(value)]
                else:
                    df_filtered = df_filtered[df_filtered[column] == value]
                self._log(f"Filter applied - {column}: {value} → {len(df_filtered)} seasons", "INFO")
        return df_filtered

    def _get_json_path(self, row: pd.Series) -> str:
        """
        Build the JSON file path for a season.

        Args:
            row (pd.Series): Season row.

        Returns:
            str: JSON file path.
        """
        season_name = get_season_name_from_url(row['results_url'])
        continent_dir = sanitize_dir_name(row["continent"])
        country_dir = sanitize_dir_name(row["country"])
        competition_dir = sanitize_dir_name(row['competition'])
        competition_id = str(row['competition_id'])
        season_name = normalize_season_string(season_name)
        return os.path.join(
            self.data_dir,
            continent_dir,
            country_dir,
            competition_dir,
            competition_id,
            season_name,
            'squads.json'
        )

    def _print_progress(self, stats: Dict[str, Any], current: int, total: int) -> None:
        """
        Print processing progress.

        Args:
            stats (Dict[str, Any]): Statistics.
            current (int): Current index.
            total (int): Total count.
        """
        elapsed = time.time() - stats['start_time']
        rate = current / elapsed if elapsed > 0 else 0
        self._log(
            f"Progress: {current}/{total} ({current/total*100:.1f}%) | "
            f"Speed: {rate:.2f} seasons/min | "
            f"Success: {stats['success']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}",
            "INFO"
        )

    def _print_final_summary(self, stats: Dict[str, Any]) -> None:
        """
        Print final processing summary.

        Args:
            stats (Dict[str, Any]): Statistics.
        """
        self._log("="*50, "INFO")
        self._log("FINAL SUMMARY", "INFO")
        self._log("="*50, "INFO")
        self._log(f"Total time: {stats['duration']:.1f} seconds", "INFO")
        self._log(f"Seasons processed: {stats['processed']}/{stats['total_seasons']}", "INFO")
        self._log(f"Success: {stats['success']}", "INFO")
        self._log(f"Skipped (already existed): {stats['skipped']}", "INFO")
        self._log(f"Errors: {stats['errors']}", "INFO")
        if stats['duration'] > 0:
            rate = stats['processed'] / (stats['duration'] / 60)
            self._log(f"Average speed: {rate:.2f} seasons/minute", "INFO")

    def save_squads_dataframe(
        self,
        df_squads: pd.DataFrame,
        filename: str = "all_squads.csv"
    ) -> str:
        filepath = os.path.join(self.schema_dir, filename)
        self.storage.ensure_directory(self.schema_dir)
        df_extended = extend_dataframe_with_unique_rows(self.storage, df_squads, filepath)
        self.storage.save_dataframe_csv(df_extended, filepath)
        self._log(f"Squads summary saved to: {filepath}", "INFO")
        return filepath


# -----------------------------------------------------------
# ------------------ Convenience functions ------------------
# -----------------------------------------------------------
def download_squads_by_filters(
    df_seasons: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    skip_existing: bool = True,
    start_index: int = 0,
    limit: Optional[int] = None,
    page_size: int = 50,
    detailed: bool = True,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    save_consolidated: bool = True,
    consolidated_filename: str = "all_squads.csv",
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Download squads applying common filters.

    Args:
        df_seasons (pd.DataFrame): Seasons DataFrame.
        continent (Optional[str]): Filter by continent.
        country (Optional[str]): Filter by country.
        competition (Optional[str]): Filter by competition.
        skip_existing (bool): Skip existing files.
        start_index (int): Start index.
        limit (Optional[int]): Limit of seasons to process.
        page_size (int): API page size.
        detailed (bool): Fetch detailed info.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScraperSquads.

    Returns:
        Dict[str, Any]: Processing statistics.
    """
    filters = {}
    if continent:
        filters['continent'] = continent
    if country:
        filters['country'] = country
    if competition:
        filters['competition'] = competition

    scraper = ScraperSquads(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    scraper.set_pagination_config(page_size=page_size, detailed=detailed)
    return scraper.process_seasons(
        df_seasons,
        filters=filters,
        skip_existing=skip_existing,
        start_index=start_index,
        limit=limit,
        save_consolidated=save_consolidated,
        consolidated_filename=consolidated_filename
    )

def find_squads_resume_index(
    df_seasons: pd.DataFrame,
    filters: Optional[Dict[str, Any]] = None,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None
) -> int:
    """
    Find the index from which to resume squads downloading based on already processed seasons.

    Args:
        df_seasons (pd.DataFrame): DataFrame with seasons.
        filters (Optional[Dict[str, Any]]): Filters to apply.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        int: Index to resume from.
    """
    scraper = ScraperSquads(storage_type=storage_type, s3_bucket=s3_bucket)
    df_filtered = scraper._apply_filters(df_seasons, filters) if filters else df_seasons

    for idx, row in df_filtered.iterrows():
        json_path = scraper._get_json_path(row)
        if not scraper.storage.file_exists(json_path):
            scraper._log(f"Resume point found at index {idx}: {row.get('competition', 'N/A')} - {row.get('season', 'N/A')}", "INFO")
            return idx
    scraper._log("All squads already processed", "INFO")
    return len(df_filtered)

def smart_download_squads(
    df_seasons: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    restart_from_zero: bool = False,
    batch_size: int = 100,
    page_size: int = 50,
    detailed: bool = True,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    save_consolidated: bool = True,
    consolidated_filename: str = "all_squads.csv",
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Smart function to automatically detect whether to continue or start from scratch for squads downloading.

    Args:
        df_seasons (pd.DataFrame): Seasons DataFrame.
        continent (Optional[str]): Filter by continent.
        country (Optional[str]): Filter by country.
        competition (Optional[str]): Filter by competition.
        restart_from_zero (bool): If True, deletes existing data and starts from scratch.
        batch_size (int): Number of seasons to process in this batch.
        page_size (int): API page size.
        detailed (bool): Fetch detailed info.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScraperSquads.

    Returns:
        Dict[str, Any]: Processing statistics.
    """
    filters = {}
    if continent:
        filters['continent'] = continent
    if country:
        filters['country'] = country
    if competition:
        filters['competition'] = competition

    scraper = ScraperSquads(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    scraper.set_pagination_config(page_size=page_size, detailed=detailed)
    df_filtered = scraper._apply_filters(df_seasons, filters) if filters else df_seasons

    print(f"🎯 Applied filters: {filters if filters else 'None'}")
    print(f"📋 Seasons to process: {len(df_filtered)}")

    if batch_size is None:
        batch_size = len(df_filtered)

    if restart_from_zero:
        print("🔥 Restart mode: Deleting existing squads...")
        # Efficiently delete all squads.json files in the filtered set
        deleted_count = 0
        if scraper.storage.storage_type == 'local':
            import glob
            for _, row in df_filtered.iterrows():
                json_path = scraper._get_json_path(row)
                if os.path.exists(json_path):
                    try:
                        os.remove(json_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"[WARNING] Could not delete {json_path}: {e}")
        else:
            # S3: batch delete
            keys_to_delete = []
            for _, row in df_filtered.iterrows():
                json_path = scraper._get_json_path(row)
                keys_to_delete.append({'Key': json_path})
            if keys_to_delete:
                for i in range(0, len(keys_to_delete), 1000):
                    batch = keys_to_delete[i:i+1000]
                    scraper.storage.s3_client.delete_objects(
                        Bucket=scraper.storage.s3_bucket,
                        Delete={'Objects': batch}
                    )
                deleted_count = len(keys_to_delete)
        # Also remove the global CSV if present
        csv_path = os.path.join(scraper.schema_dir, consolidated_filename)
        if scraper.storage.file_exists(csv_path):
            if scraper.storage.storage_type == 'local':
                os.remove(csv_path)
            else:
                scraper.storage.s3_client.delete_object(Bucket=scraper.storage.s3_bucket, Key=csv_path)
            print(f"🗑️  Deleted global squads CSV: {csv_path}")
        print(f"🗑️  Deleted {deleted_count} existing squads")
        start_index = 0
    else:
        start_index = find_squads_resume_index(df_seasons, filters, storage_type, s3_bucket)
        if start_index >= len(df_filtered):
            print("✅ All squads already downloaded")
            existing_count = sum(
                scraper.storage.file_exists(scraper._get_json_path(row))
                for _, row in df_filtered.iterrows()
            )
            return {
                'total_seasons': len(df_filtered),
                'processed': len(df_filtered),
                'success': existing_count,
                'skipped': existing_count,
                'errors': len(df_filtered) - existing_count,
                'duration': 0,
                'progress': {
                    'processed_seasons': len(df_filtered),
                    'total_seasons': len(df_filtered),
                    'percentage': 100.0
                }
            }

    print(f"🚀 Starting download from season {start_index + 1}/{len(df_filtered)}")

    stats = download_squads_by_filters(
        df_seasons,
        continent=continent,
        country=country,
        competition=competition,
        skip_existing=not restart_from_zero,
        start_index=start_index,
        limit=batch_size,
        page_size=page_size,
        detailed=detailed,
        storage_type=storage_type,
        s3_bucket=s3_bucket,
        save_consolidated=save_consolidated,
        consolidated_filename=consolidated_filename,
        **scraper_kwargs
    )

    if 'progress' not in stats:
        stats['progress'] = {}

    stats['progress'].update({
        'processed_seasons': min(start_index + batch_size, len(df_filtered)),
        'total_seasons': len(df_filtered),
        'percentage': (min(start_index + batch_size, len(df_filtered)) / len(df_filtered)) * 100
    })

    print(f"\n📈 Total progress: {stats['progress']['processed_seasons']}/{stats['progress']['total_seasons']} ({stats['progress']['percentage']:.1f}%)")

    return stats

def load_existing_squads(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    squads_glob: str = '**/squads.json',
    filters: Optional[Dict[str, Any]] = None,
    consolidated_filename: str = "all_squads.csv"
) -> pd.DataFrame:
    """
    Load all existing squads from the global CSV if present, otherwise fallback to scanning all squads.json files.

    Args:
        storage_type (str): 'local' or 's3'.
        s3_bucket (Optional[str]): S3 bucket name.
        squads_glob (str): Glob pattern for squads.json files.
        filters (Optional[Dict[str, Any]]): Filters to apply.
        consolidated_filename (str): Name of the global CSV file.

    Returns:
        pd.DataFrame: DataFrame with all squads found.
    """
    scraper = ScraperSquads(storage_type=storage_type, s3_bucket=s3_bucket)
    csv_path = os.path.join(scraper.schema_dir, consolidated_filename)
    try:
        df_squads = scraper.storage.load_dataframe_csv(csv_path)
        scraper._log(f"Loaded squads summary from: {csv_path}", "INFO")
    except Exception:
        # Fallback: scan all squads.json files
        print("[INFO] Falling back to scanning all squads.json files...")
        squads_list = []
        if storage_type == 'local':
            import glob
            base_dir = scraper.data_dir
            pattern = os.path.join(base_dir, squads_glob)
            for json_file in glob.glob(pattern, recursive=True):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Try to reconstruct summary info from path and JSON
                        path_parts = json_file.split(os.sep)
                        if len(path_parts) >= 7:
                            continent = path_parts[-7]
                            country = path_parts[-6]
                            competition = path_parts[-5]
                            competition_id = path_parts[-4]
                            season = path_parts[-3]
                        else:
                            continent = country = competition = competition_id = season = None
                        squads_list.append({
                            'continent': continent,
                            'country': country,
                            'competition': competition,
                            'competition_id': competition_id,
                            'season': season,
                            'file_path': json_file,
                            'has_squads': True
                        })
                except Exception as e:
                    print(f"⚠️  Error reading {json_file}: {e}")
        else:
            paginator = scraper.storage.s3_client.get_paginator('list_objects_v2')
            prefix = f"{scraper.data_dir}/"
            for page in paginator.paginate(Bucket=scraper.storage.s3_bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('squads.json'):
                        try:
                            response = scraper.storage.s3_client.get_object(Bucket=scraper.storage.s3_bucket, Key=key)
                            content = response['Body'].read().decode('utf-8')
                            # Try to reconstruct summary info from path and JSON
                            path_parts = key.split('/')
                            if len(path_parts) >= 7:
                                continent = path_parts[-7]
                                country = path_parts[-6]
                                competition = path_parts[-5]
                                competition_id = path_parts[-4]
                                season = path_parts[-3]
                            else:
                                continent = country = competition = competition_id = season = None
                            squads_list.append({
                                'continent': continent,
                                'country': country,
                                'competition': competition,
                                'competition_id': competition_id,
                                'season': season,
                                'file_path': key,
                                'has_squads': True
                            })
                        except Exception as e:
                            print(f"⚠️  Error reading {key}: {e}")

        df_squads = pd.DataFrame(squads_list)
        # Save fallback as global CSV for future use
        if not df_squads.empty:
            scraper.save_squads_dataframe(df_squads, filename=consolidated_filename)

    if filters and not df_squads.empty:
        for col, val in filters.items():
            if col in df_squads.columns:
                if isinstance(val, list):
                    df_squads = df_squads[df_squads[col].isin(val)]
                else:
                    df_squads = df_squads[df_squads[col] == val]
    return df_squads


def save_squads_dataframe(
    df_squads: pd.DataFrame,
    filename: str = "all_squads.csv",
    storage_type: str = "local",
    s3_bucket: Optional[str] = None
) -> str:
    """
    Save the squads DataFrame to CSV in the schema directory.

    Args:
        df_squads (pd.DataFrame): Squads DataFrame.
        filename (str): CSV filename.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        str: Path to saved file.
    """
    scraper = ScraperSquads(storage_type=storage_type, s3_bucket=s3_bucket)
    filepath = os.path.join(scraper.schema_dir, filename)
    df_extended = extend_dataframe_with_unique_rows(scraper.storage, df_squads, filepath)
    scraper.storage.save_dataframe_csv(df_extended, filepath)
    scraper._log(f"Squads saved to: {filepath}", "INFO")
    return filepath

# -----------------------------------------------------------
# ------------------ Testing functions ----------------------
# -----------------------------------------------------------
def test_scraper_squads() -> bool:
    """
    Test function for ScraperSquads.

    Returns:
        bool: True if test passes, False otherwise.
    """
    print("=== Testing ScraperSquads ===")
    try:
        from scraper_seasons import load_existing_seasons
        for storage_type in ["local"]:
            print(f"\nTesting with storage: {storage_type.upper()}")
            s3_bucket = None
            df_seasons = load_existing_seasons(storage_type=storage_type, s3_bucket=s3_bucket)
            print(f"Loaded seasons: {len(df_seasons)}")
            stats = download_squads_by_filters(
                df_seasons,
                country='Argentina',
                skip_existing=True,
                start_index=0,
                limit=2,
                page_size=25,
                detailed=True,
                storage_type=storage_type,
                s3_bucket=s3_bucket
            )
            print(f"\nTest result ({storage_type}):")
            print(f"Processed: {stats['processed']}")
            print(f"Success: {stats['success']}")
            print(f"Skipped: {stats['skipped']}")
            print(f"Errors: {stats['errors']}")
        return stats['errors'] == 0
    except Exception as e:
        print(f"Test error: {e}")
        return False

if __name__ == "__main__":
    test_scraper_squads()