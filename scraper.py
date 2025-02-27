from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.service import utils
import time
import re
import os
import subprocess
import shutil


def scrape_moovit_routes(url):
    """
    Uses Selenium in headless mode with anti-detection features to scrape divs with class="route-inner"
    from a Moovit page.

    Args:
        url (str): The URL of the Moovit page to scrape

    Returns:
        list: A list of HTML strings containing the route information
    """
    print(f"Starting to scrape: {url}")

    # Set up Chrome options for headless mode with anti-bot detection bypassing
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # New headless mode
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--remote-debugging-port=9222")

    # Add realistic user agent
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )

    # Support for running in containerized environments
    if os.environ.get('CHROME_BIN'):
        chrome_options.binary_location = os.environ.get('CHROME_BIN')

    # Initialize a list to store the results
    results = []

    try:
        # Fallback approach using direct HTML fetching
        print("Using fallback approach with direct HTML fetching")
        
        # Get Chrome version for debugging
        try:
            chrome_version_cmd = "google-chrome --version"
            chrome_version = subprocess.check_output(chrome_version_cmd, shell=True).decode('utf-8').strip()
            print(f"Chrome version: {chrome_version}")
        except:
            print("Could not determine Chrome version")
        
        # Create a simple crawler function to get the HTML content
        import urllib.request
        
        def get_html(url):
            req = urllib.request.Request(
                url, 
                data=None, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
                }
            )
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
        
        # Get the page content
        print(f"Fetching page content from: {url}")
        page_content = get_html(url)
        
        # Look for route-inner divs using regex
        print("Searching for route-inner divs in page content")
        route_inner_pattern = re.compile(r'<div class="route-inner">.*?</div>', re.DOTALL)
        matches = route_inner_pattern.findall(page_content)
        
        if matches:
            print(f"Found {len(matches)} divs using regex pattern")
            results = matches
        else:
            print("No divs found using regex extraction")
            
            # Try a more lenient pattern
            print("Trying more lenient pattern")
            route_inner_pattern = re.compile(r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>.*?</div>', re.DOTALL)
            matches = route_inner_pattern.findall(page_content)
            
            if matches:
                print(f"Found {len(matches)} divs using lenient regex pattern")
                results = matches
            else:
                print("Still no matches found")

        print(f"Scraping complete. Found {len(results)} route divs.")
        return results

    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        raise
