"""
Common Utility Functions
========================

This module contains general-purpose functions used throughout the project,
including driver configuration, data cleaning, and URL manipulation.

Author: Sports Data Campus - Lucas Bracamonte, Eduardo M. Pereira, Jaime Jimenez
Date: July 2025
"""

import os
import re
import random
import string
import requests
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urlparse
from fuzzywuzzy import process, fuzz
from typing import Any, Optional, Dict
from urllib.parse import urlparse, unquote

try:
    import boto3
except ImportError:
    boto3 = None  

load_dotenv()



def get_env_variable(var_name: str, default: Optional[Any] = None, required: bool = False) -> Optional[str]:
    """
    Get an environment variable, with options for default value or required flag.

    Args:
        var_name (str): Name of the environment variable.
        default (Any, optional): Default value if variable is not found.
        required (bool, optional): If True and variable is not found, raises ValueError.

    Returns:
        Optional[str]: Value of the environment variable or default.

    Raises:
        ValueError: If required=True and variable is not found.
    """
    value = os.environ.get(var_name)
    if value is None:
        if required:
            raise ValueError(f"Environment variable '{var_name}' is required but not defined.")
        return default
    return value


def get_aws_credentials() -> Dict[str, Optional[str]]:
    """
    Get AWS credentials from environment variables.

    Returns:
        Dict[str, Optional[str]]: Dictionary with AWS credentials.
    """
    return {
        'bucket': get_env_variable('AWS_BUCKET'),
        'region': get_env_variable('AWS_REGION', 'us-east-1'),
        'access_key': get_env_variable('AWS_ACCESS_KEY_ID'),
        'secret_key': get_env_variable('AWS_SECRET_ACCESS_KEY'),
    }


def empty_s3_bucket() -> None:
    """
    Deletes all files and folders recursively from an S3 bucket.

    Raises:
        ValueError: If bucket name is not provided.
        ImportError: If boto3 is not installed.
    """
    if boto3 is None:
        raise ImportError("boto3 is required for S3 operations.")

    aws_creds = get_aws_credentials()
    s3_bucket = aws_creds['bucket']

    # Extract bucket name from ARN if necessary
    if s3_bucket and s3_bucket.startswith('arn:aws:s3:::'):
        s3_bucket = s3_bucket.split(':', 5)[-1]
        print(f"Using S3 bucket: {s3_bucket}")

    if not s3_bucket:
        raise ValueError("S3 bucket is required for 's3' storage mode.")

    # Initialize S3 client with credentials if provided
    if aws_creds['access_key'] and aws_creds['secret_key']:
        s3_client = boto3.client(
            's3',
            region_name=aws_creds['region'],
            aws_access_key_id=aws_creds['access_key'],
            aws_secret_access_key=aws_creds['secret_key']
        )
    else:
        s3_client = boto3.client('s3')

    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=s3_bucket)

    deleted_count = 0
    for page in pages:
        if "Contents" in page:
            objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
            response = s3_client.delete_objects(
                Bucket=s3_bucket,
                Delete={"Objects": objects_to_delete}
            )
            deleted_count += len(response.get("Deleted", []))

    print(f"✅ Deleted {deleted_count} objects from bucket '{s3_bucket}'.")


def random_sleep_time(min_seconds: float = 3.0, max_seconds: float = 6.0) -> float:
    """
    Generates a random sleep time to simulate human behavior.

    Args:
        min_seconds (float, optional): Minimum sleep time in seconds.
        max_seconds (float, optional): Maximum sleep time in seconds.

    Returns:
        float: Sleep time in seconds.

    Example:
        >>> sleep_time = random_sleep_time()
        >>> time.sleep(sleep_time)
    """
    return random.uniform(min_seconds, max_seconds)


def normalize_name(name: str) -> str:
    """
    Normalize a name from path (e.g., 'copa_santa_fe') to title case (e.g., 'Copa Santa Fe').
    """
    if not name:
        return name
    # Replace underscores with spaces, title case, and strip
    return name.replace('_', ' ').title().strip()


def sanitize_dir_name(name: Optional[str]) -> str:
    """
    Cleans a string to be a valid directory name.

    Replaces problematic characters not allowed in file or directory names
    across different operating systems.

    Args:
        name (Optional[str]): Name to clean.

    Returns:
        str: Cleaned name valid for directory.

    Example:
        >>> clean_name = sanitize_dir_name("Tournament 2024/25 *final*")
        >>> print(clean_name)  # "Tournament 2024_25 _final_"
    """
    if name is None:
        return "unnamed"

    # Normalize and remove accents/diacritics
    nfkd_form = unicodedata.normalize('NFKD', str(name))
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    # Lowercase
    clean_name = only_ascii.lower()

    # Replace problematic characters and spaces with underscores
    problematic_chars = ['/', '\\', '*', '?', '"', '<', '>', '|', ':', ' ']
    for char in problematic_chars:
        clean_name = clean_name.replace(char, '_')

    # Remove any character that is not a letter, digit, or underscore
    allowed = set(string.ascii_lowercase + string.digits + '_')
    clean_name = ''.join(c for c in clean_name if c in allowed)

    # Remove consecutive underscores
    clean_name = re.sub(r'_+', '_', clean_name)
    # Remove leading/trailing underscores
    clean_name = clean_name.strip('_')

    return clean_name


