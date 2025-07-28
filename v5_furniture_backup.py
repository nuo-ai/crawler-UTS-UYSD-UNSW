#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
房产数据爬虫脚本 - v2 (for Web UI integration)
- Reads URLs from config/temp_urls.txt if present, otherwise config/url.txt.
- Outputs to a timestamped CSV file.
- Prints the output CSV filename to stdout.
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Set, Any
from dataclasses import dataclass, field
from functools import wraps
import threading
import re
import yaml
import random
import gc
import sys # Added for printing to stdout

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree # type: ignore

# =============================================================================
# 项目路径配置
# =============================================================================
PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / 'logs'
CONFIG_DIR = PROJECT_ROOT / 'config'
OUTPUT_DIR = PROJECT_ROOT / 'output'
DATA_DIR = OUTPUT_DIR / 'data' # Retained from original, though not explicitly used for CSV output path

for d_path in (LOG_DIR, CONFIG_DIR, OUTPUT_DIR, DATA_DIR):
    d_path.mkdir(exist_ok=True)

# =============================================================================
# 日志配置
# =============================================================================
def setup_logger(name: str = 'domain_crawler_v2') -> logging.Logger: # Changed logger name
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(logging.DEBUG)
    if logger_instance.handlers:
        return logger_instance
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log_file = LOG_DIR / f"domain_crawler_v2_{datetime.now():%Y%m%d_%H%M%S}.log" # Changed log file name
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger_instance.addHandler(ch)
    logger_instance.addHandler(fh)
    return logger_instance

logger = setup_logger()

