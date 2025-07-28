import pandas as pd
import json
from collections import Counter
import logging
from pathlib import Path

# --- 配置 ---
# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义输入和输出文件路径
# 使用Path对象来处理路径，确保跨平台兼容性
INPUT_CSV_PATH = Path('output/data/20250726_160346_results.csv')
OUTPUT_REPORT_PATH = Path('output/feature_analysis_report.txt')
OUTPUT_DIR = Path('output')

# --- 主逻辑 ---
def analyze_property_features():
    """
    读取CSV文件，解析'property_features'列，统计所有feature的出现频率，
    并生成一份排序后的报告。
    """
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 检查输入文件是否存在
    if not INPUT_CSV_PATH.exists():
        logging.error(f"错误：输入文件未找到，请检查路径: {INPUT_CSV_PATH}")
        return

    logging.info(f"开始读取CSV文件: {INPUT_CSV_PATH}...")
    try:
        # 使用pandas读取CSV
        df = pd.read_csv(INPUT_CSV_PATH)
        logging.info(f"文件读取成功，共加载 {len(df)} 条记录。")
    except FileNotFoundError:
        logging.error(f"错误：无法找到文件 {INPUT_CSV_PATH}")
        return
    except Exception as e:
        logging.error(f"读取CSV文件时发生错误: {e}")
        return

    # 检查 'property_features' 列是否存在
    if 'property_features' not in df.columns:
        logging.error("错误：CSV文件中缺少 'property_features' 列。")
        return

    # 使用Counter来统计所有features的频率
    all_features_counter = Counter()
    
    logging.info("开始解析 'property_features' 列并统计...")

    # 遍历DataFrame中的每一行
    for index, row in df.iterrows():
        # 获取 'property_features' 列的内容
        features_json_str = row['property_features']
        
        # 检查内容是否为有效的字符串
        if not isinstance(features_json_str, str) or not features_json_str.strip():
            continue

        try:
            # 解析JSON字符串
            features_list = json.loads(features_json_str)
            
            # 确保解析后是列表格式
            if isinstance(features_list, list):
                # 清理每个feature标签，去除首尾空格并转为小写，以保证统计准确性
                cleaned_features = [str(feature).strip().lower() for feature in features_list]
                # 更新计数器
                all_features_counter.update(cleaned_features)
        except json.JSONDecodeError:
            # 如果某一行无法解析，记录一个警告并继续
            logging.warning(f"警告：在第 {index + 2} 行解析JSON失败。内容: '{features_json_str[:100]}...'")
            continue

    logging.info(f"统计完成，共发现 {len(all_features_counter)} 个独特的feature标签。")

    # 按频率从高到低排序
    sorted_features = all_features_counter.most_common()

    # 将结果写入报告文件
    logging.info(f"正在将分析报告写入到: {OUTPUT_REPORT_PATH}...")
    try:
        with open(OUTPUT_REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write("房源特性分析报告\n")
            f.write("="*30 + "\n")
            f.write(f"数据来源: {INPUT_CSV_PATH.name}\n")
            f.write(f"总房源数: {len(df)}\n")
            f.write(f"独立Feature标签数: {len(sorted_features)}\n")
            f.write("="*30 + "\n\n")
            f.write("Feature 频率列表 (从高到低):\n")
            f.write("-" * 30 + "\n")
            
            # 写入每个feature和它的频率
            for feature, count in sorted_features:
                f.write(f"{feature}: {count}\n")
                
        logging.info("报告生成成功！")
    except IOError as e:
        logging.error(f"写入报告文件时发生错误: {e}")

# --- 程序入口 ---
if __name__ == "__main__":
    analyze_property_features()
