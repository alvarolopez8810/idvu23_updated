"""
Fixture Scraper
===============

This module provides the ScraperFixture class for scraping sports fixtures
from the ScoresWay API, organizing and saving JSON data using a consistent
storage abstraction.

Author: Sports Data Campus - Lucas Bracamonte, Eduardo M. Pereira, Jaime Jimenez
Date: October 2025
"""

import os
import glob
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


class ScraperFixture(BaseScraper):
    """
    Scraper for downloading sports fixtures from the ScoresWay API.
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
        Initialize the ScraperFixture.

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
        self.api_base_url = "https://api.performfeeds.com/soccerdata/match"
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36'
        }
        self.session = self._create_session_with_retries()        

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
            status_forcelist=[500, 502, 503, 504, 429]
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

    def set_delay_range(self, min_delay: float, max_delay: float) -> None:
        """
        Set the delay range between requests.

        Args:
            min_delay (float): Minimum delay in seconds.
            max_delay (float): Maximum delay in seconds.
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._log(f"Delay range set: {min_delay}-{max_delay} seconds", "INFO")

    def fetch_fixture_json(self, tournament_id: str, competition_name: str, referer: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch fixture data from the API.

        Args:
            tournament_id (str): Tournament ID.
            competition_name (str): Competition name.
            referer (Optional[str]): Referer URL.

        Returns:
            Dict[str, Any]: Fixture data as JSON.

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
                f"?_rt=c&tmcl={tournament_id}&live=yes&_pgSz=400&_lcl=en&_fmt=jsonp"
                f"&sps=widgets&_clbk={self.callback_id}"
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

            fixture_data = json.loads(content[json_start:json_end])
            return fixture_data

        except requests.RequestException as e:
            raise Exception(f"Request error: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON parsing error: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")

    def save_fixture_json(self, season_row: pd.Series, skip_existing: bool = True) -> bool:
        """
        Download and save fixture JSON for a season.

        Args:
            season_row (pd.Series): Row from the seasons DataFrame.
            skip_existing (bool): Skip if file already exists.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
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
            json_path = os.path.join(dir_path, 'fixture.json')

            if skip_existing and self.storage.file_exists(json_path):
                self._log(f"File already exists, skipping: {json_path}", "INFO")
                return True

            fixture_data = self.fetch_fixture_json(
                tournament_id=tournament_id,
                competition_name=competition,
                referer=season_row['season_url']
            )

            if self.storage.storage_type == 'local':
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(fixture_data, f, ensure_ascii=False, indent=2)
                self._log(f"Fixture saved: {json_path}", "INFO")
            else:
                json_str = json.dumps(fixture_data, ensure_ascii=False, indent=2)
                self.storage.s3_client.put_object(
                    Bucket=self.storage.s3_bucket,
                    Key=json_path,
                    Body=json_str.encode('utf-8')
                )
                self._log(f"Fixture saved to S3: s3://{self.storage.s3_bucket}/{json_path}", "INFO")

            self.random_sleep()
            return True

        except Exception as e:
            self._log(f"Error processing {season_row.get('season', 'N/A')}: {str(e)}", "ERROR")
            return False

    def process_seasons(
        self,
        df_seasons: pd.DataFrame,
        filters: Optional[Dict[str, Any]] = None,
        skip_existing: bool = True,
        start_index: int = 0,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process multiple seasons to download fixtures.

        Args:
            df_seasons (pd.DataFrame): DataFrame with seasons.
            filters (Optional[Dict[str, Any]]): Filters to apply.
            skip_existing (bool): Skip existing files.
            start_index (int): Start index.
            limit (Optional[int]): Limit of seasons to process.

        Returns:
            Dict[str, Any]: Processing statistics.
        """
        try:
            df_filtered = self._apply_filters(df_seasons, filters)
            end_index = len(df_filtered)
            if limit:
                end_index = min(start_index + limit, end_index)
            df_to_process = df_filtered.iloc[start_index:end_index]

            self._log(f"Starting fixture download: {len(df_to_process)} seasons", "INFO")
            stats = {
                'total_seasons': len(df_to_process),
                'processed': 0,
                'success': 0,
                'skipped': 0,
                'errors': 0,
                'start_time': time.time()
            }

            for idx, (_, row) in enumerate(df_to_process.iterrows()):
                try:
                    self._log(f"Processing {idx + 1}/{len(df_to_process)}: {row.get('competition', 'N/A')} - {row.get('season', 'N/A')}", "INFO")
                    result = self.save_fixture_json(row, skip_existing)
                    stats['processed'] += 1
                    if result:
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
            return stats

        except Exception as e:
            self._log(f"Processing error: {e}", "ERROR")
            raise

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
        competition_dir = f"{sanitize_dir_name(row['competition'])}"
        competition_id = str(row['competition_id'])
        season_name = normalize_season_string(season_name)
        return os.path.join(
            self.data_dir,
            continent_dir,
            country_dir,
            competition_dir,
            competition_id,
            season_name,
            'fixture.json'
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


# -----------------------------------------------------------
# ------------------ Convenience functions ------------------
# -----------------------------------------------------------
def download_fixtures_by_filters(
    df_seasons: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    skip_existing: bool = True,
    start_index: int = 0,
    limit: Optional[int] = None,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Download fixtures applying common filters.

    Args:
        df_seasons (pd.DataFrame): Seasons DataFrame.
        continent (Optional[str]): Filter by continent.
        country (Optional[str]): Filter by country.
        competition (Optional[str]): Filter by competition.
        skip_existing (bool): Skip existing files.
        start_index (int): Start index.
        limit (Optional[int]): Limit of seasons to process.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScraperFixture.

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

    scraper = ScraperFixture(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    return scraper.process_seasons(
        df_seasons,
        filters=filters,
        skip_existing=skip_existing,
        start_index=start_index,
        limit=limit
    )

def download_all_fixtures(
    df_seasons: pd.DataFrame,
    skip_existing: bool = True,
    start_index: int = 0,
    limit: Optional[int] = None,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Download fixtures for all seasons.

    Args:
        df_seasons (pd.DataFrame): Seasons DataFrame.
        skip_existing (bool): Skip existing files.
        start_index (int): Start index.
        limit (Optional[int]): Limit of seasons to process.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScraperFixture.

    Returns:
        Dict[str, Any]: Processing statistics.
    """
    scraper = ScraperFixture(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    return scraper.process_seasons(
        df_seasons,
        skip_existing=skip_existing,
        start_index=start_index,
        limit=limit
    )


def find_fixture_resume_index(
    df_seasons: pd.DataFrame,
    filters: Optional[Dict[str, Any]] = None,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None
) -> int:
    """
    Find the index from which to resume fixture downloading based on already processed seasons.

    Args:
        df_seasons (pd.DataFrame): DataFrame with seasons.
        filters (Optional[Dict[str, Any]]): Filters to apply.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        int: Index to resume from.
    """
    scraper = ScraperFixture(storage_type=storage_type, s3_bucket=s3_bucket)
    df_filtered = scraper._apply_filters(df_seasons, filters) if filters else df_seasons

    for idx, row in df_filtered.iterrows():
        json_path = scraper._get_json_path(row)
        if not scraper.storage.file_exists(json_path):
            scraper._log(f"Resume point found at index {idx}: {row.get('competition', 'N/A')} - {row.get('season', 'N/A')}", "INFO")
            return idx
    scraper._log("All fixtures already processed", "INFO")
    return len(df_filtered)


def resume_fixtures_download(
    df_seasons: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    batch_size: int = 100,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Resume fixture downloading from where it left off.

    Args:
        df_seasons (pd.DataFrame): DataFrame with seasons.
        continent (Optional[str]): Filter by continent.
        country (Optional[str]): Filter by country.
        competition (Optional[str]): Filter by competition.
        batch_size (int): Number of seasons to process in this batch.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScraperFixture.

    Returns:
        Dict[str, Any]: Processing statistics.
    """
    return smart_download_fixtures(
        df_seasons,
        continent=continent,
        country=country,
        competition=competition,
        restart_from_zero=False,
        batch_size=batch_size,
        storage_type=storage_type,
        s3_bucket=s3_bucket,
        **scraper_kwargs
    )


def smart_download_fixtures(
    df_seasons: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    restart_from_zero: bool = False,
    batch_size: int = 100,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    **scraper_kwargs
) -> Dict[str, Any]:
    """
    Smart function to automatically detect whether to continue or start from scratch for fixture downloading.
    Also saves a consolidated all_fixtures.csv in schema_dir.
    """
    filters = {}
    if continent:
        filters['continent'] = continent
    if country:
        filters['country'] = country
    if competition:
        filters['competition'] = competition

    scraper = ScraperFixture(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    df_filtered = scraper._apply_filters(df_seasons, filters) if filters else df_seasons

    print(f"🎯 Applied filters: {filters if filters else 'None'}")
    print(f"📋 Seasons to process: {len(df_filtered)}")

    if batch_size is None:
        batch_size = len(df_seasons)

    if restart_from_zero:
        deleted_count = 0
        print("🔥 Restart mode: Deleting existing fixtures...")
        for _, row in df_filtered.iterrows():
            json_path = scraper._get_json_path(row)
            if scraper.storage.file_exists(json_path):
                if scraper.storage.storage_type == 'local':
                    os.remove(json_path)
                else:
                    scraper.storage.s3_client.delete_object(Bucket=scraper.storage.s3_bucket, Key=json_path)
                deleted_count += 1
        print(f"🗑️  Deleted {deleted_count} existing fixtures")
        start_index = 0
    else:
        start_index = find_fixture_resume_index(df_seasons, filters, storage_type, s3_bucket)
        start_index = 0 # TODO: hardcoded. Fix this. It needs to resume properly. Check the data with a checkpoint and not just counting files
        if start_index >= len(df_filtered):
            print("✅ All fixtures already downloaded")
            existing_count = sum(
                scraper.storage.file_exists(scraper._get_json_path(row))
                for _, row in df_filtered.iterrows()
            )
            # Save all_fixtures.csv if not present
            df_fixtures = load_existing_fixtures(storage_type=storage_type, s3_bucket=s3_bucket)
            if not df_fixtures.empty:
                save_fixtures_dataframe(df_fixtures, filename="all_fixtures.csv", storage_type=storage_type, s3_bucket=s3_bucket)
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

    stats = download_fixtures_by_filters(
        df_seasons,
        continent=continent,
        country=country,
        competition=competition,
        skip_existing=not restart_from_zero,
        #skip_existing=restart_from_zero, # TODO - check this logic since it's in conflict with the restart_from_zero flag. Probably restart_from_zero needs to be less invasive.
        start_index=start_index,
        limit=batch_size,
        storage_type=storage_type,
        s3_bucket=s3_bucket,
        **scraper_kwargs
    )

    # After downloading, save all_fixtures.csv
    df_fixtures = load_existing_fixtures(storage_type=storage_type, s3_bucket=s3_bucket)
    if not df_fixtures.empty:
        save_fixtures_dataframe(df_fixtures, filename="all_fixtures.csv", storage_type=storage_type, s3_bucket=s3_bucket)

    if 'progress' not in stats:
        stats['progress'] = {}

    stats['progress'].update({
        'processed_seasons': min(start_index + batch_size, len(df_filtered)),
        'total_seasons': len(df_filtered),
        'percentage': (min(start_index + batch_size, len(df_filtered)) / len(df_filtered)) * 100
    })

    print(f"\n📈 Total progress: {stats['progress']['processed_seasons']}/{stats['progress']['total_seasons']} ({stats['progress']['percentage']:.1f}%)")

    return stats


def load_existing_fixtures(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    fixtures_glob: str = '**/fixture.json',
    filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Load the consolidated fixtures DataFrame from schema_dir/all_fixtures.csv if it exists.
    If not, fallback to scanning all fixture.json files.
    """
    scraper = ScraperFixture(storage_type=storage_type, s3_bucket=s3_bucket)
    csv_path = os.path.join(scraper.schema_dir, "all_fixtures.csv")
    # TODO: Check this is not correct, since not new data will be inserted if the CSV exists
    try:
        if scraper.storage.file_exists(csv_path):
            df_fixtures = scraper.storage.load_dataframe_csv(csv_path)
            print(f"[INFO] Loaded fixtures from {csv_path}")
            if filters:
                for column, value in filters.items():
                    if column in df_fixtures.columns:
                        if isinstance(value, list):
                            df_fixtures = df_fixtures[df_fixtures[column].isin(value)]
                        else:
                            df_fixtures = df_fixtures[df_fixtures[column] == value]
            return df_fixtures
    except Exception as e:
        print(f"[WARN] Could not load {csv_path}: {e}")

    # Fallback: scan all fixture.json files (current logic)
    print("[INFO] Falling back to scanning all fixture.json files...")
    storage = scraper.storage
    data_dir = scraper.data_dir
    fixture_files = []

    if storage_type == "local":
        fixture_files = glob.glob(f"{data_dir}/{fixtures_glob}", recursive=True)
    else:
        fixture_files = []
        continuation_token = None
        more_pages = True
        while more_pages:
            list_kwargs = {
                'Bucket': s3_bucket,
                'Prefix': f"{data_dir}/"
            }
            if continuation_token:
                list_kwargs['ContinuationToken'] = continuation_token
            resp = storage.s3_client.list_objects_v2(**list_kwargs)
            contents = resp.get('Contents', [])
            for obj in contents:
                key = obj['Key']
                if key.endswith('fixture.json'):
                    fixture_files.append(key)
            more_pages = resp.get('IsTruncated', False)
            continuation_token = resp.get('NextContinuationToken', None)

    all_fixtures = []
    for file_path in fixture_files:
        try:
            # Load JSON
            if storage_type == "local":
                with open(file_path, 'r', encoding='utf-8') as f:
                    fixture_data = json.load(f)
            else:
                response = storage.s3_client.get_object(Bucket=s3_bucket, Key=file_path)
                content = response['Body'].read().decode('utf-8')
                fixture_data = json.loads(content)

            meta = fixture_data.get('meta', {}) if isinstance(fixture_data, dict) else {}
            continent = meta.get('continent')
            country = meta.get('country')
            competition = meta.get('competition')
            competition_id = meta.get('competition_id')
            season = meta.get('season')

            if not continent or not country or not competition or not competition_id or not season:
                path_parts = file_path.split('/')
                if len(path_parts) >= 6:
                    if not continent:
                        continent = path_parts[-6].replace('_', ' ').title()
                    if not country:
                        country = path_parts[-5].replace('_', ' ').title()
                    if not competition:
                        competition = path_parts[-4].replace('_', ' ').title()
                    if not competition_id:
                        competition_id = path_parts[-3]
                    if not season:
                        season = path_parts[-2]

            matches = []
            if isinstance(fixture_data, dict):
                if 'fixtures' in fixture_data:
                    matches = fixture_data['fixtures']
                elif 'match' in fixture_data:
                    matches = fixture_data['match']

            match_dates = []
            for match in matches:
                if isinstance(match, dict):
                    if 'date' in match:
                        match_dates.append(match['date'])
                    elif 'matchInfo' in match and 'date' in match['matchInfo']:
                        match_dates.append(match['matchInfo']['date'])
                    elif 'matchInfo' in match and 'startDate' in match['matchInfo']:
                        match_dates.append(match['matchInfo']['startDate'])

            match_dates = sorted([d for d in match_dates if d])
            first_match_date = match_dates[0] if match_dates else None
            last_match_date = match_dates[-1] if match_dates else None

            fixture_info = {
                'continent': continent,
                'country': country,
                'competition': competition,
                'competition_id': competition_id,
                'season': season,
                'fixture_path': file_path,
                'num_matches': len(matches),
                'first_match_date': first_match_date,
                'last_match_date': last_match_date
            }
            all_fixtures.append(fixture_info)
        except Exception as e:
            print(f"[DEBUG] Error loading {file_path}: {e}")
            continue

    df_fixtures = pd.DataFrame(all_fixtures)
    if filters:
        for column, value in filters.items():
            if column in df_fixtures.columns:
                if isinstance(value, list):
                    df_fixtures = df_fixtures[df_fixtures[column].isin(value)]
                else:
                    df_fixtures = df_fixtures[df_fixtures[column] == value]
    sort_columns = ['continent', 'country', 'competition', 'season']
    sort_columns = [col for col in sort_columns if col in df_fixtures.columns]
    if sort_columns:
        df_fixtures = df_fixtures.sort_values(by=sort_columns)
    return df_fixtures


def save_fixtures_dataframe(
    df_fixtures: pd.DataFrame,
    filename: str = "all_fixtures.csv",
    storage_type: str = "local",
    s3_bucket: Optional[str] = None
) -> str:
    """
    Save the fixtures DataFrame to CSV in the schema directory.

    Args:
        df_fixtures (pd.DataFrame): Fixtures DataFrame.
        filename (str): CSV filename.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        str: Path to saved file.
    """
    scraper = ScraperFixture(storage_type=storage_type, s3_bucket=s3_bucket)    
    filepath = os.path.join(scraper.schema_dir, filename)
    df_extended = extend_dataframe_with_unique_rows(scraper.storage, df_fixtures, filepath)
    scraper.storage.save_dataframe_csv(df_extended, filepath)
    scraper._log(f"Fixtures saved to: {filepath}", "INFO")
    return filepath


# -----------------------------------------------------------
# ------------------ Testing functions ----------------------
# -----------------------------------------------------------
def test_scraper_fixture() -> bool:
    """
    Test function for ScraperFixture.

    Returns:
        bool: True if test passes, False otherwise.
    """
    print("=== Testing ScraperFixture ===")
    try:
        from scraper_seasons import load_existing_seasons
        for storage_type in ["local"]:
            print(f"\nTesting with storage: {storage_type.upper()}")
            s3_bucket = None
            df_seasons = load_existing_seasons(storage_type=storage_type, s3_bucket=s3_bucket)
            print(f"Loaded seasons: {len(df_seasons)}")
            stats = download_fixtures_by_filters(
                df_seasons,
                country='Argentina',
                skip_existing=True,
                start_index=0,
                limit=3,
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
    test_scraper_fixture()