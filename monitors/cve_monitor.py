import requests
import time
import re
import os
import shutil
import sys
from datetime import datetime
from sqlalchemy import create_engine

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from database.models import CVERecord, get_session
from utils.logger import setup_logger
from utils.github_token_manager import GitHubTokenManager

logger = setup_logger(__name__)

class CVEMonitor:
    def __init__(self):
        # 使用统一的GitHub Token管理器
        self.token_manager = GitHubTokenManager()
        self.keywords = Config.GITHUB_KEYWORDS
        
        # Database setup
        self.engine = create_engine(f'sqlite:///{Config.DB_PATH_CVE}')
        
    def get_headers(self):
        """获取带有Authorization头的请求头"""
        return self.token_manager.get_headers()
    
    def rotate_token(self):
        """轮换到下一个token"""
        self.token_manager.rotate_token()

    def search_github(self, keyword):
        url = f"https://api.github.com/search/repositories?q={keyword}&sort=updated&order=desc"
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10, proxies={'http': None, 'https': None})
            if response.status_code == 200:
                return response.json().get('items', [])
            elif response.status_code == 403:
                logger.warning("Rate limit exceeded. Rotating token.")
                self.rotate_token()
                time.sleep(2)
                return []
            else:
                logger.error(f"GitHub API error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
            return []

    def extract_cve_id(self, text):
        match = re.search(r'CVE-\d{4}-\d{4,7}', text, re.IGNORECASE)
        return match.group(0).upper() if match else None

    def process_repo(self, repo_data):
        repo_name = repo_data.get('name', '')
        description = repo_data.get('description', '') or ''
        html_url = repo_data.get('html_url', '')
        
        # Combine name and description for searching
        full_text = f"{repo_name} {description}"
        cve_id = self.extract_cve_id(full_text)
        
        if not cve_id:
            return

        # Check blacklist (simplified)
        if any(u in repo_data.get('owner', {}).get('login', '') for u in Config.BLACKLIST_USERS):
            return

        session = get_session(self.engine)
        try:
            # Check if exists
            existing = session.query(CVERecord).filter_by(cve_id=cve_id).first()
            
            if existing:
                # Update if needed
                if existing.repo_url != html_url:
                    # Maybe update logic here, or just log
                    pass
            else:
                # Create new record
                new_record = CVERecord(
                    cve_id=cve_id,
                    description=description,
                    repo_url=html_url,
                    publish_time=datetime.strptime(repo_data['created_at'], "%Y-%m-%dT%H:%M:%SZ"),
                    update_time=datetime.utcnow()
                )
                session.add(new_record)
                session.commit()
                logger.info(f"New CVE found: {cve_id} in {html_url}")
                
        except Exception as e:
            logger.error(f"Database error processing {cve_id}: {e}")
        finally:
            session.close()

    def monitor(self):
        logger.info("Starting CVE Monitor cycle...")
        for keyword in self.keywords:
            logger.info(f"Searching for {keyword}...")
            items = self.search_github(keyword)
            for item in items:
                self.process_repo(item)
                time.sleep(0.5) # Be nice to API
