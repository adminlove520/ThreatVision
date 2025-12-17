import requests
import time
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from database.models import Repository, get_session
from utils.logger import setup_logger
from utils.github_token_manager import GitHubTokenManager

logger = setup_logger(__name__)

class GithubMonitor:
    def __init__(self):
        # 使用统一的GitHubTokenManager
        self.token_manager = GitHubTokenManager()
        self.watched_repos = Config.WATCHED_REPOSITORIES
        
        # Database setup
        self.engine = create_engine(f'sqlite:///{Config.DB_PATH_REPO}')

    def get_headers(self):
        return self.token_manager.get_headers()

    def rotate_token(self):
        self.token_manager.rotate_token()

    def get_repo_info(self, repo_name):
        """Get info for a specific repo (owner/name)"""
        url = f"https://api.github.com/repos/{repo_name}"
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                self.rotate_token()
                return None
            else:
                logger.warning(f"Failed to get repo info for {repo_name}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching repo {repo_name}: {e}")
            return None

    def analyze_commits(self, repo_name):
        """Fetch recent commits to see if there's interesting activity"""
        url = f"https://api.github.com/repos/{repo_name}/commits"
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                commits = response.json()
                # Simple logic: return latest commit message
                if commits:
                    return commits[0].get('commit', {}).get('message', '')
            return ""
        except Exception as e:
            logger.error(f"Error fetching commits for {repo_name}: {e}")
            return ""

    def process_repo(self, repo_name):
        data = self.get_repo_info(repo_name)
        if not data:
            return

        session = get_session(self.engine)
        try:
            repo = session.query(Repository).filter_by(url=data['html_url']).first()
            
            latest_commit_msg = self.analyze_commits(repo_name)
            
            if repo:
                # Update existing
                repo.stars = data['stargazers_count']
                repo.last_updated = datetime.strptime(data['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
                # Logic to detect if it's "high value" based on changes could go here
            else:
                # Create new
                new_repo = Repository(
                    name=data['name'],
                    url=data['html_url'],
                    description=data['description'],
                    stars=data['stargazers_count'],
                    last_updated=datetime.strptime(data['updated_at'], "%Y-%m-%dT%H:%M:%SZ"),
                    is_high_value=True # Watched repos are high value by default
                )
                session.add(new_repo)
                logger.info(f"Added watched repo: {repo_name}")
            
            session.commit()
        except Exception as e:
            logger.error(f"Database error processing {repo_name}: {e}")
        finally:
            session.close()

    def monitor(self):
        logger.info("Starting GitHub Repo Monitor cycle...")
        for repo_name in self.watched_repos:
            logger.info(f"Checking watched repo: {repo_name}")
            self.process_repo(repo_name)
            time.sleep(1)
