"""
Competition Scraper
===================

This module handles scraping and processing of sports competition data
from ScoresWay, organizing the information into DataFrames and creating
directory structures for data storage.

Author: Sports Data Campus - Lucas Bracamonte, Eduardo M. Pereira, Jaime Jimenez
Date: July 2025
"""

import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple

from utils import (
    sanitize_dir_name,
    extend_dataframe_with_unique_rows
)
from scraper_base import BaseScraper


class ScraperCompetition(BaseScraper):
    """
    Scraper for sports competitions from ScoresWay.
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
        continents: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        competitions_filter_dict: Optional[dict] = None
    ) -> None:
        """
        Initialize the competition scraper.

        Args:
            base_url (str): Base URL of the website.
            storage_type (str): Storage type ('local' or 's3').
            s3_bucket (Optional[str]): S3 bucket name (optional).
            data_dir (str): Directory for storing data.
            schema_dir (str): Directory for storing schema files.
            log_dir (str): Directory for logs.
            log_level (str): Logging level.
            verbose (bool): Verbose output.
            continents (Optional[List[str]]): Continents to filter.
            countries (Optional[List[str]]): Countries to filter.
        """
        super().__init__(
            base_url=base_url,
            storage_type=storage_type,
            s3_bucket=s3_bucket,
            data_dir=data_dir,
            schema_dir=schema_dir,
            log_dir=log_dir,
            log_level=log_level,
            verbose=verbose
        )
        self.competitions_url: str = f"{self.base_url}/en_GB/soccer/competitions"
        self.continents = continents
        self.countries = countries
        self.competitions_filter_dict = competitions_filter_dict  
        self._log(f"Initialized ScraperCompetition with storage: {self.storage.storage_type.upper()}", "INFO")
        self._log(f"   - Filters - Continents: {self.continents if self.continents else 'None'}, "
                  f"Countries: {self.countries if self.countries else 'None'}, Competitions: "
                  f"{self.competitions_filter_dict if self.competitions_filter_dict else 'None'}", "INFO")

    def fetch_competitions_data(self) -> Dict:
        """
        Fetch competition data from the website.

        Returns:
            Dict: JSON data of competitions.

        Raises:
            Exception: If data cannot be fetched.
        """
        try:
            self._log(f"{self.fetch_competitions_data.__name__} - Fetching competition data...", "INFO")
            response = requests.get(self.competitions_url, headers=self.headers)
            self._log(f"Peticion: {self.competitions_url}", "INFO")
            self._log(f"Headers: {self.headers}", "INFO")
            response.raise_for_status()
            self._log(f"Respuesta: {response.status_code}", "INFO")
            soup = BeautifulSoup(response.text, 'html.parser')
            script = soup.find('script', {'id': 'compData', 'type': 'application/json'})
            if not script:
                raise Exception("Could not find script with ID 'compData'.")

            data = json.loads(script.string)
            return data

        except requests.RequestException as e:
            self._log(f"Request error while fetching competition data: {e}", "ERROR")
            raise Exception(f"Request error while fetching competition data: {e}")
        except json.JSONDecodeError as e:
            self._log(f"JSON parsing error while fetching competition data: {e}", "ERROR")
            raise Exception(f"JSON parsing error while fetching competition data: {e}")
        except Exception as e:
            self._log(f"Unexpected error while fetching competition data: {e}", "ERROR")
            raise Exception(f"Unexpected error while fetching competition data: {e}")

    def parse_competition_data(self, data: Dict) -> pd.DataFrame:
        """
        Parse competition data and convert to DataFrame.

        Args:
            data (Dict): JSON data of competitions.

        Returns:
            pd.DataFrame: DataFrame with competition information.
        """
        self._log(f"{self.parse_competition_data.__name__} - Parsing competition data...", "INFO")
        competitions: List[Dict] = []
        filter_set = self._build_competition_filter_set() if self.competitions_filter_dict else None

        try:
            for continent in data.get('continents', []):
                continent_name = continent.get('name')
                if self.continents and continent_name not in self.continents:
                    continue
                for country in continent.get('countries', []):
                    country_name = country.get('name')
                    if self.countries and country_name not in self.countries:
                        continue
                    for comp in country.get('comps', []):
                        comp_name = comp.get('name')
                        if filter_set and (continent_name, country_name, comp_name) not in filter_set:
                            continue
                        competition_info = {
                            'continent': continent_name,
                            'country': country_name,
                            'competition': comp_name,
                            'competition_id': comp.get('id'),
                            'url': f"{self.base_url}{comp.get('url')}" if comp.get('url') else None,
                            'crest': f"{self.base_url}{comp.get('crest')}" if comp.get('crest') else None,
                            'top': comp.get('top'),
                            'order': comp.get('ord')
                        }
                        competitions.append(competition_info)
                        self._log(f"   - Processed: {continent_name} - {country_name} - {comp_name}", "DEBUG")
            df = pd.DataFrame(competitions)
            self._log(f"✅ Parsed {len(competitions)} competitions", "INFO")
            return df
        except Exception as e:
            self._log(f"Error parsing competition data: {e}", "ERROR")
            raise Exception(f"Error parsing competition data: {e}")
        
    def get_country_competitions_dict(self) -> Dict[str, List[Tuple[str, int]]]:
        """
        Fetches competition data and returns a dictionary mapping each country
        to a list of (competition_name, competition_id) tuples.

        Returns:
            Dict[str, List[Tuple[str, int]]]: {country: [(competition_name, competition_id), ...], ...}
        """
        data = self.fetch_competitions_data()
        country_dict: Dict[str, List[Tuple[str, int]]] = {}

        for continent in data.get('continents', []):
            if self.continents and continent.get('name') not in self.continents:
                continue
            for country in continent.get('countries', []):
                country_name = country.get('name')
                if self.countries and country_name not in self.countries:
                    continue
                for comp in country.get('comps', []):
                    comp_tuple = (comp.get('name'), comp.get('id'))
                    if country_name not in country_dict:
                        country_dict[country_name] = []
                    country_dict[country_name].append(comp_tuple)
        return country_dict

    def save_competitions_csv(self, df: pd.DataFrame, filename: str = 'all_competitions.csv') -> str:
        """
        Save the competitions DataFrame as a CSV file in the schema directory.

        Args:
            df (pd.DataFrame): DataFrame with competitions.
            filename (str): CSV file name.

        Returns:
            str: Path where the file was saved.
        """
        try:
            filepath = os.path.join(self.schema_dir, filename)
            df_extended = extend_dataframe_with_unique_rows(self.storage, df, filepath)
            saved_path = self.storage.save_dataframe_csv(df_extended, filepath)
            self._log(f"✅ Competitions saved at: {saved_path}", "INFO")
            return saved_path
        except Exception as e:
            self._log(f"Error saving CSV: {e}", "ERROR")
            raise Exception(f"Error saving CSV: {e}")

    def load_competitions_csv(self, filename: str = 'all_competitions.csv') -> pd.DataFrame:
        """
        Load the competitions DataFrame from a CSV file in the schema directory.

        Args:
            filename (str): CSV file name.

        Returns:
            pd.DataFrame: DataFrame with competitions.

        Raises:
            Exception: If file is not found or cannot be loaded.
        """
        try:
            filepath = os.path.join(self.schema_dir, filename)
            df = self.storage.load_dataframe_csv(filepath)
            storage_type = "S3" if self.storage.storage_type == 's3' else "local"
            self._log(f"✅ Competitions loaded from: {filepath} ({storage_type})", "INFO")
            return df
        except FileNotFoundError:
            storage_location = f"S3 bucket '{self.storage.s3_bucket}'" if self.storage.storage_type == 's3' else "local filesystem"
            self._log(f"File not found: {filepath} in {storage_location}", "ERROR")
            raise Exception(f"File not found: {filepath} in {storage_location}")
        except Exception as e:
            self._log(f"Error loading CSV: {e}", "ERROR")
            raise Exception(f"Error loading CSV: {e}")

    def create_directory_structure(self, df: pd.DataFrame) -> None:
        """
        Create directory structure based on competitions.

        Args:
            df (pd.DataFrame): DataFrame with competitions.
        """
        try:
            self.storage.ensure_directory(self.data_dir)
            created_dirs = 0

            for _, row in df.iterrows():
                required_fields = ['continent', 'country', 'competition', 'competition_id']
                if not all(pd.notna(row[field]) for field in required_fields):
                    continue

                continent_dir = sanitize_dir_name(row['continent'])
                country_dir = sanitize_dir_name(row['country'])                
                competition_dir = sanitize_dir_name(row['competition'])
                competition_id = str(row['competition_id'])

                full_path = os.path.join(
                    self.data_dir,
                    continent_dir,
                    country_dir,
                    competition_dir,
                    competition_id
                )

                self.storage.ensure_directory(full_path)
                created_dirs += 1

            storage_type = "S3" if self.storage.storage_type == 's3' else "local"
            self._log(f"✅ Directory structure created successfully in {storage_type}", "INFO")
            self._log(f"   - Directories created: {created_dirs}", "INFO")
            self._log(f"   - Total competitions processed: {len(df)}", "INFO")

        except Exception as e:
            self._log(f"Error creating directory structure: {e}", "ERROR")
            raise Exception(f"Error creating directory structure: {e}")

    def get_competition_summary(self, df: pd.DataFrame) -> Dict:
        """
        Generate a statistical summary of competitions.

        Args:
            df (pd.DataFrame): DataFrame with competitions.

        Returns:
            Dict: Statistical summary.
        """
        try:
            summary = {
                'total_competitions': len(df),
                'total_continents': df['continent'].nunique(),
                'total_countries': df['country'].nunique(),
                'competitions_by_continent': df['continent'].value_counts().to_dict(),
                'top_competitions': df[df['top'] == True]['competition'].tolist() if 'top' in df.columns else []
            }
            self._log(f"Competition summary generated: {summary}", "DEBUG")
            return summary
        except Exception as e:
            self._log(f"Error generating summary: {e}", "ERROR")
            raise Exception(f"Error generating summary: {e}")

    def _build_competition_filter_set(self):
        """
        Builds a set of (continent, country, competition_name) for fast filtering.
        """
        filter_set = set()
        if self.competitions_filter_dict:
            for continent, countries in self.competitions_filter_dict.items():
                for country, comps in countries.items():
                    for comp_name, _ in comps:
                        filter_set.add((continent, country, comp_name))
        return filter_set


# -----------------------------------------------------------
# ------------------ Convenience functions ------------------
# -----------------------------------------------------------
def fetch_country_competitions_dict(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    schema_dir: str = "schema",
    log_dir: str = "logs",
    log_level: str = "INFO",
    verbose: bool = True,
    continents: Optional[List[str]] = None,
    countries: Optional[List[str]] = None
) -> Dict[str, List[Tuple[str, int]]]:
    """
    Loads competitions and returns a dictionary mapping each country to a list of (competition_name, competition_id).

    Args:
        storage_type (str): Storage type.
        s3_bucket (Optional[str]): S3 bucket name.
        schema_dir (str): Directory for schema files.
        log_dir (str): Directory for logs.
        log_level (str): Logging level.
        verbose (bool): Verbose output.
        continents (Optional[List[str]]): Continents to filter.
        countries (Optional[List[str]]): Countries to filter.

    Returns:
        Dict[str, List[Tuple[str, int]]]: {country: [(competition_name, competition_id), ...], ...}
    """
    scraper = ScraperCompetition(
        storage_type=storage_type,
        s3_bucket=s3_bucket,
        schema_dir=schema_dir,
        log_dir=log_dir,
        log_level=log_level,
        verbose=verbose,
        continents=continents,
        countries=countries
    )
    country_comp_dict = scraper.get_country_competitions_dict()
    return country_comp_dict


def scrape_and_save_competitions(
    save_csv: bool = True,
    create_dirs: bool = True,
    continents: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    schema_dir: str = "schema",
    log_dir: str = "logs",
    log_level: str = "INFO",
    verbose: bool = True,
    competitions_dict: Optional[dict] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    Main function to scrape and save competitions.

    Args:
        save_csv (bool): Whether to save as CSV.
        create_dirs (bool): Whether to create directory structure.
        continents (Optional[List[str]]): Continents to filter.
        countries (Optional[List[str]]): Countries to filter.
        storage_type (str): Storage type ('local' or 's3').
        s3_bucket (Optional[str]): S3 bucket name.
        schema_dir (str): Directory for schema files.
        log_dir (str): Directory for logs.
        log_level (str): Logging level.
        verbose (bool): Verbose output.

    Returns:
        Tuple[pd.DataFrame, Dict]: DataFrame of competitions and summary.
    """
    scraper = ScraperCompetition(
        storage_type=storage_type,
        s3_bucket=s3_bucket,
        schema_dir=schema_dir,
        log_dir=log_dir,
        log_level=log_level,
        verbose=verbose,
        continents=continents,
        countries=countries,
        competitions_filter_dict=competitions_dict
    )

    try:
        data = scraper.fetch_competitions_data()
        df = scraper.parse_competition_data(data)

        if save_csv:
            scraper.save_competitions_csv(df)

        if create_dirs:
            scraper.create_directory_structure(df)

        summary = scraper.get_competition_summary(df)
        return df, summary

    except Exception as e:
        print(f"❌ Error in scraping: {e}")
        raise


