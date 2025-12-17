# 抑制所有FutureWarning警告，特别是google.generativeai的弃用警告
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import json
import time
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from config import Config

# 初始化logger
logger = setup_logger(__name__)

import openai
# 只使用新的google.genai包
try:
    from google import genai
    logger.info("Using new google.genai package")
except ImportError:
    logger.error("google.genai package is not available. Please install it with 'pip install google-genai'")
    genai = None

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
        self.gemini_client = None
        
        if self.gemini_api_key:
            try:
                # 使用新版google.genai包的Client API
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Gemini client: {e}")
                self.gemini_client = None

    def _get_prompt(self, analysis_type, content):
        if analysis_type == 'cve':
            return f"""
            # Role
            You are a Senior Cybersecurity Threat Intelligence Analyst (资深网络安全威胁情报分析师). Your task is to analyze the following CVE vulnerability and provide a professional risk assessment in **Chinese**.

            # Input Data
            CVE Information: {content}

            # Analysis Requirements
            1. **Risk Assessment**: Determine the practical risk level (CRITICAL/HIGH/MEDIUM/LOW) based on exploitability and impact.
            2. **Exploitation Status**: Accurate determination of exploit availability.
            3. **Technical Depth**: Provide technical details on the vulnerability mechanism and attack vector.
            4. **Value**: Assess the value for security researchers and defenders.
            5. **Language**: **All content in the JSON values must be in Chinese (简体中文).**

            # Output Format
            Return a strictly valid JSON object with the following schema:
            {{
                "risk_level": "CRITICAL", // CRITICAL, HIGH, MEDIUM, or LOW (Keep these keywords in English)
                "exploitation_status": "POC Available", // POC Available, Active Exploitation, No Known Exploit, or Unknown (Keep these keywords in English)
                "summary": "简明的漏洞概述，2-3句话 (Must be in Chinese)",
                "key_findings": [
                    "关键发现 1 (Must be in Chinese)",
                    "关键发现 2 (Must be in Chinese)",
                    "关键发现 3 (Must be in Chinese)"
                ],
                "technical_details": [
                    "漏洞原理说明 (Must be in Chinese)",
                    "攻击向量细节 (Must be in Chinese)",
                    "修复建议 (Must be in Chinese)"
                ],
                "affected_components": [
                    "受影响组件 1",
                    "受影响组件 2"
                ],
                "value_assessment": "对安全社区的价值评估 (Must be in Chinese)"
            }}
            """
        elif analysis_type == 'repo':
            return f"""
            # Role
            You are a Senior Security Researcher (资深安全研究员) specializing in open-source threat intelligence. Your task is to analyze the following GitHub repository update in **Chinese**.

            # Input Data
            Repository Information: {content}

            # Analysis Requirements
            1. **Classification**: Accurately classify the tool/code.
            2. **Intent Analysis**: Determine if the update introduces new offensive capabilities or is a defensive improvement.
            3. **Risk Level**: Assess the potential impact if this tool is misused.
            4. **Language**: **All content in the JSON values must be in Chinese (简体中文).**

            # Output Format
            Return a strictly valid JSON object with the following schema:
            {{
                "security_type": "POC", // POC, Exploit, Security Tool, C2 Framework, Malware, Research, or Other (Keep these keywords in English)
                "update_type": "SECURITY_CRITICAL", // SECURITY_CRITICAL, SECURITY_IMPROVEMENT, NEW_FEATURE, or GENERAL_UPDATE (Keep these keywords in English)
                "risk_level": "HIGH", // CRITICAL, HIGH, MEDIUM, or LOW (Keep these keywords in English)
                "summary": "仓库及更新的简明概述 (Must be in Chinese)",
                "key_findings": [
                    "主要能力 1 (Must be in Chinese)",
                    "主要能力 2 (Must be in Chinese)",
                    "主要能力 3 (Must be in Chinese)"
                ],
                "technical_details": [
                    "技术实现细节 (Must be in Chinese)",
                    "使用场景 (Must be in Chinese)"
                ],
                "affected_components": [
                    "目标技术/协议",
                    "受影响组件"
                ],
                "value_assessment": "对安全研究或红队的价值 (Must be in Chinese)",
                "is_malware": false // true if the repo itself is malicious, false otherwise
            }}
            """
        else:
            return f"Analyze the following text and provide a summary in JSON format (in Chinese): {content}"

    def _call_openai(self, prompt):
        if not self.openai_api_key:
            raise Exception("OpenAI API key not configured")
            
        # Validate Base URL
        if "api.openai.com" in self.openai_base_url and not self.openai_base_url.endswith("/v1"):
             logger.warning(f"OpenAI Base URL '{self.openai_base_url}' might be missing '/v1' suffix. Standard is 'https://api.openai.com/v1'")

        max_retries = 3
        for attempt in range(max_retries):
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
                error_msg = str(e)
                logger.warning(f"OpenAI API call failed (Attempt {attempt+1}/{max_retries}): {error_msg}")
                
                # Check for HTML response (Proxy/404 issue)
                if "<html" in error_msg.lower() or "404" in error_msg:
                    logger.error("OpenAI returned HTML or 404. This usually indicates a proxy or base URL configuration issue.")
                    logger.error(f"Current Base URL: {self.openai_base_url}")
                    # If it's a configuration error, retrying might not help, but we'll follow the loop
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt) # Exponential backoff: 1s, 2s, 4s
                else:
                    logger.error("OpenAI API failed after all retries.")
                    return None

    def _call_gemini(self, prompt):
        if not self.gemini_api_key:
            raise Exception("Gemini API key not configured")
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting analysis with Gemini ({self.gemini_model}) (Attempt {attempt+1}/{max_retries})")
                
                # 使用google.genai客户端库，按照API文档最佳实践
                from google import genai
                
                # 确保客户端已经初始化
                if not hasattr(self, 'gemini_client') or not self.gemini_client:
                    logger.info("Initializing Gemini client...")
                    self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                    logger.info("Gemini client initialized successfully")
                
                # 使用客户端库调用Gemini API，按照API文档
                # 注意：generate_content方法不接受generation_config参数
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=[
                        {
                            'parts': [
                                {
                                    'text': prompt + "\n\nOutput strictly valid JSON."
                                }
                            ]
                        }
                    ]
                )
                
                # 处理响应，按照客户端库的响应格式
                text = ""
                if hasattr(response, 'text'):
                    # 直接获取文本响应
                    text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    # 结构化响应
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    text += part.text
                
                # 清理JSON格式
                if text:
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    return text.strip()
                
                logger.warning(f"No valid text content found in Gemini response: {response}")
                # If no text, retry
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                
            except Exception as e:
                logger.warning(f"Gemini API call failed (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("Gemini API failed after all retries.")
                    return None
        return None
    
    def analyze_content(self, content, analysis_type='cve'):
        prompt = self._get_prompt(analysis_type, content)
        
        # 优先使用配置的提供商
        primary_provider = Config.AI_PROVIDER
        
        # 1. Try Primary Provider
        if primary_provider == 'gemini' and self.gemini_api_key:
            result = self._call_gemini(prompt)
            if result:
                validated = self._validate_json(result)
                if validated: return validated
        elif primary_provider == 'openai' and self.openai_api_key:
            result = self._call_openai(prompt)
            if result:
                validated = self._validate_json(result)
                if validated: return validated
        
        # 2. Try Secondary Provider (Fallback)
        logger.info(f"Primary provider {primary_provider} failed or not configured. Trying fallback...")
        
        if primary_provider == 'gemini' and self.openai_api_key:
            # Fallback to OpenAI
            result = self._call_openai(prompt)
            if result:
                validated = self._validate_json(result)
                if validated: return validated
        elif primary_provider != 'gemini' and self.gemini_api_key:
             # Fallback to Gemini
            result = self._call_gemini(prompt)
            if result:
                validated = self._validate_json(result)
                if validated: return validated
                
        logger.error("All AI providers failed.")
        return None

    def classify_article(self, title, source=''):
        """
        Classify article into categories: 漏洞分析, 安全研究, 威胁情报, 安全工具, 最佳实践, 吃瓜新闻, 其他
        """
        prompt = f"""
        # Role
        You are a Tech Content Curator for a cybersecurity news feed. Your task is to categorize the following article based on its title and source.

        # Input Data
        Article Title: {title}
        Source: {source}

        # Categories
        - **漏洞分析**: Deep dives into specific vulnerabilities (CVEs), reproduction steps, or exploit analysis.
        - **安全研究**: Technical research papers, reverse engineering, new attack techniques, or whitepapers.
        - **威胁情报**: APT reports, active campaign analysis, malware analysis, or breach reports.
        - **安全工具**: Releases or updates of security tools (red team/blue team).
        - **最佳实践**: Guides, tutorials, compliance, or defensive hardening.
        - **吃瓜新闻**: Industry news, acquisitions, gossip, or high-level summaries.
        - **其他**: Anything that doesn't fit the above.

        # Output Format
        Return a strictly valid JSON object:
        {{
            "category": "Category Name" // Must be one of the exact category names listed above
        }}
        """
        
        try:
            # Use primary provider
            if Config.AI_PROVIDER == 'gemini':
                result = self._call_gemini(prompt)
            else:
                result = self._call_openai(prompt)
            
            if result:
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
