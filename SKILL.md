---
name: kddp-metadata-analyzer
description: |
 # 分析金蝶云EBC产品的元数据文件（.dym、.dymx）。
 # 支持解析部署元数据、表单元数据、实体元数据、插件配置、继承关系等。
 # 支持 ZIP 压缩包自动解压，找出其中的所有 dym/dymx 文件并批量分析。
 # 适用于金蝶开发人员、实施顾问进行元数据审查、问题排查和文档生成。
metadata:
  openclaw:
    emoji: "📊"
---

# 金蝶元数据分析器 (Kddp Metadata Analyzer)

## 功能概述

本 Skill 用于分析金蝶云EBC产品的元数据文件：

- **.dym** 文件 - 部署元数据（Deploy）
- **.dymx** 文件 - 扩展元数据（Extension Language）
- **.zip** 文件 - 金蝶部署包，自动解压并分析其中的所有 dym/dymx 文件

## 使用场景

1. **分析单个文件** - 直接分析 dym 或 dymx 文件
2. **批量分析** - 提供 ZIP 压缩包，自动解压并分析所有元数据文件
3. **元数据审查** - 快速了解一个元数据包的结构和内容
4. **问题排查** - 分析继承关系、插件配置、字段定义等
5. **文档生成** - 自动生成元数据说明文档

## 核心能力

### 1. 解析部署元数据 (DeployMetadata)

```xml
<DeployMetadata>
  <MasterId>主数据ID</MasterId>
  <BizappId>业务应用ID</BizappId>
  <DesignMetas>设计元数据集合</DesignMetas>
</DeployMetadata>
```

提取信息：
- 业务对象编号 (Number)
- ISV 标识
- 实体 ID 和父级 ID
- 继承路径 (InheritPath)
- 版本信息

### 2. 解析表单元数据 (DesignFormMeta)

分析内容：
- 表单类型（基础资料、单据、报表等）
- 界面配置（PC端/移动端列表、单据）
- 插件清单
- 字段和列配置
- 过滤条件

### 3. 解析实体元数据 (DesignEntityMeta)

分析内容：
- 实体类型和继承关系
- 字段定义
- 业务规则
- 数据映射

### 4. 继承关系分析

```
根元数据
    ↓
父级元数据1
    ↓
父级元数据2
    ↓
当前元数据（扩展）
```

### 5. 插件分析

提取所有插件：
- 插件标识 (FPK)
- 类名 (ClassName)
- 源编号 (SourceNumber)
- 启用状态
- 用途说明

## 使用方法

### 分析单个文件

直接告诉我要分析的金蝶元数据文件路径：

> "分析 C:\\Users\\kingdee\\Desktop\\xxx.zip"
> "帮我看看这个 dym、dymx 文件"

### 分析 ZIP 压缩包

给我一个金蝶部署包（ZIP 格式），我会自动：

> "分析这个 ZIP 包里的元数据"
> "帮我看看这个压缩包"

处理流程：
1. 解压 ZIP 文件到临时目录
2. 递归查找所有 .dym 和 .dymx 文件
3. 逐个解析每个元数据文件
4. 生成汇总分析报告
5. 自动清理临时文件

### 输出内容

分析报告包含：
- ZIP 包中找到的文件数量
- 每个文件的元数据信息（ID、ISV、版本、插件数量等）
- 插件清单汇总
- 文件大小和路径信息

## 输出格式

分析报告包含：

### 📋 基本信息
- 文件名、大小、编码
- 元数据类型、业务对象
- ISV 标识、版本信息

### 🔍 核心元数据
- 实体 ID、主数据 ID
- 业务应用 ID
- 继承路径

### 📦 设计元数据
- 表单元数据详情
- 实体元数据详情
- 界面配置清单

### 🔌 插件清单
- 所有 JS 插件列表
- 插件用途和状态

### 🏗️ 继承关系
- 可视化继承链
- 父级元数据说明

## 技术说明

### 支持的文件格式

**1. dym 文件 - 部署元数据**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<DeployMetadata>
  <MasterId>...</MasterId>
  <BizappId>...</BizappId>
  <DesignMetas>...</DesignMetas>
</DeployMetadata>
```

**2. dymx 文件 - 扩展元数据**
与 dym 类似，包含扩展和差异信息。

**3. ZIP 文件 - 金蝶部署包**
支持金蝶云平台的部署包压缩文件，自动解压后分析其中的所有元数据文件。

### 常见元数据类型

| DevType | 说明 |
|---------|------|
| 0 | 标准产品 |
| 1 | 行业产品 |
| 2 | 扩展开发 |
| 3 | 客户开发 |

### 常见模型类型

| ModelType | 说明 |
|-----------|------|
| BaseFormModel | 基础表单模型 |
| BillFormModel | 单据表单模型 |
| ReportModel | 报表模型 |
| TreeModel | 树形模型 |
| ListModel | 列表模型 |

## 注意事项

1. 确保文件编码为 UTF-8，否则可能出现乱码
2. 大型 dym/dymx 文件可能需要更长的解析时间
3. 部分加密或压缩的元数据文件可能无法直接解析
4. 分析结果仅供参考，具体业务逻辑需结合源码理解

## 相关链接

- 金蝶云苍穹开发平台: https://www.kingdee.com/
- 金蝶开发者社区: https://developer.kingdee.com/
