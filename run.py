import argparse
import os
from src.main import start_crawler
from src.config_loader import load_yaml_config

def main():
    """主函数，用于解析命令行参数并启动爬虫。"""
    parser = argparse.ArgumentParser(description="Domain.com.au 爬虫启动器")
    parser.add_argument(
        '--mode',
        type=str,
        default='full',
        choices=['full', 'mini'],
        help="选择运行模式: 'full' (默认) 或 'mini' (简约模式)。"
    )
    parser.add_argument(
        '--config',
        type=str,
        help="指定自定义配置文件的路径。如果提供，将覆盖--mode选择。"
    )
    args = parser.parse_args()

    config = None
    if args.config:
        print(f"🚀 使用自定义配置文件: {args.config}")
        config = load_yaml_config(args.config)
    else:
        config_file = f"config/crawler_config_{args.mode}.yaml"
        print(f"🚀 启动 '{args.mode}' 模式，加载配置文件: {config_file}")
        config = load_yaml_config(config_file)

    if not config:
        print("❌ 错误: 无法加载配置，程序退出。")
        return

    # Add the mode to the config for internal use
    config['mode'] = args.mode
    
    start_crawler(config)

    print("✅ 爬虫任务完成！")

if __name__ == "__main__":
    main()
