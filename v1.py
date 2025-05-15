#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
房产数据爬虫脚本 - 增强版
整合了v2.1和v3.0的优势，并添加了新的功能增强。

特性：
1. 配置驱动的设计
2. 统一的数据模型
3. 智能特征提取
4. 数据清洗和验证
5. 批量写入机制
6. 完善的错误处理
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from functools import wraps
import threading
# from concurrent.futures import ThreadPoolExecutor, as_completed
# import queue
import re
import yaml
import random
import gc

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree

# =============================================================================
# 项目路径配置
# =============================================================================
PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / 'logs'
CONFIG_DIR = PROJECT_ROOT / 'config'
OUTPUT_DIR = PROJECT_ROOT / 'output'
DATA_DIR = OUTPUT_DIR / 'data'

for d_path in (LOG_DIR, CONFIG_DIR, OUTPUT_DIR, DATA_DIR):
    d_path.mkdir(exist_ok=True)

# =============================================================================
# 日志配置
# =============================================================================
def setup_logger(name: str = 'domain_crawler') -> logging.Logger:
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(logging.DEBUG)
    if logger_instance.handlers:
        return logger_instance
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log_file = LOG_DIR / f"domain_crawler_{datetime.now():%Y%m%d_%H%M%S}.log"
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
            'features': {'enable_advanced_features': True, 'enable_data_validation': True, 'enable_batch_write': True}
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

CONFIG = load_config()

# =============================================================================
# 数据模型
# =============================================================================
@dataclass
class PropertyFeatures:
    has_air_conditioning: bool = False; is_furnished: bool = False
    has_balcony: bool = False; has_dishwasher: bool = False
    has_laundry: bool = False; has_built_in_wardrobe: bool = False
    has_gym: bool = False; has_pool: bool = False
    has_parking: bool = False; allows_pets: bool = False
    has_security_system: bool = False; has_storage: bool = False
    has_study_room: bool = False; has_garden: bool = False
    def to_dict(self) -> Dict[str, bool]: return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    def merge(self, other: 'PropertyFeatures') -> None:
        for fld in self.__dataclass_fields__:
            if not getattr(self, fld): setattr(self, fld, getattr(other, fld))

@dataclass
class PropertyData:
    listing_id: str = ""; property_url: str = ""; address: str = ""
    suburb: str = ""; state: str = ""; postcode: str = ""
    property_type: str = ""; rent_pw: float = 0.0; bond: float = 0.0
    bedrooms: int = 0; bathrooms: int = 0; parking_spaces: int = 0
    available_date: str = ""
    inspection_times: List[str] = field(default_factory=list)
    agency_name: str = ""; agent_name: str = ""; agent_phone: str = ""; agent_email: str = ""
    property_headline: str = ""; property_description: str = ""
    features: PropertyFeatures = field(default_factory=PropertyFeatures)
    latitude: float = 0.0; longitude: float = 0.0
    images: str = ""; property_features: str = ""
    agent_profile_url: str = ""; agent_logo_url: str = ""
    enquiry_form_action: str = ""
    def to_dict(self) -> Dict[str, any]:
        result = {}
        for field_name, field_value in self.__dict__.items():
            if field_name == 'features': result.update(field_value.to_dict())
            elif field_name == 'inspection_times': result['inspection_times'] = '; '.join(field_value)
            else: result[field_name] = field_value
        return result

EXPECTED_COLUMNS = [
    'listing_id', 'property_url', 'address', 'suburb', 'state', 'postcode', 
    'property_type', 'rent_pw', 'bond', 'bedrooms', 'bathrooms', 'parking_spaces', 
    'available_date', 'inspection_times', 'agency_name', 'agent_name', 'agent_phone', 
    'agent_email', 'property_headline', 'property_description', 
    'has_air_conditioning', 'is_furnished', 'has_balcony', 'has_dishwasher', 
    'has_laundry', 'has_built_in_wardrobe', 'has_gym', 'has_pool', 'has_parking', 
    'allows_pets', 'has_security_system', 'has_storage', 'has_study_room', 'has_garden', 
    'latitude', 'longitude', 'images', 'property_features', 'agent_profile_url', 
    'agent_logo_url', 'enquiry_form_action'
]

