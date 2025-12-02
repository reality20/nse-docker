from curl_cffi import requests
import time
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NSEClient:
    def __init__(self):
        self.base_url = "https://www.nseindia.com"
        # Modern browser headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        # Using curl_cffi Session which mimics browser TLS fingerprints
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update(self.headers)

        self.last_cookie_time = 0
        self.cookie_expiry = 300 # Refresh cookies every 5 minutes

    def refresh_cookies(self):
        try:
            logger.info("Refreshing cookies...")
            # Random delay to seem more human if called often (though usually called once at start)
            time.sleep(random.uniform(0.5, 1.5))

            response = self.session.get(self.base_url, timeout=30)
            logger.info(f"Homepage status: {response.status_code}")

            if response.status_code == 403:
                logger.error("403 Forbidden on Homepage. IP might be blocked or headers rejected.")

            self.last_cookie_time = time.time()
        except Exception as e:
            logger.error(f"Error refreshing cookies: {e}")

    def get_nifty_price(self):
        if time.time() - self.last_cookie_time > self.cookie_expiry:
            self.refresh_cookies()

        try:
            url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

            # API specific headers
            api_headers = {
                'Referer': 'https://www.nseindia.com/get-quotes/equity?symbol=NIFTY',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'X-Requested-With': 'XMLHttpRequest'
            }

            # Merge with default headers, but update with API specific ones
            # curl_cffi handles headers merge nicely

            response = self.session.get(url, headers=api_headers, timeout=10)

            if response.status_code == 401 or response.status_code == 403:
                logger.warning(f"Got {response.status_code}, refreshing cookies and retrying...")
                self.refresh_cookies()
                # Wait a bit before retry
                time.sleep(2)
                response = self.session.get(url, headers=api_headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                price = data.get('records', {}).get('underlyingValue')
                timestamp = data.get('records', {}).get('timestamp')
                return {
                    "symbol": "NIFTY",
                    "price": price,
                    "timestamp": timestamp
                }
            else:
                logger.error(f"Failed to fetch data. Status: {response.status_code}")
                # Log a snippet of response if it's text, to debug
                try:
                    logger.error(f"Response text (first 200 chars): {response.text[:200]}")
                except:
                    pass
                return None
        except Exception as e:
            logger.error(f"Exception fetching price: {e}")
            return None
