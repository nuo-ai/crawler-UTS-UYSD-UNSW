#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Domain爬虫冒烟测试
验证爬虫的基本功能是否正常工作
"""

import os
import sys
import pytest
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from domain_crawler import DomainCrawler, PropertyData, CONFIG

# 测试URL（仅抓取一页）
TEST_URL = "https://www.domain.com.au/rent/?suburb=sydney-nsw-2000&page=1"

def test_crawler_initialization():
    """测试爬虫初始化"""
    crawler = DomainCrawler()
    assert crawler is not None
    assert crawler.feature_extractor is not None
    assert crawler.data_cleaner is not None
    assert crawler.data_validator is not None
    assert crawler.batch_writer is not None

def test_process_search_page():
    """测试搜索页面处理"""
    crawler = DomainCrawler()
    links = crawler.process_search_page(TEST_URL)
    
    assert isinstance(links, list)
    assert len(links) > 0
    assert all(isinstance(link, str) for link in links)
    assert all(link.startswith('http') for link in links)

def test_crawl_single_listing():
    """测试单个房源抓取"""
    crawler = DomainCrawler()
    # 首先获取一个有效的房源链接
    links = crawler.process_search_page(TEST_URL)
    assert len(links) > 0
    
    # 抓取第一个房源
    property_data = crawler.crawl_detail(links[0])
    
    # 验证返回数据
    assert isinstance(property_data, PropertyData)
    assert property_data.listing_id != ""
    assert property_data.property_url != ""
    assert property_data.address != ""
    assert property_data.rent_pw > 0
    assert property_data.features is not None

def test_batch_writing():
    """测试批量写入功能"""
    crawler = DomainCrawler()
    
    # 修改批量写入大小为2以便测试
    crawler.batch_writer.batch_size = 2
    
    # 获取房源链接
    links = crawler.process_search_page(TEST_URL)
    assert len(links) >= 2
    
    # 抓取前两个房源
    for link in links[:2]:
        property_data = crawler.crawl_detail(link)
        assert property_data is not None
    
    # 验证输出目录中是否有CSV文件
    csv_files = list(PROJECT_ROOT.glob('output/data/*.csv'))
    assert len(csv_files) > 0
    
    # 验证最新的CSV文件
    latest_csv = max(csv_files, key=os.path.getctime)
    assert latest_csv.stat().st_size > 0

def test_feature_extraction():
    """测试特征提取"""
    crawler = DomainCrawler()
    
    # 测试文本特征提取
    test_description = """
    This modern apartment features air conditioning and is fully furnished.
    Includes a dishwasher and internal laundry.
    Pet friendly building with secure parking.
    """
    
    features = crawler.feature_extractor._extract_from_text(test_description)
    assert features.has_air_conditioning
    assert features.is_furnished
    assert features.has_dishwasher
    assert features.has_laundry
    assert features.allows_pets
    assert features.has_parking

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