def normalize_match_row(row: pd.Series) -> Dict[str, Any]:
    """
    Normalize a match row to standard field names, compatible with processor_fixtures.py.

    Args:
        row (pd.Series): Row with match information.

    Returns:
        Dict[str, Any]: Normalized match info.
    """
    return {
        "match_id": row.get("match_id") or row.get("Partido_ID") or row.get("Partido ID"),
        "date": row.get("date") or row.get("Fecha"),
        "date_raw": row.get("date_raw"),
        "time": row.get("time"),
        "home_team": row.get("home_team") or row.get("Equipo_Local") or row.get("Equipo Local"),
        "away_team": row.get("away_team") or row.get("Equipo_Visitante") or row.get("Equipo Visitante"),
        "home_score": row.get("home_score"),
        "away_score": row.get("away_score"),
        "venue": row.get("venue"),
        "status": row.get("status"),
        "coverage": row.get("coverage"),
        "last_updated": row.get("last_updated"),
        "tournament_id": row.get("tournament_id") or row.get("Torneo_ID") or row.get("torneo_id"),
        "competition": row.get("competition") or row.get("Competicion") or row.get("competicion"),
        "competition_id": row.get("competition_id") or row.get("ID_Competicion") or row.get("id_competicion"),
        "country": row.get("country") or row.get("Pais") or row.get("pais"),
        "continent": row.get("continent") or row.get("Continente") or row.get("continente"),
        "season": row.get("season") or row.get("Temporada") or row.get("temporada"),
        "fixture_path": row.get("fixture_path"),
        "attendance": row.get("attendance"),
        "weather_temperature": row.get("weather_temperature"),
        "weather_conditions": row.get("weather_conditions"),
    }

def normalize_season_string(season: str) -> str:
    """
    Normalize a season string to the format 'YYYY' or 'YYYY-YYYY'.

    Args:
        season (str): Season string, e.g. '2024', '2024/2025', '2024-2025'

    Returns:
        str: Normalized season string, e.g. '2024' or '2024-2025'
    """
    season = season.strip().split()[0]
    # Match YYYY
    if re.fullmatch(r"\d{4}", season):
        return season
    # Match YYYY/YYYY or YYYY-YYYY
    match = re.match(r"(\d{4})[/-](\d{4})", season)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    raise ValueError(f"Invalid season format: {season}")

def get_tournament_id(url: str) -> Optional[str]:
    """
    Extracts the tournament ID from a season URL.

    Modifies the URL by changing 'results' to 'fixtures' and extracts
    the tournament identifier using regular expressions.

    Args:
        url (str): URL of the tournament results page.

    Returns:
        Optional[str]: Tournament ID if found, None otherwise.

    Example:
        >>> url = "https://example.com/soccer/league/premier-league-2024/results"
        >>> tournament_id = get_tournament_id(url)
        >>> print(tournament_id)  # "premier-league-2024"
    """
    try:
        url = url.replace('results', 'fixtures')
        match = re.search(r'soccer/[^/]+/([^/]+)/fixtures', url)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error extracting tournament ID from {url}: {e}")
    return None


def get_season_name_from_url(url: str) -> Optional[str]:
    """
    Extracts the season name from a results URL.

    Parses the URL structure and extracts the season name,
    decoding special characters if necessary.

    Args:
        url (str): URL of the results page.

    Returns:
        Optional[str]: Season name if found, None otherwise.

    Example:
        >>> url = "https://example.com/soccer/spain/la-liga-2024-25/results"
        >>> season = get_season_name_from_url(url)
        >>> print(season)  # "la-liga-2024-25"
    """
    try:
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p and p != 'soccer']
        if len(parts) >= 2:
            season_part = parts[1]
            # Match at the end: YYYY or YYYY-YYYY
            match = re.search(r'(?:^|[^\d])(\d{4}-\d{4}|\d{4})(?:$|[^\d])', season_part)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error extracting season name from {url}: {e}")
    return None


