import os
import sys
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from config import Config

# 初始化logger
logger = setup_logger(__name__)

import openai
# 使用新的google.genai包替代过时的google.generativeai
try:
    import google.genai as genai
    logger.info("Using new google.genai package")
except ImportError:
    # 兼容处理：如果新包不可用，尝试使用旧包
    import google.generativeai as genai
    logger.warning("Using deprecated google.generativeai package, please upgrade to google.genai")

class AIAnalyzer:
    def __init__(self):
        # OpenAI Setup
        self.openai_api_key = Config.OPENAI_API_KEY
        self.openai_base_url = Config.OPENAI_BASE_URL
        self.openai_model = Config.OPENAI_MODEL
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
            openai.base_url = self.openai_base_url

        # Gemini Setup
        self.gemini_api_key = Config.GEMINI_API_KEY
        self.gemini_model = Config.GEMINI_MODEL
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)

    def _get_prompt(self, analysis_type, content):
        if analysis_type == 'cve':
            return f"""
            分析以下CVE漏洞信息,返回详细的结构化JSON分析。

            CVE信息: {content}

            请返回以下JSON格式(严格遵守,不要添加其他字段):
            {{
                "risk_level": "CRITICAL/HIGH/MEDIUM/LOW之一",
                "exploitation_status": "POC可用/漏洞利用可用/无公开利用/未知",
                "summary": "简明的漏洞概述,2-3句话",
                "key_findings": [
                    "关键发现1",
                    "关键发现2",
                    "至少3-5个关键点"
                ],
                "technical_details": [
                    "技术细节1: 漏洞原理说明",
                    "技术细节2: 利用方法",
                    "技术细节3: 修复建议"
                ],
                "affected_components": [
                    "受影响的软件/系统1",
                    "受影响的软件/系统2"
                ],
                "value_assessment": "对安全研究人员的价值评估,说明为什么重要"
            }}
            """
        elif analysis_type == 'repo':
            return f"""
            分析以下GitHub仓库更新信息,返回详细的结构化JSON分析。

            仓库信息: {content}

            请返回以下JSON格式(严格遵守):
            {{
                "security_type": "POC更新/漏洞利用/安全工具/C2框架/安全研究/恶意软件/其他",
                "update_type": "SECURITY_CRITICAL/SECURITY_IMPROVEMENT/新增/GENERAL_UPDATE",
                "risk_level": "CRITICAL/HIGH/MEDIUM/LOW",
                "summary": "仓库更新的简明概述,2-3句话",
                "key_findings": [
                    "关键发现1",
                    "关键发现2",
                    "至少3-4个关键点"
                ],
                "technical_details": [
                    "技术细节1",
                    "技术细节2"
                ],
                "affected_components": [
                    "相关技术/产品1",
                    "相关技术/产品2"
                ],
                "value_assessment": "对安全研究的价值,为什么值得关注",
                "is_malware": false
            }}
            """
        else:
            return f"Analyze the following text and provide a summary in JSON format: {content}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _call_openai(self, prompt):
        if not self.openai_api_key:
            raise Exception("OpenAI API key not configured")
            
        try:
            response = openai.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a cybersecurity expert assistant. You output strictly valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _call_gemini(self, prompt):
        if not self.gemini_api_key:
            raise Exception("Gemini API key not configured")
            
        try:
            model = genai.GenerativeModel(self.gemini_model)
            # Gemini doesn't enforce JSON mode as strictly as OpenAI, so we ask nicely
            response = model.generate_content(prompt + "\n\nOutput strictly valid JSON.")
            # Simple cleanup to ensure we get JSON
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return text.strip()
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise e

    def analyze_content(self, content, analysis_type='cve'):
        prompt = self._get_prompt(analysis_type, content)
        
        primary_provider = Config.AI_PROVIDER
        
        if primary_provider == 'gemini':
            # Try Gemini first
            try:
                logger.info(f"Attempting analysis with Gemini ({analysis_type})")
                result = self._call_gemini(prompt)
                return self._validate_json(result)
            except Exception as e:
                logger.warning(f"Gemini failed, switching to OpenAI: {e}")
                try:
                    result = self._call_openai(prompt)
                    return self._validate_json(result)
                except Exception as e2:
                    logger.error(f"All AI models failed after retries: {e2}")
                    return None
        else:
            # Default: Try OpenAI first
            try:
                logger.info(f"Attempting analysis with OpenAI ({analysis_type})")
                result = self._call_openai(prompt)
                return self._validate_json(result)
            except Exception as e:
                logger.warning(f"OpenAI failed, switching to Gemini: {e}")
                try:
                    result = self._call_gemini(prompt)
                    return self._validate_json(result)
                except Exception as e2:
                    logger.error(f"All AI models failed after retries: {e2}")
                    return None

    def classify_article(self, title, source=''):
        """
        Classify article into categories: 漏洞分析, 安全研究, 威胁情报, 安全工具, 最佳实践, 吃瓜新闻, 其他
        """
        prompt = f"""
        请将以下安全相关文章标题分类到一个最合适的类别中。
        
        文章标题: {title}
        来源: {source}
        
        类别选项:
        - 漏洞分析: CVE漏洞、漏洞复现、漏洞挖掘等
        - 安全研究: 技术研究、逆向分析、渗透测试案例等
        - 威胁情报: APT组织、攻击事件、恶意软件分析等
        - 安全工具: 安全工具介绍、工具更新等
        - 最佳实践: 安全防护指南、最佳实践、安全建议等
        - 吃瓜新闻: 行业动态、安全事件、周报等
        - 其他: 不属于以上任何类别
        
        返回JSON格式: {{"category": "类别名称"}}
        只返回一个最合适的类别,不要解释。
        """
        
        try:
            # Use primary provider
            if Config.AI_PROVIDER == 'gemini':
                result = self._call_gemini(prompt)
            else:
                result = self._call_openai(prompt)
            
            parsed = self._validate_json(result)
            if parsed and 'category' in parsed:
                return parsed['category']
        except Exception as e:
            logger.warning(f"Article classification failed: {e}")
        
        return "其他"

    def _validate_json(self, json_str):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from AI response")
            return None
