# everyone loves a slinky. except for, well, YOU KNOW WHO. 
# <3 <3
# blackout 2025.
#
# v1.0





import requests
import time
import subprocess
import shutil
import json
import os
import random  # For jitter in backoff

# Query parameters
query = 'Sha1-Hulud: The Second Coming'
params = {
    'q': query,
    'sort': 'updated',
    'order': 'desc',
    'per_page': 100  # Max per page
}

# GitHub API base URL
api_url = 'https://api.github.com/search/repositories'

# Persistence file
seen_file = 'seen_repos.json'

# Download directory
download_dir = 'downloads'
os.makedirs(download_dir, exist_ok=True)

# Load seen repos if exists, else initialize empty dict {full_name: updated_at}
if os.path.exists(seen_file):
    with open(seen_file, 'r') as f:
        seen_repos = json.load(f)
    print(f"Loaded baseline from {seen_file} with {len(seen_repos)} repos.")
else:
    seen_repos = {}
    print(f"No baseline file found. Will fetch and download all initial repos.")

def fetch_all_repos():
    """Fetch all repos matching query, handling pagination and retries."""
    repos = []
    url = api_url
    while url:
        for attempt in range(3):  # Retry up to 3 times
            try:
                response = requests.get(url, params=params if url == api_url else None, timeout=30)
                if response.status_code != 200:
                    if response.status_code == 403:
                        print("Rate limit hit. Backing off...")
                        time.sleep(300)  # 5 min for rate limit
                    else:
                        print(f"Error fetching: {response.status_code} - {response.text}")
                    break  # Non-retryable, break retry loop
                data = response.json()
                repos.extend(data.get('items', []))
                # Get next page from Link header
                url = response.links.get('next', {}).get('url')
                break  # Success, break retry loop
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"Network error on attempt {attempt+1}: {e}. Retrying after backoff...")
                time.sleep((2 ** attempt) + random.uniform(0, 1))  # Exponential backoff with jitter
            except Exception as e:
                print(f"Unexpected error: {e}")
                time.sleep(300)
                break
        else:
            print("Max retries reached. Skipping this fetch cycle.")
            return []  # Return empty on failure
    return repos

print(f"Starting monitor for new/updated repos matching: {query}")
print("Press Ctrl+C to stop.")

try:
    while True:
        repos = fetch_all_repos()
        if not repos:
            print("Fetch failed; sleeping before next attempt.")
            time.sleep(300)  # Longer sleep on full failure
            continue
        
        new_or_updated_count = 0
        
        for repo in repos:
            full_name = repo['full_name']
            updated_at = repo['updated_at']  # ISO string, comparable lexicographically
            
            if full_name not in seen_repos or updated_at > seen_repos[full_name]:
                # New or updated: Download ZIP
                zip_url = f"https://github.com/{full_name}/archive/refs/heads/main.zip"
                zip_path = os.path.join(download_dir, f"{full_name.replace('/', '-')}-main.zip")
                
                print(f"New/updated repo detected: {full_name} ({updated_at}) - Downloading ZIP to {zip_path}...")
                
                # Download using wget if available, else curl
                if shutil.which("wget"):
                    subprocess.call(["wget", "-O", zip_path, zip_url])
                elif shutil.which("curl"):
                    subprocess.call(["curl", "-o", zip_path, zip_url])
                else:
                    print("Neither wget nor curl is available. Install one to download files.")
                
                # Update timestamp
                seen_repos[full_name] = updated_at
                new_or_updated_count += 1
        
        if new_or_updated_count == 0:
            print("No new or updated repos found in this check.")
        else:
            print(f"Downloaded {new_or_updated_count} new/updated repo ZIPs.")
        
        # Save updated seen_repos
        with open(seen_file, 'w') as f:
            json.dump(seen_repos, f, indent=4)
        
        time.sleep(60)  # Poll every 60 seconds
        
except KeyboardInterrupt:
    print("Monitoring stopped.")
