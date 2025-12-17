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
    GITHUB_TOKENS = os.getenv('GITHUB_TOKENS', '').split(',')
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
