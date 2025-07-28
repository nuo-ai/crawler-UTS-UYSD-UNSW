import time
import random
import re
from datetime import datetime
from typing import List, Dict, Any
from .config_loader import load_features_config, get_url_list
from .data_models import set_features_config as set_global_features_config
from .scraper import DomainScraper
from .excel_writer import BatchWriter, get_expected_columns

def process_single_url(scraper: DomainScraper, url: str, writer: BatchWriter, expected_columns: List[str]):
    """处理单个房源详情页URL。"""
    print(f"正在处理详情页: {url}")
    listing = scraper.get_listing_details(url)
    if listing:
        writer.add(listing)
        print(f"成功提取房源信息: ID={listing.listing_id}")
    else:
        print(f"未能提取房源信息: {url}")

def process_search_url(scraper: DomainScraper, search_url: str, writer: BatchWriter, config: Dict[str, Any]):
    """处理单个搜索结果页URL，包含分页 (移植自备份脚本的 search 方法)。"""
    page = 1
    all_listing_urls: List[str] = []
    
    # 从配置中获取性能参数
    performance_config = config.get('performance', {})
    res_thresh = performance_config.get('results_per_page_threshold', 10)
    page_delay_min = performance_config.get('page_delay_min', 2.0)
    page_delay_max = performance_config.get('page_delay_max', 3.5)
    delay_min = performance_config.get('delay_min', 0.8)
    delay_max = performance_config.get('delay_max', 2.2)

    while True:
        # 构造分页URL，兼容不同格式
        if 'page=' in search_url:
            paginated_url = re.sub(r"page=\d+", f"page={page}", search_url)
        else:
            paginated_url = f"{search_url}&page={page}"

        print(f"正在抓取第{page}页: {paginated_url}")
        
        listing_urls_on_page = scraper.find_listings_on_page(paginated_url)
        
        if not listing_urls_on_page:
            print(f"第 {page} 页无房源链接或已达末页, 结束对 {search_url} 搜索.")
            break
            
        all_listing_urls.extend(listing_urls_on_page)
        print(f"第{page}页找到{len(listing_urls_on_page)}个房源")
        
        # 如果当前页房源数小于阈值，则认为是最后一页
        if len(listing_urls_on_page) < res_thresh:
            print(f"当前页房源数 ({len(listing_urls_on_page)}) < 阈值 ({res_thresh})，判断为最后一页.")
            break

        page += 1
        time.sleep(random.uniform(page_delay_min, page_delay_max))

    unique_listing_urls = sorted(list(set(all_listing_urls)))
    print(f"搜索完成，总共找到 {len(unique_listing_urls)} 个不重复的房源链接")

    expected_columns = get_expected_columns(scraper.feature_extractor.features_config)

    for i, listing_url in enumerate(unique_listing_urls):
        try:
            print(f"处理第{i+1}/{len(unique_listing_urls)}个房源: {listing_url}")
            process_single_url(scraper, listing_url, writer, expected_columns)
            time.sleep(random.uniform(delay_min, delay_max))
        except Exception as e:
            print(f"处理房源 {listing_url} 时发生严重错误，跳过此房源: {e}")
            time.sleep(5)
            continue

def start_crawler(config: Dict[str, Any]):
    """爬虫主启动函数。"""
    features_config = load_features_config(config.get('features_config_path', 'config/features_config.yaml'))
    set_global_features_config(features_config)

    scraper = DomainScraper(features_config, crawler_config=config)
    writer = BatchWriter(output_dir=config.get('output_dir', 'output'), buffer_size=config.get('buffer_size', 50))
    
    url_list = get_url_list(config.get('url_file_path', 'config/url.txt'))
    
    expected_columns = get_expected_columns(features_config)
    
    # Filter columns for minimal mode if specified
    if config.get('mode') == 'minimal' and 'minimal_columns' in config:
        expected_columns = [col for col in expected_columns if col in config['minimal_columns']]

    for url in url_list:
        if "/rent/" in url: # Assume it's a search URL
            process_search_url(scraper, url, writer, config)
        else: # Assume it's a single listing URL
            process_single_url(scraper, url, writer, expected_columns)
            
        # Flush remaining items for this URL and save to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suburb_name = url.split('/')[4].split(',')[0] if '/rent/' in url else "listing"
        filename = f"{timestamp}_{suburb_name}_{len(writer.buffer)}properties.xlsx"
        writer.flush(filename, expected_columns)

    print("所有URL处理完毕。")
