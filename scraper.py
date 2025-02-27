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
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json


def scrape_moovit_routes(url):
    """
    Uses direct HTTP requests and regex pattern matching to extract route-inner divs
    from a Moovit page without relying on Selenium or ChromeDriver.

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
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
                page_content = response.read().decode('utf-8')
                print(f"Successfully fetched page content, length: {len(page_content)} characters")
                
                # Save a snippet of the content for debugging
                content_sample = page_content[:1000] + "..." if len(page_content) > 1000 else page_content
                print(f"Content sample: {content_sample}")
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
        has_route_inner = "route-inner" in page_content
        print(f"Page contains 'route-inner': {has_route_inner}")
        
        if not has_route_inner:
            print("Warning: The page doesn't contain 'route-inner' class")
            # Return empty list as no matches will be found
            return []
        
        # Multiple pattern matching approaches
        patterns = [
            # Pattern 1: Exact class match with multiple possible HTML structures
            r'<div[^>]*class="route-inner"[^>]*>.*?</div>',
            
            # Pattern 2: Class with possible additional classes
            r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>.*?</div>',
            
            # Pattern 3: Nested divs with route-inner
            r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>.*?<div.*?</div>.*?</div>',
            
            # Pattern 4: Broader match for the entire route block
            r'<div[^>]*class="[^"]*route-inner[^"]*"[^>]*>[\s\S]*?</div>\s*</div>'
        ]
        
        # Try each pattern until we find matches
        for i, pattern in enumerate(patterns, 1):
            print(f"Trying pattern {i}: {pattern}")
            route_inner_pattern = re.compile(pattern, re.DOTALL)
            matches = route_inner_pattern.findall(page_content)
            
            if matches:
                print(f"Pattern {i} found {len(matches)} matches")
                for j, match in enumerate(matches[:2], 1):  # Print first 2 samples only
                    sample = match[:100] + "..." if len(match) > 100 else match
                    print(f"Sample match {j}: {sample}")
                
                results = matches
                break
        
        # If no pattern worked, try a custom extraction
        if not results:
            print("No matches with regular patterns, trying custom extraction...")
            
            # Try to find the start points of all route-inner divs
            start_positions = [m.start() for m in re.finditer(r'<div[^>]*class="[^"]*route-inner[^"]*"', page_content)]
            
            if start_positions:
                print(f"Found {len(start_positions)} potential start positions")
                
                for pos in start_positions:
                    # Find the closing div tag by counting opening and closing div tags
                    open_count = 1
                    current_pos = pos
                    start_chunk = page_content[pos:pos+100]
                    print(f"Starting extraction from position {pos}, chunk: {start_chunk}...")
                    
                    for i in range(pos + 1, len(page_content)):
                        if page_content[i:i+5] == '<div ':
                            open_count += 1
                        elif page_content[i:i+6] == '</div>':
                            open_count -= 1
                            if open_count == 0:
                                # Found matching closing tag
                                route_html = page_content[pos:i+6]
                                results.append(route_html)
                                print(f"Extracted route with length {len(route_html)}")
                                break
                    
                    # Limit to first 10 results for performance
                    if len(results) >= 10:
                        break
        
        # Clean up results to remove any duplicate or malformed entries
        if results:
            # Remove duplicates while preserving order
            unique_results = []
            seen = set()
            for item in results:
                if item not in seen:
                    seen.add(item)
                    unique_results.append(item)
            
            results = unique_results
            print(f"After deduplication: {len(results)} unique routes found")
        
        return results

    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        # Print traceback for better debugging
        import traceback
        traceback.print_exc()
        return []
