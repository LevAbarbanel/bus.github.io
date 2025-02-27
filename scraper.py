from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import os


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

    # Add realistic user agent
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Support for running in containerized environments
    if os.environ.get('CHROME_BIN'):
        chrome_options.binary_location = os.environ.get('CHROME_BIN')

    # Initialize a list to store the results
    results = []

    try:
        # Initialize the WebDriver
        # For deployment platforms that have their own Chrome binary
        if os.environ.get('CHROMEDRIVER_PATH'):
            driver = webdriver.Chrome(
                service=Service(os.environ.get('CHROMEDRIVER_PATH')),
                options=chrome_options
            )
        else:
            # For local development
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

        # Execute CDP command to modify navigator.webdriver flag
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        # Navigate to the URL
        print(f"Navigating to URL...")
        driver.get(url)

        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(15)  # Allow time for dynamic content to load

        # Log page title for debugging
        print(f"Page title: {driver.title}")

        # Try multiple search strategies to find route-inner divs
        route_inner_divs = []

        # Strategy 1: Direct class search
        print("Trying Strategy 1: Direct class search")
        direct_search = driver.find_elements(By.CLASS_NAME, "route-inner")
        if direct_search:
            print(f"  Found {len(direct_search)} divs with direct class search")
            route_inner_divs = direct_search

        # Strategy 2: CSS Selector (if Strategy 1 failed)
        if not route_inner_divs:
            print("Trying Strategy 2: CSS Selector")
            css_search = driver.find_elements(By.CSS_SELECTOR, "div.route-inner")
            if css_search:
                print(f"  Found {len(css_search)} divs with CSS selector")
                route_inner_divs = css_search

        # Strategy 3: XPath (if previous strategies failed)
        if not route_inner_divs:
            print("Trying Strategy 3: XPath")
            xpath_search = driver.find_elements(By.XPATH, "//div[contains(@class, 'route-inner')]")
            if xpath_search:
                print(f"  Found {len(xpath_search)} divs with XPath")
                route_inner_divs = xpath_search

        # If we found divs with any strategy, extract their HTML
        if route_inner_divs:
            print(f"Processing {len(route_inner_divs)} route divs...")
            for div in route_inner_divs:
                results.append(div.get_attribute('outerHTML'))
        else:
            # Strategy 4: Extract using regex from page source if all else fails
            print("Trying Strategy 4: Regex extraction from page source")
            page_source = driver.page_source
            print(f"Page source contains 'route-inner': {'route-inner' in page_source}")

            route_inner_pattern = re.compile(r'<div class="route-inner">.*?</div>', re.DOTALL)
            matches = route_inner_pattern.findall(page_source)

            if matches:
                print(f"Found {len(matches)} divs using regex pattern")
                results = matches
            else:
                print("No divs found using regex extraction")

        print(f"Scraping complete. Found {len(results)} route divs.")
        return results

    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        raise

    finally:
        # Ensure the browser is closed
        if 'driver' in locals():
            print("Closing WebDriver...")
            driver.quit()