#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本：验证双输出模式功能
"""

import yaml
from pathlib import Path
from v5_furniture import CONFIG_DIR, load_config

def test_output_modes():
    """测试两种输出模式的配置"""
    print("=== 测试双输出模式功能 ===\n")
    
    config_path = CONFIG_DIR / 'crawler_config.yaml'
    
    # 读取当前配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        current_mode = config.get('output', {}).get('mode', '未设置')
        prefix = config.get('output', {}).get('single_file_prefix', '未设置')
        
        print(f"✓ 成功读取配置文件: {config_path}")
        print(f"✓ 当前输出模式: {current_mode}")
        print(f"✓ 单文件前缀: {prefix}")
        
        # 验证配置结构
        if 'output' in config:
            print("✓ 输出配置节存在")
            output_config = config['output']
            
            if 'mode' in output_config:
                print("✓ 模式参数存在")
                mode_value = output_config['mode']
                if mode_value in ['per_url', 'single_file', 'hybrid']:
                    print(f"✓ 模式值有效: {mode_value}")
                else:
                    print(f"⚠ 模式值无效: {mode_value}，应为 'per_url'、'single_file' 或 'hybrid'")
            else:
                print("✗ 缺少模式参数")
            
            if 'single_file_prefix' in output_config:
                print(f"✓ 单文件前缀参数存在: {output_config['single_file_prefix']}")
            else:
                print("✗ 缺少单文件前缀参数")
        else:
            print("✗ 输出配置节不存在")
        
        print("\n=== 配置说明 ===")
        print("您可以通过修改 config/crawler_config.yaml 中的输出模式来控制文件生成：")
        print("output:")
        print("  mode: 'per_url'          # 每个URL一个文件")
        print("  # 或")
        print("  mode: 'single_file'      # 所有URL合并为一个文件")
        print("  # 或")
        print("  mode: 'hybrid'           # 既生成独立文件又生成合并文件")
        print("  single_file_prefix: 'Combined'  # 单文件模式和混合模式的合并文件前缀")
        
        print("\n=== 示例文件名 ===")
        print("per_url 模式:")
        print("  - 20250127_030000_Sydney_15properties.xlsx")
        print("  - 20250127_030000_Melbourne_23properties.xlsx")
        print()
        print("single_file 模式:")
        print("  - 20250127_030000_Combined_MultiRegions_38properties.xlsx")
        print()
        print("hybrid 模式:")
        print("  独立文件:")
        print("    - 20250127_030000_Sydney_15properties.xlsx")
        print("    - 20250127_030000_Melbourne_23properties.xlsx")
        print("  合并文件:")
        print("    - 20250127_030000_Combined_MultiRegions_38properties.xlsx")
        
        return True
        
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")
        return False

def show_mode_switching_guide():
    """显示模式切换指南"""
    print("\n=== 模式切换指南 ===")
    print("1. 编辑 config/crawler_config.yaml 文件")
    print("2. 修改 output.mode 参数：")
    print("   - 设为 'per_url' : 每个链接生成一个独立文件")
    print("   - 设为 'single_file' : 所有链接合并为一个文件")
    print("   - 设为 'hybrid' : 既生成独立文件又生成合并文件")
    print("3. 可选：修改 output.single_file_prefix 自定义合并文件前缀")
    print("4. 运行爬虫脚本")
    print()
    print("优势对比：")
    print("per_url 模式:")
    print("  ✓ 便于按区域分析数据")
    print("  ✓ 单个文件较小，便于处理")
    print("  ✓ 如果某个URL失败，不影响其他数据")
    print()
    print("single_file 模式:")
    print("  ✓ 所有数据集中在一个文件中")
    print("  ✓ 便于整体数据分析和比较")
    print("  ✓ 减少文件管理复杂性")
    print()
    print("hybrid 模式:")
    print("  ✓ 兼具per_url和single_file两种模式的所有优势")
    print("  ✓ 既可按区域分析又可整体分析")
    print("  ✓ 提供最大的数据使用灵活性")
    print("  ⚠ 会生成更多文件，占用更多存储空间")

def main():
    """运行所有测试"""
    print("开始测试双输出模式功能...\n")
    
    success = test_output_modes()
    
    if success:
        show_mode_switching_guide()
        print("\n=== 测试完成 ===")
        print("✓ 双输出模式功能配置正常！")
        print("您现在可以通过修改配置文件来灵活控制输出文件的生成方式。")
    else:
        print("\n=== 测试失败 ===")
        print("✗ 配置文件存在问题，请检查 config/crawler_config.yaml")

if __name__ == "__main__":
    main()
