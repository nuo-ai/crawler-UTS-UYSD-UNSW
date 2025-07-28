# 新项目结构设计 (New Project Structure Design)

**日期:** 2025年7月27日  
**任务:** 1.2 - 设计新的项目结构  
**当前状态:** 清理后的项目文件盘点完成

---

## 🎯 设计目标

1. **模块化** - 清晰的职责分离
2. **可维护性** - 符合Python项目最佳实践
3. **易扩展** - 为未来功能扩展预留空间
4. **专业化** - 标准的开源项目结构

---

## 📁 新项目结构设计

```
domain-crawler/                          # 项目根目录
├── README.md                            # 🆕 主项目文档
├── requirements.txt                     # ✅ 保持不变
├── .gitignore                          # 🆕 Git忽略配置
├── setup.py                            # 🆕 包安装配置（可选）
├── 
├── src/                                # 🆕 源代码目录
│   ├── __init__.py                     # Python包标识
│   ├── main.py                         # 🆕 主程序入口点
│   ├── crawler/                        # 🆕 爬虫核心模块
│   │   ├── __init__.py
│   │   ├── scraper.py                  # 📦 重构自 v5_furniture.py
│   │   ├── data_models.py              # 🆕 数据模型定义
│   │   ├── feature_extractor.py        # 🆕 Feature提取器
│   │   └── batch_writer.py             # 🆕 批量写入器
│   ├── config/                         # 🆕 配置管理模块
│   │   ├── __init__.py
│   │   ├── config_loader.py            # 🆕 配置加载器
│   │   └── settings.py                 # 🆕 设置管理
│   └── utils/                          # 🆕 工具函数
│       ├── __init__.py
│       ├── logger.py                   # 🆕 日志工具
│       └── helpers.py                  # 🆕 辅助函数
│
├── config/                             # ✅ 配置文件目录
│   ├── crawler_config.yaml             # ✅ 保持
│   ├── features_config.yaml            # ✅ 保持
│   ├── aircon_keywords.yaml            # ✅ 保持
│   ├── furniture_keywords.yaml         # ✅ 保持
│   └── url.txt                         # ✅ 保持
│
├── tests/                              # 🆕 测试目录
│   ├── __init__.py
│   ├── test_scraper.py                 # 📦 重构自 test_features_extraction.py
│   ├── test_config.py                  # 🆕 配置测试
│   ├── test_output_modes.py            # ✅ 保持
│   └── fixtures/                       # 🆕 测试数据
│       └── sample_data.html
│
├── docs/                               # 🆕 文档目录
│   ├── README.md                       # 🆕 详细文档
│   ├── architecture.md                 # 🆕 架构设计文档
│   ├── configuration.md               # 🆕 配置指南
│   ├── api_reference.md               # 🆕 API参考
│   └── examples/                       # 🆕 使用示例
│       ├── basic_usage.py
│       └── advanced_config.py
│
├── scripts/                            # 🆕 脚本目录
│   ├── run_crawler.py                  # 🆕 快速运行脚本
│   ├── validate_config.py              # 🆕 配置验证脚本
│   └── clean_output.py                 # 🆕 清理输出脚本
│
├── output/                             # 🆕 输出目录（空，.gitignore忽略）
│   └── .gitkeep                        # 🆕 保持目录存在
│
└── archive/                            # 🆕 归档目录
    ├── legacy_versions/                # 📦 历史版本
    │   ├── v5_furniture_backup.py      # 📦 移入
    │   ├── v5_minimal.py               # 📦 移入
    │   └── v5.py                       # 📦 移入
    ├── documentation/                  # 📦 历史文档
    │   ├── DUAL_OUTPUT_MODES_GUIDE.md  # 📦 移入
    │   ├── THREE_OUTPUT_MODES_IMPLEMENTATION.md # 📦 移入
    │   ├── furniture_keywords_deployment_guide.md # 📦 移入
    │   └── REFACTORING_SUMMARY.md      # 📦 移入
    └── analysis_scripts/               # 📦 分析脚本
        ├── analyze_features.py         # 📦 移入
        └── analyze_ac.py               # 📦 移入
```

