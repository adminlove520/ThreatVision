import os
import sys
import requests
from datetime import datetime
from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class GitHubReleaseManager:
    """
    用于管理GitHub Release的工具类
    负责创建Release、上传资产文件等操作
    """
    
    def __init__(self):
        # 优先使用GitHub Actions自动生成的GITHUB_TOKEN
        github_action_token = os.getenv('GITHUB_TOKEN')
        if github_action_token:
            self.tokens = [github_action_token]
            logger.info("Using GitHub Actions generated GITHUB_TOKEN")
        else:
            # 否则使用配置中的tokens（从.env文件加载）
            self.tokens = Config.GITHUB_TOKENS
            if self.tokens and self.tokens != ['']:
                logger.info(f"Using GitHub tokens from .env file: {len(self.tokens)} token(s) available")
            else:
                logger.warning("No GitHub tokens available from .env file")
        
        # 确保tokens是列表类型
        if not isinstance(self.tokens, list):
            self.tokens = []
        
        # 过滤掉空token
        self.tokens = [token for token in self.tokens if token.strip()]
        
        self.current_token_index = 0
        self.repo = os.getenv('GITHUB_REPOSITORY', '')
        
        # 如果没有设置GITHUB_REPOSITORY环境变量，尝试从当前目录的git配置中获取
        if not self.repo:
            self.repo = self._get_repo_from_git()
        
        self.api_base_url = 'https://api.github.com'
    
    def _get_repo_from_git(self):
        """从git配置中获取仓库信息"""
        try:
            import subprocess
            # 获取远程仓库URL
            remote_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode('utf-8').strip()
            # 解析URL格式，提取owner/repo
            if 'github.com' in remote_url:
                # 处理HTTPS格式: https://github.com/owner/repo.git
                if remote_url.startswith('https://'):
                    return remote_url.split('/')[-2] + '/' + remote_url.split('/')[-1].replace('.git', '')
                # 处理SSH格式: git@github.com:owner/repo.git
                elif remote_url.startswith('git@'):
                    return remote_url.split(':')[-1].replace('.git', '')
        except Exception as e:
            logger.error(f"Failed to get repo from git: {e}")
        return ''
    
    def get_headers(self):
        """获取GitHub API请求头"""
        if not self.tokens:
            logger.warning("No GitHub tokens available")
            return {}
        token = self.tokens[self.current_token_index]
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def rotate_token(self):
        """轮换GitHub令牌"""
        if not self.tokens:
            return
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        logger.info(f"Rotated to GitHub token index: {self.current_token_index}")
    
    def create_release(self, tag_name, release_name, body=''):
        """
        创建GitHub Release
        
        Args:
            tag_name: Release标签名
            release_name: Release名称
            body: Release描述
            
        Returns:
            Release信息或None
        """
        if not self.repo:
            logger.error("GitHub repository not specified")
            return None
        
        url = f"{self.api_base_url}/repos/{self.repo}/releases"
        
        data = {
            'tag_name': tag_name,
            'name': release_name,
            'body': body,
            'draft': False,
            'prerelease': False
        }
        
        try:
            response = requests.post(url, headers=self.get_headers(), json=data, timeout=30)
            
            if response.status_code == 201:
                logger.info(f"Created GitHub Release: {release_name}")
                return response.json()
            elif response.status_code == 401:
                logger.error(f"GitHub API 401 Unauthorized: Invalid or expired token")
                logger.warning("Please check your GitHub token configuration")
            elif response.status_code == 403:
                logger.warning("GitHub API rate limit exceeded, rotating token")
                self.rotate_token()
            else:
                logger.error(f"Failed to create release: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to GitHub API. Please check your network connection.")
        except requests.exceptions.Timeout:
            logger.error("GitHub API request timed out")
        except Exception as e:
            logger.error(f"Error creating release: {e}")
        
        return None
    
    def upload_asset(self, release_id, file_path, content_type='application/octet-stream'):
        """
        上传资产文件到GitHub Release
        
        Args:
            release_id: Release ID
            file_path: 本地文件路径
            content_type: 文件内容类型
            
        Returns:
            上传结果或None
        """
        if not self.repo:
            logger.error("GitHub repository not specified")
            return None
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # 使用正确的GitHub API URL格式
        url = f"{self.api_base_url}/repos/{self.repo}/releases/{release_id}/assets"
        
        try:
            with open(file_path, 'rb') as f:
                headers = self.get_headers()
                headers['Content-Type'] = content_type
                headers['Content-Length'] = str(file_size)
                
                # 使用multipart/form-data上传
                files = {
                    'asset': (file_name, f, content_type)
                }
                
                response = requests.post(url, headers=headers, files=files, timeout=60)
                
                if response.status_code == 201:
                    logger.info(f"Uploaded asset: {file_name}")
                    return response.json()
                elif response.status_code == 401:
                    logger.error(f"GitHub API 401 Unauthorized: Invalid or expired token")
                    logger.warning("Please check your GitHub token configuration")
                elif response.status_code == 403:
                    logger.warning("GitHub API rate limit exceeded, rotating token")
                    self.rotate_token()
                elif response.status_code == 404:
                    logger.error(f"Failed to upload asset: 404 - Release not found or no permission")
                else:
                    logger.error(f"Failed to upload asset: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to GitHub API. Please check your network connection.")
        except requests.exceptions.Timeout:
            logger.error("GitHub API request timed out")
        except Exception as e:
            logger.error(f"Error uploading asset: {e}")
        
        return None
    
    def push_report_to_release(self, report_path):
        """
        将日报推送到GitHub Release
        
        Args:
            report_path: 日报文件路径
            
        Returns:
            Release信息或None
        """
        if not report_path or not os.path.exists(report_path):
            logger.error(f"Invalid report path: {report_path}")
            return None
        
        # 从文件路径提取日期信息
        date_str = os.path.basename(report_path).replace('Daily_', '').replace('.md', '')
        tag_name = f"daily-report-{date_str}"
        release_name = f"安全资讯日报 {date_str}"
        
        # 读取报告内容作为Release描述
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建Release
        release = self.create_release(tag_name, release_name, content)
        
        if release:
            # 上传报告文件
            self.upload_asset(release['id'], report_path, 'text/markdown')
            
            # 查找并上传其他相关文件
            report_dir = os.path.dirname(report_path)
            for root, dirs, files in os.walk(report_dir):
                for file in files:
                    if file != os.path.basename(report_path):
                        file_path = os.path.join(root, file)
                        self.upload_asset(release['id'], file_path)
        
        return release
    
    def update_remote_repo(self):
        """
        更新远程仓库（可选）
        
        这个方法可以用于将生成的报告推送到远程仓库的特定分支
        """
        try:
            import subprocess
            
            # 添加所有修改
            subprocess.run(['git', 'add', '.'], check=True)
            
            # 提交修改
            commit_msg = f"Update daily report - {datetime.now().strftime('%Y-%m-%d')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            # 推送到远程仓库
            subprocess.run(['git', 'push'], check=True)
            
            logger.info("Remote repository updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update remote repository: {e}")
            return False