# =============================================================================
# 特征提取, 数据清洗 & 验证 (Unchanged)
# =============================================================================
class FeatureExtractor:
    def __init__(self):
        self.patterns = {"air_conditioning": [r"air.?con", r"cooling", r"climate control", r"空调", r"冷气"],"furnished": [r"furnished", r"furniture included", r"fully equipped", r"带家具", r"家具齐全"],"balcony": [r"balcony", r"terrace", r"阳台"], "dishwasher": [r"dishwasher", r"洗碗机"],"laundry": [r"laundry", r"washer", r"dryer", r"洗衣", r"烘干机"],"wardrobe": [r"built.?in", r"wardrobe", r"衣柜"], "gym": [r"gym", r"fitness", r"健身"],"pool": [r"pool", r"swimming", r"游泳池"],"parking": [r"parking", r"garage", r"car space", r"停车"],"pets": [r"pet.?friendly", r"pets allowed", r"允许宠物", r"宠物友好"],"security": [r"security", r"intercom", r"安保", r"门禁"],"storage": [r"storage", r"储物"], "study": [r"study", r"home office", r"书房", r"学习区"],"garden": [r"garden", r"yard", r"花园", r"院子"]}
        self.compiled_patterns = {ft: [re.compile(p, re.IGNORECASE) for p in ps] for ft, ps in self.patterns.items()}
    def extract(self, json_data: dict, description: str) -> PropertyFeatures:
        features = self._extract_from_json(json_data)
        if CONFIG['features']['enable_advanced_features']:
            text_features = self._extract_from_text(description); features.merge(text_features)
        return features
    def _extract_from_json(self, json_data: dict) -> PropertyFeatures:
        features = PropertyFeatures()
        s_features = {f.get("name", "").lower() for f in json_data.get("structuredFeatures", [])}
        features.has_air_conditioning = any("air conditioning" in n or "cooling" in n for n in s_features); features.is_furnished = any("furnished" in n for n in s_features); features.has_balcony = any("balcony" in n or "terrace" in n for n in s_features); features.has_dishwasher = any("dishwasher" in n for n in s_features); features.has_laundry = any("laundry" in n or "washing machine" in n for n in s_features); features.allows_pets = any("pet" in n for n in s_features)
        return features
    def _extract_from_text(self, text: str) -> PropertyFeatures:
        features = PropertyFeatures(); text_l = text.lower()
        for f_name, patterns in self.compiled_patterns.items():
            a_f_name = "allows_pets" if f_name=="pets" else "is_furnished" if f_name=="furnished" else f"has_{f_name}"
            if hasattr(features, a_f_name): setattr(features, a_f_name, any(p.search(text_l) for p in patterns))
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
    def clean_text(text: str) -> str:
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text); text = ' '.join(text.split())
        return text.strip()

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
# 请求管理
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
# 批量写入管理
# =============================================================================
class BatchWriter:
    def __init__(self):
        self.buffer: List[PropertyData] = []; self._lock = threading.Lock()
    def add(self, item: PropertyData) -> None:
        with self._lock: self.buffer.append(item)
    def flush(self) -> bool:
        if not self.buffer: logger.info("缓冲区中无数据可刷新至CSV。"); return True
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
                output_file = OUTPUT_DIR / 'merged_results.csv' 
                df_final.to_csv(output_file, index=False, encoding='utf-8-sig', na_rep='')
                logger.info(f"已成功保存 {len(df_final)} 条记录到: {output_file}")
                self.buffer = []
                return True
            except Exception as e:
                logger.error(f"写入合并CSV文件 (merged_results.csv) 失败: {e}", exc_info=True)
                return False

