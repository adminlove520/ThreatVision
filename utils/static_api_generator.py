import json
import os
import sys
import shutil
from datetime import datetime
from sqlalchemy import create_engine, desc

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from database.models import CVERecord, Repository, get_session
from utils.logger import setup_logger

logger = setup_logger(__name__)

from utils.mitre_checker import MitreChecker
from utils.cisa_checker import CISAChecker
from utils.cnnvd_checker import CNNVDChecker

class StaticAPIGenerator:
    def __init__(self):
        self.output_dir = os.path.join(Config.BASE_DIR, 'output', 'api')
        self.reports_dir = os.path.join(Config.DATA_DIR)
        
        # Database engines
        self.cve_engine = create_engine(f'sqlite:///{Config.DB_PATH_CVE}')
        self.repo_engine = create_engine(f'sqlite:///{Config.DB_PATH_REPO}')
        
        # Checkers
        self.mitre = MitreChecker()
        self.cisa = CISAChecker()
        self.cnnvd = CNNVDChecker()

    def ensure_output_dir(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'reports'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'cves'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'repos'), exist_ok=True)

    def generate_reports_api(self):
        """Generate /api/reports and /api/reports/{date}"""
        logger.info("Generating Reports API...")
        
        reports_list = []
        
        # Walk through data directory to find reports
        for root, dirs, files in os.walk(self.reports_dir):
            for file in files:
                if file.startswith('Daily_') and file.endswith('.md'):
                    date_str = file.replace('Daily_', '').replace('.md', '')
                    file_path = os.path.join(root, file)
                    
                    # Add to list
                    reports_list.append({
                        'date': date_str,
                        'path': file_path
                    })
                    
                    # Generate individual report JSON
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    report_data = {
                        'date': date_str,
                        'content': content
                    }
                    
                    # Save /api/reports/{date}.json
                    with open(os.path.join(self.output_dir, 'reports', f'{date_str}.json'), 'w', encoding='utf-8') as f:
                        json.dump(report_data, f, ensure_ascii=False)
        
        # Sort reports by date desc
        reports_list.sort(key=lambda x: x['date'], reverse=True)
        
        # Save /api/reports.json (index)
        index_data = {
            'total': len(reports_list),
            'reports': [{'date': r['date']} for r in reports_list]
        }
        
        with open(os.path.join(self.output_dir, 'reports.json'), 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False)

    def generate_cves_api(self):
        """Generate /api/cves and /api/cves/{id}"""
        logger.info("Generating CVEs API...")
        
        session = get_session(self.cve_engine)
        try:
            # Get all CVEs sorted by time
            cves = session.query(CVERecord).order_by(desc(CVERecord.update_time)).limit(100).all()
            
            cves_list = []
            for cve in cves:
                # Enrich Data
                mitre_info = self.mitre.check_cve(cve.cve_id)
                cisa_info = self.cisa.check_cve(cve.cve_id)
                cnnvd_info = self.cnnvd.check_cve(cve.cve_id)
                
                cve_data = {
                    'cve_id': cve.cve_id,
                    'description': cve.description,
                    'publish_time': cve.publish_time.isoformat() if cve.publish_time else None,
                    'update_time': cve.update_time.isoformat() if cve.update_time else None,
                    'cvss_score': cve.cvss_score,
                    'ai_analysis': cve.ai_analysis,
                    'mitre': mitre_info,
                    'cisa': cisa_info,
                    'cnnvd': cnnvd_info
                }
                cves_list.append(cve_data)
                
                # Save /api/cves/{id}.json
                with open(os.path.join(self.output_dir, 'cves', f'{cve.cve_id}.json'), 'w', encoding='utf-8') as f:
                    json.dump(cve_data, f, ensure_ascii=False)
            
            # Save /api/cves.json (index)
            index_data = {
                'total': len(cves_list),
                'cves': cves_list
            }
            
            with open(os.path.join(self.output_dir, 'cves.json'), 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False)
                
        finally:
            session.close()

    def generate_repos_api(self):
        """Generate /api/repos"""
        logger.info("Generating Repos API...")
        
        session = get_session(self.repo_engine)
        try:
            # Get all Repos sorted by update time
            repos = session.query(Repository).order_by(desc(Repository.last_updated)).limit(50).all()
            
            repos_list = []
            for repo in repos:
                repo_data = {
                    'name': repo.name,
                    'description': repo.description,
                    'url': repo.url,
                    'stars': repo.stars,
                    'last_updated': repo.last_updated.isoformat() if repo.last_updated else None,
                    'ai_analysis': repo.ai_analysis
                }
                repos_list.append(repo_data)
            
            # Save /api/repos.json (index)
            index_data = {
                'total': len(repos_list),
                'repos': repos_list
            }
            
            with open(os.path.join(self.output_dir, 'repos.json'), 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False)
                
        finally:
            session.close()

    def generate(self):
        self.ensure_output_dir()
        self.generate_reports_api()
        self.generate_cves_api()
        self.generate_repos_api()
        logger.info(f"Static API generated in {self.output_dir}")

if __name__ == "__main__":
    generator = StaticAPIGenerator()
    generator.generate()
