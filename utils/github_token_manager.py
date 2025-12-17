import os
from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class GitHubTokenManager:
    """
    统一的GitHub Token管理类
    负责token的获取、轮换和验证
    """
    
    def __init__(self):
        """初始化Token管理器"""
        self.tokens = Config.GITHUB_TOKENS
        self.current_token_index = 0
        self.token_count = len(self.tokens)
        
        logger.info(f"GitHubTokenManager initialized with {self.token_count} tokens")
        if self.token_count > 0:
            logger.debug(f"First token: {self.tokens[0][:10]}...")
        else:
            logger.warning("No GitHub tokens available, GitHub API calls will be unauthenticated")
    
    def get_token(self):
        """获取当前可用的GitHub token"""
        if self.token_count == 0:
            return None
        return self.tokens[self.current_token_index]
    
    def get_headers(self):
        """获取带有Authorization头的请求头"""
        token = self.get_token()
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if token:
            headers['Authorization'] = f'token {token}'
        return headers
    
    def rotate_token(self):
        """轮换到下一个token"""
        if self.token_count <= 1:
            return
        
        self.current_token_index = (self.current_token_index + 1) % self.token_count
        logger.info(f"Rotated to GitHub token index: {self.current_token_index}")
    
    def has_tokens(self):
        """检查是否有可用的tokens"""
        return self.token_count > 0
    
    def add_token(self, token):
        """添加一个新的token"""
        if token and token not in self.tokens:
            self.tokens.append(token)
            self.token_count = len(self.tokens)
            logger.info(f"Added new GitHub token, now have {self.token_count} tokens")
    
    def get_all_tokens(self):
        """获取所有可用的tokens"""
        return self.tokens.copy()
    
    def remove_token(self, token):
        """移除一个token"""
        if token in self.tokens:
            self.tokens.remove(token)
            self.token_count = len(self.tokens)
            logger.info(f"Removed GitHub token, now have {self.token_count} tokens")
            
            # 如果当前索引超出范围，重置到第一个token
            if self.current_token_index >= self.token_count and self.token_count > 0:
                self.current_token_index = 0
    
    def reset(self):
        """重置token索引到第一个"""
        self.current_token_index = 0
        logger.info("Reset GitHub token index to 0")
