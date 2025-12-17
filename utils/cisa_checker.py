import requests
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class CISAChecker:
    def __init__(self, cache_file='data/cisa_kev.json'):
        self.kev_url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        self.cache_file = cache_file
        self.kev_data = {}
        self.load_data()

    def load_data(self):
        """Load KEV data from cache or download if expired/missing"""
        if os.path.exists(self.cache_file):
            # Check age (update daily)
            mtime = os.path.getmtime(self.cache_file)
            if (datetime.now().timestamp() - mtime) < 86400:
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        self.kev_data = json.load(f)
                    return
                except:
                    pass
        
        self.update_data()

    def update_data(self):
        """Download latest KEV catalog"""
        try:
            response = requests.get(self.kev_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # Convert to dict for fast lookup by CVE ID
                self.kev_data = {vuln['cveID']: vuln for vuln in data.get('vulnerabilities', [])}
                
                # Save cache
                os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.kev_data, f)
                logger.info("Updated CISA KEV cache")
            else:
                logger.error(f"Failed to download CISA KEV: {response.status_code}")
        except Exception as e:
            logger.error(f"Error updating CISA KEV: {e}")

    def check_cve(self, cve_id):
        """
        Check if CVE is in CISA KEV.
        Returns: dict or None
        """
        vuln = self.kev_data.get(cve_id)
        if vuln:
            return {
                'in_kev': True,
                'date_added': vuln.get('dateAdded'),
                'vendor_project': vuln.get('vendorProject'),
                'product': vuln.get('product'),
                'required_action': vuln.get('requiredAction')
            }
        return None

if __name__ == "__main__":
    checker = CISAChecker()
    # Test with a known KEV
    print(checker.check_cve("CVE-2021-44228"))
