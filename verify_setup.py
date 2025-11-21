import sys
import os
import logging

# Add code dir to path
sys.path.append(os.path.abspath("d:/safePro/project_20251121/ThreatVision/code"))

def verify_imports():
    print("Verifying imports...")
    try:
        from config import Config
        from database.models import init_db
        from utils.logger import setup_logger
        from monitors.cve_monitor import CVEMonitor
        from monitors.github_monitor import GithubMonitor
        from ai.analyzer import AIAnalyzer
        from main import ThreatVision
        import yaml
        from utils.dingtalk import DingTalkSender
        from utils.opml_manager import OPMLManager
        import feedparser
        import listparser
        print("Imports successful.")
        return True
    except Exception as e:
        print(f"Import failed: {e}")
        return False

def verify_init():
    print("Verifying initialization...")
    try:
        from main import ThreatVision
        app = ThreatVision()
        app.init_system()
        print("Initialization successful.")
        return True
    except Exception as e:
        print(f"Initialization failed: {e}")
        return False

if __name__ == "__main__":
    if verify_imports() and verify_init():
        print("VERIFICATION PASSED")
    else:
        print("VERIFICATION FAILED")
