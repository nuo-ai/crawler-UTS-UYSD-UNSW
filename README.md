# Domain.com.au 房产爬虫 (v6)

本项目包含一个功能强大且稳定的 Python 脚本 (`v6_reverted.py`)，用于从 Domain.com.au 抓取住宅租赁房产数据。它被设计为健壮、可配置且易于使用。

## 关于我

你好！我是一名热衷于数据和自动化的开发者。这个项目是我为了解决从 Domain.com.au 手动收集租房信息的繁琐过程而创建的。我希望这个工具能帮助你更高效地找到理想的住所。

如果你有任何建议或问题，欢迎随时与我联系！

---

## 主要特点

- **稳定与健壮**: 基于经过验证的稳定代码库构建，确保可靠的抓取。
- **丰富的数据提取**: 捕获广泛的数据点，包括房产详情、定价、中介信息以及全面的功能列表。
- **动态功能管理**: 这是此版本的突出特点。您只需编辑一个配置文件，即可定义要抓取的房产功能（例如，“阳台”、“洗碗机”、“宠物友好”），而无需接触任何 Python 代码。
- **Excel 输出**: 为每个抓取的 URL 生成一个干净、带时间戳的 `.xlsx` 文件，可随时进行分析。
- **可配置**: 爬虫行为（网络设置、延迟）可通过 `config/crawler_config.yaml` 进行微调。

## 安装

确保您已安装 Python 3.x 和 pip。

要安装所有必需的 Python 库，请运行：
```bash
pip install pandas requests lxml PyYAML openpyxl
```

## 如何运行

1.  **配置 URL**: 编辑 `config/url.txt` 文件。添加一个或多个 Domain.com.au 搜索结果 URL，每行一个。为了快速测试，您可以使用 `config/temp_urls.txt`，如果其中包含任何 URL，则将使用它而不是 `url.txt`。

2.  **运行脚本**: 从您的终端执行主脚本：
    ```bash
    python v6_reverted.py
    ```

3.  **查找您的数据**: 脚本将处理每个 URL，并将结果另存为 `output/` 目录中的单独 `.xlsx` 文件。文件名将带有时间戳并包含区域名称（例如，`20250728_212216_Forest_Lodge_14properties.xlsx`）。

## 动态功能管理

该脚本最强大的功能是其无需编辑代码即可进行自定义的能力。您可以精确控制检测哪些房产功能并将其作为列添加到最终的 Excel 文件中。

这一切都在 **`config/features_config.yaml`** 文件中进行管理。

### 工作原理

脚本在启动时读取 `features_config.yaml` 文件。对于文件中定义的每个功能，它将：
1.  动态地向输出的 Excel 文件中添加一个相应的布尔值（TRUE/FALSE）列。
2.  扫描房产的描述和功能列表，查找您指定的关键字。
3.  如果找到任何关键字，该房产对应列中的值将被设置为 `TRUE`。

### `features_config.yaml` 结构

该文件是一个功能列表。每个功能有三个部分：

-   `name`: 功能的中文名称（供参考）。
-   `column_name`: 输出 Excel 文件中的列名。**必须是有效的 Python 变量名**（例如，`has_dishwasher`，无空格）。
-   `keywords`: 在房产描述中搜索的关键字列表。搜索不区分大小写。

### 示例：添加“宠物友好”功能

要添加一个检查是否允许宠物的功能，您需要将以下内容添加到 `config/features_config.yaml` 中：

```yaml
- name: 允许宠物
  column_name: allows_pets
  keywords:
    - "pet friendly"
    - "pets allowed"
    - "pets considered"
    - "允许宠物"
```

添加此内容并重新运行脚本后，您的输出 Excel 文件现在将包含一个名为 `allows_pets` 的新列，对于描述中包含任何指定关键字的房产，该列的值将为 `TRUE`。
