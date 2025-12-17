import time
import schedule
import threading
import signal
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from database.models import init_db, get_session, CVERecord, Repository
from monitors.cve_monitor import CVEMonitor
from monitors.github_monitor import GithubMonitor
from ai.analyzer import AIAnalyzer
from utils.logger import setup_logger
from utils.article_manager import ArticleManager
from utils.article_fetcher import ArticleFetcher
from utils.queue_manager import QueueManager

logger = setup_logger("Main")

class ThreatVision:
    def __init__(self):
        self.running = True
        self.cve_monitor = CVEMonitor()
        self.github_monitor = GithubMonitor()
        self.analyzer = AIAnalyzer()
        self.article_manager = ArticleManager()
        self.article_fetcher = ArticleFetcher()
        
        # Redis Queue Manager
        self.queue_manager = QueueManager()
        
        # Thread pool for analysis tasks (fallback if Redis is not available)
        self.executor = ThreadPoolExecutor(max_workers=3)

    def init_system(self):
        logger.info("Initializing ThreatVision...")
        init_db()
        logger.info("Database initialized.")

    def run_monitors(self):
        """Run monitors in a loop"""
        while self.running:
            try:
                logger.info("--- Starting Monitor Cycle ---")
                
                # Check if monitoring is enabled at all
                if Config.MONITORING.get('enabled', True):
                    # 1. CVE Monitor - Add to Redis Queue
                    if Config.MONITORING.get('cve', True):
                        logger.info("Running CVE Monitor...")
                        if self.queue_manager.is_connected():
                            self.queue_manager.add_cve_monitor_task()
                        else:
                            # Fallback to direct execution
                            logger.warning("Redis not connected, falling back to direct execution for CVE monitoring")
                            self.cve_monitor.monitor()
                    else:
                        logger.info("CVE monitoring is disabled in config")
                
                # 2. GitHub Monitor - Add to Redis Queue
                if Config.MONITORING.get('enabled', True) and Config.MONITORING.get('github', True):
                    logger.info("Running GitHub Monitor...")
                    if self.queue_manager.is_connected():
                        self.queue_manager.add_github_monitor_task()
                    else:
                        # Fallback to direct execution
                        logger.warning("Redis not connected, falling back to direct execution for GitHub monitoring")
                        self.github_monitor.monitor()
                else:
                    logger.info("GitHub monitoring is disabled in config")
                
                # 3. Trigger Analysis (Async) - only if auto_analyze is enabled
                if Config.MONITORING.get('enabled', True) and Config.MONITORING.get('auto_analyze', True):
                    logger.info("Triggering AI analysis...")
                    self.trigger_analysis()
                else:
                    logger.info("Auto analysis is disabled in config")
                
                logger.info(f"Cycle complete. Sleeping for {Config.MONITOR_INTERVAL}s")
                for _ in range(Config.MONITOR_INTERVAL):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(60)

    def trigger_analysis(self):
        """Check DB for unanalyzed items and submit to AI"""
        # CVEs
        session = get_session(self.cve_monitor.engine)
        try:
            unprocessed_cves = session.query(CVERecord).filter(CVERecord.ai_analysis == None).limit(5).all()
            for cve in unprocessed_cves:
                if self.queue_manager.is_connected():
                    self.queue_manager.add_analysis_task('cve', cve.cve_id, cve.description)
                else:
                    # Fallback to direct execution
                    self.executor.submit(self.analyze_cve, cve.cve_id, cve.description)
        finally:
            session.close()

        # Repos
        session = get_session(self.github_monitor.engine)
        try:
            unprocessed_repos = session.query(Repository).filter(Repository.ai_analysis == None).limit(5).all()
            for repo in unprocessed_repos:
                if self.queue_manager.is_connected():
                    self.queue_manager.add_analysis_task('repo', repo.name, repo.description)
                else:
                    # Fallback to direct execution
                    self.executor.submit(self.analyze_repo, repo.name, repo.description)
        finally:
            session.close()

    def analyze_cve(self, cve_id, description):
        logger.info(f"Analyzing CVE: {cve_id}")
        result = self.analyzer.analyze_content(description, 'cve')
        if result:
            # Update DB
            import json
            session = get_session(self.cve_monitor.engine)
            try:
                record = session.query(CVERecord).filter_by(cve_id=cve_id).first()
                if record:
                    record.ai_analysis = json.dumps(result)
                    if result.get('risk_level') == 'High':
                        record.is_high_value = True
                    session.commit()
                    logger.info(f"Analysis complete for {cve_id}")
            except Exception as e:
                logger.error(f"Error saving analysis for {cve_id}: {e}")
            finally:
                session.close()

    def analyze_repo(self, repo_name, description):
        logger.info(f"Analyzing Repo: {repo_name}")
        result = self.analyzer.analyze_content(description, 'repo')
        if result:
            import json
            session = get_session(self.github_monitor.engine)
            try:
                record = session.query(Repository).filter_by(name=repo_name).first()
                if record:
                    record.ai_analysis = json.dumps(result)
                    session.commit()
                    logger.info(f"Analysis complete for {repo_name}")
            except Exception as e:
                logger.error(f"Error saving analysis for {repo_name}: {e}")
            finally:
                session.close()

    def daily_job(self):
        logger.info("Running daily reporting job...")
        
        # 1. Fetch Articles (RSS + Configured Sources) - only if articles monitoring is enabled
        articles = []
        if Config.MONITORING.get('enabled', True) and Config.MONITORING.get('articles', True):
            # RSS Feeds from OPML
            try:
                from utils.opml_manager import OPMLManager
                opml_manager = OPMLManager()
                # 使用新的方法获取更详细的feed信息
                feeds_with_info = opml_manager.get_merged_feeds(return_objects=True)
                logger.info(f"Processing {len(feeds_with_info)} RSS feeds for daily report")
                rss_feeds = [feed['url'] for feed in feeds_with_info]
                
                # Fetch RSS articles in parallel
                logger.info(f"Fetching articles from {len(rss_feeds)} feeds in parallel...")
                futures = []
                for url in rss_feeds:
                    futures.append(self.executor.submit(self.article_fetcher.fetch_rss_articles, [url]))
                
                for future in as_completed(futures):
                    try:
                        fetched = future.result()
                        if fetched:
                            articles.extend(fetched)
                    except Exception as e:
                        logger.error(f"Error in RSS fetch task: {e}")
                
                logger.info(f"Fetched total {len(articles)} articles from RSS feeds.")
            except Exception as e:
                logger.error(f"Error fetching RSS articles: {e}")
        else:
            logger.info("Articles monitoring is disabled in config")

        # Filter new articles
        new_articles = []
        for art in articles:
            if self.article_manager.is_new_url(art['url']):
                new_articles.append(art)
                self.article_manager.mark_as_processed(art['url'])
        
        logger.info(f"Total new articles to report: {len(new_articles)}")

        # 2. Collect data for report
        session_cve = get_session(self.cve_monitor.engine)
        cves = session_cve.query(CVERecord).filter(CVERecord.is_high_value == True).limit(10).all()

        session_repo = get_session(self.github_monitor.engine)
        repos = session_repo.query(Repository).filter(Repository.is_high_value == True).limit(10).all()

        # 3. Generate Report (pass analyzer for article classification)
        report_path = self.article_manager.generate_daily_report(cves, repos, new_articles, self.analyzer)
        logger.info(f"Daily job finished. Report: {report_path}")

        session_cve.close()
        session_repo.close()

    def run_once(self):
        """Run a single cycle of monitoring, analysis, and reporting (for CI/CD)"""
        self.init_system()
        logger.info("Running single execution cycle...")
        
        # 1. Monitors
        if Config.MONITORING.get('enabled', True):
            if Config.MONITORING.get('cve', True):
                logger.info("Running CVE Monitor...")
                self.cve_monitor.monitor()
            else:
                logger.info("CVE monitoring is disabled in config")
        
        if Config.MONITORING.get('enabled', True) and Config.MONITORING.get('github', True):
            logger.info("Running GitHub Monitor...")
            self.github_monitor.monitor()
        else:
            logger.info("GitHub monitoring is disabled in config")
        
        # 2. Analysis
        if Config.MONITORING.get('enabled', True) and Config.MONITORING.get('auto_analyze', True):
            logger.info("Triggering AI analysis...")
            
            try:
                # Check if Redis queue is enabled and available
                if self.queue_manager.is_connected():
                    # When Redis queue is available, execute analysis tasks directly instead of adding to queue
                    # This ensures analysis completes before report generation
                    logger.info("Using direct execution for analysis tasks to ensure completion before report generation")
                    
                    # CVEs
                    session = get_session(self.cve_monitor.engine)
                    try:
                        unprocessed_cves = session.query(CVERecord).filter(CVERecord.ai_analysis == None).limit(5).all()
                        for cve in unprocessed_cves:
                            try:
                                self.analyze_cve(cve.cve_id, cve.description)
                            except Exception as e:
                                logger.error(f"Error analyzing CVE {cve.cve_id}: {e}")
                                # 继续分析下一个CVE，不中断整个流程
                                continue
                    finally:
                        session.close()
                    
                    # Repos
                    session = get_session(self.github_monitor.engine)
                    try:
                        unprocessed_repos = session.query(Repository).filter(Repository.ai_analysis == None).limit(5).all()
                        for repo in unprocessed_repos:
                            try:
                                self.analyze_repo(repo.name, repo.description)
                            except Exception as e:
                                logger.error(f"Error analyzing Repo {repo.name}: {e}")
                                # 继续分析下一个仓库，不中断整个流程
                                continue
                    finally:
                        session.close()
                else:
                    # When Redis queue is not available, use thread pool
                    self.trigger_analysis()
                    # Wait for completion
                    logger.info("Waiting for analysis to complete...")
                    self.executor.shutdown(wait=True)
                    
                    # Re-init executor for potential future use (though we are exiting)
                    self.executor = ThreadPoolExecutor(max_workers=3)
            except Exception as e:
                logger.error(f"Error during AI analysis: {e}")
                logger.info("AI analysis failed, proceeding to report generation with available data...")
        else:
            logger.info("Auto analysis is disabled in config")
        
        # 3. Report
        logger.info("Generating daily report...")
        self.daily_job()
        logger.info("Single execution cycle complete.")

    def start(self):
        self.init_system()
        
        # Schedule daily report (e.g., at 09:00 AM)
        schedule.every().day.at("09:00").do(self.daily_job)
        
        # Start monitor thread
        monitor_thread = threading.Thread(target=self.run_monitors, daemon=True)
        monitor_thread.start()
        
        # Start scheduler loop
        logger.info("System started. Press Ctrl+C to stop.")
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        logger.info("Stopping system...")
        self.running = False
        logger.info("Waiting for pending tasks to complete...")
        self.executor.shutdown(wait=True)
        logger.info("System stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Run one cycle and exit (for Cron/CI)')
    args = parser.parse_args()

    app = ThreatVision()
    
    if args.once:
        app.run_once()
    else:
        # Handle signals
        def signal_handler(sig, frame):
            app.stop()
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        app.start()
