import requests
import feedparser
import time
import random
import re
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class ArticleFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fetch_url(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    def fetch_rss_articles(self, feed_urls):
        """
        Fetch articles from a list of RSS feed URLs.
        Returns a list of dicts: {'title': str, 'url': str, 'source': str, 'published': str}
        """
        articles = []
        for url in feed_urls:
            try:
                logger.info(f"Fetching RSS feed: {url}")
                feed = feedparser.parse(url)
                
                # Get feed title
                feed_title = feed.feed.get('title', 'Unknown Source')
                
                # Process entries (limit to top 5 per feed to avoid spam)
                for entry in feed.entries[:5]:
                    title = entry.get('title', 'No Title')
                    link = entry.get('link', '')
                    published = entry.get('published', entry.get('updated', ''))
                    
                    if title and link:
                        articles.append({
                            'title': title,
                            'url': link,
                            'source': feed_title,
                            'published': published
                        })
            except Exception as e:
                logger.error(f"Error parsing RSS feed {url}: {e}")
        
        return articles

    def fetch_wechat_articles(self, target_url):
        """
        Fetch articles from a given WeChat public account URL or similar.
        """
        articles = []
        try:
            logger.info(f"Fetching articles from {target_url}")
            # Simulate request with retries
            for i in range(3):
                try:
                    response = requests.get(target_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        links = soup.find_all('a', href=True)
                        for link in links:
                            title = link.get_text(strip=True)
                            url = link['href']
                            if title and url and 'http' in url:
                                articles.append({'title': title, 'url': url, 'source': 'Web'})
                        break
                except Exception as e:
                    logger.warning(f"Attempt {i+1} failed: {e}")
                    time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
        
        return articles

    def clean_title(self, title):
        """Remove common noise from titles"""
        return re.sub(r'[【】\[\]]', '', title).strip()
