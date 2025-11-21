import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class DingTalkSender:
    def __init__(self):
        self.token = Config.DINGTALK_TOKEN
        self.secret = Config.DINGTALK_SECRET
        self.api_url = "https://oapi.dingtalk.com/robot/send"

    def _get_signed_url(self):
        if not self.token or not self.secret:
            return None
        
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        return f"{self.api_url}?access_token={self.token}&timestamp={timestamp}&sign={sign}"

    def send_markdown(self, title, text):
        """
        Send a markdown message to DingTalk
        """
        url = self._get_signed_url()
        if not url:
            logger.warning("DingTalk configuration missing. Skipping notification.")
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            }
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("DingTalk notification sent successfully.")
                return True
            else:
                logger.error(f"DingTalk API error: {result}")
                return False
        except Exception as e:
            logger.error(f"Error sending DingTalk notification: {e}")
            return False
