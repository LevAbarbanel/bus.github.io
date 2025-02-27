from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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
        route_divs = scrape_with_http_request(url)
        return jsonify({"routes": route_divs})
    except Exception as e:
        # Log the error (would be captured by the hosting platform)
        print(f"Error scraping {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500

def scrape_with_http_request(url):
    """
    Uses direct HTTP requests and regex to scrape route information from Moovit.
    This method avoids the need for Selenium and ChromeDriver.
    
    Args:
        url (str): The URL of the Moovit page to scrape
        
    Returns:
        list: A list of HTML strings containing the route information
    """
    print(f"Starting to scrape: {url}")
    results = []
    
    try:
        # Create request with headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://moovitapp.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Get the page content
        print(f"Fetching page content from: {url}")
        req = Request(url, headers=headers)
        
        try:
            with urlopen(req, timeout=30) as response:
                page_source = response.read().decode('utf-8')
                print(f"Successfully fetched page content, length: {len(page_source)} characters")
        except HTTPError as e:
            print(f"HTTP Error: {e.code} - {e.reason}")
            return []
        except URLError as e:
            print(f"URL Error: {e.reason}")
            return []
        except Exception as e:
            print(f"Error fetching content: {str(e)}")
            return []
        
        # Check if content contains the expected pattern
        has_route_inner = "route-inner" in page_source
        print(f"Page contains 'route-inner': {has_route_inner}")
        
        # Try multiple pattern matching strategies in order
        
        # Strategy 1: Direct class search with regex
        print("Trying Strategy 1: Direct class regex")
        route_inner_pattern = re.compile(r'<div class="route-inner">.*?</div>', re.DOTALL)
        matches = route_inner_pattern.findall(page_source)
        
        if matches:
            print(f"Strategy 1 successful: Found {len(matches)} divs with direct regex")
            results = matches
        else:
            print("Strategy 1 failed: No matches found")
        
        # Strategy 2: More flexible class regex
        if not results:
            print("Trying Strategy 2: Flexible class regex")
            route_inner_pattern = re.compile(r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>.*?</div>', re.DOTALL)
            matches = route_inner_pattern.findall(page_source)
            
            if matches:
                print(f"Strategy 2 successful: Found {len(matches)} divs with flexible regex")
                results = matches
            else:
                print("Strategy 2 failed: No matches found")
        
        # Strategy 3: Balance tag matching approach for nested divs
        if not results:
            print("Trying Strategy 3: Balanced tag matching")
            start_positions = [m.start() for m in re.finditer(r'<div[^>]*class="[^"]*route-inner[^"]*"', page_source)]
            
            if start_positions:
                print(f"Found {len(start_positions)} potential start positions")
                
                for start_pos in start_positions:
                    # Extract a chunk to find the balanced closing tag
                    div_count = 1
                    for i in range(start_pos + 1, len(page_source)):
                        if page_source[i:i+4] == '<div':
                            div_count += 1
                        elif page_source[i:i+6] == '</div>':
                            div_count -= 1
                            if div_count == 0:
                                # We found the matching closing tag
                                div_html = page_source[start_pos:i+6]
                                results.append(div_html)
                                break
                
                if results:
                    print(f"Strategy 3 successful: Found {len(results)} divs with balanced tag matching")
                else:
                    print("Strategy 3 failed: No valid divs found")
        
        # Strategy 4: Extremely lenient pattern
        if not results:
            print("Trying Strategy 4: Very lenient pattern")
            # This pattern looks for routes with nested content
            route_inner_pattern = re.compile(r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>[\s\S]*?</div>\s*</div>', re.DOTALL)
            matches = route_inner_pattern.findall(page_source)
            
            if matches:
                print(f"Strategy 4 successful: Found {len(matches)} divs with lenient pattern")
                results = matches
            else:
                print("Strategy 4 failed: No matches found")
                
                # Save a sample of the page source for debugging
                sample = page_source[:500] + "..." if len(page_source) > 500 else page_source
                print(f"Page source sample: {sample}")
        
        # Cleanup and return results
        if results:
            # Remove duplicates while preserving order
            unique_results = []
            seen = set()
            for item in results:
                if item not in seen:
                    seen.add(item)
                    unique_results.append(item)
            
            results = unique_results
            print(f"Final result: {len(results)} unique routes found")
            return results
        else:
            print("No routes found with any strategy")
            return []
            
    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    import os
    # Get port from environment variable (for deployment platforms)
    port = int(os.environ.get('PORT', 5000))
    # Run the app
    app.run(host='0.0.0.0', port=port)