def load_existing_competitions(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    schema_dir: str = "schema",
    log_dir: str = "logs",
    log_level: str = "INFO",
    verbose: bool = True,
    continents: Optional[List[str]] = None,
    countries: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Load competitions from an existing CSV.

    Args:
        storage_type (str): Storage type ('local' or 's3').
        s3_bucket (Optional[str]): S3 bucket name.
        schema_dir (str): Directory for schema files.
        log_dir (str): Directory for logs.
        log_level (str): Logging level.
        verbose (bool): Verbose output.
        continents (Optional[List[str]]): Continents to filter.
        countries (Optional[List[str]]): Countries to filter.

    Returns:
        pd.DataFrame: DataFrame with competitions.
    """
    scraper = ScraperCompetition(
        storage_type=storage_type,
        s3_bucket=s3_bucket,
        schema_dir=schema_dir,
        log_dir=log_dir,
        log_level=log_level,
        verbose=verbose,
        continents=continents,
        countries=countries
    )
    return scraper.load_competitions_csv()


# -----------------------------------------------------------
# ------------------ Testing functions ----------------------
# -----------------------------------------------------------
def test_scraper_competition(
    storage_type: str = "local",
    s3_bucket: Optional[str] = None,
    schema_dir: str = "schema",
    log_dir: str = "logs",
    log_level: str = "INFO",
    verbose: bool = True
) -> bool:
    """
    Test function for the competition scraper.

    Args:
        storage_type (str): Storage type ('local' or 's3').
        s3_bucket (Optional[str]): S3 bucket name.
        schema_dir (str): Directory for schema files.
        log_dir (str): Directory for logs.
        log_level (str): Logging level.
        verbose (bool): Verbose output.

    Returns:
        bool: True if successful, False otherwise.
    """
    print("=== Testing ScraperCompetition ===")
    print(f"Storage mode: {storage_type.upper()}")

    try:
        df, summary = scrape_and_save_competitions(
            storage_type=storage_type,
            s3_bucket=s3_bucket,
            schema_dir=schema_dir,
            log_dir=log_dir,
            log_level=log_level,
            verbose=verbose
        )

        print(f"\n📊 Summary:")
        print(f"   - Total competitions: {summary['total_competitions']}")
        print(f"   - Total continents: {summary['total_continents']}")
        print(f"   - Total countries: {summary['total_countries']}")

        print(f"\n🔝 First 5 competitions:")
        print(df.head())

        return True

    except Exception as e:
        print(f"❌ Error in testing: {e}")
        return False


if __name__ == "__main__":
    # Example usage with local filesystem
    test_scraper_competition(storage_type="local")

    # Example usage with S3
    # test_scraper_competition(storage_type="s3", s3_bucket="arn:aws:s3:::scores-way-data")