def get_sdapi_outlet_key(competition_url: str) -> str:
    """
    Extracts the sdapi_outlet_key from a competition page.

    Args:
        competition_url (str): URL of the competition page.

    Returns:
        str: sdapi_outlet_key value.

    Raises:
        Exception: If HTTP request fails.
        ValueError: If sdapi_outlet_key is not found.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5) Chrome/135.0 Mobile Safari/537.36'
    }
    try:
        response = requests.get(competition_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"HTTP request error: {e}")

    soup = BeautifulSoup(response.text, 'html.parser')
    for script in soup.find_all('script'):
        if script.string and "sdapi_outlet_key" in script.string:
            match = re.search(r'sdapi_outlet_key\s*:\s*"([^"]+)"', script.string)
            if match:
                return match.group(1)
    raise ValueError("sdapi_outlet_key not found on the page.")


def fuzzy_intersect_competitions(
    dict_continent_country_competitions: dict,
    dict_country_competitions: dict,
    fuzzy_threshold: int = 80
) -> dict:
    """
    Returns a nested dictionary with the intersection of competitions, using fuzzy matching.
    Keeps the original structure: Continent -> Country -> [ (competition_name, competition_id), ... ]
    
    Args:
        dict_continent_country_competitions (dict): Continent -> Country -> [competition_name, ...]
        dict_country_competitions (dict): Country -> [(competition_name, competition_id), ...]
        fuzzy_threshold (int): Minimum fuzzy match score to consider a match.

    Returns:
        dict: Continent -> Country -> [ (competition_name, competition_id), ... ]
    """
    result = {}
    for continent, countries in dict_continent_country_competitions.items():
        for country, competitions in countries.items():
            available = dict_country_competitions.get(country, [])
            available_names = [name for name, _ in available]
            available_dict = {name: comp_id for name, comp_id in available}
            matched = []
            seen_ids = set()
            for wanted in competitions:
                if available_names:
                    res = process.extractOne(wanted, available_names, scorer=fuzz.token_sort_ratio)
                    if res:
                        match, score = res
                        comp_id = available_dict[match]
                        if score >= fuzzy_threshold and comp_id not in seen_ids:
                            matched.append((match, comp_id))
                            seen_ids.add(comp_id)
            if matched:
                if continent not in result:
                    result[continent] = {}
                result[continent][country] = matched
    return result


def extend_dataframe_with_unique_rows(
    storage_manager,
    df_new: pd.DataFrame,
    filename: str,
    priority_suffixes: tuple = ("_path", "url", "results_url")
) -> pd.DataFrame:
    """
    Extends an existing CSV file (if exists) with unique rows from df_new,
    comparing only columns ending with the given suffixes (priority order).

    Args:
        storage_manager: StorageManager instance for file operations.
        df_new (pd.DataFrame): DataFrame with new rows to add.
        filename (str): Path to the CSV file.
        priority_suffixes (tuple): Suffixes to use for column comparison.

    Returns:
        pd.DataFrame: Extended DataFrame (existing + unique new rows).
    """
    # Load existing DataFrame if file exists, else create empty DataFrame
    if storage_manager.file_exists(filename):
        df_existing = storage_manager.load_dataframe_csv(filename)
    else:
        df_existing = pd.DataFrame(columns=df_new.columns)

    # Find columns to use for comparison, in priority order
    compare_cols = [col for col in df_new.columns if col.endswith(priority_suffixes)]
    if not compare_cols:
        raise ValueError("No columns with the specified suffixes found for comparison.")

    # Build a set of tuples for fast comparison from existing DataFrame
    existing_tuples = set(
        tuple(row[col] for col in compare_cols)
        for _, row in df_existing.iterrows()
    )

    # Collect new unique rows
    new_rows = []
    for _, row in df_new.iterrows():
        row_tuple = tuple(row[col] for col in compare_cols)
        if row_tuple not in existing_tuples:
            new_rows.append(row)

    # Append new unique rows to the existing DataFrame
    if new_rows:
        df_extended = pd.concat([df_existing, pd.DataFrame(new_rows, columns=df_new.columns)], ignore_index=True)
    else:
        df_extended = df_existing.copy()

    return df_extended


def test_utils() -> None:
    """
    Test function to verify the utility functions.
    """
    print("=== Testing Utility Functions ===")

    # Test sanitize_dir_name
    test_name = "Tournament 2024/25 *final*"
    clean = sanitize_dir_name(test_name)
    print(f"Sanitize: '{test_name}' -> '{clean}'")

    # Test get_tournament_id
    test_url = "https://example.com/soccer/spain/la-liga-2024/results"
    tournament_id = get_tournament_id(test_url)
    print(f"Tournament ID: {tournament_id}")

    # Test get_season_name_from_url
    season = get_season_name_from_url(test_url)
    print(f"Season name: {season}")

    # Test random_sleep_time
    sleep_time = random_sleep_time()
    print(f"Random sleep: {sleep_time:.2f} seconds")


if __name__ == "__main__":
    test_utils()