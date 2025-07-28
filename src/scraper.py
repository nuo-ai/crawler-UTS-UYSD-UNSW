from curl_cffi import requests as cffi_requests
from lxml import html
import re
import json
import time
import random
from typing import List, Optional, Dict, Any
from datetime import datetime
from .data_models import PropertyListing, PropertyFeatures
from .feature_extractor import FeatureExtractor

class DataCleaner:
    @staticmethod
    def clean_price(price: str) -> float:
        if not price: return 0.0
        try: return float(re.sub(r'[^\d.]', '', price))
        except (ValueError, TypeError): return 0.0
    
    @staticmethod
    def clean_text(text: str) -> str:
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text); text = ' '.join(text.split())
        return text.strip()

class DomainScraper:
    """Domain.com.au的爬虫核心类，使用curl_cffi并实现速率控制。"""
    def __init__(self, features_config: Dict[str, Any], crawler_config: Dict[str, Any]):
        self.feature_extractor = FeatureExtractor(features_config)
        self.config = crawler_config
        self.session = cffi_requests.Session()
        self.last_request_time = 0
        self.data_cleaner = DataCleaner()
        
        headers = self.config.get('headers', {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        })
        self.session.headers.update(headers)

    def _wait_for_rate_limit(self):
        """在每次请求前进行精确的速率控制，模拟人类行为。"""
        performance_config = self.config.get('performance', {})
        reqs_per_sec = performance_config.get('requests_per_second', 1.0)
        
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        wait_time = (1.0 / reqs_per_sec) - elapsed
        
        if wait_time > 0:
            time.sleep(wait_time)
        
        self.last_request_time = time.time()

    def get_listing_details(self, url: str) -> Optional[PropertyListing]:
        """获取单个房源的详细信息 (完整移植自备份脚本的 crawl_detail)。"""
        try:
            print(f"正在处理详情页: {url}")
            self._wait_for_rate_limit()
            timeout = self.config.get('network', {}).get('timeout', 30)
            response = self.session.get(url, impersonate="chrome120", timeout=timeout)
            response.raise_for_status()
            
            tree = html.fromstring(response.content)
            
            json_script_content = tree.xpath('//script[@id="__NEXT_DATA__"]/text()')
            if not json_script_content:
                print(f"错误: 在 {url} 未找到 __NEXT_DATA__ script tag")
                return None
            
            base_json = json.loads(json_script_content[0])
            
            # --- Start of copied logic from v5_furniture_backup.py ---
            comp_props = base_json.get("props", {}).get("pageProps", {}).get("componentProps", {})
            root_q = comp_props.get("rootGraphQuery", {}).get("listingByIdV2", {}) or {}
            list_sum = comp_props.get("listingSummary", {}) or {}
            
            # If the primary path fails, try the secondary path for listing data
            if not root_q:
                listing_from_page_props = base_json.get("props", {}).get("pageProps", {}).get("listing", {})
                if listing_from_page_props and isinstance(listing_from_page_props, dict):
                    root_q = listing_from_page_props
                else:
                    print(f"错误: 在 {url} 的JSON中通过所有已知路径均未找到 'listing' 数据")
                    return None

            agents_list = root_q.get("agents", [])
            agent_p = agents_list[0] if agents_list else {}
            addr_info = root_q.get("displayableAddress", {}) or {}
            
            prop_feat_els = tree.xpath("//div[@id='property-features']//li")
            prop_feat_list = [li.xpath("string(.)").strip() for li in prop_feat_els if li.xpath("string(.)")]
            
            description = self.data_cleaner.clean_text(root_q.get("description", ""))
            text_blob = f"{description} {' '.join(prop_feat_list)}".lower()
            features_obj = self.feature_extractor.extract(text_blob)
            
            img_urls_raw = [img.get("url", "") for img in root_q.get("media", []) if img.get("type") == "image" and img.get("url")]
            cover_image_val = img_urls_raw[0] if img_urls_raw else ""

            property_type_val = root_q.get("propertyType", "")
            if not property_type_val:
                property_type_elements = tree.xpath('//span[@class="css-1efi8gv"]/text()')
                if property_type_elements:
                    property_type_val = property_type_elements[0].strip()

            # Adapt to new PropertyListing model
            listing = PropertyListing(
                listing_id=str(root_q.get("listingId") or root_q.get("id")),
                url=url,
                address=self.data_cleaner.clean_text(list_sum.get("address") or addr_info.get("displayAddress") or ""),
                suburb=addr_info.get("suburbName", ''),
                price=root_q.get("priceDetails", {}).get("displayPrice", ''),
                property_type=property_type_val,
                bedrooms=root_q.get("bedrooms") or list_sum.get("beds"),
                bathrooms=root_q.get("bathrooms") or list_sum.get("baths"),
                parking=root_q.get("carspaces") or list_sum.get("parking"),
                title=root_q.get("headline", ''),
                description=description,
                features=features_obj,
                cover_image_url=cover_image_val,
                images=img_urls_raw,
                agent_name=agent_p.get("fullName", ''),
                agent_phone=agent_p.get("phoneNumber", ''),
                agency_name=(root_q.get("agency", {}) or {}).get("name", ''),
                raw_features_text=" ".join(prop_feat_list),
                date_scraped=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            print(f"成功提取房源信息: ID={listing.listing_id}")
            return listing
            # --- End of copied logic ---

        except (cffi_requests.errors.RequestsError, json.JSONDecodeError, Exception) as e:
            print(f"错误: 抓取或解析详情页 {url} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_main_image(self, listing_data: Dict[str, Any]) -> Optional[str]:
        media = listing_data.get('media', [])
        if not media:
            return None
        
        for item in media:
            if item.get('type') == 'image' and item.get('main', False) and 'url' in item:
                return item['url']
        
        for item in media:
            if item.get('type') == 'image' and 'url' in item:
                return item['url']
        
        return None

    def _get_agent_info(self, listing_data: Dict[str, Any], key: str) -> Optional[str]:
        agents = listing_data.get('advertiser', {}).get('agents', [])
        if agents:
            return agents[0].get(key)
        return None

    def find_listings_on_page(self, search_url: str) -> List[str]:
        """从搜索结果页找到所有房源的链接。"""
        try:
            self._wait_for_rate_limit()
            timeout = self.config.get('network', {}).get('timeout', 30)
            response = self.session.get(search_url, impersonate="chrome120", timeout=timeout)
            response.raise_for_status()
            tree = html.fromstring(response.content)
            
            links = []
            # Use the same XPath pattern as the working backup script
            common_link_pattern = tree.xpath(".//ul[@data-testid='results']/li//a[contains(@href, 'www.domain.com.au') and string-length(@href) > 40]/@href")

            if common_link_pattern:
                links = [link for link in common_link_pattern if link.startswith("https://www.domain.com.au/")]
            
            # Fallback XPath patterns from backup script if primary pattern fails
            if not links:
                listing_items_xpath = ".//ul[@data-testid='results']/li"
                link_xpath_inside_item = ".//a[contains(@class, 'address') or @data-testid='listing-card-link' or contains(@href,'/1')]/@href"
                for item_element in tree.xpath(listing_items_xpath):
                    href_list = item_element.xpath(link_xpath_inside_item)
                    if not href_list: 
                        href_list = item_element.xpath(".//div[@class='css-qrqvvg']/a/@href")
                    if not href_list: 
                        href_list = item_element.xpath("(.//a[contains(@href,'www.domain.com.au')])[1]/@href")

                    if href_list:
                        link_candidate = href_list[0]
                        if link_candidate.startswith("/"): 
                            link_candidate = "https://www.domain.com.au" + link_candidate
                        if link_candidate.startswith("https://www.domain.com.au/"): 
                            links.append(link_candidate)
            
            if not links: 
                print(f"警告: 在页面 {search_url} 上未找到房源链接，请检查XPath选择器。")
            
            return list(set(links))  # Ensure unique links
        except cffi_requests.errors.RequestsError as e:
            print(f"错误: 抓取搜索页 {search_url} 失败: {e}")
            return []
