import os
import requests
import listparser
import yaml
import sys
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class OPMLManager:
    def __init__(self):
        self.opml_dir = os.path.join(Config.DATA_DIR, 'opml')
        os.makedirs(self.opml_dir, exist_ok=True)
        # 优先从config.yaml读取RSS配置
        self.rss_config = Config.YAML_CONFIG.get('rss', {})
        # 保留news_sources.yaml作为补充配置
        self.news_sources_path = os.path.join(Config.DATA_DIR, 'news_sources.yaml')
        self.global_settings = {
            'refresh_interval': 3600,
            'max_retries': 3,
            'timeout': 15
        }

    def fetch_opml_files(self):
        """
        Download enabled OPML files from configuration.
        """
        downloaded_files = []
        timeout = self.global_settings['timeout']
        
        # 读取news_sources.yaml作为补充配置
        if os.path.exists(self.news_sources_path):
            try:
                with open(self.news_sources_path, 'r', encoding='utf-8') as f:
                    news_config = yaml.safe_load(f) or {}
                
                # 更新全局设置
                if 'global_settings' in news_config:
                    self.global_settings.update(news_config['global_settings'])
                    timeout = self.global_settings['timeout']
                
                logger.info(f"Loaded supplementary configuration from {self.news_sources_path}")
            except Exception as e:
                logger.error(f"Failed to load news_sources.yaml: {e}")
        
        # 从传统配置加载 OPML 源
        for name, config in self.rss_config.items():
            if not config.get('enabled', False):
                continue
            
            url = config.get('url')
            if not url:
                logger.warning(f"No URL specified for OPML source: {name}")
                continue
                
            filename = config.get('filename', f"{name}.opml")
            filepath = os.path.join(self.opml_dir, filename)
            
            try:
                logger.info(f"Downloading OPML: {name} from {url}")
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                downloaded_files.append(filepath)
                logger.info(f"Saved OPML to {filepath}")
            except Exception as e:
                logger.error(f"Failed to download OPML {name}: {e}")
        
        return downloaded_files

    def parse_opml(self, filepath: str) -> List[Dict[str, str]]:
        """
        Parse a single OPML file and return a structured list of feed information.
        """
        try:
            # Read file content first
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # Parse content
            parsed = listparser.parse(content)
            
            if parsed.bozo:
                logger.warning(f"OPML parsing had issues (bozo=1) for {filepath}: {parsed.bozo_exception}")
            
            feeds = []
            for feed in parsed.feeds:
                if hasattr(feed, 'url') and feed.url:
                    feed_info = {
                        'url': feed.url,
                        'title': getattr(feed, 'title', '').strip() or os.path.basename(filepath),
                        'description': getattr(feed, 'description', '').strip(),
                        'language': getattr(feed, 'language', '').strip() or 'unknown',
                        'category': getattr(feed, 'category', '').strip() or 'General',
                        'enabled': True
                    }
                    feeds.append(feed_info)
            
            logger.info(f"Parsed {len(feeds)} feeds from {filepath}")
            return feeds
        except Exception as e:
            logger.error(f"Error parsing OPML {filepath}: {e}")
            return []
    
    def convert_opml_to_yaml(self, opml_files: List[str], output_file: Optional[str] = None) -> bool:
        """
        Convert OPML files to a YAML configuration file.
        """
        if output_file is None:
            output_file = self.news_sources_path
        
        feeds_by_category: Dict[str, List[Dict[str, Any]]] = {}
        all_feeds = []
        
        # Parse all OPML files
        for opml_file in opml_files:
            if not os.path.exists(opml_file):
                logger.warning(f"OPML file not found: {opml_file}, skipping.")
                continue
            
            logger.info(f"Processing OPML file: {opml_file}")
            feeds = self.parse_opml(opml_file)
            all_feeds.extend(feeds)
        
        # Organize feeds by category
        for feed in all_feeds:
            category = feed['category']
            if category not in feeds_by_category:
                feeds_by_category[category] = []
            feeds_by_category[category].append(feed)
        
        # Generate YAML config
        yaml_config = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_feeds': len(all_feeds),
                'categories': list(feeds_by_category.keys())
            },
            'global_settings': self.global_settings,
            'feeds': feeds_by_category
        }
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        try:
            # Write to YAML file
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info(f"Successfully converted {len(all_feeds)} feeds from {len(opml_files)} OPML files to {output_file}")
            logger.info(f"Categories: {', '.join(feeds_by_category.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to write YAML configuration: {e}")
            return False

    def get_merged_feeds(self, use_local: bool = True, return_objects: bool = False) -> List:
        """
        Get merged RSS feed URLs.
        If use_local=True, use existing OPML files from disk without re-downloading.
        If use_local=False, download fresh OPML files first.
        If return_objects=True, return full feed objects instead of just URLs.
        """
        all_feed_objects: List[Dict[str, str]] = []
        feed_urls: Set[str] = set()
        
        # Step 1: Process OPML files from config.yaml (primary configuration)
        logger.info("Processing OPML files from config.yaml (primary configuration)")
        
        if use_local:
            # Use existing OPML files
            opml_files = []
            for name, config in self.rss_config.items():
                if not config.get('enabled', False):
                    continue
                filename = config.get('filename', f"{name}.opml")
                filepath = os.path.join(self.opml_dir, filename)
                if os.path.exists(filepath):
                    opml_files.append(filepath)
                    logger.info(f"Using local OPML: {filepath}")
                else:
                    logger.warning(f"OPML file not found: {filepath}, will download it")
                    # Download this specific file
                    try:
                        url = config.get('url')
                        if url:
                            response = requests.get(url, timeout=self.global_settings['timeout'])
                            response.raise_for_status()
                            with open(filepath, 'wb') as f:
                                f.write(response.content)
                            opml_files.append(filepath)
                            logger.info(f"Downloaded missing OPML to {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to download OPML {name}: {e}")
        else:
            # Download all OPML files
            opml_files = self.fetch_opml_files()
        
        # Parse OPML files from config.yaml
        for filepath in opml_files:
            feeds = self.parse_opml(filepath)
            logger.info(f"Found {len(feeds)} feeds in {os.path.basename(filepath)}")
            
            for feed in feeds:
                if feed['url'] not in feed_urls:
                    feed_urls.add(feed['url'])
                    all_feed_objects.append(feed)
        
        # Step 2: Read supplementary feeds from news_sources.yaml if available
        if os.path.exists(self.news_sources_path):
            try:
                logger.info(f"Processing supplementary feeds from {self.news_sources_path}")
                with open(self.news_sources_path, 'r', encoding='utf-8') as f:
                    news_config = yaml.safe_load(f) or {}
                
                # Extract all enabled feeds from categories
                if 'feeds' in news_config:
                    supplementary_count = 0
                    for category, feeds in news_config['feeds'].items():
                        for feed in feeds:
                            if feed.get('enabled', True) and feed.get('url') not in feed_urls:
                                feed_urls.add(feed['url'])
                                all_feed_objects.append(feed)
                                supplementary_count += 1
                    
                    logger.info(f"Added {supplementary_count} supplementary feeds from news_sources.yaml")
            except Exception as e:
                logger.error(f"Failed to load supplementary feeds from news_sources.yaml: {e}")
        
        logger.info(f"Total unique RSS feeds found: {len(feed_urls)}")
        
        if return_objects:
            return all_feed_objects
        else:
            return list(feed_urls)
    
    def update_all_sources(self) -> bool:
        """
        Update all OPML sources and convert to YAML configuration.
        """
        try:
            # Download all OPML files from config.yaml
            opml_files = self.fetch_opml_files()
            
            # Also include any existing OPML files not in configuration
            for filename in os.listdir(self.opml_dir):
                if filename.endswith('.opml'):
                    filepath = os.path.join(self.opml_dir, filename)
                    if filepath not in opml_files and os.path.exists(filepath):
                        opml_files.append(filepath)
            
            if not opml_files:
                logger.warning("No OPML files found to process")
                return False
            
            # Convert to YAML as supplementary configuration
            return self.convert_opml_to_yaml(opml_files)
        except Exception as e:
            logger.error(f"Failed to update all sources: {e}")
            return False

