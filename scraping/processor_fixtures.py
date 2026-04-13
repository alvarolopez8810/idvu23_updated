"""
ProcessorFixture
================

Processes downloaded fixture JSON files, extracting match details and organizing them
into DataFrames for further analysis. Uses BaseScraper for logging and storage management.
All DataFrames are saved into the schema directory.

Author: Sports Data Campus
Date: October 2025
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

from scraper_base import BaseScraper
from storage_manager import StorageManager
from utils import (
    get_season_name_from_url, 
    get_tournament_id, 
    sanitize_dir_name,
    normalize_season_string,
    extend_dataframe_with_unique_rows
)


class ProcessorFixture(BaseScraper):
    """
    Processor for fixture JSON files, producing normalized DataFrames.
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
        self.processed_files = 0
        self.skipped_files = 0
        self.error_files = 0

    def _get_fixture_path(self, season_row: pd.Series) -> Optional[str]:
        """
        Build the fixture.json path for a season row.
        """
        try:
            season_name = get_season_name_from_url(season_row["results_url"])
            if not season_name:
                return None
            continent = sanitize_dir_name(season_row["continent"])
            country = sanitize_dir_name(season_row["country"])
            competition = sanitize_dir_name(season_row["competition"])
            competition_id = str(season_row["competition_id"])
            season_name = normalize_season_string(season_name)
            dir_path = os.path.join(
                self.data_dir, continent, country, competition, competition_id, season_name
            )
            return os.path.join(dir_path, "fixture.json")
        except Exception as exc:
            self._log(f"Error building fixture path: {exc}", "ERROR")
            return None

    def _load_json(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Load JSON content from local path or S3 key.
        """
        try:
            if self.storage.storage_type == "local":
                with open(path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            resp = self.storage.s3_client.get_object(Bucket=self.storage.s3_bucket, Key=path)
            body = resp["Body"].read()
            return json.loads(body.decode("utf-8"))
        except Exception as exc:
            self._log(f"Failed to load JSON {path}: {exc}", "WARNING")
            return None

    def _extract_matches(self, fixture_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Return a list of raw match dicts from fixture JSON.
        """
        if not isinstance(fixture_json, dict):
            return []
        if "fixtures" in fixture_json and isinstance(fixture_json["fixtures"], list):
            return fixture_json["fixtures"]
        if "match" in fixture_json and isinstance(fixture_json["match"], list):
            return fixture_json["match"]
        for v in fixture_json.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return []

    def _normalize_match(
        self, raw: Dict[str, Any], season_row: pd.Series, tournament_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize a raw match dictionary to a flat record with consistent keys.
        """
        try:
            match_info = raw.get("matchInfo") if isinstance(raw, dict) else None
            if not match_info:
                match_info = raw

            match_id = match_info.get("id") or match_info.get("matchId") or raw.get("id")
            date_raw = match_info.get("date") or match_info.get("startDate") or raw.get("date")
            time_raw = match_info.get("time") or raw.get("time")

            contestants = match_info.get("contestant") or match_info.get("contestants") or []
            home = contestants[0].get("name") if len(contestants) > 0 and contestants[0] else None
            away = contestants[1].get("name") if len(contestants) > 1 and contestants[1] else None

            score = match_info.get("score") or {}
            home_score = score.get("home") or score.get("homeGoals") or None
            away_score = score.get("away") or score.get("awayGoals") or None

            venue = match_info.get("venue") or {}
            venue_name = venue.get("shortName") or venue.get("longName") or venue.get("name")

            status = match_info.get("matchStatus") or match_info.get("status")
            coverage = match_info.get("coverageLevel")
            last_updated = match_info.get("lastUpdated") or match_info.get("updatedAt")

            date_iso = self._normalize_date(date_raw)

            attendance = match_info.get('attendance')
            weather = match_info.get('weather', {})

            record = {
                "match_id": match_id,
                "date": date_iso,
                "date_raw": date_raw,
                "time": time_raw,
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "venue": venue_name,
                "status": status,
                "coverage": coverage,
                "last_updated": last_updated,
                "tournament_id": tournament_id,
                "competition": season_row.get("competition"),
                "competition_id": season_row.get("competition_id"),
                "country": season_row.get("country"),
                "continent": season_row.get("continent"),
                "season": season_row.get("season"),
                "fixture_path": self._get_fixture_path(season_row),
                "attendance": attendance,
                "weather_temperature": weather.get("temperature"),
                "weather_conditions": weather.get("conditions")
            }
            return record
        except Exception as exc:
            self._log(f"Normalization error: {exc}", "WARNING")
            return None

    @staticmethod
    def _normalize_date(raw: Optional[str]) -> Optional[str]:
        """
        Try to parse common date formats to ISO date string YYYY-MM-DD.
        """
        if not raw:
            return None
        if isinstance(raw, str) and raw.endswith("Z"):
            try:
                return datetime.fromisoformat(raw.replace("Z", "")).date().isoformat()
            except Exception:
                pass
        known_formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]
        for fmt in known_formats:
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except Exception:
                continue
        return raw

    def process_season(self, season_row: pd.Series) -> List[Dict[str, Any]]:
        """
        Process a single season row: locate fixture.json, load, extract and normalize matches.
        """
        json_path = self._get_fixture_path(season_row)
        if not json_path:
            self._log(f"Missing fixture path for season row: {season_row.get('competition')} - {season_row.get('season')}", "WARNING")
            self.skipped_files += 1
            return []

        if not self.storage.file_exists(json_path):
            self._log(f"Fixture file not found: {json_path}", "WARNING")
            self.skipped_files += 1
            return []

        fixture_json = self._load_json(json_path)
        if not fixture_json:
            self.error_files += 1
            return []

        tournament_id = get_tournament_id(season_row.get("season_url") or season_row.get("season_url", ""))
        raw_matches = self._extract_matches(fixture_json)
        records: List[Dict[str, Any]] = []
        for raw in raw_matches:
            normalized = self._normalize_match(raw, season_row, tournament_id)
            if normalized:
                records.append(normalized)

        self.processed_files += 1
        self._log(f"Processed fixture: {json_path} → {len(records)} matches", "INFO")
        return records

    def create_matches_dataframe(
        self,
        df_seasons: pd.DataFrame,
        filters: Optional[Dict[str, Any]] = None,
        save_consolidated: bool = True,
        consolidated_filename: Optional[str] = None,
        save_individual: bool = False,
    ) -> pd.DataFrame:
        """
        Process many seasons and return consolidated DataFrame of matches.
        """
        self.processed_files = 0
        self.skipped_files = 0
        self.error_files = 0

        df_to_process = self._apply_filters(df_seasons, filters)
        self._log(f"Starting processing of {len(df_to_process)} seasons", "INFO")
        all_records: List[Dict[str, Any]] = []

        for idx, (_, row) in enumerate(df_to_process.iterrows()):
            try:
                self._log(f"Processing season {idx+1}/{len(df_to_process)}: {row.get('competition')} - {row.get('season')}", "DEBUG")
                records = self.process_season(row)
                if records:
                    all_records.extend(records)
                    if save_individual:
                        json_path = self._get_fixture_path(row)
                        if json_path:
                            self._save_individual_results(records, json_path)
                if (idx + 1) % 20 == 0:
                    self._print_progress(idx + 1, len(df_to_process), len(all_records))
            except KeyboardInterrupt:
                self._log("Processing interrupted by user", "WARNING")
                break
            except Exception as exc:
                self._log(f"Error processing season row {idx}: {exc}", "ERROR")
                self.error_files += 1
                continue

        if not all_records:
            self._log("No matches were processed", "WARNING")
            return pd.DataFrame()

        df_matches = pd.DataFrame(all_records)
        if "date" in df_matches.columns:
            try:
                df_matches["date"] = pd.to_datetime(df_matches["date"], errors="ignore")
            except Exception:
                pass

        if save_consolidated:
            filename = consolidated_filename or "all_matches.csv"
            schema_path = os.path.join(self.schema_dir, filename)
            self.storage.ensure_directory(self.schema_dir)
            df_extended = extend_dataframe_with_unique_rows(self.storage, df_matches, schema_path)
            self._save_results(df_extended, schema_path)

        self._print_final_summary(df_matches, filters)
        return df_matches

    def _apply_filters(self, df: pd.DataFrame, filters: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply filters to seasons DataFrame (continent, country, competition, etc.)
        """
        if filters is None or not filters:
            return df
        df_filtered = df.copy()
        for col, val in filters.items():
            if col in df_filtered.columns:
                if isinstance(val, list):
                    df_filtered = df_filtered[df_filtered[col].isin(val)]
                else:
                    df_filtered = df_filtered[df_filtered[col] == val]
                self._log(f"Filter applied - {col}: {val} → {len(df_filtered)} seasons", "DEBUG")
        return df_filtered

    def _save_results(self, df_matches: pd.DataFrame, path: str) -> None:
        """
        Save the consolidated DataFrame to CSV in the schema directory.
        """
        try:
            self.storage.save_dataframe_csv(df_matches, path)
            self._log(f"Consolidated matches saved to: {path}", "INFO")
        except Exception as e:
            self._log(f"Error saving consolidated results: {e}", "ERROR")

    def _save_individual_results(self, matches: List[Dict[str, Any]], json_path: str) -> None:
        """
        Save individual season matches as CSV next to fixture.json.
        """
        try:
            if not matches:
                return
            df_temp = pd.DataFrame(matches)
            fixture_dir = os.path.dirname(json_path)
            csv_path = os.path.join(fixture_dir, "matches.csv")
            self.storage.save_dataframe_csv(df_temp, csv_path)
            self._log(f"Saved individual matches: {csv_path}", "INFO")
        except Exception as e:
            self._log(f"Error saving individual results: {e}", "ERROR")

    def _print_progress(self, current: int, total: int, total_matches: int) -> None:
        """
        Print processing progress.
        """
        percentage = (current / total) * 100
        self._log(
            f"Progress: {current}/{total} ({percentage:.1f}%) | "
            f"Processed: {self.processed_files} | Skipped: {self.skipped_files} | "
            f"Errors: {self.error_files} | Total matches: {total_matches}",
            "INFO"
        )

    def _print_final_summary(self, df_matches: pd.DataFrame, filters: Optional[Dict[str, Any]]) -> None:
        """
        Print final processing summary.
        """
        self._log("=" * 50, "INFO")
        self._log("FINAL SUMMARY", "INFO")
        self._log("=" * 50, "INFO")
        self._log(f"Processed files: {self.processed_files}", "INFO")
        self._log(f"Skipped files: {self.skipped_files}", "INFO")
        self._log(f"Error files: {self.error_files}", "INFO")
        self._log(f"Total matches extracted: {len(df_matches)}", "INFO")
        if not df_matches.empty:
            self._log(f"Unique competitions: {df_matches['competition'].nunique()}", "INFO")
            self._log(f"Unique countries: {df_matches['country'].nunique()}", "INFO")
            teams = pd.concat([df_matches['home_team'], df_matches['away_team']]).nunique()
            self._log(f"Unique teams: {teams}", "INFO")
            if 'date' in df_matches.columns and df_matches['date'].notna().any():
                try:
                    valid_dates = df_matches[df_matches['date'].notna()]
                    if not valid_dates.empty:
                        self._log(f"Date range: {valid_dates['date'].min()} to {valid_dates['date'].max()}", "INFO")
                except Exception:
                    pass
        if filters:
            self._log(f"Filters applied: {filters}", "INFO")


# -----------------------------------------------------------
# ------------------ Convenience functions ------------------
# -----------------------------------------------------------
def process_matches_by_filters(
    df_seasons: pd.DataFrame,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    competition: Optional[str] = None,
    save_consolidated: bool = True,
    consolidated_filename: Optional[str] = None,
    save_individual: bool = False,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
) -> pd.DataFrame:
    """
    Process matches applying common filters and save consolidated CSV to schema dir.
    """
    filters: Dict[str, Any] = {}
    if continent:
        filters["continent"] = continent
    if country:
        filters["country"] = country
    if competition:
        filters["competition"] = competition

    processor = ProcessorFixture(storage_type=storage_type, s3_bucket=s3_bucket)
    return processor.create_matches_dataframe(
        df_seasons,
        filters=filters,
        save_consolidated=save_consolidated,
        consolidated_filename=consolidated_filename,
        save_individual=save_individual,
    )


def process_all_matches(
    df_seasons: pd.DataFrame,
    save_consolidated: bool = True,
    consolidated_filename: Optional[str] = None,
    save_individual: bool = False,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
) -> pd.DataFrame:
    """
    Process all matches without filters.
    """
    processor = ProcessorFixture(storage_type=storage_type, s3_bucket=s3_bucket)
    return processor.create_matches_dataframe(
        df_seasons,
        save_consolidated=save_consolidated,
        consolidated_filename=consolidated_filename,
        save_individual=save_individual,
    )


def load_existing_matches(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    consolidated_path: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Load the consolidated matches DataFrame from the schema directory.
    """
    processor = ProcessorFixture(storage_type=storage_type, s3_bucket=s3_bucket)
    if not consolidated_path:
        consolidated_path = os.path.join(processor.schema_dir, "all_matches.csv")
    try:
        df_matches = processor.storage.load_dataframe_csv(consolidated_path)
        processor._log(f"Loaded {len(df_matches)} matches from {consolidated_path}", "INFO")
    except Exception as e:
        processor._log(f"Error loading consolidated matches: {e}", "ERROR")
        return pd.DataFrame()
    if filters:
        for column, value in filters.items():
            if column in df_matches.columns:
                if isinstance(value, list):
                    df_matches = df_matches[df_matches[column].isin(value)]
                else:
                    df_matches = df_matches[df_matches[column] == value]
        processor._log(f"Applied filters: {filters}", "INFO")
    return df_matches


# -----------------------------------------------------------
# ------------------ Testing functions ----------------------
# -----------------------------------------------------------
def test_processor_fixture() -> bool:
    """
    Basic self-test: loads seasons and processes a small subset.
    """
    print("=== Testing ProcessorFixture ===")
    try:
        from scraper_seasons import load_existing_seasons
        df_seasons = load_existing_seasons(storage_type="local")
        if df_seasons.empty:
            print("No seasons available for testing")
            return False
        df_small = df_seasons.head(5)
        df_matches = process_matches_by_filters(df_small, save_individual=False)
        print(f"Processed {len(df_matches)} matches from {len(df_small)} seasons")
        return not df_matches.empty
    except Exception as exc:
        print(f"Test failed: {exc}")
        return False


if __name__ == "__main__":
    test_processor_fixture()