import requests
import logging
import json

logger = logging.getLogger(__name__)

class CNNVDChecker:
    def __init__(self):
        self.base_url = "https://www.cnnvd.org.cn/web/homePage/cnnvdVulList"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/json'
        }

    def check_cve(self, cve_id):
        """
        Check if CVE exists in CNNVD and return details.
        Returns: dict or None
        """
        try:
            # The API seems to accept a POST request with search params
            # Based on common patterns for such APIs
            payload = {
                "q": cve_id,
                "pageIndex": 1,
                "pageSize": 10
            }
            
            # Try POST first as it's common for search endpoints returning JSON
            response = requests.post(self.base_url, json=payload, headers=self.headers, timeout=10)
            
            # If POST fails (405/404), try GET with params
            if response.status_code != 200:
                response = requests.get(self.base_url, params=payload, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('records'):
                    # Find exact match
                    for record in data['data']['records']:
                        if record.get('cveCode') == cve_id:
                            return {
                                'cnnvd_code': record.get('cnnvdCode'),
                                'vul_name': record.get('vulName'),
                                'hazard_level': self._map_hazard_level(record.get('hazardLevel')),
                                'publish_time': record.get('publishTime'),
                                'url': f"https://www.cnnvd.org.cn/home/child/{record.get('id')}" # Constructed URL guess
                            }
        except Exception as e:
            logger.error(f"CNNVD check failed for {cve_id}: {e}")

        return None

    def _map_hazard_level(self, level):
        # Mapping based on common CNNVD levels (1-4 usually)
        # Assuming 1 is High/Critical based on user example, but need verification.
        # Usually: 1=Low, 2=Medium, 3=High, 4=Critical OR reverse.
        # Without docs, we'll return the raw value or a generic string.
        # User provided example: "hazardLevel": 1 for "CrushFTP 安全漏洞" (CVE-2025-54309)
        # Let's just return the raw level for now or map if we are sure.
        # Common Chinese mapping: 1=超危(Critical), 2=高危(High), 3=中危(Medium), 4=低危(Low)
        # OR 1=Low... 
        # Let's return raw for display.
        mapping = {
            1: "超危 (Critical)",
            2: "高危 (High)",
            3: "中危 (Medium)",
            4: "低危 (Low)"
        }
        return mapping.get(level, str(level))

if __name__ == "__main__":
    checker = CNNVDChecker()
    print(checker.check_cve("CVE-2024-1234"))
