# 双输出模式功能使用指南

## 🎯 功能概述

房地产爬虫系统现在支持两种灵活的输出模式，您可以根据需要选择：

- **per_url 模式**：每个链接生成一个独立的Excel文件
- **single_file 模式**：所有链接的数据合并到一个Excel文件

## ⚙️ 配置方式

编辑 `config/crawler_config.yaml` 文件中的 `output` 配置节：

```yaml
# 输出设置
output:
  mode: 'per_url'                 # 'per_url' 或 'single_file'
  single_file_prefix: 'Combined'  # 单文件模式的文件前缀
```

## 📋 模式详解

### 1. per_url 模式（默认）
- **用途**：需要按区域分别分析数据时
- **文件生成**：每个URL生成一个独立文件
- **文件命名**：`20250127_030000_Sydney_15properties.xlsx`
- **优势**：
  - 便于按区域分析数据
  - 单个文件较小，便于处理
  - 某个URL失败不影响其他数据

### 2. single_file 模式
- **用途**：需要整体数据分析和比较时
- **文件生成**：所有URL的数据合并为一个文件
- **文件命名**：`20250127_030000_Combined_MultiRegions_38properties.xlsx`
- **优势**：
  - 所有数据集中在一个文件中
  - 便于整体数据分析和比较
  - 减少文件管理复杂性

## 🚀 使用步骤

1. **选择输出模式**
   ```yaml
   output:
     mode: 'per_url'      # 或 'single_file'
   ```

2. **可选：自定义合并文件前缀**（仅single_file模式）
   ```yaml
   output:
     mode: 'single_file'
     single_file_prefix: 'MyProject'  # 会生成 MyProject_MultiRegions_XX.xlsx
   ```

3. **运行爬虫**
   ```bash
   python v5_furniture.py
   ```

## 📁 文件命名规则

### per_url 模式
- 格式：`{时间戳}_{区域名}_{房源数}properties.xlsx`
- 示例：
  - `20250127_030000_Sydney_15properties.xlsx`
  - `20250127_030000_Melbourne_23properties.xlsx`

### single_file 模式
- 格式：`{时间戳}_{前缀}_{区域描述}_{总房源数}properties.xlsx`
- 示例：
  - `20250127_030000_Combined_MultiRegions_38properties.xlsx`
  - `20250127_030000_Combined_Sydney_15properties.xlsx`

## 🔧 技术实现

- **配置驱动**：通过YAML配置文件控制行为
- **向后兼容**：默认行为保持不变（per_url模式）
- **内存优化**：单文件模式在内存中累积数据，最后统一写入
- **错误处理**：两种模式都有完善的错误恢复机制

## ✅ 测试验证

运行测试脚本验证配置：

```bash
python test_output_modes.py
```

此脚本会验证配置文件的完整性和有效性。

---

**注意**：修改配置后无需重启服务，直接运行爬虫即可应用新的输出模式。
