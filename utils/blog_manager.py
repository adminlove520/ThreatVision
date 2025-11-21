import requests
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class BlogManager:
    def __init__(self):
        self.api_url = Config.BLOG_API_URL
        self.token = Config.BLOG_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def publish_article(self, title, content, tags=None):
        """
        Publish a new article to the blog.
        Adapts to a generic API structure (e.g., WordPress REST API or similar).
        """
        if not self.api_url or not self.token:
            logger.warning("Blog configuration missing. Skipping publish.")
            return None

        data = {
            'title': title,
            'content': content,
            'status': 'publish',
            'tags': tags or ['Security', 'ThreatVision']
        }

        try:
            response = requests.post(f"{self.api_url}/posts", headers=self.headers, json=data)
            if response.status_code in [200, 201]:
                logger.info(f"Successfully published article: {title}")
                return response.json().get('id')
            else:
                logger.error(f"Failed to publish article. Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error publishing article: {e}")
            return None

    def update_article(self, post_id, title=None, content=None):
        """Update an existing article"""
        if not self.api_url or not self.token:
            return False

        data = {}
        if title: data['title'] = title
        if content: data['content'] = content

        try:
            response = requests.post(f"{self.api_url}/posts/{post_id}", headers=self.headers, json=data)
            if response.status_code == 200:
                logger.info(f"Successfully updated article: {post_id}")
                return True
            else:
                logger.error(f"Failed to update article. Status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error updating article: {e}")
            return False
