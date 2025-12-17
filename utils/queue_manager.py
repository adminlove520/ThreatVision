from config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

# Try to import Redis and RQ modules
try:
    import redis
    from rq import Queue
    from rq.job import Job
    REDIS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Redis/RQ modules not available: {e}")
    REDIS_AVAILABLE = False

class QueueManager:
    def __init__(self):
        self.redis_conn = None
        self.queue = None
        self.redis_available = False
        self.connection_checked = False
        self.ping_checked = False
        self.memory_queue = []  # In-memory queue as fallback
        self.use_memory_queue = True  # Default to memory queue
        
        # Only try to connect to Redis if:
        # 1. Redis is enabled in config
        # 2. Redis/RQ modules are available
        if Config.REDIS_ENABLED and REDIS_AVAILABLE:
            try:
                # Create Redis connection
                self.redis_conn = redis.from_url(Config.REDIS_URL)
                
                # Immediately check if connection is alive
                if self.redis_conn.ping():
                    # Create Queue instance only if connection is alive
                    self.queue = Queue(Config.REDIS_QUEUE, connection=self.redis_conn)
                    logger.info(f"Connected to Redis queue: {Config.REDIS_QUEUE}")
                    self.redis_available = True
                    self.use_memory_queue = False
                else:
                    logger.warning("Redis server is running but ping failed, falling back to in-memory queue")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                logger.info("Redis is not available, using in-memory queue")
                self.redis_conn = None
                self.queue = None
        elif Config.REDIS_ENABLED:
            logger.warning("Redis is enabled but Redis/RQ modules are not available, using in-memory queue")
        else:
            logger.info("Redis is disabled in config, using in-memory queue")
    
    def add_task(self, func, *args, **kwargs):
        """Add a task to the queue, or execute directly if queue is unavailable"""
        # If Redis queue is available, use it
        if self.queue and not self.use_memory_queue:
            try:
                job = self.queue.enqueue(func, *args, **kwargs)
                logger.info(f"Added task to queue: {func.__name__} (Job ID: {job.id})")
                return job.id
            except Exception as e:
                logger.warning(f"Failed to add task to Redis queue: {e}")
                logger.info("Falling back to direct execution")
                
        # Fallback to direct execution (in-memory queue alternative)
        try:
            logger.info(f"Executing task directly: {func.__name__}")
            func(*args, **kwargs)
            return f"direct-{id(func)}"  # Return a dummy ID for direct execution
        except Exception as e:
            logger.error(f"Failed to execute task directly: {e}")
            return None
    
    def get_job_status(self, job_id):
        """Get the status of a job"""
        if not self.redis_conn:
            logger.error("Redis connection not initialized")
            return None
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return {
                'id': job.id,
                'status': job.status,
                'result': job.result,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'ended_at': job.ended_at
            }
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None
    
    def get_queue_length(self):
        """Get the current queue length"""
        if not self.queue:
            logger.error("Queue not initialized")
            return 0
        
        try:
            return len(self.queue)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    def is_connected(self):
        """Check if Redis connection is alive"""
        # If we don't have a connection at all, return False immediately
        if not self.redis_conn:
            return False
        
        # Only check connection once per instance to avoid repeated logs
        if self.ping_checked:
            return self.redis_available
        
        try:
            # Try to ping Redis to check if connection is alive
            self.redis_available = self.redis_conn.ping()
            self.ping_checked = True
            return self.redis_available
        except Exception as e:
            # Only log warning once, not every time we check
            # We already logged the connection failure in __init__
            self.redis_available = False
            self.ping_checked = True
            return False
    
    def add_cve_monitor_task(self):
        """Add CVE monitor task to queue"""
        from monitors.cve_monitor import CVEMonitor
        
        def cve_monitor_wrapper():
            cve_monitor = CVEMonitor()
            cve_monitor.monitor()
        
        return self.add_task(cve_monitor_wrapper)
    
    def add_github_monitor_task(self):
        """Add GitHub monitor task to queue"""
        from monitors.github_monitor import GithubMonitor
        
        def github_monitor_wrapper():
            github_monitor = GithubMonitor()
            github_monitor.monitor()
        
        return self.add_task(github_monitor_wrapper)
    
    def add_analysis_task(self, item_type, item_id, description):
        """Add AI analysis task to queue"""
        def analysis_wrapper():
            from ai.analyzer import AIAnalyzer
            from database.models import get_session
            from monitors.cve_monitor import CVEMonitor
            from monitors.github_monitor import GithubMonitor
            
            analyzer = AIAnalyzer()
            result = analyzer.analyze_content(description, item_type)
            
            if item_type == 'cve':
                session = get_session(CVEMonitor.engine)
                try:
                    from database.models import CVERecord
                    cve = session.query(CVERecord).filter(CVERecord.cve_id == item_id).first()
                    if cve:
                        import json
                        cve.ai_analysis = json.dumps(result)
                        if result.get('risk_level') == 'High':
                            cve.is_high_value = True
                        session.commit()
                        logger.info(f"Analysis complete for CVE: {item_id}")
                finally:
                    session.close()
            elif item_type == 'repo':
                session = get_session(GithubMonitor.engine)
                try:
                    from database.models import Repository
                    repo = session.query(Repository).filter(Repository.name == item_id).first()
                    if repo:
                        import json
                        repo.ai_analysis = json.dumps(result)
                        session.commit()
                        logger.info(f"Analysis complete for Repo: {item_id}")
                finally:
                    session.close()
        
        return self.add_task(analysis_wrapper)
    
    def add_article_fetch_task(self, feed_urls):
        """Add article fetch task to queue"""
        def fetch_wrapper():
            from utils.article_fetcher import ArticleFetcher
            fetcher = ArticleFetcher()
            return fetcher.fetch_rss_articles(feed_urls)
        
        return self.add_task(fetch_wrapper)
    
    def add_daily_report_task(self):
        """Add daily report generation task to queue"""
        def report_wrapper():
            from threatvision import ThreatVision
            threatvision = ThreatVision()
            threatvision.daily_job()
        
        return self.add_task(report_wrapper)
