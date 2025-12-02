import requests
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NSEClient:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.base_url = "https://www.nseindia.com"
        self.last_cookie_time = 0
        self.cookie_expiry = 300 # Refresh cookies every 5 minutes just in case

    def refresh_cookies(self):
        try:
            logger.info("Refreshing cookies...")
            response = self.session.get(self.base_url, timeout=10)
            logger.info(f"Homepage status: {response.status_code}")
            self.last_cookie_time = time.time()
        except Exception as e:
            logger.error(f"Error refreshing cookies: {e}")

    def get_nifty_price(self):
        if time.time() - self.last_cookie_time > self.cookie_expiry:
            self.refresh_cookies()

        try:
            # Using option-chain API as it contains the underlying index value
            url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
            response = self.session.get(url, timeout=5)

            if response.status_code == 401 or response.status_code == 403:
                logger.warning(f"Got {response.status_code}, refreshing cookies and retrying...")
                self.refresh_cookies()
                response = self.session.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                # The underlying value is usually at records -> underlyingValue
                price = data.get('records', {}).get('underlyingValue')
                timestamp = data.get('records', {}).get('timestamp')
                return {
                    "symbol": "NIFTY",
                    "price": price,
                    "timestamp": timestamp
                }
            else:
                logger.error(f"Failed to fetch data. Status: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Exception fetching price: {e}")
            return None
