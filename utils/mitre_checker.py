import requests
import logging

logger = logging.getLogger(__name__)

class MitreChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def check_cve(self, cve_id):
        """
        Check if CVE exists and return details if possible.
        Returns: dict or None
        """
        # 1. Try CVE.org API (New MITRE API)
        try:
            url = f"https://cveawg.mitre.org/api/cve/{cve_id}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extract useful info
                try:
                    metadata = data.get('cveMetadata', {})
                    cna = data.get('containers', {}).get('cna', {})
                    
                    # Dates
                    date_published = metadata.get('datePublished')
                    date_updated = metadata.get('dateUpdated')
                    
                    # Description
                    desc = "N/A"
                    if 'descriptions' in cna:
                        desc = cna['descriptions'][0].get('value', 'N/A')
                        
                    # Metrics (CVSS)
                    metrics = []
                    if 'metrics' in cna:
                        for m in cna['metrics']:
                            if 'cvssV3_1' in m:
                                metrics.append(m['cvssV3_1'])
                            elif 'cvssV3_0' in m:
                                metrics.append(m['cvssV3_0'])
                            elif 'cvssV2_0' in m:
                                metrics.append(m['cvssV2_0'])
                                
                    # Affected Products
                    affected = []
                    if 'affected' in cna:
                        for item in cna['affected']:
                            product = item.get('product', 'Unknown')
                            vendor = item.get('vendor', 'Unknown')
                            versions = []
                            if 'versions' in item:
                                for v in item['versions']:
                                    ver_str = v.get('version', '')
                                    if v.get('lessThan'):
                                        ver_str += f" ( < {v.get('lessThan')} )"
                                    versions.append(ver_str)
                            affected.append({
                                'vendor': vendor,
                                'product': product,
                                'versions': versions
                            })
                            
                    # References
                    references = []
                    if 'references' in cna:
                        for ref in cna['references']:
                            references.append({
                                'url': ref.get('url'),
                                'name': ref.get('name', ref.get('url'))
                            })

                    return {
                        'source': 'CVE.org',
                        'exists': True,
                        'cna': metadata.get('assignerShortName', 'Unknown'),
                        'description': desc,
                        'datePublished': date_published,
                        'dateUpdated': date_updated,
                        'metrics': metrics,
                        'affected': affected,
                        'references': references,
                        'url': f"https://www.cve.org/CVERecord?id={cve_id}"
                    }
                except Exception as e:
                    logger.error(f"Error parsing CVE data: {e}")
                    return {'source': 'CVE.org', 'exists': True, 'url': f"https://www.cve.org/CVERecord?id={cve_id}"}
        except Exception as e:
            logger.error(f"CVE.org API failed for {cve_id}: {e}")

        # 2. Fallback to MITRE HTML
        try:
            url = f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={cve_id}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200 and cve_id in response.text and "CVE" in response.text:
                return {
                    'source': 'MITRE Legacy',
                    'exists': True,
                    'url': url,
                    'description': 'Details available on MITRE website'
                }
        except Exception as e:
            logger.error(f"MITRE HTML check failed for {cve_id}: {e}")

        return None

if __name__ == "__main__":
    # Test
    checker = MitreChecker()
    print(checker.check_cve("CVE-2023-1234"))
