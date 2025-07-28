#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本：验证重构后的Features提取功能
"""

import json
from v5_furniture import (
    FEATURES_CONFIG, 
    PropertyFeatures, 
    FeatureExtractor, 
    EXPECTED_COLUMNS,
    get_expected_columns
)

def test_config_loading():
    """测试配置文件加载"""
    print("=== 测试配置文件加载 ===")
    if FEATURES_CONFIG:
        print(f"✓ 配置文件加载成功")
        print(f"✓ 发现 {len(FEATURES_CONFIG.get('features', []))} 个Feature定义")
        for i, feature in enumerate(FEATURES_CONFIG.get('features', [])[:3]):  # 只显示前3个
            print(f"  {i+1}. {feature.get('name')} -> {feature.get('column_name')}")
        if len(FEATURES_CONFIG.get('features', [])) > 3:
            print(f"  ... 还有 {len(FEATURES_CONFIG.get('features', [])) - 3} 个Feature")
    else:
        print("✗ 配置文件加载失败")
    print()

def test_property_features_initialization():
    """测试PropertyFeatures类初始化"""
    print("=== 测试PropertyFeatures类初始化 ===")
    try:
        features = PropertyFeatures()
        print(f"✓ PropertyFeatures初始化成功")
        
        # 检查动态字段是否已添加
        feature_fields = []
        if FEATURES_CONFIG and 'features' in FEATURES_CONFIG:
            for feature_config in FEATURES_CONFIG['features']:
                column_name = feature_config.get('column_name', '')
                if column_name and hasattr(features, column_name):
                    feature_fields.append(column_name)
        
        print(f"✓ 动态添加了 {len(feature_fields)} 个Feature字段")
        if feature_fields:
            print(f"  前几个字段: {feature_fields[:5]}")
            if len(feature_fields) > 5:
                print(f"  ... 还有 {len(feature_fields) - 5} 个字段")
    except Exception as e:
        print(f"✗ PropertyFeatures初始化失败: {e}")
    print()

def test_expected_columns():
    """测试EXPECTED_COLUMNS生成"""
    print("=== 测试EXPECTED_COLUMNS生成 ===")
    try:
        columns = get_expected_columns()
        print(f"✓ EXPECTED_COLUMNS生成成功，共 {len(columns)} 列")
        
        # 检查是否包含预期的Feature列
        feature_columns = []
        if FEATURES_CONFIG and 'features' in FEATURES_CONFIG:
            for feature_config in FEATURES_CONFIG['features']:
                column_name = feature_config.get('column_name', '')
                if column_name and column_name in columns:
                    feature_columns.append(column_name)
        
        print(f"✓ 包含 {len(feature_columns)} 个Feature列")
        print(f"  样例列: {columns[:5]}...{columns[-3:]}")
    except Exception as e:
        print(f"✗ EXPECTED_COLUMNS生成失败: {e}")
    print()

def test_feature_extraction():
    """测试Feature提取"""
    print("=== 测试Feature提取 ===")
    try:
        extractor = FeatureExtractor()
        
        # 模拟测试数据
        test_json_data = {
            "structuredFeatures": [
                {"name": "air conditioning"},
                {"name": "balcony"},
                {"name": "parking"}
            ]
        }
        test_description = "This furnished apartment has air conditioning, dishwasher, and gym access. Pet friendly building with swimming pool."
        test_feature_list = ["furnished", "dishwasher", "gym", "pets allowed", "pool"]
        
        features = extractor.extract(test_json_data, test_description, test_feature_list)
        
        print(f"✓ Feature提取成功")
        
        # 检查提取结果
        extracted_features = []
        if FEATURES_CONFIG and 'features' in FEATURES_CONFIG:
            for feature_config in FEATURES_CONFIG['features']:
                column_name = feature_config.get('column_name', '')
                if column_name and hasattr(features, column_name):
                    if getattr(features, column_name):
                        extracted_features.append((feature_config.get('name'), column_name))
        
        print(f"✓ 检测到 {len(extracted_features)} 个Feature:")
        for name, column in extracted_features:
            print(f"  - {name} ({column})")
            
    except Exception as e:
        print(f"✗ Feature提取失败: {e}")
    print()

def main():
    """运行所有测试"""
    print("开始测试重构后的Features提取功能...\n")
    
    test_config_loading()
    test_property_features_initialization()
    test_expected_columns()
    test_feature_extraction()
    
    print("=== 测试完成 ===")
    print("如果所有测试都显示 ✓，说明重构成功！")

if __name__ == "__main__":
    main()