---

## 🔄 文件迁移计划

### **📦 需要重构的核心文件**

1. **`v5_furniture.py` → `src/crawler/scraper.py`**
   - 拆分为多个模块（scraper, feature_extractor, data_models, batch_writer）
   - 保持所有现有功能

2. **新增 `src/main.py`**
   - 作为程序主入口点
   - 简化的命令行接口

3. **新增 `src/config/config_loader.py`**
   - 统一的配置加载逻辑
   - 支持配置验证

### **📁 需要移动的文件**

| 当前位置 | 新位置 | 操作 |
|----------|--------|------|
| `test_features_extraction.py` | `tests/test_scraper.py` | 移动+重命名 |
| `test_output_modes.py` | `tests/test_output_modes.py` | 移动 |
| `v5_furniture_backup.py` | `archive/legacy_versions/` | 归档 |
| `v5_minimal.py` | `archive/legacy_versions/` | 归档 |
| `v5.py` | `archive/legacy_versions/` | 归档 |
| `DUAL_OUTPUT_MODES_GUIDE.md` | `archive/documentation/` | 归档 |
| `THREE_OUTPUT_MODES_IMPLEMENTATION.md` | `archive/documentation/` | 归档 |
| `furniture_keywords_deployment_guide.md` | `archive/documentation/` | 归档 |
| `config/REFACTORING_SUMMARY.md` | `archive/documentation/` | 归档 |
| `output/analyze_features.py` | `archive/analysis_scripts/` | 归档 |
| `output/analyze_ac.py` | `archive/analysis_scripts/` | 归档 |

---

## 🆕 需要创建的新文件

### **核心模块文件**
- `src/__init__.py`
- `src/main.py` - 主程序入口
- `src/crawler/__init__.py`
- `src/crawler/data_models.py` - 数据模型（从v5_furniture.py提取）
- `src/crawler/feature_extractor.py` - Feature提取（从v5_furniture.py提取）
- `src/crawler/batch_writer.py` - 批量写入（从v5_furniture.py提取）
- `src/config/__init__.py`
- `src/config/config_loader.py` - 配置加载器
- `src/config/settings.py` - 设置管理
- `src/utils/__init__.py`
- `src/utils/logger.py` - 日志工具
- `src/utils/helpers.py` - 辅助函数

### **文档文件**
- `README.md` - 新的主文档
- `docs/README.md` - 详细文档
- `docs/architecture.md` - 架构设计
- `docs/configuration.md` - 配置指南
- `docs/api_reference.md` - API参考
- `docs/examples/basic_usage.py` - 基础使用示例
- `docs/examples/advanced_config.py` - 高级配置示例

### **脚本文件**
- `scripts/run_crawler.py` - 快速运行
- `scripts/validate_config.py` - 配置验证
- `scripts/clean_output.py` - 清理输出

### **项目配置文件**
- `.gitignore` - Git忽略配置
- `setup.py` - 包安装配置（可选）
- `output/.gitkeep` - 保持输出目录

---

## 🏗️ 重构优势

### **代码组织**
- **单一职责原则** - 每个模块专注一个功能
- **清晰的导入路径** - `from src.crawler.scraper import DomainScraper`
- **易于测试** - 每个模块可独立测试

### **可维护性**
- **模块化设计** - 修改一个功能不影响其他部分
- **统一配置管理** - 所有配置通过config_loader统一处理
- **标准化日志** - 统一的日志格式和级别

### **扩展性**
- **插件架构预留** - 新的Feature提取器可轻松添加
- **配置驱动** - 新的输出格式通过配置添加
- **API就绪** - 为集成到更大系统做准备

---

## 🎯 下一步执行计划

**经您确认此结构设计后，我们将执行：**

1. **创建新目录结构**
2. **拆分和重构 `v5_furniture.py`**
3. **移动现有文件到新位置**
4. **创建新的文档和脚本**
5. **更新所有import路径**
6. **验证重构后的功能完整性**

---

*结构设计完成时间: 2025年7月27日 19:41*
