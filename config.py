import os
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Base Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    DB_DIR = DATA_DIR # Database files in data directory
    CONFIG_YAML_PATH = os.path.join(BASE_DIR, 'config.yaml')

    # Ensure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # Load YAML Config
    try:
        with open(CONFIG_YAML_PATH, 'r', encoding='utf-8') as f:
            YAML_CONFIG = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load config.yaml: {e}")
        YAML_CONFIG = {}

    # Database Paths
    DB_PATH_CVE = os.path.join(DB_DIR, 'cve_record.db')
    DB_PATH_REPO = os.path.join(DB_DIR, 'github_repo.db')

    # GitHub Configuration
    # 优先使用环境变量GITHUB_TOKEN，然后是GITHUB_TOKENS，最后是配置文件中的值
    github_token = os.getenv('GITHUB_TOKEN')
    github_tokens_env = os.getenv('GITHUB_TOKENS')
    
    # 处理GITHUB_TOKENS环境变量（逗号分隔）
    github_tokens_from_env = []
    if github_tokens_env:
        github_tokens_from_env = [token.strip() for token in github_tokens_env.split(',') if token.strip()]
    
    # 从配置文件加载GitHub tokens
    github_tokens_from_config = YAML_CONFIG.get('github_tokens', [])
    
    # 合并所有tokens，确保去重和优先级
    GITHUB_TOKENS = []
    
    # 优先添加GITHUB_TOKEN
    if github_token:
        GITHUB_TOKENS.append(github_token)
    
    # 添加环境变量中的tokens
    GITHUB_TOKENS.extend(github_tokens_from_env)
    
    # 添加配置文件中的tokens
    if isinstance(github_tokens_from_config, list):
        GITHUB_TOKENS.extend(github_tokens_from_config)
    
    # 去重，避免重复使用同一个token
    GITHUB_TOKENS = list(dict.fromkeys(GITHUB_TOKENS))
    
    # 其他GitHub配置
    GITHUB_KEYWORDS = YAML_CONFIG.get('github_keywords', [])
    WATCHED_REPOSITORIES = YAML_CONFIG.get('watched_repositories', [])

    # Blacklists
    BLACKLIST_USERS = []
    BLACKLIST_REPOSITORIES = []

    # AI Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai').lower() # openai or gemini
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

    # Monitor Configuration
    MONITOR_INTERVAL = int(os.getenv('MONITOR_INTERVAL', 300))

    # Blog Configuration
    ENABLE_BLOG_PUBLISH = os.getenv('ENABLE_BLOG_PUBLISH', 'false').lower() == 'true'
    BLOG_API_URL = os.getenv('BLOG_API_URL')
    BLOG_TOKEN = os.getenv('BLOG_TOKEN')

    # DingTalk Configuration
    DINGTALK_TOKEN = os.getenv('DINGTALK_TOKEN')
    DINGTALK_SECRET = os.getenv('DINGTALK_SECRET')

    # Article Sources
    ARTICLE_SOURCES = YAML_CONFIG.get('article_sources', [])
    
    # Monitoring Configuration
    MONITORING = YAML_CONFIG.get('monitoring', {
        'enabled': True,
        'cve': True,
        'github': True,
        'articles': True,
        'auto_analyze': True
    })

    # Logging
    LOG_FILE = os.path.join(LOG_DIR, 'security_monitor.log')

    # Redis Configuration
    # Load from YAML config first, then override with environment variables
    REDIS_CONFIG = YAML_CONFIG.get('redis', {})
    REDIS_ENABLED = REDIS_CONFIG.get('enabled', False)
    REDIS_URL = os.getenv('REDIS_URL', REDIS_CONFIG.get('url', 'redis://localhost:6379/0'))
    REDIS_QUEUE = os.getenv('REDIS_QUEUE', REDIS_CONFIG.get('queue', 'threatvision_queue'))
    
    # UI Configuration
    UI_DATA_DIR = os.path.join(DATA_DIR, 'ui_data')
    UI_PORT = int(os.getenv('UI_PORT', '8000'))
    
    # RSS Configuration
    RSS_FILE = os.path.join(DATA_DIR, 'rss', 'security_news.xml')
    RSS_TITLE = '安全资讯日报'
    RSS_DESCRIPTION = '基于AI自动生成的安全资讯日报'
    RSS_LINK = os.getenv('RSS_LINK', '')
    
    # Ensure directories exist
    os.makedirs(UI_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'rss'), exist_ok=True)
    # Proxy Configuration
    PROXY_URL = os.getenv('PROXY_URL') or os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY')

    @staticmethod
    def get_proxies():
        """Get proxies dictionary for requests"""
        if Config.PROXY_URL:
            return {
                "http": Config.PROXY_URL,
                "https": Config.PROXY_URL
            }
        return None