# =============================================================================
# 配置加载
# =============================================================================
def load_config() -> dict:
    config_path = CONFIG_DIR / 'crawler_config.yaml'
    if not config_path.exists():
        default_config_content = {
            'network': {'max_retries': 3, 'backoff_factor': 0.5, 'retry_statuses': [500, 502, 503, 504], 'timeout': 20},
            'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'},
            'performance': {'requests_per_second': 1.5, 'batch_size': 50, 'results_per_page_threshold': 10,
                            'delay_min': 0.8, 'delay_max': 2.2, 'page_delay_min': 2.0, 'page_delay_max': 3.5,
                            'inter_url_delay_min': 3.0, 'inter_url_delay_max': 7.0},
            'features': {'enable_advanced_features': True, 'enable_data_validation': True, 'enable_batch_write': True, 'from_property_features_list': True, 'preserve_description_format': True, 'translate_to_chinese': False}
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f_default_config:
                yaml.dump(default_config_content, f_default_config, default_flow_style=False)
            logger.info(f"Default configuration file created at {config_path}. Please review it.")
        except Exception as e_cfg:
            logger.error(f"Configuration file not found: {config_path} and failed to create a default: {e_cfg}")
            raise FileNotFoundError(f"配置文件不存在: {config_path} and failed to create a default: {e_cfg}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_furniture_keywords() -> Optional[dict]:
    """加载家具关键词配置文件"""
    keywords_path = CONFIG_DIR / 'furniture_keywords.yaml'
    if not keywords_path.exists():
        logger.warning(f"Furniture keywords file not found: {keywords_path}. Using fallback keywords.")
        return None
    
    try:
        with open(keywords_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load furniture keywords: {e}. Using fallback keywords.")
        return None

def load_aircon_keywords() -> Optional[dict]:
    """加载空调关键词配置文件"""
    keywords_path = CONFIG_DIR / 'aircon_keywords.yaml'
    if not keywords_path.exists():
        logger.warning(f"Aircon keywords file not found: {keywords_path}. Using fallback keywords.")
        return None
    
    try:
        with open(keywords_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load aircon keywords: {e}. Using fallback keywords.")
        return None

CONFIG = load_config()
FURNITURE_KEYWORDS = load_furniture_keywords()
AIRCON_KEYWORDS = load_aircon_keywords()

# =============================================================================
# 辅助函数 - 从URL提取区域名称
# =============================================================================
def extract_region_from_url(url: str) -> str:
    """
    从Domain搜索URL中提取区域名称
    支持多种URL格式：
    - 单个区域: /rent/sydney-nsw-2000/
    - 多个区域: /rent/sydney-nsw-2000+parramatta-nsw-2150/
    - 带其他参数的URL
    """
    try:
        # 使用正则表达式提取区域部分
        # 匹配 /rent/ 后面到 ? 或 / 之前的部分
        pattern = r'/rent/([^/?]+)'
        match = re.search(pattern, url)
        
        if match:
            region_part = match.group(1)
            
            # 处理多个区域的情况（用+连接）
            if '+' in region_part:
                # 取第一个区域作为主要区域
                regions = region_part.split('+')
                main_region = regions[0]
                # 提取区域名称（去掉州和邮编）
                region_name = main_region.split('-')[0].replace('-', ' ').title()
                return f"{region_name}_Multi" # 标记为多区域
            else:
                # 单个区域，提取区域名称
                region_name = region_part.split('-')[0].replace('-', ' ').title()
                return region_name
        else:
            # 如果无法匹配，返回默认值
            return "Unknown_Region"
            
    except Exception as e:
        logger.warning(f"Failed to extract region from URL {url}: {e}")
        return "Unknown_Region"

# =============================================================================
# 数据模型 (Unchanged from v1)
# =============================================================================
@dataclass
class PropertyFeatures:
    furnishing_status: str = 'unfurnished'  # Replaces is_furnished. Can be 'furnished', 'unfurnished', or 'optional'.
    air_conditioning_type: str = 'none' # Replaces has_air_conditioning. Can be 'none', 'ducted', 'split_system', etc.
    has_air_conditioning: bool = False
    has_balcony: bool = False; has_dishwasher: bool = False
    has_laundry: bool = False; has_built_in_wardrobe: bool = False
    has_gym: bool = False; has_pool: bool = False
    has_parking: bool = False; allows_pets: bool = False
    has_security_system: bool = False; has_storage: bool = False
    has_study_room: bool = False; has_garden: bool = False
    def to_dict(self) -> Dict[str, Union[bool, str]]: return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    def merge(self, other: 'PropertyFeatures') -> None:
        # Custom merge logic for the new furnishing_status
        if self.furnishing_status == 'unfurnished':
            self.furnishing_status = other.furnishing_status
        
        # Custom merge logic for the new air_conditioning_type
        if self.air_conditioning_type == 'none':
            self.air_conditioning_type = other.air_conditioning_type

        for fld in self.__dataclass_fields__:
            if fld not in ['furnishing_status', 'air_conditioning_type']:
                if not getattr(self, fld):
                    setattr(self, fld, getattr(other, fld))

@dataclass
class PropertyData:
    listing_id: str = ""; property_url: str = ""; address: str = ""
    suburb: str = ""; state: str = ""; postcode: str = ""
    property_type: str = ""; rent_pw: float = 0.0; bond: float = 0.0
    bedrooms: int = 0; bathrooms: int = 0; parking_spaces: int = 0
    bedroom_display: str = ""  # 专门用于前端显示的卧室数（如 "Studio", "1", "2"）
    available_date: str = ""
    inspection_times: List[str] = field(default_factory=list)
    agency_name: str = ""; agent_name: str = ""; cover_image: str = ""; agent_phone: str = ""; agent_email: str = ""
    property_headline: str = ""; property_description: str = ""
    features: PropertyFeatures = field(default_factory=PropertyFeatures)
    latitude: float = 0.0; longitude: float = 0.0
    images: str = ""; property_features: str = "" # Storing as JSON strings
    agent_profile_url: str = ""; agent_logo_url: str = ""
    enquiry_form_action: str = ""
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for field_name, field_value in self.__dict__.items():
            if field_name == 'features': result.update(field_value.to_dict())
            elif field_name == 'inspection_times': result['inspection_times'] = '; '.join(field_value)
            else: result[field_name] = field_value
        return result

EXPECTED_COLUMNS = [
    'listing_id', 'property_url', 'address', 'suburb', 'state', 'postcode',
    'property_type', 'rent_pw', 'bond', 'bedrooms', 'bathrooms', 'parking_spaces',
    'bedroom_display', 'available_date', 'inspection_times', 'agency_name', 'agent_name', 'cover_image', 'agent_phone',
    'agent_email', 'property_headline', 'property_description',
    'furnishing_status', 'has_air_conditioning', 'air_conditioning_type', 'has_balcony', 'has_dishwasher',
    'has_laundry', 'has_built_in_wardrobe', 'has_gym', 'has_pool', 'has_parking',
    'allows_pets', 'has_security_system', 'has_storage', 'has_study_room', 'has_garden',
    'latitude', 'longitude', 'images', 'property_features', 'agent_profile_url',
    'agent_logo_url', 'enquiry_form_action', 'image_1', 'image_2', 'image_3', 'image_4'
]

# =============================================================================
# 特征提取, 数据清洗 & 验证 (MODIFIED for furniture and AC detection)
# =============================================================================
class FeatureExtractor:
    def __init__(self):
        self.patterns = {
            "balcony": [r"balcony", r"terrace", "deck", r"阳台"],
            "dishwasher": [r"dishwasher", r"洗碗机"],
            "laundry": [r"laundry", r"washer", r"dryer", r"洗衣", r"烘干机"],
            "built_in_wardrobe": [r"built.{0,3}in", r"wardrobe", r"wardrobes", r"衣柜"],
            "gym": [r"gym", r"fitness", r"健身"],
            "pool": [r"pool", r"swimming", r"游泳池"],
            "parking": [r"parking", r"garage", r"car space", r"停车"],
            "pets": [r"pets?\s+allow", r"pet.?friendly", r"允许宠物", r"宠物友好"],
            "security": [r"security", r"intercom", r"安保", r"门禁"],
            "storage": [r"storage", r"储物"],
            "study": [r"study", r"home office", r"书房", r"学习区"],
            "garden": [r"garden", r"yard", r"花园", r"院子"]
        }
        self.compiled_patterns = {ft: [re.compile(p, re.IGNORECASE) for p in ps] for ft, ps in self.patterns.items()}

        # Load and process all furniture keywords once during initialization
        self._positive_keywords = set()
        self._negative_keywords = set()
        self._optional_keywords = set()
        if FURNITURE_KEYWORDS:
            for key, keyword_set in [('positive_keywords', self._positive_keywords), 
                                     ('negative_keywords', self._negative_keywords), 
                                     ('optional_keywords', self._optional_keywords)]:
                config = FURNITURE_KEYWORDS.get(key, {})
                if config:
                    for category_keywords in config.values():
                        keyword_set.update(kw.lower() for kw in category_keywords)
            
            logger.info(f"Loaded {len(self._positive_keywords)} positive, {len(self._negative_keywords)} negative, and {len(self._optional_keywords)} optional furniture keywords.")
        else:
            logger.warning("Furniture keywords configuration not found or empty. Furnished detection will be degraded.")

        # Load and process all aircon keywords
        self._aircon_keywords: Dict[str, Set[str]] = {}
        self._aircon_keyword_order: List[str] = []
        if AIRCON_KEYWORDS:
            self._aircon_keyword_order = [
                'negative_keywords', 'ducted_keywords', 'reverse_cycle_keywords', 
                'split_system_keywords', 'general_keywords', 'other_keywords'
            ]
            for key in self._aircon_keyword_order:
                config = AIRCON_KEYWORDS.get(key, {})
                if config:
                    self._aircon_keywords[key] = set()
                    for category_keywords in config.values():
                        self._aircon_keywords[key].update(kw.lower() for kw in category_keywords)
            logger.info(f"Loaded {sum(len(s) for s in self._aircon_keywords.values())} air conditioning keywords across {len(self._aircon_keywords)} categories.")
        else:
            logger.warning("Aircon keywords configuration not found or empty. AC detection will be degraded.")

    def _get_furnishing_status(self, text: str) -> str:
        """
        Robustly determines furnishing status using pre-loaded keyword sets.
        Logic: Negative > Optional > Positive.
        """
        if not text: return 'unfurnished'
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in self._negative_keywords): return 'unfurnished'
        if any(keyword in text_lower for keyword in self._optional_keywords): return 'optional'
        if any(keyword in text_lower for keyword in self._positive_keywords): return 'furnished'
        return 'unfurnished'

    def _get_air_conditioning_type(self, text: str) -> str:
        """
        Determines air conditioning type based on a prioritized keyword search.
        """
        if not text or not self._aircon_keywords: return 'none'
        text_lower = text.lower()

        for key in self._aircon_keyword_order:
            if key in self._aircon_keywords:
                # Using an explicit loop for robustness to avoid potential issues with generator expressions
                for keyword in self._aircon_keywords[key]:
                    if keyword in text_lower:
                        if key == 'negative_keywords':
                            return 'none'
                        # Return on first match based on priority
                        return key.replace('_keywords', '')
        
        return 'none'

    def extract(self, json_data: dict, description: str, feature_list: List[str]) -> PropertyFeatures:
        features = PropertyFeatures()

        # Combine all text sources into one blob for efficient checking
        text_blob = description.lower()
        text_blob += " " + " ".join(f.lower() for f in feature_list)
        
        s_features_set = {f.get("name", "").lower() for f in json_data.get("structuredFeatures", [])}
        text_blob += " " + " ".join(s_features_set)

        # Centralized feature extraction for regex-based patterns
        for f_name, patterns in self.compiled_patterns.items():
            a_f_name = "allows_pets" if f_name == "pets" else f"has_{f_name}"
            if hasattr(features, a_f_name):
                if any(p.search(text_blob) for p in patterns):
                    setattr(features, a_f_name, True)
        
        # Use the new, tri-state furnishing status check
        features.furnishing_status = self._get_furnishing_status(text_blob)
        
        # Use the new, detailed air conditioning type check
        features.air_conditioning_type = self._get_air_conditioning_type(text_blob)
        if features.air_conditioning_type != 'none':
            features.has_air_conditioning = True

        # More specific keyword checks can be added here for higher accuracy if needed
        if any(keyword in text_blob for keyword in ["built in wardrobe", "builtin wardrobe", "robe", "walk in robe"]):
            features.has_built_in_wardrobe = True
        if any(keyword in text_blob for keyword in ["secure parking", "underground parking", "carport"]):
            features.has_parking = True
        
        return features

class DataCleaner:
    @staticmethod
    def clean_price(price: str) -> float:
        if not price: return 0.0
        try: return float(re.sub(r'[^\d.]', '', price))
        except (ValueError, TypeError): return 0.0
    @staticmethod
    def clean_date(date_str: str) -> str:
        if not date_str: return datetime.now().strftime('%Y-%m-%d')
        try:
            if 'T' in date_str: return date_str.split('T')[0]
            if date_str.upper() == 'NOW': return datetime.now().strftime('%Y-%m-%d')
            patterns = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']
            for p in patterns:
                try: return datetime.strptime(date_str, p).strftime('%Y-%m-%d')
                except ValueError: continue
            return date_str
        except Exception: return datetime.now().strftime('%Y-%m-%d')
    
    @staticmethod
    def clean_available_date(date_str: str) -> str:
        """
        专门处理入住日期的智能清理
        将过期日期转换为 'Available Now'，保留未来日期
        """
        if not date_str: 
            return "Available Now"
        
        try:
            # 处理包含时间的ISO格式
            if 'T' in date_str: 
                date_str = date_str.split('T')[0]
            
            # 处理明确的 "现在" 关键词
            if any(keyword in date_str.upper() for keyword in ['NOW', 'AVAILABLE', 'IMMEDIATE']):
                return "Available Now"
            
            # 尝试解析各种日期格式
            parsed_date = None
            patterns = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S']
            
            for pattern in patterns:
                try:
                    parsed_date = datetime.strptime(date_str, pattern)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                today = datetime.now().date()
                available_date = parsed_date.date()
                
                # 如果是今天或之前的日期，返回 "Available Now"
                if available_date <= today:
                    logger.debug(f"过期入住日期 {date_str} 转换为 'Available Now'")
                    return "Available Now"
                else:
                    # 未来的日期，保留原格式
                    return available_date.strftime('%Y-%m-%d')
            else:
                # 无法解析的日期，检查是否包含有意义的文本
                date_lower = date_str.lower().strip()
                if any(word in date_lower for word in ['now', 'immediate', 'available', 'asap']):
                    return "Available Now"
                else:
                    # 默认为现在可入住
                    logger.debug(f"无法解析日期格式 '{date_str}'，默认为 'Available Now'")
                    return "Available Now"
                    
        except Exception as e:
            logger.debug(f"处理入住日期 '{date_str}' 时出错: {e}，默认为 'Available Now'")
            return "Available Now"
    @staticmethod
    def clean_text(text: str) -> str:
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text); text = ' '.join(text.split())
        return text.strip()
    
    @staticmethod
    def clean_description(text: str, preserve_format: bool = True) -> str:
        """
        专门用于清理房源描述的方法
        可以选择保留格式或进行传统的文本清理
        """
        if not text: return ""
        
        if preserve_format:
            # 保留格式的清理：转换HTML到类似markdown格式
            # 保留段落分隔
            text = re.sub(r'<br\s*/?>', '\n', text)  # <br> -> 换行
            text = re.sub(r'</p>\s*<p[^>]*>', '\n\n', text)  # 段落间加双换行
            text = re.sub(r'<p[^>]*>', '', text)  # 移除开始的 <p> 标签
            text = re.sub(r'</p>', '\n', text)  # 结束的 </p> 变成换行
            
            # 转换列表
            text = re.sub(r'<li[^>]*>', '• ', text)  # <li> -> 项目符号
            text = re.sub(r'</li>', '\n', text)  # </li> -> 换行
            text = re.sub(r'</?[uo]l[^>]*>', '\n', text)  # 移除 <ul> <ol> 标签并换行
            
            # 移除其他HTML标签但保留内容
            text = re.sub(r'<[^>]+>', '', text)
            
            # 清理多余的空白但保留换行
            text = re.sub(r'[ \t]+', ' ', text)  # 多个空格/制表符合并为一个空格
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 多个连续换行合并为双换行
            text = re.sub(r'^\s+|\s+$', '', text)  # 移除开头和结尾的空白
            
            return text.strip()
        else:
            # 传统的清理方式（兼容性）
            return DataCleaner.clean_text(text)

class DataValidator:
    @staticmethod
    def validate_property(data: PropertyData) -> Tuple[bool, List[str]]:
        errors = []
        if not data.listing_id: errors.append("缺少listing_id")
        if not data.property_url: errors.append("缺少property_url")
        if data.rent_pw < 0: errors.append("rent_pw不能为负数")
        if data.bedrooms < 0: errors.append("bedrooms不能为负数")
        if data.bathrooms < 0: errors.append("bathrooms不能为负数")
        if data.latitude and not (-90 <= data.latitude <= 90): errors.append("latitude超出有效范围")
        if data.longitude and not (-180 <= data.longitude <= 180): errors.append("longitude超出有效范围")
        return not errors, errors

# =============================================================================
# 请求管理 (Unchanged from v1)
# =============================================================================
def safe_request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = CONFIG['network']['max_retries']
        backoff_factor = CONFIG['network']['backoff_factor']
        last_exception = None
        for i_retry in range(retries):
            try: return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                last_exception = e
                if i_retry < retries - 1:
                    wait_time = (2 ** i_retry) * backoff_factor
                    logger.warning(f"请求失败 ({i_retry+1}/{retries})，{wait_time:.1f}s后重试: {e}"); time.sleep(wait_time)
        logger.error(f"请求失败，已达到最大重试次数: {last_exception if last_exception else 'Unknown Error'}");
        if last_exception: raise last_exception
        raise RuntimeError("Request failed after max retries, no exception stored.")
    return wrapper

class RequestManager:
    def __init__(self):
        self.session = self._create_session(); self.last_request_time = 0; self._lock = threading.Lock()
    def _create_session(self) -> requests.Session:
        s = requests.Session()
        rs = Retry(total=CONFIG['network']['max_retries'], backoff_factor=CONFIG['network']['backoff_factor'], status_forcelist=CONFIG['network']['retry_statuses'])
        a = HTTPAdapter(max_retries=rs); s.mount("http://", a); s.mount("https://", a)
        s.headers.update(CONFIG['headers']); return s
    def _wait_for_rate_limit(self):
        with self._lock:
            current_time = time.time(); elapsed = current_time - self.last_request_time
            base_delay = 1.0 / CONFIG['performance']['requests_per_second']
            random_delay_factor = CONFIG['performance'].get('random_delay_factor', 0.5)
            random_delay = random.uniform(0, base_delay * random_delay_factor)
            wait_time = base_delay + random_delay - elapsed
            if wait_time > 0: time.sleep(wait_time)
            self.last_request_time = time.time()
    @safe_request
    def get(self, url: str, **kwargs) -> requests.Response:
        try:
            self._wait_for_rate_limit()
            resp = self.session.get(url, timeout=CONFIG['network']['timeout'], **kwargs)
            resp.raise_for_status()
            if not resp.content: raise requests.exceptions.RequestException("空响应内容")
            ct = resp.headers.get('content-type', '')
            if not ('text/html' in ct or 'application/json' in ct):
                raise requests.exceptions.RequestException(f"意外的响应类型: {ct}")
            return resp
        except requests.Timeout as e_timeout: logger.error(f"请求超时: {url}"); raise e_timeout
        except requests.HTTPError as e_http: logger.error(f"HTTP错误: {url}, 状态码: {e_http.response.status_code}"); raise e_http
        except requests.exceptions.RequestException as e_req: logger.error(f"请求异常: {url}, 错误: {e_req}"); raise e_req
        except Exception as e_generic: logger.error(f"未预期的错误 during GET: {url}, 错误: {e_generic}"); raise e_generic

# =============================================================================
# 批量写入管理 (MODIFIED for timestamped filename and returning filename)
# =============================================================================
class BatchWriter:
    def __init__(self):
        self.buffer: List[PropertyData] = []; self._lock = threading.Lock()
    def add(self, item: PropertyData) -> None:
        with self._lock: self.buffer.append(item)
    def flush(self, region: str = "Unknown", total_count: int = 0) -> Optional[str]: # MODIFIED: Added region and total_count parameters
        if not self.buffer:
            logger.info("缓冲区中无数据可刷新至XLSX。")
            return None # MODIFIED
        with self._lock:
            try:
                data_dicts = [item.to_dict() for item in self.buffer]
                temp_df = pd.DataFrame(data_dicts)
                df_final = pd.DataFrame(columns=EXPECTED_COLUMNS)
                for col in EXPECTED_COLUMNS:
                    if col in temp_df.columns:
                        df_final[col] = temp_df[col]
                    else:
                        df_final[col] = "" 
                
                # MODIFIED: Customized filename with timestamp, region, and total count
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # 清理区域名称，移除特殊字符
                clean_region = re.sub(r'[^\w\s-]', '', region).replace(' ', '_')
                output_filename = f"{timestamp}_{clean_region}_{total_count}properties.xlsx"
                output_file_path = OUTPUT_DIR / output_filename
                
                # MODIFIED: Changed from CSV to XLSX output
                df_final.to_excel(output_file_path, index=False, engine='openpyxl')
                logger.info(f"已成功保存 {len(df_final)} 条记录到: {output_file_path} (区域: {region}, 总房源数: {total_count})")
                self.buffer = []
                return str(output_file_path) # MODIFIED: Return the full path as string
            except Exception as e:
                logger.error(f"写入XLSX文件 ({output_filename if 'output_filename' in locals() else 'unknown'}) 失败: {e}", exc_info=True)
                return None # MODIFIED

# =============================================================================
# 爬虫核心 (Largely unchanged, detail extraction logic is complex and specific)
# =============================================================================
class DomainCrawler:
    def __init__(self):
        self.request_manager = RequestManager(); self.feature_extractor = FeatureExtractor()
        self.data_cleaner = DataCleaner(); self.data_validator = DataValidator()
        self.batch_writer = BatchWriter(); self._lock = threading.Lock() # _lock not used in this class in v1
    
    def _extract_inspection_times(self, document: etree._Element) -> List[str]:
        times = []
        for b in document.xpath('//div[@data-testid="listing-details__inspections-block"]'):
            try:
                d_el = b.xpath('.//span[@data-testid="listing-details__inspections-block-day"]/text()')
                t_el = b.xpath('.//span[@data-testid="listing-details__inspections-block-time"]/text()')
                if d_el and t_el: times.append(f"{d_el[0].strip()}, {t_el[0].strip()}")
            except Exception as e: logger.debug(f"_extract_inspection_times method 1 error: {e}")
        if not times:
            try:
                js_txt = "".join(document.xpath(".//script[@id='__NEXT_DATA__']/text()"))
                if js_txt:
                    js_data = json.loads(js_txt)
                    props = js_data.get("props", {}).get("pageProps", {}).get("componentProps", {})
                    for i_item in props.get("inspectionDetails", {}).get("inspections", []):
                        st, et = i_item.get("startTime", ""), i_item.get("endTime", "")
                        if st and et: times.append(f"{st} - {et}")
            except Exception as e: logger.debug(f"_extract_inspection_times method 2 error: {e}")
        return times
    
    def _generate_bedroom_display(self, bedrooms: int, property_type: str, 
                                  property_features: List[str], headline: str, 
                                  description: str) -> str:
        """
        智能生成 bedroom_display 字段
        根据多个数据源判断是否为 Studio 或显示实际卧室数
        """
        # 如果卧室数大于0，直接返回数字字符串
        if bedrooms > 0:
            return str(bedrooms)
        
        # 卧室数为0时，需要判断是否为Studio
        # 检查多个数据源中是否包含Studio关键词
        text_sources = [
            property_type.lower() if property_type else "",
            headline.lower() if headline else "",
            description.lower() if description else "",
            " ".join(property_features).lower() if property_features else ""
        ]
        
        # Studio相关关键词
        studio_keywords = [
            "studio", "studios", "studio apartment", 
            "studio unit", "open plan", "efficiency apartment"
        ]
        
        # 检查是否包含Studio关键词
        for text in text_sources:
            if text and any(keyword in text for keyword in studio_keywords):
                logger.debug(f"检测到Studio关键词在: {text[:50]}...")
                return "Studio"
        
        # 如果都没有明确指示是Studio，但卧室数为0
        # 大概率是数据问题或确实是Studio，倾向于返回"Studio"
        logger.debug(f"卧室数为0但未找到Studio关键词，默认返回Studio")
        return "Studio"
    
    def crawl_detail(self, house_href: str) -> Optional[PropertyData]:
        try:
            logger.info(f"正在抓取详情页: {house_href}")
            response = self.request_manager.get(house_href)
            house_document = etree.HTML(response.text)
            
            try:
                json_script = "".join(house_document.xpath(".//script[@id='__NEXT_DATA__']/text()"))
                if not json_script: logger.error(f"__NEXT_DATA__ script tag not found: {house_href}"); return None
                base_json = json.loads(json_script)
            except Exception as e: logger.error(f"解析详情页JSON失败 for {house_href}: {e}", exc_info=True); return None
            
            comp_props = base_json.get("props", {}).get("pageProps", {}).get("componentProps", {})
            root_q = comp_props.get("rootGraphQuery", {}).get("listingByIdV2", {}) or {}
            list_sum = comp_props.get("listingSummary", {}) or {}
            agents_list = root_q.get("agents", []); agent_p = agents_list[0] if agents_list else {}
            addr_info = root_q.get("displayableAddress", {}) or {}; geo_info = addr_info.get("geolocation", {}) or {}
            
            prop_feat_els = house_document.xpath("//div[@id='property-features']//li")
            prop_feat_list = [li.xpath("string(.)").strip() for li in prop_feat_els if li.xpath("string(.)")]
            
            features_obj = self.feature_extractor.extract(root_q, root_q.get("description", ""), prop_feat_list)
            
            img_urls_raw = [img.get("url", "") for img in root_q.get("largeMedia", []) if img.get("url")]
            images_json = json.dumps(img_urls_raw)
            
            # 提取封面图片（第一张图片）
            cover_image_val = img_urls_raw[0] if img_urls_raw else ""

            property_features_json = json.dumps(prop_feat_list)

            enquiry_form_action = ""
            apply_link_el = house_document.xpath('//div[@data-testid="listing-details__agent-details-cta-box"]//a[contains(@href, "snug.com") or contains(@href, "2apply.com.au")]/@href')
            if apply_link_el:
                enquiry_form_action = apply_link_el[0].strip()
            
            if not enquiry_form_action:
                oneform_action_el = house_document.xpath('//div[@data-testid="listing-details__agent-details-cta-box"]//form[@data-testid="listing-details__oneform-button-form"]/@action')
                if not oneform_action_el:
                    oneform_action_el = house_document.xpath('//div[@data-testid="listing-details__agent-details-cta-box"]//form[contains(@class, "css-")]/@action')
                if oneform_action_el:
                    enquiry_form_action = oneform_action_el[0].strip()
            
            if not enquiry_form_action:
                original_enquiry_el = house_document.xpath("//form[@id='enquiry-form']/@action")
                if original_enquiry_el:
                    enquiry_form_action = original_enquiry_el[0].strip()

            if not enquiry_form_action:
                 logger.debug(f"Enquiry/Apply link/action for {house_href} NOT found via any XPaths.") # Changed to debug
            else:
                logger.debug(f"Enquiry/Apply link/action FOUND for {house_href}: {enquiry_form_action}") # Changed to debug


            property_type_val = root_q.get("propertyType", "")
            if not property_type_val:
                property_type_elements = house_document.xpath('//span[@class="css-1efi8gv"]/text()')
                if property_type_elements:
                    property_type_val = property_type_elements[0].strip()

            agent_phone_val = agent_p.get("phoneNumber", "")
            if not agent_phone_val or agent_phone_val.strip().lower() == "call" or not agent_phone_val.strip():
                agent_phone_href_el = house_document.xpath('//a[@data-testid="listing-details__phone-cta-button"]/@href')
                if agent_phone_href_el and agent_phone_href_el[0].startswith("tel:"):
                    agent_phone_val = agent_phone_href_el[0].replace("tel:", "").strip()
                else:
                    agent_phone_el_text = house_document.xpath('//a[@data-testid="listing-details__phone-cta-button"]/span[@class="css-1s26z8e"]/span/text()')
                    if agent_phone_el_text:
                         agent_phone_val = agent_phone_el_text[0].strip()


            agent_logo_url_val = (agent_p.get("agency", {}) or {}).get("logoUrl", "") 
            if not agent_logo_url_val:
                agent_logo_el = house_document.xpath('//a[@class="css-wrjy08"]/img[@data-testid="listing-details__agent-details-branding-lazy"]/@src')
                if agent_logo_el:
                    agent_logo_url_val = agent_logo_el[0].strip()

            # 智能生成 bedroom_display 字段
            bedrooms_raw = list_sum.get("beds", 0)
            bedroom_display_val = self._generate_bedroom_display(
                bedrooms_raw, 
                property_type_val, 
                prop_feat_list, 
                root_q.get("headline", ""), 
                root_q.get("description", "")
            )

            data_item = PropertyData(
                listing_id=root_q.get("listingId", ""), property_url=house_href,
                address=self.data_cleaner.clean_text(list_sum.get("address", "")),
                suburb=addr_info.get("suburbName", ""), state=addr_info.get("state", ""),
                postcode=addr_info.get("postcode", ""),
                property_type=property_type_val,
                rent_pw=self.data_cleaner.clean_price(list_sum.get("title", "")),
                bond=self.data_cleaner.clean_price(str((root_q.get("priceDetails", {}) or {}).get("bond", 0))),
                bedrooms=bedrooms_raw, bathrooms=list_sum.get("baths", 0),
                parking_spaces=list_sum.get("parking", 0),
                bedroom_display=bedroom_display_val,
                available_date=self.data_cleaner.clean_available_date((root_q.get("dateAvailableV2", {}) or {}).get("isoDate", "")),
                inspection_times=self._extract_inspection_times(house_document),
                agency_name=(root_q.get("agency", {}) or {}).get("name", ""),
                agent_name=agent_p.get("fullName", ""), 
                cover_image=cover_image_val,
                agent_phone=agent_phone_val, 
                agent_email=agent_p.get("email", ""),
                agent_profile_url=agent_p.get("profileUrl", ""),
                agent_logo_url=agent_logo_url_val, 
                property_headline=root_q.get("headline", ""),
                property_description=self.data_cleaner.clean_description(
                    root_q.get("description", ""), 
                    preserve_format=CONFIG['features'].get('preserve_description_format', True)
                ),
                features=features_obj,
                latitude=float(geo_info.get("latitude", 0.0) or 0.0),
                longitude=float(geo_info.get("longitude", 0.0) or 0.0),
                images=images_json, property_features=property_features_json,
                enquiry_form_action=enquiry_form_action,
            )
            
            if CONFIG['features'].get('enable_data_validation', False):
                is_valid, errors = self.data_validator.validate_property(data_item)
                if not is_valid: logger.warning(f"数据验证失败 for {house_href}: {errors}")
            
            logger.info(f"成功提取房源信息: ID={data_item.listing_id or 'N/A'} for URL: {house_href}") # MODIFIED to INFO and added URL
            if CONFIG['features']['enable_batch_write']: self.batch_writer.add(data_item)
            return data_item
        except Exception as e:
            logger.error(f"抓取详情页失败: {house_href}", exc_info=True); return None
    
    def process_search_page(self, url: str) -> List[str]:
        try:
            resp = self.request_manager.get(url); doc = etree.HTML(resp.text)
            links = []
            common_link_pattern = doc.xpath(".//ul[@data-testid='results']/li//a[contains(@href, 'www.domain.com.au') and string-length(@href) > 40]/@href")

            if common_link_pattern:
                links = [link for link in common_link_pattern if link.startswith("https://www.domain.com.au/")]
            
            if not links:
                listing_items_xpath = ".//ul[@data-testid='results']/li"
                link_xpath_inside_item = ".//a[contains(@class, 'address') or @data-testid='listing-card-link' or contains(@href,'/1')]/@href"
                for item_element in doc.xpath(listing_items_xpath):
                    href_list = item_element.xpath(link_xpath_inside_item)
                    if not href_list: href_list = item_element.xpath(".//div[@class='css-qrqvvg']/a/@href")
                    if not href_list: href_list = item_element.xpath("(.//a[contains(@href,'www.domain.com.au')])[1]/@href")

                    if href_list:
                        link_candidate = href_list[0]
                        if link_candidate.startswith("/"): link_candidate = "https://www.domain.com.au" + link_candidate
                        if link_candidate.startswith("https://www.domain.com.au/"): links.append(link_candidate)
            
            if not links: logger.warning(f"在页面 {url} 上未找到房源链接，请检查XPath选择器。")
            return list(set(links)) # Ensure unique links
        except Exception as e: logger.error(f"处理搜索页面失败: {url}", exc_info=True); return []
    
    def save_progress(self, url: str, page: int, progress_file_name: str) -> None: # MODIFIED to accept progress_file_name
        try:
            prog = {"url": url, "page": page, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            with open(PROJECT_ROOT / progress_file_name, 'w', encoding='utf-8') as f: json.dump(prog, f, indent=2)
            logger.debug(f"保存进度到 {progress_file_name}: URL={url}, 页码={page}")
        except Exception as e: logger.error(f"保存进度到 {progress_file_name} 失败: {e}")
    
    def load_progress(self, progress_file_name: str) -> Optional[dict]: # MODIFIED to accept progress_file_name
        try:
            p_file = PROJECT_ROOT / progress_file_name
            if p_file.exists():
                with open(p_file, 'r', encoding='utf-8') as f: prog = json.load(f)
                logger.info(f"从 {progress_file_name} 加载到上次进度: {prog.get('url','N/A')}, 页码 {prog.get('page','N/A')}"); return prog
        except Exception as e: logger.error(f"从 {progress_file_name} 加载进度失败: {e}"); return None
    
    def search(self, input_url: str, using_temp_urls: bool) -> int: # MODIFIED to return total link count
        page = 1
        total_links_processed = 0  # ADDED: Track total links processed
        progress_file_name = "progress_temp.json" if using_temp_urls else "progress.json"

        # Progress loading logic (optional, can be simplified if temp URLs don't need progress)
        # For simplicity, if using_temp_urls, we might always start fresh or use a separate progress file.
        # The run method already deletes 'progress.json'. If temp_urls are used, we might not want to load/save progress.
        # Current implementation will use 'progress_temp.json' for temp URLs.
        
        # prog = self.load_progress(progress_file_name) 
        # if prog and prog.get('url') == input_url and isinstance(prog.get('page'), int):
        #     page = prog['page']; logger.info(f"从上次进度 ({progress_file_name}) 继续: 第{page}页 for {input_url}")
        
        res_thresh = CONFIG.get('performance', {}).get('results_per_page_threshold', 10)
        delay_min = CONFIG['performance'].get('delay_min', 0.8)
        delay_max = CONFIG['performance'].get('delay_max', 2.2)
        page_delay_min = CONFIG['performance'].get('page_delay_min',2.0)
        page_delay_max = CONFIG['performance'].get('page_delay_max',3.5)

        while True:
            s_url = f"{input_url}&page={page}" if 'page=' not in input_url else input_url.replace(re.findall(r"page=\d+", input_url)[0] if re.findall(r"page=\d+", input_url) else "", f"page={page}")
            if '&page=' not in s_url and 'page=' not in s_url : # if input_url is a base search url without page param
                 s_url = f"{input_url}&page={page}"


            logger.info(f"正在抓取第{page}页: {s_url}")
            links = self.process_search_page(s_url)
            if not links: 
                logger.info(f"第 {page} 页无房源链接或已达末页, 结束对 {input_url} 搜索.")
                break
            
            logger.info(f"第{page}页找到{len(links)}个房源"); succ_count = 0
            total_links_processed += len(links)  # ADDED: Accumulate total links
            for i_idx, detail_url in enumerate(links):
                try:
                    logger.info(f"处理第{i_idx+1}/{len(links)}个房源: {detail_url}")
                    if self.crawl_detail(detail_url): succ_count += 1
                    time.sleep(random.uniform(delay_min, delay_max))
                except Exception as e: logger.error(f"处理房源 {detail_url} 失败: {e}", exc_info=True); time.sleep(5.0)
            
            logger.info(f"本页成功处理{succ_count}/{len(links)}个房源")
            
            # Only save progress if not using temp URLs, or if specifically designed for it.
            # For now, let's only save progress for non-temp URLs to keep it simple.
            if not using_temp_urls:
                self.save_progress(input_url, page + 1, progress_file_name)

            if page % 5 == 0: gc.collect(); logger.info("执行内存回收")
            
            if len(links) < res_thresh : 
                logger.info(f"当前页房源数 ({len(links)}) < 阈值 ({res_thresh})，判断为最后一页.")
                break
            
            logger.info(f"完成第{page}页处理"); page += 1
            time.sleep(random.uniform(page_delay_min, page_delay_max))
        
        logger.info(f"搜索完成，总共处理了 {total_links_processed} 个房源链接")
        return total_links_processed  # ADDED: Return total link count
    
    def run(self) -> List[str]: # MODIFIED: Returns list of output filenames
        output_files = []  # MODIFIED: Store multiple output files
        try:
            logger.info("开始运行房源信息采集程序 (v2)...")
            
            temp_url_file = CONFIG_DIR / 'temp_urls.txt'
            default_url_file = CONFIG_DIR / 'url.txt'
            using_temp_urls = False

            if temp_url_file.exists() and temp_url_file.stat().st_size > 0:
                url_cfg_path = temp_url_file
                using_temp_urls = True
                logger.info(f"检测到临时URL文件: {url_cfg_path}，将使用此文件中的URL。")
                # For temp URLs, we generally don't want to persist progress from previous temp runs.
                # So, we can delete or ignore 'progress_temp.json'.
                temp_progress_file = PROJECT_ROOT / "progress_temp.json"
                if temp_progress_file.exists():
                    try: temp_progress_file.unlink()
                    except OSError as e: logger.warning(f"无法删除临时进度文件 {temp_progress_file}: {e}")

            elif default_url_file.exists():
                url_cfg_path = default_url_file
                logger.info(f"未找到或临时URL文件为空，将使用默认URL文件: {url_cfg_path}")
                # Standard progress file handling for default URLs
                progress_file = PROJECT_ROOT / 'progress.json'
                if progress_file.exists():
                    try:
                        progress_file.unlink(); logger.info(f"已删除旧的进度文件: {progress_file} (针对默认URL)。")
                    except OSError as e: logger.error(f"删除进度文件 {progress_file} 失败: {e}。")
            else:
                logger.error(f"默认配置文件不存在: {default_url_file}")
                logger.info("创建示例配置文件 (url.txt)...")
                with open(default_url_file, "w", encoding="utf-8") as f:
                    f.write("# URL list, one per line\nhttps://www.domain.com.au/rent/?suburb=sydney-nsw-2000\n")
                logger.info(f"示例配置文件已创建: {default_url_file}. 请填充后运行."); return []

            with open(url_cfg_path, "r", encoding="utf-8") as f:
                urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
            
            if not urls: logger.error(f"配置文件 {url_cfg_path} 中无有效URL."); return []
            
            logger.info(f"找到{len(urls)}个URL待处理 (来源: {'temp_urls.txt' if using_temp_urls else 'url.txt'}): {urls}")
            inter_url_delay_min = CONFIG['performance'].get('inter_url_delay_min', 3.0)
            inter_url_delay_max = CONFIG['performance'].get('inter_url_delay_max', 7.0)

            for i_url, url in enumerate(urls, 1):
                try:
                    logger.info(f"开始处理 ({i_url}/{len(urls)}): {url}")
                    total_count = 0  # ADDED: Track total count for this URL
                    
                    if using_temp_urls:
                        # URLs from temp_urls.txt are assumed to be direct detail links
                        logger.info(f"Processing as direct detail URL (from temp_urls.txt): {url}")
                        if self.crawl_detail(url):
                            total_count = 1  # Single property processed
                    else:
                        # URLs from url.txt are assumed to be search pages
                        logger.info(f"Processing as search URL (from url.txt): {url}")
                        total_count = self.search(url, using_temp_urls)  # MODIFIED: Get total count
                    
                    # ADDED: Extract region name and flush data for this URL
                    region_name = extract_region_from_url(url)
                    logger.info(f"完成处理URL: {url}，开始保存数据 (区域: {region_name}, 房源数: {total_count})")
                    
                    if CONFIG['features']['enable_batch_write']:
                        output_file = self.batch_writer.flush(region=region_name, total_count=total_count)
                        if output_file:
                            output_files.append(output_file)
                            logger.info(f"URL {url} 的数据已保存到: {output_file}")
                        else:
                            logger.warning(f"URL {url} 没有数据保存或保存失败")
                    
                    if i_url < len(urls): # Apply delay between all top-level URLs
                        inter_url_delay = random.uniform(inter_url_delay_min, inter_url_delay_max)
                        logger.info(f"下一个URL前延迟 {inter_url_delay:.1f} 秒...")
                        time.sleep(inter_url_delay)
                except Exception as e: 
                    logger.error(f"处理URL {url} 严重错误，跳过.", exc_info=True)
                    # ADDED: Even on error, try to save any collected data
                    try:
                        region_name = extract_region_from_url(url)
                        if CONFIG['features']['enable_batch_write']:
                            output_file = self.batch_writer.flush(region=region_name, total_count=0)
                            if output_file:
                                output_files.append(output_file)
                                logger.info(f"错误处理后，URL {url} 的部分数据已保存到: {output_file}")
                    except Exception as save_error:
                        logger.error(f"错误处理后保存数据也失败: {save_error}")
            
            # MODIFIED: No final flush needed as each URL is processed individually
            logger.info(f"所有URL处理完毕，共生成 {len(output_files)} 个输出文件")
            for output_file in output_files:
                logger.info(f"生成的文件: {output_file}")
            
            logger.info("爬虫任务完成。")
            return output_files # MODIFIED: Return list of files

        except Exception as e:
            logger.critical(f"程序运行期间发生严重错误: {e}", exc_info=True)
            # MODIFIED: Try to save any remaining data with unknown region
            if CONFIG['features']['enable_batch_write']:
                logger.info("尝试在程序异常退出前保存已收集的数据...")
                try:
                    output_csv_path_on_exc = self.batch_writer.flush(region="Error_Recovery", total_count=0)
                    if output_csv_path_on_exc:
                        output_files.append(output_csv_path_on_exc)
                        logger.info(f"发生错误前的数据已尝试保存到: {output_csv_path_on_exc}")
                    else:
                        logger.error("错误发生后，数据保存失败或无数据。")
                except Exception as save_exc:
                    logger.error(f"异常处理中保存数据失败: {save_exc}")
            return output_files # MODIFIED: Return files generated so far
        finally:
            logger.info("房源信息采集程序 (v2) 结束。")


if __name__ == "__main__":
    crawler = DomainCrawler()
    output_files = crawler.run()  # MODIFIED: Get list of output files
    if output_files:
        print(f"生成了 {len(output_files)} 个输出文件:")  # MODIFIED: Print summary
        for output_file in output_files:
            print(output_file)  # Print each output filename to stdout
        sys.exit(0) # Exit with success code
    else:
        print("没有生成任何输出文件")
        sys.exit(1) # Exit with error code if no file was produced or error occurred