# =============================================================================
# 爬虫核心
# =============================================================================
class DomainCrawler:
    def __init__(self):
        self.request_manager = RequestManager(); self.feature_extractor = FeatureExtractor()
        self.data_cleaner = DataCleaner(); self.data_validator = DataValidator()
        self.batch_writer = BatchWriter(); self._lock = threading.Lock()
    
    def _extract_inspection_times(self, document: etree._Element) -> List[str]:
        times = []
        for b in document.xpath('//div[@data-testid="listing-details__inspections-block"]'):
            try:
                d_el = b.xpath('.//span[@data-testid="listing-details__inspections-block-day"]/text()')
                t_el = b.xpath('.//span[@data-testid="listing-details__inspections-block-time"]/text()')
                if d_el and t_el: times.append(f"{d_el[0].strip()}, {t_el[0].strip()}")
            except Exception as e: logger.debug(f"_extract_inspection_times method 1 error: {e}") # Added context
        if not times:
            try:
                js_txt = "".join(document.xpath(".//script[@id='__NEXT_DATA__']/text()"))
                if js_txt:
                    js_data = json.loads(js_txt)
                    props = js_data.get("props", {}).get("pageProps", {}).get("componentProps", {})
                    for i_item in props.get("inspectionDetails", {}).get("inspections", []):
                        st, et = i_item.get("startTime", ""), i_item.get("endTime", "")
                        if st and et: times.append(f"{st} - {et}")
            except Exception as e: logger.debug(f"_extract_inspection_times method 2 error: {e}") # Added context
        return times
    
    def crawl_detail(self, house_href: str) -> Optional[PropertyData]:
        try:
            logger.info(f"正在抓取详情页: {house_href}")
            response = self.request_manager.get(house_href)
            house_document = etree.HTML(response.text)
            
            try:
                json_script = "".join(house_document.xpath(".//script[@id='__NEXT_DATA__']/text()"))
                if not json_script: logger.error(f"__NEXT_DATA__ script tag not found: {house_href}"); return None
                base_json = json.loads(json_script)
            except Exception as e: logger.error(f"解析详情页JSON失败 for {house_href}: {e}", exc_info=True); return None # Added exc_info
            
            comp_props = base_json.get("props", {}).get("pageProps", {}).get("componentProps", {})
            root_q = comp_props.get("rootGraphQuery", {}).get("listingByIdV2", {}) or {}
            list_sum = comp_props.get("listingSummary", {}) or {}
            agents_list = root_q.get("agents", []); agent_p = agents_list[0] if agents_list else {}
            addr_info = root_q.get("displayableAddress", {}) or {}; geo_info = addr_info.get("geolocation", {}) or {}
            
            features_obj = self.feature_extractor.extract(root_q, root_q.get("description", ""))
            
            img_urls_raw = [img.get("url", "") for img in root_q.get("largeMedia", []) if img.get("url")]
            images_json = json.dumps(img_urls_raw)

            prop_feat_els = house_document.xpath("//div[@id='property-features']//li")
            prop_feat_list = [li.xpath("string(.)").strip() for li in prop_feat_els if li.xpath("string(.)")]
            property_features_json = json.dumps(prop_feat_list)

            # Enquiry Form Action / Link Extraction (Enhanced)
            enquiry_form_action = ""
            # Path for Snug or 2Apply links (<a> tags)
            apply_link_el = house_document.xpath('//div[@data-testid="listing-details__agent-details-cta-box"]//a[contains(@href, "snug.com") or contains(@href, "2apply.com.au")]/@href')
            if apply_link_el:
                enquiry_form_action = apply_link_el[0].strip()
                logger.debug(f"Apply link (Snug/2Apply) for {house_href} extracted: {enquiry_form_action}")
            
            if not enquiry_form_action: # Path for 1form (<form> action)
                oneform_action_el = house_document.xpath('//div[@data-testid="listing-details__agent-details-cta-box"]//form[@data-testid="listing-details__oneform-button-form"]/@action')
                if not oneform_action_el:
                    oneform_action_el = house_document.xpath('//div[@data-testid="listing-details__agent-details-cta-box"]//form[contains(@class, "css-")]/@action')
                if oneform_action_el:
                    enquiry_form_action = oneform_action_el[0].strip()
                    logger.debug(f"Enquiry form action (1form) for {house_href} extracted: {enquiry_form_action}")
            
            if not enquiry_form_action: # Original fallback
                original_enquiry_el = house_document.xpath("//form[@id='enquiry-form']/@action")
                if original_enquiry_el:
                    enquiry_form_action = original_enquiry_el[0].strip()
                    logger.debug(f"Enquiry form action (fallback id='enquiry-form') for {house_href} extracted: {enquiry_form_action}")

            if not enquiry_form_action:
                 logger.warning(f"Enquiry/Apply link/action for {house_href} NOT found via any XPaths.")
            else:
                logger.info(f"Enquiry/Apply link/action FOUND for {house_href}: {enquiry_form_action}")


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
                    logger.debug(f"Agent phone for {house_href} extracted from href: {agent_phone_val}")
                else:
                    agent_phone_el_text = house_document.xpath('//a[@data-testid="listing-details__phone-cta-button"]/span[@class="css-1s26z8e"]/span/text()')
                    if agent_phone_el_text:
                         agent_phone_val = agent_phone_el_text[0].strip() # Could still be "Call"
                         logger.debug(f"Agent phone for {house_href} from button text: {agent_phone_val}")
                    else:
                        logger.debug(f"Agent phone for {house_href} not found via JSON, href, or button text.")


            agent_logo_url_val = (agent_p.get("agency", {}) or {}).get("logoUrl", "") 
            if not agent_logo_url_val:
                agent_logo_el = house_document.xpath('//a[@class="css-wrjy08"]/img[@data-testid="listing-details__agent-details-branding-lazy"]/@src')
                if agent_logo_el:
                    agent_logo_url_val = agent_logo_el[0].strip()

            data_item = PropertyData(
                listing_id=root_q.get("listingId", ""), property_url=house_href,
                address=self.data_cleaner.clean_text(list_sum.get("address", "")),
                suburb=addr_info.get("suburbName", ""), state=addr_info.get("state", ""),
                postcode=addr_info.get("postcode", ""),
                property_type=property_type_val,
                rent_pw=self.data_cleaner.clean_price(list_sum.get("title", "")),
                bond=self.data_cleaner.clean_price(str((root_q.get("priceDetails", {}) or {}).get("bond", 0))),
                bedrooms=list_sum.get("beds", 0), bathrooms=list_sum.get("baths", 0),
                parking_spaces=list_sum.get("parking", 0),
                available_date=self.data_cleaner.clean_date((root_q.get("dateAvailableV2", {}) or {}).get("isoDate", "")),
                inspection_times=self._extract_inspection_times(house_document),
                agency_name=(root_q.get("agency", {}) or {}).get("name", ""),
                agent_name=agent_p.get("fullName", ""), 
                agent_phone=agent_phone_val, 
                agent_email=agent_p.get("email", ""),
                agent_profile_url=agent_p.get("profileUrl", ""),
                agent_logo_url=agent_logo_url_val, 
                property_headline=root_q.get("headline", ""),
                property_description=self.data_cleaner.clean_text(root_q.get("description", "")),
                features=features_obj,
                latitude=float(geo_info.get("latitude", 0.0) or 0.0),
                longitude=float(geo_info.get("longitude", 0.0) or 0.0),
                images=images_json, property_features=property_features_json,
                enquiry_form_action=enquiry_form_action,
            )
            
            if CONFIG['features'].get('enable_data_validation', False):
                is_valid, errors = self.data_validator.validate_property(data_item)
                if not is_valid: logger.warning(f"数据验证失败 for {house_href}: {errors}")
            
            logger.info(f"成功提取房源信息: ID={data_item.listing_id or 'N/A'}")
            if CONFIG['features']['enable_batch_write']: self.batch_writer.add(data_item)
            return data_item
        except Exception as e:
            logger.error(f"抓取详情页失败: {house_href}", exc_info=True); return None
    
    def process_search_page(self, url: str) -> List[str]:
        try:
            resp = self.request_manager.get(url); doc = etree.HTML(resp.text)
            links = []
            # Assuming the structure is ul/li/div/a
            # Test this XPath carefully if issues persist: .//ul[@data-testid='results']/li//a[@data-testid='listing-card-link']/@href
            # Or the more specific one you had: .//ul[@data-testid='results']/li/div/div/div/div/div/a (this looks very fragile)
            # The original one: .//ul[@data-testid='results']/li//div[@class='css-qrqvvg']/a/@href
            listing_items_xpath = ".//ul[@data-testid='results']/li" # Container for each listing
            link_xpath_inside_item = ".//a[contains(@class, 'address') or @data-testid='listing-card-link' or contains(@href,'/1')]/@href" # More robust link finding
            
            # First try to find links using a more specific common pattern if exists
            # This is an example, the actual class or testid for the link might be different
            # common_link_pattern = doc.xpath(".//ul[@data-testid='results']/li//div[contains(@class,'css-')]/a/@href") # Generalize class
            common_link_pattern = doc.xpath(".//ul[@data-testid='results']/li//a[contains(@href, 'www.domain.com.au') and string-length(@href) > 40]/@href")


            if common_link_pattern:
                links = [link for link in common_link_pattern if link.startswith("https://www.domain.com.au/")]
                logger.debug(f"Found {len(links)} links using common pattern for {url}")


            if not links: # Fallback to iterating each list item if common pattern fails or finds nothing
                logger.debug(f"Common link pattern failed for {url}, trying item iteration.")
                for item_element in doc.xpath(listing_items_xpath):
                    # Try to find the most prominent link within the item
                    href_list = item_element.xpath(link_xpath_inside_item)
                    if not href_list: # More specific fallbacks if the general one fails
                         href_list = item_element.xpath(".//div[@class='css-qrqvvg']/a/@href") # Original specific path
                    if not href_list:
                         href_list = item_element.xpath("(.//a[contains(@href,'www.domain.com.au')])[1]/@href") # Any first valid domain link

                    if href_list:
                        # Ensure it's a full URL, prepend domain if it's a relative path
                        link_candidate = href_list[0]
                        if link_candidate.startswith("/"):
                            link_candidate = "https://www.domain.com.au" + link_candidate
                        if link_candidate.startswith("https://www.domain.com.au/"): # Final check
                             links.append(link_candidate)
            
            if not links:
                logger.warning(f"在页面 {url} 上未找到房源链接，请检查XPath选择器。")
            return links
        except Exception as e: logger.error(f"处理搜索页面失败: {url}", exc_info=True); return []
    
    def save_progress(self, url: str, page: int) -> None:
        try:
            prog = {"url": url, "page": page, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            with open(PROJECT_ROOT / 'progress.json', 'w', encoding='utf-8') as f: json.dump(prog, f, indent=2)
            logger.debug(f"保存进度: URL={url}, 页码={page}")
        except Exception as e: logger.error(f"保存进度失败: {e}")
    
    def load_progress(self) -> Optional[dict]:
        try:
            p_file = PROJECT_ROOT / 'progress.json'
            if p_file.exists():
                with open(p_file, 'r', encoding='utf-8') as f: prog = json.load(f)
                logger.info(f"加载到上次进度: {prog.get('url','N/A')}, 页码 {prog.get('page','N/A')}"); return prog
        except Exception as e: logger.error(f"加载进度失败: {e}"); return None
    
    def search(self, input_url: str):
        page = 1 # Default to start from page 1
        # Progress loading is now handled by run method's deletion of progress file
        # prog = self.load_progress() 
        # if prog and prog.get('url') == input_url and isinstance(prog.get('page'), int):
        #     page = prog['page']; logger.info(f"从上次进度继续: 第{page}页 for {input_url}")
        
        res_thresh = CONFIG.get('performance', {}).get('results_per_page_threshold', 10)
        delay_min = CONFIG['performance'].get('delay_min', 0.8)
        delay_max = CONFIG['performance'].get('delay_max', 2.2)
        page_delay_min = CONFIG['performance'].get('page_delay_min',2.0)
        page_delay_max = CONFIG['performance'].get('page_delay_max',3.5)

        while True:
            s_url = f"{input_url}&page={page}"
            logger.info(f"正在抓取第{page}页: {s_url}")
            links = self.process_search_page(s_url)
            if not links: 
                logger.info(f"第 {page} 页无房源链接或已达末页, 结束对 {input_url} 搜索.")
                break
            
            logger.info(f"第{page}页找到{len(links)}个房源"); succ_count = 0
            for i_idx, detail_url in enumerate(links):
                try:
                    logger.info(f"处理第{i_idx+1}/{len(links)}个房源: {detail_url}")
                    if self.crawl_detail(detail_url): succ_count += 1
                    time.sleep(random.uniform(delay_min, delay_max))
                except Exception as e: logger.error(f"处理房源 {detail_url} 失败: {e}", exc_info=True); time.sleep(5.0)
            
            logger.info(f"本页成功处理{succ_count}/{len(links)}个房源")
            self.save_progress(input_url, page + 1) # Save progress after successfully processing a page
            if page % 5 == 0: gc.collect(); logger.info("执行内存回收")
            # The check for len(links) < res_thresh should ideally be after attempting to get links for the *next* page
            # or have a mechanism to detect if the current page is the last one based on site cues (e.g., "next" button disabled)
            # For now, this break condition remains, assuming less than threshold implies end of results.
            if len(links) < res_thresh : 
                logger.info(f"当前页房源数 ({len(links)}) < 阈值 ({res_thresh})，判断为最后一页.")
                break
            
            logger.info(f"完成第{page}页处理"); page += 1
            time.sleep(random.uniform(page_delay_min, page_delay_max))
    
    def run(self):
        try:
            logger.info("开始运行房源信息采集程序...")
            progress_file = PROJECT_ROOT / 'progress.json'
            if progress_file.exists():
                try:
                    progress_file.unlink(); logger.info(f"已删除旧的进度文件: {progress_file}，将从头开始爬取。")
                except OSError as e: logger.error(f"删除进度文件失败: {progress_file}, 错误: {e}。")
            else: logger.info("未找到进度文件，将从头开始爬取。")

            url_cfg_path = CONFIG_DIR / 'url.txt'
            if not url_cfg_path.exists():
                logger.error(f"配置文件不存在: {url_cfg_path}"); logger.info("创建示例配置文件...")
                with open(url_cfg_path, "w", encoding="utf-8") as f:
                    f.write("# URL list, one per line\nhttps://www.domain.com.au/rent/?suburb=sydney-nsw-2000\n")
                logger.info(f"示例配置文件已创建: {url_cfg_path}. 请填充后运行."); return
            
            with open(url_cfg_path, "r", encoding="utf-8") as f:
                urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
            if not urls: logger.error(f"配置文件 {url_cfg_path} 中无有效URL."); return
            
            logger.info(f"找到{len(urls)}个URL待处理: {urls}")
            inter_url_delay_min = CONFIG['performance'].get('inter_url_delay_min', 3.0)
            inter_url_delay_max = CONFIG['performance'].get('inter_url_delay_max', 7.0)
            for i_url, url in enumerate(urls, 1):
                try:
                    logger.info(f"开始处理 ({i_url}/{len(urls)}): {url}"); self.search(url)
                    logger.info(f"完成处理URL: {url}")
                    if i_url < len(urls): 
                        inter_url_delay = random.uniform(inter_url_delay_min, inter_url_delay_max)
                        logger.info(f"下一个URL前延迟 {inter_url_delay:.1f} 秒...")
                        time.sleep(inter_url_delay)
                except Exception as e: logger.error(f"处理URL {url} 严重错误，跳过.", exc_info=True)
            
            if CONFIG['features']['enable_batch_write']:
                logger.info("所有URL处理完毕，开始最终数据写入到 merged_results.csv...")
                if self.batch_writer.flush(): logger.info("最终数据成功写入 merged_results.csv。")
                else: logger.error("最终数据写入 merged_results.csv 失败。")
            else: logger.info("批量写入已禁用，未保存数据。")
            logger.info("爬虫任务完成。")
        except Exception as e:
            logger.critical(f"程序运行期间发生严重错误: {e}", exc_info=True)
            if CONFIG['features']['enable_batch_write']:
                logger.info("尝试在程序异常退出前保存已收集的数据...")
                if self.batch_writer.flush(): logger.info("发生错误前的数据已尝试保存。")
                else: logger.error("错误发生后，数据保存失败。")
        finally: logger.info("房源信息采集程序结束。")

if __name__ == "__main__":
    DomainCrawler().run()