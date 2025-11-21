import os
import yaml
import listparser
import argparse
from datetime import datetime

def parse_opml_file(opml_file):
    """
    Parse an OPML file and return a structured dictionary of feeds.
    """
    try:
        with open(opml_file, 'rb') as f:
            content = f.read()
        
        parsed = listparser.parse(content)
        feeds = []
        
        for feed in parsed.feeds:
            feed_info = {
                'url': getattr(feed, 'url', ''),
                'title': getattr(feed, 'title', '').strip() or f'Feed {len(feeds) + 1}',
                'description': getattr(feed, 'description', '').strip(),
                'language': getattr(feed, 'language', '').strip(),
                'category': getattr(feed, 'category', '').strip() or 'General',
                'enabled': True
            }
            
            # 过滤掉空URL
            if feed_info['url']:
                feeds.append(feed_info)
        
        return feeds
    except Exception as e:
        print(f"Error parsing {opml_file}: {e}")
        return []

def convert_opml_to_yaml(opml_files, output_file):
    """
    Convert multiple OPML files to a single YAML configuration file.
    """
    feeds_by_category = {}
    all_feeds = []
    
    # 解析所有OPML文件
    for opml_file in opml_files:
        if not os.path.exists(opml_file):
            print(f"Warning: {opml_file} not found, skipping.")
            continue
        
        print(f"Processing {opml_file}...")
        feeds = parse_opml_file(opml_file)
        all_feeds.extend(feeds)
    
    # 按类别组织feed
    for feed in all_feeds:
        category = feed['category']
        if category not in feeds_by_category:
            feeds_by_category[category] = []
        feeds_by_category[category].append(feed)
    
    # 生成YAML配置
    yaml_config = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_feeds': len(all_feeds),
            'categories': list(feeds_by_category.keys())
        },
        'global_settings': {
            'refresh_interval': 3600,
            'max_retries': 3,
            'timeout': 15
        },
        'feeds': feeds_by_category
    }
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 写入YAML文件
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"Successfully converted {len(all_feeds)} feeds from {len(opml_files)} OPML files to {output_file}")
    print(f"Categories: {', '.join(feeds_by_category.keys())}")

def main():
    parser = argparse.ArgumentParser(description='Convert OPML files to YAML configuration')
    parser.add_argument('opml_files', nargs='+', help='Path to OPML files')
    parser.add_argument('-o', '--output', default='news_sources.yaml', help='Output YAML file path')
    
    args = parser.parse_args()
    convert_opml_to_yaml(args.opml_files, args.output)

if __name__ == '__main__':
    main()