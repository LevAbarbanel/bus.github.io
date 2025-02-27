from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/', methods=['GET'])
def index():
    """Simple health check endpoint."""
    return jsonify({
        "status": "running",
        "message": "Moovit scraper API is up and running.",
        "usage": {
            "endpoint": "/scrape",
            "method": "POST",
            "body": {
                "url": "https://moovitapp.com/url/to/scrape"
            }
        }
    })

@app.route('/scrape', methods=['POST'])
def scrape():
    """Endpoint to scrape Moovit routes from a given URL."""
    data = request.json
    
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400
    
    url = data.get('url')
    
    if not url or 'moovitapp.com' not in url:
        return jsonify({"error": "Invalid URL. Must be a Moovit URL."}), 400
    
    try:
        # Call the scraping function
        route_divs = scrape_with_headless_selenium(url)
        return jsonify({"routes": route_divs})
    except Exception as e:
        # Log the error (would be captured by the hosting platform)
        print(f"Error scraping {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def scrape_with_headless_selenium(url):
    """
    Uses Selenium in headless mode with anti-detection features to scrape divs with class="route-inner"
    from a JavaScript-rendered web page that might employ anti-bot measures.

    Args:
        url (str): The URL of the website to scrape
        
    Returns:
        list: A list of HTML strings containing the route information
    """
    print(f"Setting up Chrome WebDriver in headless mode with anti-detection features...")
    
    # Results list to return
    results = []

    # Set up Chrome options for headless mode with anti-bot detection bypassing
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # New headless mode
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Add a realistic user agent (important for headless mode)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Support for containerized environments
    if os.environ.get('CHROME_BIN'):
        chrome_options.binary_location = os.environ.get('CHROME_BIN')

    try:
        # We'll try different ChromeDriver initialization approaches
        driver = None
        
        # First approach: Try using ChromeDriverManager (works locally)
        try:
            print("Attempting to initialize with ChromeDriverManager...")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e1:
            print(f"ChromeDriverManager approach failed: {str(e1)}")
            
            # Second approach: Try direct initialization
            try:
                print("Attempting direct Chrome initialization...")
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as e2:
                print(f"Direct initialization failed: {str(e2)}")
                
                # Third approach: Try with environment variable path
                if os.environ.get('CHROMEDRIVER_PATH'):
                    try:
                        print(f"Trying with CHROMEDRIVER_PATH: {os.environ.get('CHROMEDRIVER_PATH')}")
                        driver = webdriver.Chrome(
                            service=Service(os.environ.get('CHROMEDRIVER_PATH')),
                            options=chrome_options
                        )
                    except Exception as e3:
                        print(f"CHROMEDRIVER_PATH approach failed: {str(e3)}")
                        raise Exception("All ChromeDriver initialization approaches failed")
                else:
                    raise Exception("CHROMEDRIVER_PATH not set and other approaches failed")
        
        if not driver:
            raise Exception("Failed to initialize ChromeDriver with any approach")

        # Execute CDP command to modify navigator.webdriver flag
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        # Navigate to the URL
        print(f"Navigating to {url}...")
        driver.get(url)

        # Wait for page to load
        print("Waiting for page to load completely...")
        time.sleep(15)  # Longer wait in headless mode

        # Print page title to verify we're on the right page
        print(f"Page title: {driver.title}")

        # Try multiple search strategies
        print("Searching for route information using multiple strategies...")

        # Strategy 1: Direct class search
        route_inner_divs = driver.find_elements(By.CLASS_NAME, "route-inner")
        if route_inner_divs:
            print(f"Strategy 1 successful: Found {len(route_inner_divs)} divs with class 'route-inner'")
        else:
            print("Strategy 1 failed: No elements found with direct class search")

        # Strategy 2: CSS Selector
        route_inner_css = driver.find_elements(By.CSS_SELECTOR, "div.route-inner")
        if route_inner_css:
            print(f"Strategy 2 successful: Found {len(route_inner_css)} divs with CSS selector")
            route_inner_divs = route_inner_css
        else:
            print("Strategy 2 failed: No elements found with CSS selector")

        # Strategy 3: XPath
        route_inner_xpath = driver.find_elements(By.XPATH, "//div[contains(@class, 'route-inner')]")
        if route_inner_xpath:
            print(f"Strategy 3 successful: Found {len(route_inner_xpath)} divs with XPath")
            if not route_inner_divs:
                route_inner_divs = route_inner_xpath
        else:
            print("Strategy 3 failed: No elements found with XPath")

        # Strategy 4: Search in page source
        page_source = driver.page_source
        print(f"Page source contains 'route-inner': {'route-inner' in page_source}")

        # If we found the divs with any strategy, collect their HTML
        if route_inner_divs:
            print(f"\nFound {len(route_inner_divs)} divs with class 'route-inner':")

            # Collect HTML content of each div
            for i, div in enumerate(route_inner_divs, 1):
                html_content = div.get_attribute('outerHTML')
                print(f"\n--- Div #{i} ---")
                print(html_content)
                results.append(html_content)
                
        else:
            print("\nNo divs found with any strategy. Attempting to extract from page source...")

            # Strategy 5: Extract using regex from page source if all else fails
            route_inner_pattern = re.compile(r'<div class="route-inner">(.*?)</div>', re.DOTALL)
            matches = route_inner_pattern.findall(page_source)

            if matches:
                print(f"Found {len(matches)} divs using regex pattern:")
                for i, match in enumerate(matches, 1):
                    html_content = f"<div class=\"route-inner\">{match}</div>"
                    print(f"\n--- Div #{i} ---")
                    print(html_content)
                    results.append(html_content)
            else:
                print("No divs found using regex pattern either.")

                # Last attempt: try a non-greedy regex pattern
                route_inner_pattern = re.compile(r'<div class="route-inner">.*?</div>', re.DOTALL)
                matches = route_inner_pattern.findall(page_source)

                if matches:
                    print(f"Found {len(matches)} divs using alternative regex pattern:")
                    for i, match in enumerate(matches, 1):
                        print(f"\n--- Div #{i} ---")
                        print(match)
                        results.append(match)
                else:
                    # Last resort: try broader patterns
                    print("Trying broader pattern match...")
                    route_inner_pattern = re.compile(r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>.*?</div>', re.DOTALL)
                    matches = route_inner_pattern.findall(page_source)
                    
                    if matches:
                        print(f"Found {len(matches)} divs using broader pattern:")
                        for i, match in enumerate(matches, 1):
                            print(f"\n--- Div #{i} ---")
                            print(match)
                            results.append(match)
                
        print(f"Collected {len(results)} route divs in total")
        return results

    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        # Take screenshot for debugging
        if 'driver' in locals() and driver:
            try:
                driver.save_screenshot("/tmp/moovit_screenshot.png")
                print("Saved screenshot to /tmp/moovit_screenshot.png")
            except Exception as e:
                print(f"Failed to save screenshot: {str(e)}")

            # Close the browser
            driver.quit()
            print("WebDriver closed.")

if __name__ == '__main__':
    # Get port from environment variable (for deployment platforms)
    port = int(os.environ.get('PORT', 5000))
    # Run the app
    app.run(host='0.0.0.0', port=port)
