"""
Scrape Match Stats
==================

This module provides the ScrapeMatchStats class for downloading detailed match statistics
from the ScoresWay API, organizing files by competition and season, and saving results
using a consistent storage abstraction.

Author: Sports Data Campus
Date: October 2025
"""

import os
import json
import time
import requests
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple

from urllib.parse import quote
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from utils import (
    sanitize_dir_name, 
    normalize_match_row,
    normalize_season_string,
    extend_dataframe_with_unique_rows
)
from scraper_base import BaseScraper
from storage_manager import StorageManager


class ScrapeMatchStats(BaseScraper):
    """
    Scraper for downloading match statistics from the ScoresWay API.

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
        Initialize the ScrapeMatchStats.

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
        self.api_base_url = "https://api.performfeeds.com/soccerdata/matchstats"
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36'
        }
        self.session = self._create_session_with_retries()
        self.sleep_time = 1.0
        self.max_retries = 3
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

    def set_delay(self, sleep_time: float) -> None:
        """
        Set the delay between requests.

        Args:
            sleep_time (float): Delay in seconds.
        """
        self.sleep_time = sleep_time
        self._log(f"Delay set to {sleep_time} seconds", "INFO")

    def reset_stats(self) -> None:
        """Reset download statistics."""
        self.success = 0
        self.failures = 0
        self.skipped = 0
        self.processed = 0

    def download_match_stats(self, match_row: pd.Series, skip_existing: bool = True) -> Optional[Dict[str, Any]]:
        """
        Download statistics for a single match.

        Args:
            match_row (pd.Series): Row with match information.
            skip_existing (bool): Skip if file already exists.

        Returns:
            bool: True if downloaded successfully, False otherwise.
        """
        try:
            # Normalize row fields
            match_info = normalize_match_row(match_row)
            match_id = match_info["match_id"]
            continent = match_info["continent"]
            country = match_info["country"]
            competition = match_info["competition"]
            competition_id = match_info["competition_id"]
            tournament_id = match_info["tournament_id"]
            season = match_info["season"]
            home_team = match_info["home_team"]
            away_team = match_info["away_team"]
            date = match_info["date"]

            if not all([match_id, continent, country, competition, competition_id, season, tournament_id]):
                self._log(f"Insufficient data for match {match_id}", "WARNING")
                return False

            dir_path = self._build_stats_directory(continent, country, competition, competition_id, season, tournament_id)
            filename = self._build_filename(match_id, date, home_team, away_team)
            json_path = os.path.join(dir_path, filename)

            if skip_existing and self.storage.file_exists(json_path):
                self._log(f"File already exists, skipping: {filename}", "INFO")
                self.skipped += 1
                return True

            api_url = self._build_api_url(match_id)
            referer = self._build_referer_url(competition, season, tournament_id)
            headers = self.headers.copy()
            headers['Referer'] = referer

            self._log(f"Downloading stats: {home_team} vs {away_team}", "INFO")
            response = self.session.get(api_url, headers=headers)
            response.raise_for_status()

            json_data = self._extract_json_from_jsonp(response.text)

            if self.storage.storage_type == 'local':
                self.storage.ensure_directory(dir_path)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
            else:
                json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
                self.storage.s3_client.put_object(
                    Bucket=self.storage.s3_bucket,
                    Key=json_path,
                    Body=json_str.encode('utf-8')
                )

            self._log(f"Saved: {filename}", "INFO")
            self.success += 1
            time.sleep(self.sleep_time)
            
            # Build normalized stats info for summary
            stats_info = {
                'continent': continent,
                'country': country,
                'competition': competition,
                'id_competition': competition_id,
                'season': season,
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'date': date,
                'file_path': json_path,
                'has_stats': True
            }
            return stats_info

        except Exception as e:
            self._log(f"Error processing match {match_id if 'match_id' in locals() else 'unknown'}: {str(e)}", "ERROR")
            self.failures += 1
            return None

    def _build_stats_directory(
        self, continent: str, country: str, competition: str, competition_id: str, season: str, tournament_id: str
    ) -> str:
        """
        Build the directory path for match statistics.

        Returns:
            str: Directory path.
        """
        continent_dir = sanitize_dir_name(continent)
        country_dir = sanitize_dir_name(country)
        competition_dir = sanitize_dir_name(competition)
        season_name = normalize_season_string(str(season))

        dir_path = os.path.join(
            self.data_dir,
            continent_dir,
            country_dir,
            competition_dir,
            competition_id,
            season_name,
            tournament_id,
            'matchstats'
        )
        print("dir_path: ", dir_path)
        print(f"[DEBUG] Ensuring directory exists: {dir_path}")
        self.storage.ensure_directory(dir_path)
        return dir_path

    def _build_filename(self, match_id: str, date: str, home_team: str, away_team: str) -> str:
        """
        Build the filename for the match statistics JSON.

        Returns:
            str: Filename.
        """
        safe_home = sanitize_dir_name(str(home_team))
        safe_away = sanitize_dir_name(str(away_team))
        safe_date = sanitize_dir_name(str(date).split('_')[0]) if date else "no_date"
        #safe_date = sanitize_dir_name(str(date)) if date else "no_date"
        return f"{match_id}_{safe_date}_{safe_home}_{safe_away}.json"

    def _build_api_url(self, match_id: str) -> str:
        """
        Build the API URL for match statistics.

        Returns:
            str: API URL.
        """
        return (
            f"{self.api_base_url}/{self.sdapi_outlet_key}/"
            f"{match_id}?_rt=c&_lcl=en&_fmt=jsonp&sps=widgets&_clbk={self.callback_id}"
        )

    def _build_referer_url(self, competition: str, season: str, tournament_id: str) -> str:
        """
        Build the referer URL for the request.

        Returns:
            str: Referer URL.
        """
        url_base = f'{self.base_url}/en_GB/soccer/'
        url_competition = f"{quote(competition)}-{quote(str(season))}/{tournament_id}"
        return f"{url_base}{url_competition}/fixtures"

    def _extract_json_from_jsonp(self, content: str) -> Dict[str, Any]:
        """
        Extract pure JSON from a JSONP response.

        Args:
            content (str): JSONP response content.

        Returns:
            Dict[str, Any]: Extracted JSON data.

        Raises:
            Exception: If extraction fails.
        """
        start = content.find('(') + 1
        end = content.rfind(')')
        if start <= 0 or end <= 0 or start >= end:
            raise Exception("Unexpected JSONP response format")
        return json.loads(content[start:end])

    def process_matches(
        self,
        df_matches: pd.DataFrame,
        filters: Optional[Dict[str, Any]] = None,
        skip_existing: bool = True,
        start_index: int = 0,
        limit: Optional[int] = None,
        save_consolidated: bool = True,
        consolidated_filename: str = "all_matches_stats.csv"
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Download statistics for multiple matches and save summary CSV.
        """
        self.reset_stats()
        start_time = time.time()
        df_filtered = self._apply_filters(df_matches, filters)
        end_index = len(df_filtered)
        if limit:
            end_index = min(start_index + limit, end_index)
        df_to_process = df_filtered.iloc[start_index:end_index]

        self._log(f"Starting match stats download: {len(df_to_process)} matches", "INFO")
        all_stats: List[Dict[str, Any]] = []

        for idx, (_, row) in enumerate(df_to_process.iterrows()):
            try:
                # Normalize row fields
                match_info = normalize_match_row(row)
                home_team = match_info["home_team"]
                away_team = match_info["away_team"]

                self._log(f"Processing {idx + 1}/{len(df_to_process)}: {home_team} vs {away_team}", "INFO")
                stats_info = self.download_match_stats(row, skip_existing)
                self.processed += 1
                if stats_info:
                    all_stats.append(stats_info)
                if (idx + 1) % 20 == 0:
                    self._print_progress(idx + 1, len(df_to_process), start_time)
            except KeyboardInterrupt:
                self._log("Download interrupted by user.", "WARNING")
                break
            except Exception as e:
                self._log(f"Unexpected error in match {idx}: {e}", "ERROR")
                self.failures += 1
                self.processed += 1

        duration = time.time() - start_time
        stats = {
            'total_matches': len(df_to_process),
            'processed': self.processed,
            'success': self.success,
            'skipped': self.skipped,
            'failures': self.failures,
            'duration': duration,
            'matches_per_minute': (self.processed / (duration / 60)) if duration > 0 else 0
        }
        self._print_final_summary(stats)

        df_stats = pd.DataFrame(all_stats)
        # Save consolidated CSV
        if save_consolidated and all_stats:            
            self._save_results(df_stats, filename=consolidated_filename)

        return df_stats, stats

    def _apply_filters(self, df: pd.DataFrame, filters: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply filters to the DataFrame.

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
            column_variants = [
                column,
                column.replace('_', ' ').title(),
                column.replace(' ', '_').lower(),
                column.replace('_', ' ').title().replace(' ', '_')
            ]
            found_column = None
            for variant in column_variants:
                if variant in df_filtered.columns:
                    found_column = variant
                    break
            if found_column:
                if isinstance(value, list):
                    df_filtered = df_filtered[df_filtered[found_column].isin(value)]
                else:
                    df_filtered = df_filtered[df_filtered[found_column] == value]
                self._log(f"Filter applied - {found_column}: {value} → {len(df_filtered)} matches", "INFO")
            else:
                self._log(f"Column '{column}' not found. Available columns: {list(df_filtered.columns)}", "WARNING")
        return df_filtered

    def _print_progress(self, current: int, total: int, start_time: float) -> None:
        """
        Print processing progress.

        Args:
            current (int): Current index.
            total (int): Total count.
            start_time (float): Start time.
        """
        elapsed = time.time() - start_time
        rate = self.processed / (elapsed / 60) if elapsed > 0 else 0
        self._log(
            f"Progress: {current}/{total} ({current/total*100:.1f}%) | "
            f"Speed: {rate:.2f} matches/min | "
            f"Success: {self.success} | Skipped: {self.skipped} | Failures: {self.failures}",
            "INFO"
        )
        if elapsed > 0:
            remaining = (total - current) * (elapsed / current)
            self._log(f"Estimated time remaining: {remaining/60:.1f} minutes", "INFO")

    def _print_final_summary(self, stats: Dict[str, Any]) -> None:
        """
        Print final processing summary.

        Args:
            stats (Dict[str, Any]): Statistics.
        """
        self._log("="*60, "INFO")
        self._log("FINAL SUMMARY - MATCH STATS DOWNLOAD", "INFO")
        self._log("="*60, "INFO")
        self._log(f"Total time: {stats['duration']:.1f} seconds ({stats['duration']/60:.1f} minutes)", "INFO")
        self._log(f"Matches processed: {stats['processed']}/{stats['total_matches']}", "INFO")
        self._log(f"Success: {stats['success']}", "INFO")
        self._log(f"Skipped (already existed): {stats['skipped']}", "INFO")
        self._log(f"Failures: {stats['failures']}", "INFO")
        self._log(f"Average speed: {stats['matches_per_minute']:.2f} matches/minute", "INFO")
        if stats['success'] > 0:
            success_rate = (stats['success'] / stats['processed']) * 100
            self._log(f"Success rate: {success_rate:.1f}%", "INFO")

    def _save_results(self, df_stats: pd.DataFrame, filename: str = "all_matches_stats.csv") -> None:
        """
        Save the consolidated match stats DataFrame to CSV in the schema directory.
        """
        try:
            path = os.path.join(self.schema_dir, filename)
            self.storage.ensure_directory(self.schema_dir)
            df_extended = extend_dataframe_with_unique_rows(self.storage, df_stats, path)
            self.storage.save_dataframe_csv(df_extended, path)
            self._log(f"Consolidated match stats saved to: {path}", "INFO")
        except Exception as e:
            self._log(f"Error saving consolidated match stats: {e}", "ERROR")


# -----------------------------------------------------------
# ------------------ Convenience functions ------------------
# -----------------------------------------------------------
def download_match_stats_by_filters(
    df_matches: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    skip_existing: bool = True,
    start_index: int = 0,
    batch_size: Optional[int] = None,
    save_consolidated: bool = True,
    consolidated_filename: str = "all_matches_stats.csv",
    sleep_time: float = 1.0,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    **scraper_kwargs
) -> Tuple[pd.DataFrame, Dict]:
    """
    Download match stats applying common filters.

    Args:
        df_matches (pd.DataFrame): Matches DataFrame.
        continent (Optional[str]): Filter by continent.
        country (Optional[str]): Filter by country.
        competition (Optional[str]): Filter by competition.
        skip_existing (bool): Skip existing files.
        start_index (int): Start index.
        batch_size (Optional[int]): Batch size of matches to process.
        sleep_time (float): Delay between requests.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScrapeMatchStats.

    Returns:
        Dict[str, Any]: Processing statistics.
    """
    filters = {}
    if continent:
        filters['continente'] = continent
    if country:
        filters['pais'] = country
    if competition:
        filters['competicion'] = competition

    scraper = ScrapeMatchStats(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    scraper.set_delay(sleep_time)
    return scraper.process_matches(
        df_matches,
        filters=filters,
        skip_existing=skip_existing,
        start_index=start_index,
        limit=batch_size,
        save_consolidated=save_consolidated,
        consolidated_filename=consolidated_filename
    )


def find_match_stats_resume_index(
    df_matches: pd.DataFrame,
    filters: Optional[Dict[str, Any]] = None,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None
) -> int:
    """
    Find the index from which to resume match stats downloading.

    Args:
        df_matches (pd.DataFrame): DataFrame with matches.
        filters (Optional[Dict[str, Any]]): Filters to apply.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        int: Index to resume from.
    """
    scraper = ScrapeMatchStats(storage_type=storage_type, s3_bucket=s3_bucket)
    df_filtered = scraper._apply_filters(df_matches, filters) if filters else df_matches
    for idx, row in df_filtered.iterrows():
        # Normalize row fields
        match_info = normalize_match_row(row)
        match_id = match_info["match_id"]
        continent = match_info["continent"]
        country = match_info["country"]
        competition = match_info["competition"]
        competition_id = match_info["competition_id"]
        tournament_id = match_info["tournament_id"]
        season = match_info["season"]
        home_team = match_info["home_team"]
        away_team = match_info["away_team"]
        date = match_info["date"]

        if not all([match_id, continent, country, competition, competition_id, season, tournament_id]):
            scraper._log(f"Insufficient data for match {match_id}", "WARNING")
            continue

        #print("match_info: ", match_info)

        dir_path = scraper._build_stats_directory(continent, country, competition, competition_id, season, tournament_id)
        print("dir_path: ", dir_path)
        filename = scraper._build_filename(match_id, date, home_team, away_team)
        print("filename: ", filename)
        json_path = os.path.join(dir_path, filename)
        print("json_path: ", json_path)

        if not scraper.storage.file_exists(json_path):
            scraper._log(f"Resume point found at index {idx}: {home_team} vs {away_team}", "INFO")
            return idx
    scraper._log("All match stats already processed", "INFO")
    return len(df_filtered)

def smart_download_match_stats(
    df_matches: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    restart_from_zero: bool = False,
    batch_size: int = 100,
    save_consolidated: bool = True,
    consolidated_filename: str = "all_matches_stats.csv",
    sleep_time: float = 1.0,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    **scraper_kwargs
) -> Tuple[pd.DataFrame, Dict]:
    """
    Smart function to automatically detect whether to continue or start from scratch for match stats downloading.

    Args:
        df_matches (pd.DataFrame): DataFrame with matches.
        continent (Optional[str]): Filter by continent.
        country (Optional[str]): Filter by country.
        competition (Optional[str]): Filter by competition.
        restart_from_zero (bool): If True, deletes existing data and starts from scratch.
        batch_size (int): Number of matches to process in this batch.
        sleep_time (float): Delay between requests.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        **scraper_kwargs: Additional arguments for ScrapeMatchStats.

    Returns:
        Dict[str, Any]: Processing statistics.
    """
    filters = {}
    if continent:
        filters['continente'] = continent
    if country:
        filters['pais'] = country
    if competition:
        filters['competicion'] = competition

    scraper = ScrapeMatchStats(storage_type=storage_type, s3_bucket=s3_bucket, **scraper_kwargs)
    scraper.set_delay(sleep_time)
    df_filtered = scraper._apply_filters(df_matches, filters) if filters else df_matches

    print(f"🎯 Applied filters: {filters if filters else 'None'}")
    print(f"📋 Matches to process: {len(df_filtered)}")

    if restart_from_zero:
        print("🔥 Restart mode: Deleting existing match stats...")

        # Find all matchstats JSON files
        if scraper.storage.storage_type == 'local':
            import glob
            stats_files = glob.glob(f"{scraper.data_dir}/**/matchstats/*.json", recursive=True)
        else:
            stats_files = []
            continuation_token = None
            more_pages = True
            while more_pages:
                list_kwargs = {'Bucket': scraper.storage.s3_bucket, 'Prefix': f"{scraper.data_dir}/"}
                if continuation_token:
                    list_kwargs['ContinuationToken'] = continuation_token
                resp = scraper.storage.s3_client.list_objects_v2(**list_kwargs)
                contents = resp.get('Contents', [])
                for obj in contents:
                    key = obj['Key']
                    if 'matchstats/' in key and key.endswith('.json'):
                        stats_files.append(key)
                more_pages = resp.get('IsTruncated', False)
                continuation_token = resp.get('NextContinuationToken', None)

        deleted_count = 0
        for i, json_path in enumerate(stats_files, 1):
            try:
                print(f"[DEBUG] Deleting file {i}/{len(stats_files)}: {json_path}")
                if scraper.storage.storage_type == 'local':
                    os.remove(json_path)
                else:
                    scraper.storage.s3_client.delete_object(
                        Bucket=scraper.storage.s3_bucket,
                        Key=json_path
                    )
                deleted_count += 1
            except Exception as e:
                print(f"[WARNING] Could not delete {json_path}: {e}")

        print(f"🗑️  Deleted {deleted_count} existing match stats")
        start_index = 0
    else:
        print("restart_from_zero is: ", restart_from_zero)
        start_index = find_match_stats_resume_index(df_matches, filters, storage_type, s3_bucket)
        print("start_index: ", start_index)
        if start_index >= len(df_filtered):
            print("✅ All match stats already downloaded")
            return pd.DataFrame(), {
                'total_matches': len(df_filtered),
                'processed': len(df_filtered),
                'success': len(df_filtered),
                'skipped': len(df_filtered),
                'failures': 0,
                'duration': 0,
                'matches_per_minute': 0
            }

    print(f"🚀 Starting download from match {start_index + 1}/{len(df_filtered)}")
    return scraper.process_matches(
        df_matches,
        filters=filters,
        skip_existing=not restart_from_zero,
        start_index=start_index,
        limit=batch_size,
        save_consolidated=save_consolidated,
        consolidated_filename=consolidated_filename
    )


def save_match_stats_csv(
    df_stats: pd.DataFrame,
    filename: str = "all_matches_stats.csv",
    storage_type: str = "local",
    s3_bucket: Optional[str] = None
) -> str:
    """
    Save the match stats DataFrame to CSV in the schema directory.

    Args:
        df_stats (pd.DataFrame): Match stats DataFrame.
        filename (str): CSV filename.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        str: Path to saved file.
    """
    scraper = ScrapeMatchStats(storage_type=storage_type, s3_bucket=s3_bucket)
    filepath = os.path.join(scraper.schema_dir, filename)
    scraper.storage.save_dataframe_csv(df_stats, filepath)
    scraper._log(f"Match stats summary saved to: {filepath}", "INFO")
    return filepath


def load_existing_match_stats(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    stats_glob: str = '**/matchstats/*.json',
    filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Load all existing match stats from the configured storage.

    Args:
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        stats_glob (str): Glob pattern for stats files.
        filters (Optional[Dict[str, Any]]): Filters to apply.

    Returns:
        pd.DataFrame: DataFrame with combined stats info.
    """
    scraper = ScrapeMatchStats(storage_type=storage_type, s3_bucket=s3_bucket)
    csv_path = os.path.join(scraper.schema_dir, "all_matches_stats.csv")
    try:
        df_stats = scraper.storage.load_dataframe_csv(csv_path)
        scraper._log(f"Loaded match stats summary from: {csv_path}", "INFO")
    except Exception:
        # Fallback: scan all matchstats JSON files
        import glob, re
        data_dir = scraper.data_dir
        if storage_type == "local":
            stats_files = glob.glob(f"{data_dir}/{stats_glob}", recursive=True)
        else:
            stats_files = []
            continuation_token = None
            more_pages = True
            while more_pages:
                list_kwargs = {'Bucket': s3_bucket, 'Prefix': f"{data_dir}/"}
                if continuation_token:
                    list_kwargs['ContinuationToken'] = continuation_token
                resp = scraper.storage.s3_client.list_objects_v2(**list_kwargs)
                contents = resp.get('Contents', [])
                for obj in contents:
                    key = obj['Key']
                    if 'matchstats/' in key and key.endswith('.json'):
                        stats_files.append(key)
                more_pages = resp.get('IsTruncated', False)
                continuation_token = resp.get('NextContinuationToken', None)

        all_stats = []
        for file_path in stats_files:
            try:
                # Example path:
                # data/Continent/Country/Competition/CompetitionID/Season/TournamentID/matchstats/12345_2024-08-01_Boca_Juniors_River_Plate.json
                path_parts = file_path.split(os.sep)
                # Adjust for S3 (always '/'), or local (os.sep)
                if len(path_parts) < 9:
                    path_parts = file_path.split('/')
                # Indices based on _build_stats_directory
                # [data, continent, country, competition, competition_id, season, tournament_id, 'matchstats', filename]
                if len(path_parts) >= 9:
                    continent = path_parts[-9]
                    country = path_parts[-8]
                    competition = path_parts[-7]
                    competition_id = path_parts[-6]
                    season = path_parts[-5]
                    tournament_id = path_parts[-4]
                    filename = path_parts[-1]
                    # Extract match_id, date, home_team, away_team from filename
                    import re
                    filename_match = re.match(r'^(\d+)_([^_]+)_(.+)_(.+)\.json$', filename)
                    if filename_match:
                        match_id = filename_match.group(1)
                        date = filename_match.group(2)
                        home_team = filename_match.group(3)
                        away_team = filename_match.group(4).replace('.json', '')
                    else:
                        match_id = None
                        date = None
                        home_team = None
                        away_team = None

                    # Load JSON and try to extract more info
                    if storage_type == "local":
                        with open(file_path, 'r', encoding='utf-8') as f:
                            stats_data = json.load(f)
                    else:
                        response = scraper.storage.s3_client.get_object(Bucket=s3_bucket, Key=file_path)
                        content = response['Body'].read().decode('utf-8')
                        stats_data = json.loads(content)
                    match_info_json = stats_data.get('matchInfo', {})

                    # Try to use normalize_match_row if possible
                    # If not, fallback to extracting from path and JSON
                    stats_info = {
                        "match_id": match_id,
                        "date": date,
                        "home_team": home_team,
                        "away_team": away_team,
                        "tournament_id": tournament_id,
                        "competition": competition,
                        "competition_id": competition_id,
                        "country": country,
                        "continent": continent,
                        "season": season,
                        "file_path": file_path,
                        "has_stats": True
                    }
                    # Optionally, add more fields from match_info_json if available
                    if isinstance(match_info_json, dict):
                        stats_info["status"] = match_info_json.get("status")
                        stats_info["venue"] = match_info_json.get("venue", {}).get("name")
                        stats_info["attendance"] = match_info_json.get("attendance")
                        stats_info["weather_temperature"] = match_info_json.get("weather", {}).get("temperature")
                        stats_info["weather_conditions"] = match_info_json.get("weather", {}).get("conditions")
                        # Add more fields as needed

                    all_stats.append(stats_info)
            except Exception as e:
                print(f"[DEBUG] Error loading {file_path}: {e}")
                continue

        df_stats = pd.DataFrame(all_stats)
        if not df_stats.empty:
            save_match_stats_csv(df_stats, storage_type=storage_type, s3_bucket=s3_bucket)
    # Filtering and sorting
    if filters:
        for column, value in filters.items():
            if column in df_stats.columns:
                if isinstance(value, list):
                    df_stats = df_stats[df_stats[column].isin(value)]
                else:
                    df_stats = df_stats[df_stats[column] == value]
    sort_columns = ['continent', 'country', 'competition', 'season', 'date']
    sort_columns = [col for col in sort_columns if col in df_stats.columns]
    if sort_columns:
        df_stats = df_stats.sort_values(by=sort_columns)
    return df_stats


# -----------------------------------------------------------
# ------------------ Testing functions ----------------------
# -----------------------------------------------------------
def test_scrape_match_stats() -> bool:
    """
    Test function for ScrapeMatchStats.

    Returns:
        bool: True if test passes, False otherwise.
    """
    print("=== Testing ScrapeMatchStats ===")
    try:
        test_data = {
            'Partido_ID': ['12345'],
            'Continente': ['America'],
            'Pais': ['Argentina'],
            'Competicion': ['Liga Profesional'],
            'ID_Competicion': ['1'],
            'Torneo_ID': ['12345'],
            'Temporada': ['2024-2025'],
            'Equipo_Local': ['Boca Juniors'],
            'Equipo_Visitante': ['River Plate'],
            'Fecha': ['2024-08-01']
        }
        df_test = pd.DataFrame(test_data)
        scraper = ScrapeMatchStats(storage_type="local")
        scraper.set_delay(0.1)
        print("🧪 Testing basic functionality...")
        result = scraper.download_match_stats(df_test.iloc[0], skip_existing=True)
        print(f"Test result: {result}")
        return True
    except Exception as e:
        print(f"❌ Error in testing: {e}")
        return False

if __name__ == "__main__":
    test_scrape_match_stats()