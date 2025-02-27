from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper import scrape_moovit_routes
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
        route_divs = scrape_moovit_routes(url)
        return jsonify({"routes": route_divs})
    except Exception as e:
        # Log the error (would be captured by the hosting platform)
        print(f"Error scraping {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Get port from environment variable (for deployment platforms)
    port = int(os.environ.get('PORT', 5000))

    # Run the app
    app.run(host='0.0.0.0', port=port)