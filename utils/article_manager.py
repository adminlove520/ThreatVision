import json
import os
import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from .logger import setup_logger
from .blog_manager import BlogManager
from .dingtalk import DingTalkSender

logger = setup_logger(__name__)

class ArticleManager:
    def __init__(self):
        self.processed_urls_file = os.path.join(Config.DATA_DIR, 'processed_urls.json')
        self.processed_urls = self.load_processed_urls()
        self.blog_manager = BlogManager()
        self.dingtalk_sender = DingTalkSender()
        
        # Category emoji mapping
        self.category_emoji = {
            "漏洞分析": "🔍",
            "安全研究": "🔬",
            "威胁情报": "🎯",
            "安全工具": "🛠️",
            "最佳实践": "📚",
            "吃瓜新闻": "🍉",
            "其他": "📌"
        }

    def load_processed_urls(self):
        if os.path.exists(self.processed_urls_file):
            try:
                with open(self.processed_urls_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading processed URLs: {e}")
                return set()
        return set()

    def save_processed_urls(self):
        try:
            with open(self.processed_urls_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_urls), f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving processed URLs: {e}")

    def is_new_url(self, url):
        return url not in self.processed_urls

    def mark_as_processed(self, url):
        self.processed_urls.add(url)
        self.save_processed_urls()

    def classify_articles(self, articles, analyzer):
        """Classify articles using AI"""
        classified = {}
        for article in articles:
            try:
                category = analyzer.classify_article(article.get('title', ''), article.get('source', ''))
                if category not in classified:
                    classified[category] = []
                classified[category].append(article)
                logger.info(f"Classified '{article['title'][:50]}...' as {category}")
            except Exception as e:
                logger.error(f"Error classifying article: {e}")
                if "其他" not in classified:
                    classified["其他"] = []
                classified["其他"].append(article)
        return classified

    def format_cve_section(self, cve):
        """Format CVE with detailed analysis"""
        content = f"\n### {cve.cve_id}"
        
        # Try to extract repo name if available
        if hasattr(cve, 'url') and cve.url:
            content += f" - {cve.url.split('/')[-1]}\n\n"
        else:
            content += "\n\n"
        
        content += "#### 📌 漏洞信息\n\n"
        content += "| 属性 | 详情 |\n"
        content += "|------|------|\n"
        content += f"| CVE编号 | {cve.cve_id} |\n"
        
        if cve.ai_analysis:
            try:
                analysis = json.loads(cve.ai_analysis)
                
                risk_level = analysis.get('risk_level', 'MEDIUM')
                # Map Chinese risk levels back to English keywords if necessary
                if '高' in risk_level: risk_level = 'HIGH'
                elif '中' in risk_level: risk_level = 'MEDIUM'
                elif '低' in risk_level: risk_level = 'LOW'
                elif '严重' in risk_level: risk_level = 'CRITICAL'
                content += f"| 风险等级 | `{risk_level}` |\n"
                content += f"| 利用状态 | `{analysis.get('exploitation_status', '未知')}` |\n"
                
                if hasattr(cve, 'publish_date'):
                    content += f"| 发布时间 | {cve.publish_date} |\n"
                
                content += "\n#### 💡 分析概述\n\n"
                content += f"{analysis.get('summary', 'N/A')}\n\n"
                
                if 'key_findings' in analysis and analysis['key_findings']:
                    content += "#### 🔍 关键发现\n\n"
                    content += "| 序号 | 发现内容 |\n"
                    content += "|------|----------|\n"
                    for idx, finding in enumerate(analysis['key_findings'], 1):
                        content += f"| {idx} | {finding} |\n"
                    content += "\n"
                
                if 'technical_details' in analysis and analysis['technical_details']:
                    content += "#### 🛠️ 技术细节\n\n"
                    for detail in analysis['technical_details']:
                        content += f"> {detail}\n\n"
                    content += "\n"
                
                if 'affected_components' in analysis and analysis['affected_components']:
                    content += "#### 🎯 受影响组件\n\n"
                    content += "```\n"
                    for comp in analysis['affected_components']:
                        content += f"• {comp}\n"
                    content += "```\n\n"
                
                if 'value_assessment' in analysis:
                    content += "#### ⚡ 价值评估\n\n"
                    content += "<details>\n"
                    content += "<summary>展开查看详细评估</summary>\n\n"
                    content += f"{analysis['value_assessment']}\n"
                    content += "</details>\n\n"
                
            except Exception as e:
                logger.error(f"Error formatting CVE {cve.cve_id}: {e}")
                content += f"\n**描述**: {cve.description}\n\n"
        else:
            content += f"\n**描述**: {cve.description}\n"
            content += f"\n**CVSS评分**: {cve.cvss_score}\n\n"
        
        content += "---\n"
        return content

    def format_repo_section(self, repo):
        """Format repository with detailed analysis"""
        content = f"\n### {repo.name}"
        
        if hasattr(repo, 'url') and repo.url:
            content += f" - [{repo.name}]({repo.url})\n\n"
        else:
            content += "\n\n"
        
        content += "#### 📌 仓库信息\n\n"
        content += "| 属性 | 详情 |\n"
        content += "|------|------|\n"
        content += f"| 仓库名称 | [{repo.name}]({repo.url}) |\n"
        
        if repo.ai_analysis:
            try:
                analysis = json.loads(repo.ai_analysis)
                
                content += f"| 风险等级 | `{analysis.get('risk_level', 'MEDIUM')}` |\n"
                content += f"| 安全类型 | `{analysis.get('security_type', '其他')}` |\n"
                content += f"| 更新类型 | `{analysis.get('update_type', 'GENERAL_UPDATE')}` |\n"
                content += "\n"
                
                if repo.stars:
                    content += f"#### 📊 代码统计\n\n"
                    content += f"- ⭐ Stars: **{repo.stars}**\n\n"
                
                content += "#### 💡 分析概述\n\n"
                content += f"{analysis.get('summary', repo.description)}\n\n"
                
                if 'key_findings' in analysis and analysis['key_findings']:
                    content += "#### 🔍 关键发现\n\n"
                    content += "| 序号 | 发现内容 |\n"
                    content += "|------|----------|\n"
                    for idx, finding in enumerate(analysis['key_findings'], 1):
                        content += f"| {idx} | {finding} |\n"
                    content += "\n"
                
                if 'technical_details' in analysis and analysis['technical_details']:
                    content += "#### 🛠️ 技术细节\n\n"
                    for detail in analysis['technical_details']:
                        content += f"> {detail}\n\n"
                    content += "\n"
                
                if 'affected_components' in analysis and analysis['affected_components']:
                    content += "#### 🎯 受影响组件\n\n"
                    content += "```\n"
                    for comp in analysis['affected_components']:
                        content += f"• {comp}\n"
                    content += "```\n\n"
                
                if 'value_assessment' in analysis:
                    content += "#### ⚡ 价值评估\n\n"
                    content += "<details>\n"
                    content += "<summary>展开查看详细评估</summary>\n\n"
                    content += f"{analysis['value_assessment']}\n"
                    content += "</details>\n\n"
                
            except Exception as e:
                logger.error(f"Error formatting repo {repo.name}: {e}")
                content += f"\n**描述**: {repo.description}\n\n"
        else:
            content += f"\n**描述**: {repo.description}\n"
            content += f"\n**Stars**: {repo.stars}\n\n"
        
        content += "---\n"
        return content

    def generate_daily_report(self, cve_data, repo_data, articles_data, analyzer=None):
        """
        Generate a professional markdown report
        """
        now = datetime.datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        year_str = now.strftime('%Y')
        time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        title = f"安全资讯日报 {date_str}"
        
        # Header
        content = f"\n# {title}\n\n"
        content += "> 本文由AI自动生成,基于对安全相关仓库、CVE和最新安全研究成果的自动化分析。\n"
        content += f"> \n"
        content += f"> 更新时间:{time_str}\n\n"
        content += "<!-- more -->\n\n"
        
        # Today's News Section
        content += "## 今日资讯\n\n"
        
        if articles_data and analyzer:
            classified = self.classify_articles(articles_data, analyzer)
            
            # Order categories
            category_order = ["漏洞分析", "安全研究", "威胁情报", "安全工具", "最佳实践", "吃瓜新闻", "其他"]
            
            for category in category_order:
                if category in classified and classified[category]:
                    emoji = self.category_emoji.get(category, "📌")
                    content += f"### {emoji} {category}\n\n"
                    for article in classified[category]:
                        content += f"* [{article['title']}]({article['url']})\n"
                    content += "\n"
        elif articles_data:
            # Fallback: no classification
            content += "### 📰 安全文章\n\n"
            for article in articles_data:
                content += f"* [{article['title']}]({article['url']})\n"
            content += "\n"
        else:
            content += "今日暂无新文章。\n\n"
        
        # Security Analysis Section
        content += "## 安全分析\n"
        content += f"({date_str})\n\n"
        content += "本文档包含 AI 对安全相关内容的自动化分析结果。\n\n"
        
        # CVE Analysis
        if cve_data:
            for cve in cve_data:
                content += self.format_cve_section(cve)
        
        # Repository Analysis
        if repo_data:
            for repo in repo_data:
                content += self.format_repo_section(repo)
        
        if not cve_data and not repo_data:
            content += "今日暂无重要安全分析内容。\n\n"
        
        # Save locally: /YYYY/YYYY-MM-DD/Daily_YYYY-MM-DD.md
        report_dir = os.path.join(Config.DATA_DIR, year_str, date_str)
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"Daily_{date_str}.md")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Generated daily report: {report_path}")

        # Publish to blog if enabled
        if Config.ENABLE_BLOG_PUBLISH:
            self.blog_manager.publish_article(title, content)
        else:
            logger.info("Blog publishing is disabled.")

        # Push to DingTalk
        summary = f"# {title}\n\n生成了{len(cve_data) if cve_data else 0}个CVE分析和{len(repo_data) if repo_data else 0}个仓库分析。"
        self.dingtalk_sender.send_markdown(title, summary)
        
        # Update RSS feed
        try:
            from utils.rss_generator import RSSGenerator
            rss_generator = RSSGenerator()
            rss_generator.update_rss()
            logger.info("RSS feed updated successfully")
        except Exception as e:
            logger.error(f"Failed to update RSS feed: {e}")
        
        # Push report to GitHub Release
        try:
            from utils.github_release import GitHubReleaseManager
            github_release_manager = GitHubReleaseManager()
            github_release_manager.push_report_to_release(report_path)
            logger.info("Report pushed to GitHub Release successfully")
        except Exception as e:
            logger.error(f"Failed to push report to GitHub Release: {e}")
        
        return report_path
