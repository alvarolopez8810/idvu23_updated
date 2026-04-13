"""
Season Scraper
==============

This module provides the ScraperSeason class for scraping available sports seasons
from ScoresWay, organizing data and directories by season, and saving results
using a consistent storage abstraction.

Author: Sports Data Campus
Date: October 2025
"""

import os
import re
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from fuzzywuzzy import process, fuzz
from typing import Dict, List, Optional, Tuple, Any

from utils import (
    sanitize_dir_name,    
    get_season_name_from_url,
    normalize_season_string,
    extend_dataframe_with_unique_rows
)
from scraper_base import BaseScraper
from storage_manager import StorageManager


class ScraperSeason(BaseScraper):
    """
    Scraper for extracting sports seasons from ScoresWay.

    Inherits from BaseScraper for session, logging, and storage management.
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
        verbose: bool = True,
    ) -> None:
        """
        Initialize the ScraperSeason.

        Args:
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
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        try:
            self.session.get(f"{self.base_url}/?sport=soccer")
            self._log("Web session initialized.", "INFO")
        except Exception as e:
            self._log(f"Could not initialize web session: {e}", "WARNING")

    def get_seasons_from_competition(self, competition_row: pd.Series) -> List[Dict[str, Any]]:
        """
        Extract all available seasons for a given competition.

        Args:
            competition_row (pd.Series): Row from competitions DataFrame.

        Returns:
            List[Dict[str, Any]]: List of season info dictionaries.
        """
        url: str = competition_row["url"]
        seasons: List[Dict[str, Any]] = []

        try:
            self.random_sleep()
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")
            season_select = soup.find("select", {"id": "season-select"})

            if season_select:
                for option in season_select.find_all("option"):
                    season_text = option.text.strip()
                    season_value = option.get("value", "")
                    if season_value:
                        season_url = f"{self.base_url}{season_value}"
                        season_info = {
                            "continent": competition_row.get("continent"),
                            "country": competition_row.get("country"),
                            "competition": competition_row.get("competition"),
                            "competition_id": competition_row.get("competition_id"),
                            "competition_url": url,
                            "season": season_text,
                            "season_url": season_url,
                        }
                        seasons.append(season_info)
                self._log(
                    f"Found {len(seasons)} seasons for {competition_row.get('competition')} (from selector)",
                    "INFO",
                )
            else:
                self._log(
                    f"No season selector found in {url}, attempting alternative extraction...",
                    "WARNING",
                )
                # Try to extract season from title or URL
                title_element = soup.find("h1", class_="sw-title") or soup.find("h1")
                current_season = None
                if title_element:
                    title_text = title_element.text.strip()
                    season_patterns = [
                        r"(\d{4})[/-](\d{2,4})",
                        r"(\d{4})",
                    ]
                    for pattern in season_patterns:
                        match = re.search(pattern, title_text)
                        if match:
                            current_season = match.group(0)
                            break
                if not current_season:
                    url_path = re.sub(r"/$", "", url)
                    for segment in url_path.split("/"):
                        if re.search(r"\d{4}", segment):
                            current_season = segment
                            break
                if not current_season:
                    import datetime

                    current_year = datetime.datetime.now().year
                    current_season = f"{current_year}-{current_year+1}"
                season_info = {
                    "continent": competition_row.get("continent"),
                    "country": competition_row.get("country"),
                    "competition": competition_row.get("competition"),
                    "competition_id": competition_row.get("competition_id"),
                    "competition_url": url,
                    "season": current_season,
                    "season_url": url,
                }
                seasons.append(season_info)
                self._log(
                    f"Created single season {current_season} for {competition_row.get('competition')} (no selector)",
                    "INFO",
                )
        except requests.RequestException as e:
            self._log(f"Connection error with {url}: {e}", "ERROR")

            if hasattr(e.response, 'status_code') and e.response.status_code == 403:
                self._log(
                    f"Access forbidden (HTTP 403) for {url}. Waiting 5 seconds and retrying with alternative headers...",
                    "WARNING"
                )
                time.sleep(5)

                # Retry with alternative browser headers
                backup_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                    "sec-ch-ua": "\"Microsoft Edge\";v=\"141\", \"Not;A=Brand\";v=\"99\"",
                    "Cache-Control": "max-age=0",
                }
    
                try:
                    retry_session = requests.Session()
                    retry_session.headers.update(backup_headers)
                    retry_response = retry_session.get(url, timeout=30)
                    retry_response.raise_for_status()

                    soup = BeautifulSoup(retry_response.text, "html.parser")
                    season_select = soup.find("select", {"id": "season-select"})

                    if season_select:
                        for option in season_select.find_all("option"):
                            season_text = option.text.strip()
                            season_value = option.get("value", "")
                            if season_value:
                                season_url = f"{self.base_url}{season_value}"
                                season_info = {
                                    "continent": competition_row.get("continent"),
                                    "country": competition_row.get("country"),
                                    "competition": competition_row.get("competition"),
                                    "competition_id": competition_row.get("competition_id"),
                                    "competition_url": url,
                                    "season": season_text,
                                    "season_url": season_url,
                                }
                                seasons.append(season_info)
                        self._log(
                            f"Found {len(seasons)} seasons for {competition_row.get('competition')} (after retry with alternative headers)",
                            "INFO"
                        )
                except Exception as retry_error:
                    self._log(f"Retry after 403 failed for {url}: {retry_error}", "ERROR")
        except Exception as e:
            self._log(f"Unexpected error with {url}: {e}", "ERROR")
        return seasons

    def scrape_all_seasons(
        self,
        df_competitions: pd.DataFrame,
        start_index: int = 0,
        limit: Optional[int] = None,
        max_retries: int = 3,
    ) -> pd.DataFrame:
        """
        Extract all seasons for all competitions.

        Args:
            df_competitions (pd.DataFrame): Competitions DataFrame.
            start_index (int): Start index for processing.
            limit (Optional[int]): Limit of competitions to process.
            max_retries (int): Max retries per competition.

        Returns:
            pd.DataFrame: DataFrame with all seasons.
        """
        all_seasons: List[Dict[str, Any]] = []
        end_index = len(df_competitions)
        if limit:
            end_index = min(start_index + limit, end_index)
        total_competitions = end_index - start_index

        self._log(
            f"Starting season scraping: {total_competitions} competitions, range {start_index} to {end_index-1}",
            "INFO",
        )

        for idx in range(start_index, end_index):
            row = df_competitions.iloc[idx]
            competition_name = row.get("competition", "N/A")
            self._log(
                f"Processing {idx + 1}/{len(df_competitions)}: {competition_name}",
                "INFO",
            )
            seasons: List[Dict[str, Any]] = []
            for attempt in range(max_retries):
                if attempt > 0:
                    self._log(f"Retry {attempt+1}/{max_retries}...", "WARNING")
                    time.sleep(3 * attempt)
                seasons = self.get_seasons_from_competition(row)
                if seasons:
                    break
            all_seasons.extend(seasons)
            if idx < end_index - 1:
                self.random_sleep()
                if (idx - start_index + 1) % 3 == 0:
                    self._log("Pause to avoid blocking (4-8 seconds)...", "INFO")
                    time.sleep(random.uniform(4, 8))

        df_seasons = pd.DataFrame(all_seasons)
        if not df_seasons.empty:
            df_seasons["results_url"] = df_seasons["season_url"].str.replace(
                "fixtures", "results"
            )
        self._log(
            f"Season scraping completed! Total seasons found: {len(all_seasons)}",
            "INFO",
        )
        return df_seasons

    def save_seasons_csv(
        self, df_seasons: pd.DataFrame, filename: str = "all_seasons.csv"
    ) -> str:
        """
        Save the seasons DataFrame to CSV in the schema directory.

        Args:
            df_seasons (pd.DataFrame): Seasons DataFrame.
            filename (str): CSV filename.

        Returns:
            str: Path to saved file.
        """
        try:
            filepath = os.path.join(self.schema_dir, filename)
            df_extended = extend_dataframe_with_unique_rows(self.storage, df_seasons, filepath)
            saved_path = self.storage.save_dataframe_csv(df_extended, filepath)
            self._log(f"Seasons saved to: {saved_path}", "INFO")
            return saved_path
        except Exception as e:
            raise Exception(f"Error saving CSV: {e}")

    def load_seasons_csv(
        self, filename: str = "all_seasons.csv"
    ) -> pd.DataFrame:
        """
        Load the seasons DataFrame from CSV in the schema directory.

        Args:
            filename (str): CSV filename.

        Returns:
            pd.DataFrame: Seasons DataFrame.
        """
        try:
            filepath = os.path.join(self.schema_dir, filename)
            df = self.storage.load_dataframe_csv(filepath)
            self._log(f"Seasons loaded from: {filepath}", "INFO")
            return df
        except FileNotFoundError:
            raise Exception(f"File not found: {filepath}")
        except Exception as e:
            raise Exception(f"Error loading CSV: {e}")

    def create_seasons_directory_structure(
        self, df_seasons: pd.DataFrame
    ) -> Dict[str, int]:
        """
        Create directory structure based on seasons.

        Args:
            df_seasons (pd.DataFrame): Seasons DataFrame.

        Returns:
            Dict[str, int]: Directory creation statistics.
        """
        self.storage.ensure_directory(self.data_dir)
        created_dirs = 0
        skipped_rows = 0
        errors = 0

        for idx, row in df_seasons.iterrows():
            try:
                required_fields = [
                    "continent",
                    "country",
                    "competition",
                    "competition_id",
                    "results_url",
                ]
                if not all(pd.notna(row.get(field)) for field in required_fields):
                    skipped_rows += 1
                    continue
                continent_dir = sanitize_dir_name(row["continent"])
                country_dir = sanitize_dir_name(row["country"])                
                competition_dir = sanitize_dir_name(row['competition'])
                competition_id = str(row['competition_id'])
                season_name = get_season_name_from_url(row["results_url"])
                if not season_name:
                    skipped_rows += 1
                    continue

                print(f"Season name from URL: {season_name}")
                season_name = normalize_season_string(season_name)
                print(f"Normalized season name: {season_name}")
                season_path = os.path.join(
                    self.data_dir, continent_dir, country_dir, competition_dir, competition_id, season_name
                )
                print(f"Creating directory path: {season_path}")
                self.storage.ensure_directory(season_path)
                created_dirs += 1
            except Exception as e:
                self._log(f"Error processing row {idx}: {e}", "WARNING")
                errors += 1

        stats = {
            "total_rows": len(df_seasons),
            "created_dirs": created_dirs,
            "skipped_rows": skipped_rows,
            "errors": errors,
        }
        self._log(
            f"Directory structure created: {stats}", "INFO"
        )
        return stats

    def get_seasons_summary(self, df_seasons: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a summary of the seasons DataFrame.

        Args:
            df_seasons (pd.DataFrame): Seasons DataFrame.

        Returns:
            Dict[str, Any]: Summary statistics.
        """
        if df_seasons.empty:
            return {"total_seasons": 0}
        summary = {
            "total_seasons": len(df_seasons),
            "unique_competitions": df_seasons["competition"].nunique(),
            "unique_countries": df_seasons["country"].nunique(),
            "unique_continents": df_seasons["continent"].nunique(),
            "seasons_per_competition": df_seasons.groupby("competition")["season"].count().to_dict(),
            "seasons_per_country": df_seasons["country"].value_counts().head(10).to_dict(),
        }
        return summary

    def _get_random_user_agent(self) -> str:
        """
        Return a random User-Agent string.

        Returns:
            str: Random User-Agent.
        """
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        ]
        return random.choice(user_agents)

    def _make_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """
        Make an HTTP request with retries and User-Agent rotation.

        Args:
            url (str): URL to request.
            max_retries (int): Maximum number of retries.

        Returns:
            requests.Response: HTTP response.

        Raises:
            requests.RequestException: If all attempts fail.
        """
        for attempt in range(max_retries):
            try:
                self.session.headers.update(
                    {"User-Agent": self._get_random_user_agent()}
                )
                if attempt == 0:
                    self.session.get(f"{self.base_url}/?sport=soccer", timeout=15)
                    time.sleep(random.uniform(0.5, 1.5))
                    self.session.get(
                        f"{self.base_url}/en_GB/soccer/competitions", timeout=15
                    )
                    time.sleep(random.uniform(0.5, 1.5))
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                wait_time = 2 ** (attempt + 1)
                if attempt < max_retries - 1:
                    self._log(
                        f"Attempt {attempt+1} failed: {e}. Waiting {wait_time}s...",
                        "WARNING",
                    )
                    time.sleep(wait_time)
                else:
                    self._log(f"All attempts failed for {url}", "ERROR")
                    raise

# -----------------------------------------------------------
# ------------------ Convenience functions ------------------
# -----------------------------------------------------------
def scrape_and_save_seasons(
    df_competitions: pd.DataFrame,
    save_csv: bool = True,
    create_dirs: bool = True,
    start_index: int = 0,
    limit: Optional[int] = None,
    append_to_existing: bool = True,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    countries: Optional[List[str]] = None,
    fuzzy_threshold: float = 80,
    seasons: Optional[List[str]] = None  # <-- NEW
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Main function to scrape all seasons and optionally save and create directories.

    Args:
        df_competitions (pd.DataFrame): Competitions DataFrame.
        save_csv (bool): Whether to save to CSV.
        create_dirs (bool): Whether to create directory structure.
        start_index (int): Start index for scraping.
        limit (Optional[int]): Limit of competitions to process.
        append_to_existing (bool): Append to existing CSV if True.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        countries (Optional[List[str]]): Filter by countries.
        fuzzy_threshold (float): Fuzzy match threshold.
        seasons (Optional[List[str]]): Filter by seasons.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: Seasons DataFrame and summary.
    """
    scraper = ScraperSeason(storage_type=storage_type, s3_bucket=s3_bucket)
    if countries:
        def matches_country(country_name: str, target_countries: List[str], threshold: float = 80) -> bool:
            country_lower = country_name.lower()
            if any(country_lower == target.lower() for target in target_countries):
                return True
            for target in target_countries:
                pattern = f"^{re.escape(target)}[_\\s\\-]?[a-zA-Z0-9]*$"
                if re.search(pattern, country_name, re.IGNORECASE):
                    return True
            best_match = process.extractOne(
                country_lower, [target.lower() for target in target_countries], scorer=fuzz.token_sort_ratio
            )
            if best_match and best_match[1] >= threshold:
                return True
            return False
        original_count = len(df_competitions)
        df_competitions = df_competitions[df_competitions["country"].apply(
            lambda x: matches_country(x, countries, fuzzy_threshold)
        )]
        filtered_count = len(df_competitions)
        scraper._log(
            f"Filtering by countries: {', '.join(countries)} | Original: {original_count} | Filtered: {filtered_count}",
            "INFO",
        )
        if filtered_count == 0:
            return pd.DataFrame(), {"total_seasons": 0}

    existing_df = pd.DataFrame()
    if append_to_existing and save_csv:
        try:
            existing_df = scraper.load_seasons_csv()
            if countries:
                original_existing = len(existing_df)
                existing_df = existing_df[existing_df["country"].apply(
                    lambda x: matches_country(x, countries, fuzzy_threshold)
                )]
                scraper._log(
                    f"Existing seasons filtered: {len(existing_df)}/{original_existing}",
                    "INFO",
                )
        except Exception:
            scraper._log("No existing seasons found, starting fresh.", "INFO")

    df_new_seasons = scraper.scrape_all_seasons(df_competitions, start_index, limit)

    # --- NEW: Season filtering ---
    if seasons and not df_new_seasons.empty:
        def matches_season(season_value: str, filter_seasons: List[str]) -> bool:
            for filter_season in filter_seasons:
                if "/" in filter_season:
                    if season_value == filter_season:
                        return True
                else:
                    if season_value == filter_season:
                        return True
                    if "/" in season_value:
                        parts = season_value.split("/")
                        if filter_season in parts:
                            return True
            return False

        original_season_count = len(df_new_seasons)
        df_new_seasons = df_new_seasons[df_new_seasons["season"].apply(
            lambda x: matches_season(str(x), seasons)
        )]
        filtered_season_count = len(df_new_seasons)
        scraper._log(
            f"Filtering by seasons: {seasons} | Original: {original_season_count} | Filtered: {filtered_season_count}",
            "INFO"
        )
        if filtered_season_count == 0:
            return pd.DataFrame(), {"total_seasons": 0}

    if append_to_existing and not existing_df.empty and not df_new_seasons.empty:
        existing_keys = set(
            f"{row['competition']}_{row['competition_id']}_{row['season']}"
            for _, row in existing_df.iterrows()
        )
        new_rows = [
            row
            for _, row in df_new_seasons.iterrows()
            if f"{row['competition']}_{row['competition_id']}_{row['season']}" not in existing_keys
        ]
        if new_rows:
            df_truly_new = pd.DataFrame(new_rows)
            df_seasons = pd.concat([existing_df, df_truly_new], ignore_index=True)
        else:
            df_seasons = existing_df
    else:
        df_seasons = df_new_seasons

    if save_csv and not df_seasons.empty:
        scraper.save_seasons_csv(df_seasons)
    if create_dirs and not df_seasons.empty:
        scraper.create_seasons_directory_structure(df_seasons)
    summary = scraper.get_seasons_summary(df_seasons)
    if countries:
        summary["filtered_countries"] = countries
    if seasons:
        summary["filtered_seasons"] = seasons
    return df_seasons, summary


def find_resume_index(scraper_season, df_competitions: pd.DataFrame) -> int:
    """
    Find the index from which to resume scraping based on already processed seasons.

    Args:
        df_competitions (pd.DataFrame): DataFrame with competitions.

    Returns:
        int: Index to resume from.
    """
    try:
        try:
            existing_seasons = scraper_season.load_seasons_csv()
        except Exception:
            scraper_season._log("No existing seasons found", "INFO")
            return 0

        if existing_seasons.empty:
            return 0

        processed_competitions = set(
            f"{row['competition']}_{row['competition_id']}"
            for _, row in existing_seasons.iterrows()
        )
        for idx, row in df_competitions.iterrows():
            key = f"{row['competition']}_{row['competition_id']}"
            if key not in processed_competitions:
                scraper_season._log(f"Resume point found at index {idx}: {row['competition']}", "INFO")
                return idx

        scraper_season._log("All competitions already processed", "INFO")
        return len(df_competitions)
    except Exception as e:
        scraper_season._log(f"Error finding resume index: {e}", "WARNING")
        return 0


def resume_seasons_scraping(
    scraper_season,
    df_competitions: pd.DataFrame,
    save_csv: bool = True,
    create_dirs: bool = True,
    limit: Optional[int] = None,
    seasons: Optional[List[str]] = None 
) -> Tuple[pd.DataFrame, Dict]:
    """
    Resume scraping of seasons from where it left off.

    Args:
        df_competitions (pd.DataFrame): DataFrame with competitions.
        save_csv (bool): Whether to save to CSV.
        create_dirs (bool): Whether to create directory structure.
        limit (Optional[int]): Limit of competitions to process.
        seasons (Optional[List[str]]): Filter by seasons.

    Returns:
        Tuple[pd.DataFrame, Dict]: DataFrame of seasons and summary.
    """
    start_index = find_resume_index(scraper_season, df_competitions)
    if start_index >= len(df_competitions):
        scraper_season._log("Nothing left to process", "INFO")
        existing_df = scraper_season.load_seasons_csv()
        summary = scraper_season.get_seasons_summary(existing_df)
        return existing_df, summary

    scraper_season._log(f"Resuming from competition {start_index + 1}/{len(df_competitions)}", "INFO")
    return scrape_and_save_seasons(
        df_competitions,
        save_csv=save_csv,
        create_dirs=create_dirs,
        start_index=start_index,
        limit=limit,
        append_to_existing=True,
        storage_type=scraper_season.storage.storage_type,
        s3_bucket=getattr(scraper_season.storage, 's3_bucket', None),
        seasons=seasons 
    )


def smart_scrape_seasons(
    df_competitions: pd.DataFrame,
    restart_from_zero: bool = False,
    batch_size: int = 100,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    countries: Optional[List[str]] = None,
    fuzzy_threshold: float = 80,
    seasons: Optional[List[str]] = None,
    create_dirs: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Smart function to automatically detect whether to continue or start from scratch,
    with optional country and season filtering.

    Args:
        df_competitions (pd.DataFrame): Competitions DataFrame.
        restart_from_zero (bool): If True, deletes existing data and starts from scratch.
        batch_size (int): Number of competitions to process in this batch.
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        countries (Optional[List[str]]): List of countries to filter.
        fuzzy_threshold (float): Fuzzy match threshold.
        seasons (Optional[List[str]]): List of seasons to filter.

    Returns:
        Tuple[pd.DataFrame, Dict]: DataFrame of seasons and summary.
    """
    scraper = ScraperSeason(storage_type=storage_type, s3_bucket=s3_bucket)
    storage = scraper.storage
    csv_path = os.path.join(scraper.schema_dir, "all_seasons.csv")

    if batch_size is None:
        batch_size = len(df_competitions)

    if restart_from_zero and storage.file_exists(csv_path):
        if storage_type == "local":
            os.remove(csv_path)
        else:
            s3_client = storage.s3_client
            s3_client.delete_object(Bucket=storage.s3_bucket, Key=csv_path)
        scraper._log("Restarting from zero - previous file deleted", "INFO")

    # Country filtering (existing logic)
    if countries:
        def matches_country(country_name: str, target_countries: List[str], threshold: float = 80) -> bool:
            country_lower = country_name.lower()
            if any(country_lower == target.lower() for target in target_countries):
                return True
            for target in target_countries:
                pattern = f"^{re.escape(target)}[_\\s\\-]?[a-zA-Z0-9]*$"
                if re.search(pattern, country_name, re.IGNORECASE):
                    return True
            best_match = process.extractOne(
                country_lower, [target.lower() for target in target_countries], scorer=fuzz.token_sort_ratio
            )
            if best_match and best_match[1] >= threshold:
                return True
            return False

        original_count = len(df_competitions)
        df_competitions = df_competitions[df_competitions["country"].apply(
            lambda x: matches_country(x, countries, fuzzy_threshold)
        )]
        filtered_count = len(df_competitions)
        scraper._log(
            f"Filtering by countries: {', '.join(countries)} | Original: {original_count} | Filtered: {filtered_count}",
            "INFO",
        )
        if filtered_count == 0:
            return pd.DataFrame(), {"total_seasons": 0}

    # Resume logic (existing)
    start_idx = 0
    existing_seasons = pd.DataFrame()
    try:
        if not restart_from_zero:
            existing_seasons = scraper.load_seasons_csv()
            if countries:
                original_existing = len(existing_seasons)
                existing_seasons = existing_seasons[existing_seasons["country"].apply(
                    lambda x: matches_country(x, countries, fuzzy_threshold)
                )]
                scraper._log(
                    f"Existing seasons filtered: {len(existing_seasons)}/{original_existing}",
                    "INFO",
                )
            processed_comps = set(
                f"{row['competition']}_{row['competition_id']}"
                for _, row in existing_seasons.iterrows()
            )
            for idx, row in df_competitions.iterrows():
                key = f"{row['competition']}_{row['competition_id']}"
                if key not in processed_comps:
                    start_idx = idx
                    break
            else:
                scraper._log("All competitions already processed", "INFO")
                summary = scraper.get_seasons_summary(existing_seasons)
                summary["filtered_countries"] = countries if countries else None
                return existing_seasons, summary

        scraper._log(f"Starting from competition {start_idx + 1}/{len(df_competitions)}", "INFO")
        scraper._log(f"Existing seasons: {len(existing_seasons)}", "INFO")
        scraper._log(f"Remaining competitions: {len(df_competitions) - start_idx}", "INFO")
    except Exception as e:
        scraper._log(f"No previous data or error loading: {e}", "WARNING")
        existing_seasons = pd.DataFrame()
        start_idx = 0

    scraper._log(f"Processing {min(batch_size, len(df_competitions) - start_idx)} competitions...", "INFO")
    df_new_seasons = scraper.scrape_all_seasons(
        df_competitions,
        start_index=start_idx,
        limit=batch_size,
        max_retries=3
    )

    if seasons and not df_new_seasons.empty:
        def matches_season(season_value: str, filter_seasons: List[str]) -> bool:
            for filter_season in filter_seasons:
                if "/" in filter_season:
                    # Exact match for YYYY/YYYY
                    if season_value == filter_season:
                        return True
                else:
                    # YYYY: match exact or part of YYYY/YYYY
                    if season_value == filter_season:
                        return True
                    if "/" in season_value:
                        parts = season_value.split("/")
                        if filter_season in parts:
                            return True
            return False

        original_season_count = len(df_new_seasons)
        df_new_seasons = df_new_seasons[df_new_seasons["season"].apply(
            lambda x: matches_season(str(x), seasons)
        )]
        filtered_season_count = len(df_new_seasons)
        scraper._log(
            f"Filtering by seasons: {seasons} | Original: {original_season_count} | Filtered: {filtered_season_count}",
            "INFO"
        )
        if filtered_season_count == 0:
            return pd.DataFrame(), {"total_seasons": 0}

    # Combine with existing (existing logic)
    if not existing_seasons.empty and not df_new_seasons.empty and not restart_from_zero:
        existing_keys = set(
            f"{row['competition']}_{row['competition_id']}_{row['season']}"
            for _, row in existing_seasons.iterrows()
        )
        new_rows = [
            row for _, row in df_new_seasons.iterrows()
            if f"{row['competition']}_{row['competition_id']}_{row['season']}" not in existing_keys
        ]
        if new_rows:
            df_truly_new = pd.DataFrame(new_rows)
            df_final = pd.concat([existing_seasons, df_truly_new], ignore_index=True)
            scraper._log(f"Combining: {len(existing_seasons)} existing + {len(df_truly_new)} new = {len(df_final)} total", "INFO")
        else:
            df_final = existing_seasons
            scraper._log("No truly new seasons found", "INFO")
    else:
        df_final = df_new_seasons
        scraper._log(f"Total seasons: {len(df_final)}", "INFO")

    # Save result
    if not df_final.empty:
        saved_path = scraper.save_seasons_csv(df_final)
        scraper._log(f"Seasons saved: {saved_path}", "INFO")

        if create_dirs:
            scraper.create_seasons_directory_structure(df_final)

        summary = scraper.get_seasons_summary(df_final)
        summary["progress"] = {
            "processed_competitions": start_idx + min(batch_size, len(df_competitions) - start_idx),
            "total_competitions": len(df_competitions),
            "percentage": ((start_idx + min(batch_size, len(df_competitions) - start_idx)) / len(df_competitions)) * 100
        }
        scraper._log(
            f"Progress: {summary['progress']['processed_competitions']}/{summary['progress']['total_competitions']} ({summary['progress']['percentage']:.1f}%)",
            "INFO"
        )
    else:
        summary = scraper.get_seasons_summary(df_final)
    if countries:
        summary["filtered_countries"] = countries
    if seasons:
        summary["filtered_seasons"] = seasons

    return df_final, summary


def load_existing_seasons(
    storage_type: str = "local", s3_bucket: Optional[str] = None
) -> pd.DataFrame:
    """
    Load existing seasons from CSV.

    Args:
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.

    Returns:
        pd.DataFrame: Seasons DataFrame.
    """
    scraper = ScraperSeason(storage_type=storage_type, s3_bucket=s3_bucket)
    return scraper.load_seasons_csv()


# -----------------------------------------------------------
# ------------------ Testing functions ----------------------
# -----------------------------------------------------------
def test_scraper_season() -> bool:
    """
    Test function for ScraperSeason.

    Returns:
        bool: True if test passes, False otherwise.
    """
    print("=== Testing ScraperSeason ===")
    try:
        df_test, summary = scrape_and_save_seasons(
            df_competitions=pd.DataFrame(),  # Provide a small test DataFrame here
            save_csv=False,
            create_dirs=False,
            limit=2,
        )
        print(f"\nSummary: {summary}")
        if not df_test.empty:
            print(df_test.head(3)[["competition", "season", "country"]])
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    test_scraper_season()