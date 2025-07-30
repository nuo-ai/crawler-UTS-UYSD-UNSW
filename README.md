# Domain.com.au 房地产爬虫

## 1. 项目概述

`Domain.com.au` 房地产爬虫是一个功能强大且高度可配置的Python脚本，专为从澳大利亚领先的房地产门户网站 Domain.com.au 抓取住宅租赁房源信息而设计。该工具旨在为数据分析师、研究人员和潜在租户提供一个自动化、高效且可靠的数据收集解决方案。

该项目注重代码的健壮性、数据的准确性以及用户的易用性，通过外部YAML文件进行灵活配置，用户无需修改源代码即可轻松定制爬虫的行为和数据输出。

## 2. 主要特性

- **🚀 高效稳定的抓取**: 基于成熟的架构，确保长时间运行的稳定性和可靠性。
- **📊 丰富的数据提取**: 全面捕获房产的核心信息，包括地址、价格、卧室/浴室数量、中介联系方式、房产描述和图片等。
- **🔧 动态特征提取**: 用户可通过编辑 `features_config.yaml` 文件，自定义需要识别的房产特征（如“空调”、“洗碗机”、“允许宠物”），爬虫会自动在输出中添加相应列。
- **💾 灵活的输出格式**: 支持多种输出模式，包括为每个URL生成独立的Excel/CSV文件、将所有结果合并为单个文件，或同时执行两种模式（`hybrid`）。
- **⚙️ 高度可配置**: 爬虫的核心行为，如网络请求、延迟、用户代理和输出格式，均可通过 `crawler_config.yaml` 进行精细调整。
- **📝 清晰的日志记录**: 记录详细的运行日志，便于追踪和调试。

## 3. 技术栈

- **Python 3.x**: 作为项目的主要编程语言。
- **Requests**: 用于发送HTTP请求，获取网页内容。
- **LXML**: 高性能的XML和HTML解析库，用于从HTML中提取数据。
- **Pandas**: 用于数据处理和构建DataFrame，最终输出为Excel或CSV文件。
- **PyYAML**: 用于解析YAML配置文件。
- **Openpyxl**: 用于写入 `.xlsx` 格式的Excel文件。

## 4. 安装与环境设置

在开始之前，请确保您的系统已安装 Python 3.x 和 pip 包管理器。

1.  **克隆仓库** (如果您正在使用Git):
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **安装依赖**: 项目所需的所有库都记录在 `requirements.txt` 文件中。通过以下命令一键安装：
    ```bash
    pip install -r requirements.txt
    ```

## 5. 使用指南

### 步骤 1: 配置目标URL

-   打开 `config/url.txt` 文件。
-   将您从 Domain.com.au 复制的搜索结果页URL粘贴到此文件中，每行一个URL。

### 步骤 2: 运行爬虫

-   打开您的终端或命令行工具。
-   执行主脚本 `v5_furniture.py`:
    ```bash
    python crawler/v5_furniture.py
    ```

### 步骤 3: 查看结果

-   脚本运行完成后，抓取的数据将保存在 `output/` 目录下。
-   文件名将包含时间戳和从URL中提取的区域名称，例如 `20250730_143000_Haymarket_50properties.xlsx`。

## 6. 配置文件详解

所有配置文件均位于 `config/` 目录下，允许您在不修改代码的情况下自定义爬虫行为。

### `crawler_config.yaml`

该文件控制爬虫的核心设置。

-   **`output`**: 输出行为
    -   `mode`: `'hybrid'` | `'per_url'` | `'single_file'`
    -   `output_format`: `'xlsx'` | `'csv'`
-   **`network`**: 网络请求设置
    -   `headers`: 自定义HTTP请求头，特别是 `User-Agent`。
-   **`settings`**: 运行控制
    -   `delay_between_requests`: 请求之间的延迟（秒），以避免IP被封锁。

### `features_config.yaml`

定义您希望从房产描述中提取的自定义特征。

-   **`name`**: 特征的描述性名称（例如，“允许宠物”）。
-   **`column_name`**: 在输出文件中对应的列名（例如，`allows_pets`）。
-   **`keywords`**: 用于识别该特征的关键词列表（不区分大小写）。

### `furniture_keywords.yaml`

专门用于判断房源的家具状况 (`furnished`, `unfurnished`, `optional`)。

-   **`furnished_keywords`**: 明确表示“提供家具”的关键词。
-   **`unfurnished_keywords`**: 明确表示“不提供家具”的关键词。

## 7. 贡献指南

我们欢迎任何形式的贡献，无论是功能建议、代码改进还是文档修复。

1.  **Fork** 本仓库。
2.  创建一个新的分支 (`git checkout -b feature/YourFeature`)。
3.  进行修改并提交 (`git commit -m 'Add some feature'`)。
4.  将您的分支推送到远程 (`git push origin feature/YourFeature`)。
5.  创建一个 **Pull Request**。

## 8. 许可证

本项目采用 [MIT License](LICENSE) 授权。
    -   `max_retries`: `3` - 页面请求失败时的最大重试次数。
    -   `backoff_factor`: `0.3` - 重试之间的等待时间因子。
    -   `timeout`: `30` - 单个请求的超时时间（秒）。
    -   `retry_statuses`: `[500, 502, 503, 504]` - 遇到这些HTTP状态码时会触发重试。

-   **`performance`**: 性能设置
    -   `max_workers`: `5` - 控制同时下载多少个页面的并发线程数。
    -   `requests_per_second`: `1.0` - 限制每秒的请求频率，以避免对服务器造成过大压力。
    -   `batch_size`: `20` - 当 `enable_batch_write` 开启时，每收集到20条房产数据就写入一次文件。

-   **`headers`**: 请求头
    -   这部分内容模拟了真实的浏览器请求，以避免被网站屏蔽。通常不需要修改。

### 2. `features_config.yaml` - 动态特征提取配置

这个文件的作用已在 **“动态功能管理”** 章节中详细解释。您可以通过编辑此文件来添加、删除或修改您希望从房产描述中提取的任何特征。

### 其他配置文件说明

在 `config/` 目录下，您会看到一些用于定义爬虫具体行为的关键词文件，例如：
-   `aircon_keywords.yaml`: 定义了用于识别不同类型空调的关键词。
-   `furniture_keywords.yaml`: 定义了用于判断房源家具状态（如 `furnished`, `optional`）的关键词。

**请注意：** 这些文件是 **v5_furniture.py** 脚本正常运行所必需的。脚本会加载这些文件来辅助进行数据解析和特征提取。请根据需要维护这些关键词列表。
