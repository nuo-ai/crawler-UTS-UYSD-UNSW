import yaml
import os
from typing import Dict, Any, List

def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """加载指定路径的YAML配置文件。"""
    if not os.path.exists(file_path):
        print(f"警告: 配置文件 {file_path} 不存在。")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError) as e:
        print(f"错误: 加载或解析YAML文件 {file_path} 失败: {e}")
        return {}

def load_features_config(file_path: str = 'config/features_config.yaml') -> Dict[str, Any]:
    """加载Features配置文件。"""
    return load_yaml_config(file_path)

def load_crawler_config(file_path: str = 'config/crawler_config.yaml') -> Dict[str, Any]:
    """加载爬虫主配置文件。"""
    return load_yaml_config(file_path)

def get_url_list(file_path: str = 'config/url.txt') -> List[str]:
    """从文件加载URL列表。"""
    if not os.path.exists(file_path):
        print(f"警告: URL文件 {file_path} 不存在。")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except IOError as e:
        print(f"错误: 读取URL文件 {file_path} 失败: {e}")
        return []
