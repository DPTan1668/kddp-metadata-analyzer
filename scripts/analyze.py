#!/usr/bin/env python3
"""金蝶元数据分析器 - 支持 ZIP 包解压和 dym/dymx 文件解析"""
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import json
import tempfile
import shutil

def extract_zip(zip_path, extract_to):
    """解压 ZIP 文件，返回解压后的目录路径"""
    print(f"[解压] 正在解压: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    print(f"[解压] 已解压到: {extract_to}")
    return extract_to

def find_dym_files(directory, extensions=['.dym', '.dymx']):
    """递归查找目录下所有 dym/dymx 文件"""
    dym_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory)
                dym_files.append({
                    'full_path': full_path,
                    'rel_path': rel_path,
                    'name': file,
                    'size': os.path.getsize(full_path)
                })
    
    return dym_files

def parse_xml_file(file_path):
    """解析 XML 文件，处理命名空间"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除 XML 声明中的编码声明，统一用 utf-8
    if content.startswith('<?xml'):
        content = content.split('?>', 1)[1] if '?>' in content else content
    
    # 解析 XML
    root = ET.fromstring(content)
    return root, content

def analyze_deploy_metadata(root):
    """分析部署元数据"""
    result = {
        "元数据类型": "DeployMetadata",
        "基本属性": {},
        "设计元数据": [],
        "版本信息": {}
    }
    
    # 基本属性
    for attr in ['Multilanguage', 'MasterId', 'BizappId', 'Id', 'BOSVersion', 'BizunitId']:
        elem = root.find(attr)
        if elem is not None and elem.text:
            result["基本属性"][attr] = elem.text
    
    # 版本
    version_elem = root.find('Version')
    if version_elem is not None:
        try:
            ts = int(version_elem.text) / 1000
            dt = datetime.fromtimestamp(ts)
            result["版本信息"]["时间戳"] = version_elem.text
            result["版本信息"]["可读时间"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            result["版本信息"]["时间戳"] = version_elem.text
    
    # 设计元数据
    design_metas = root.find('DesignMetas')
    if design_metas is not None:
        for design_meta in design_metas:
            meta_info = analyze_design_meta(design_meta)
            result["设计元数据"].append(meta_info)
    
    return result

def analyze_design_meta(element):
    """分析单个设计元数据"""
    result = {
        "类型": element.tag,
        "DevType": None,
        "模型类型": None,
        "ISV": None,
        "编号": None,
        "实体ID": None,
        "父级ID": None,
        "主数据ID": None,
        "继承路径": None,
        "修改时间": None,
        "JS插件": [],
        "字段配置": []
    }
    
    # 基本属性
    for attr in ['DevType', 'ModelType', 'Isv', 'Number', 'EntityId', 'ParentId', 'MasterId', 'InheritPath', 'ModifyDate']:
        elem = element.find(attr)
        if elem is not None and elem.text:
            if attr == 'ModifyDate':
                try:
                    ts = int(elem.text) / 1000
                    dt = datetime.fromtimestamp(ts)
                    result["修改时间"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    result["修改时间"] = elem.text
            else:
                result[attr] = elem.text
    
    # DevType 说明
    dev_type_map = {0: "标准产品", 1: "行业产品", 2: "扩展开发", 3: "客户开发"}
    if result["DevType"]:
        result["DevType说明"] = dev_type_map.get(result["DevType"], "未知")
    
    # 模型类型说明
    model_type_map = {
        "BaseFormModel": "基础表单模型",
        "BillFormModel": "单据表单模型",
        "ReportModel": "报表模型",
        "TreeModel": "树形模型",
        "ListModel": "列表模型"
    }
    if result["模型类型"]:
        result["模型类型说明"] = model_type_map.get(result["模型类型"], result["模型类型"])
    
    # 解析 DataXml
    data_xml = element.find('DataXml')
    if data_xml is not None:
        data_str = ET.tostring(data_xml, encoding='unicode')
        result["DataXml预览"] = data_str[:500] + "..." if len(data_str) > 500 else data_str
        
        for child in data_xml:
            if 'Meta' in child.tag:
                result["子元数据类型"] = child.tag
    
    # 提取 JS 插件
    result["JS插件"] = extract_js_plugins(element)
    
    # 提取列表字段配置
    result["字段配置"] = extract_list_columns(element)
    
    return result

def extract_js_plugins(element):
    """提取 JS 插件列表"""
    plugins = []
    
    for plugin in element.iter('Plugin'):
        plugin_info = {}
        for child in plugin:
            plugin_info[child.tag] = child.text if child.text else ""
        
        if plugin_info:
            if plugin_info.get('Enabled') == 'true':
                plugin_info["状态"] = "启用"
            else:
                plugin_info["状态"] = "禁用"
            plugins.append(plugin_info)
    
    return plugins

def extract_list_columns(element):
    """提取列表字段配置"""
    columns = []
    
    for col in element.iter('ListColumnAp'):
        col_info = {
            "字段ID": col.findtext('ListFieldId', ''),
            "显示名称": col.findtext('Name', ''),
            "索引": col.findtext('Index', ''),
            "排序方式": col.findtext('Order', ''),
        }
        if col_info["字段ID"]:
            columns.append(col_info)
    
    return columns

def analyze_extension_metadata(root):
    """分析扩展元数据 (dymx)"""
    result = {
        "元数据类型": "ExtensionMetadata",
        "基本属性": {},
        "扩展内容": []
    }
    
    for attr in ['Id', 'Number', 'TargetId', 'TargetNumber', 'Version']:
        elem = root.find(attr)
        if elem is not None and elem.text:
            result["基本属性"][attr] = elem.text
    
    extensions = root.find('Extensions')
    if extensions is not None:
        for ext in extensions:
            ext_info = {
                "类型": ext.tag,
                "内容": ET.tostring(ext, encoding='unicode')[:200]
            }
            result["扩展内容"].append(ext_info)
    
    return result

def generate_single_report(file_path, analysis_result):
    """生成单个文件的分析报告"""
    report = []
    
    report.append("-" * 50)
    report.append(f"[文件] {file_path}")
    report.append("-" * 50)
    
    if "基本属性" in analysis_result:
        for k, v in analysis_result["基本属性"].items():
            report.append(f"  {k}: {v}")
    
    if "版本信息" in analysis_result:
        for k, v in analysis_result["版本信息"].items():
            report.append(f"  {k}: {v}")
    
    if "设计元数据" in analysis_result:
        for meta in analysis_result["设计元数据"]:
            report.append(f"  类型: {meta.get('类型', 'N/A')}")
            report.append(f"  ISV: {meta.get('ISV', 'N/A')}")
            report.append(f"  开发类型: {meta.get('DevType说明', meta.get('DevType', 'N/A'))}")
            
            plugins = meta.get('JS插件', [])
            if plugins:
                report.append(f"  JS插件: {len(plugins)} 个")
                for p in plugins[:2]:
                    report.append(f"    - {p.get('ClassName', 'N/A')}")
                if len(plugins) > 2:
                    report.append(f"    ... 还有 {len(plugins)-2} 个")
    
    return "\n".join(report)

def generate_summary_report(zip_path, dym_files, results):
    """生成汇总报告"""
    report = []
    report.append("=" * 70)
    report.append("金蝶元数据分析报告 - 批量分析")
    report.append("=" * 70)
    report.append("")
    report.append(f"[ZIP文件] {zip_path}")
    report.append(f"[分析时间] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append(f"[找到文件] 共发现 {len(dym_files)} 个 dym/dymx 文件")
    report.append("")
    
    for i, (dym_info, result) in enumerate(zip(dym_files, results), 1):
        report.append(f"\n[{i}/{len(dym_files)}] {dym_info['name']}")
        report.append("-" * 50)
        report.append(f"  路径: {dym_info['rel_path']}")
        report.append(f"  大小: {dym_info['size']:,} 字节")
        
        if result.get('基本属性'):
            for k, v in result['基本属性'].items():
                if k in ['Id', 'BizappId', 'MasterId']:
                    report.append(f"  {k}: {v}")
        
        if result.get('版本信息', {}).get('可读时间'):
            report.append(f"  修改时间: {result['版本信息']['可读时间']}")
        
        plugins = []
        if '设计元数据' in result:
            for meta in result['设计元数据']:
                plugins.extend(meta.get('JS插件', []))
        
        if plugins:
            report.append(f"  JS插件: {len(plugins)} 个")
    
    report.append("")
    report.append("=" * 70)
    report.append("分析完成")
    report.append("=" * 70)
    
    return "\n".join(report)

def main():
    # 设置 UTF-8 输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("用法: python kingdee_metadata.py <文件路径>")
        print("")
        print("支持的文件格式:")
        print("  - .dym 文件（金蝶部署元数据）")
        print("  - .dymx 文件（金蝶扩展元数据）")
        print("  - .zip 文件（金蝶部署包，自动解压并分析）")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        sys.exit(1)
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # 创建临时目录用于解压
    temp_dir = tempfile.mkdtemp(prefix="kddp_analysis_")
    
    try:
        # 处理 ZIP 文件
        if file_ext == '.zip':
            print(f"\n[检测] 这是一个 ZIP 压缩包，将自动解压分析")
            print("=" * 50)
            
            # 解压
            extract_zip(file_path, temp_dir)
            
            # 查找 dym/dymx 文件
            print("\n[扫描] 正在搜索 dym/dymx 文件...")
            dym_files = find_dym_files(temp_dir)
            
            if not dym_files:
                print("错误: 在 ZIP 包中未找到任何 .dym 或 .dymx 文件")
                sys.exit(1)
            
            print(f"[发现] 找到 {len(dym_files)} 个文件:")
            for d in dym_files:
                print(f"  - {d['rel_path']} ({d['size']:,} 字节)")
            
            print("\n" + "=" * 50)
            print("开始分析...")
            print("=" * 50)
            
            # 分析每个文件
            results = []
            for dym_info in dym_files:
                print(f"\n分析: {dym_info['name']}")
                try:
                    root, content = parse_xml_file(dym_info['full_path'])
                    
                    if root.tag == 'DeployMetadata':
                        result = analyze_deploy_metadata(root)
                    elif root.tag == 'ExtensionMetadata':
                        result = analyze_extension_metadata(root)
                    else:
                        print(f"  未知类型: {root.tag}")
                        result = {"错误": f"未知类型: {root.tag}"}
                    
                    results.append(result)
                    print(f"  OK")
                    
                except Exception as e:
                    print(f"  解析失败: {str(e)}")
                    results.append({"错误": str(e)})
            
            # 生成汇总报告
            print("\n" + "=" * 50)
            report = generate_summary_report(file_path, dym_files, results)
            print(report)
        
        # 处理单个 dym/dymx 文件
        elif file_ext in ['.dym', '.dymx']:
            print(f"正在分析: {file_path}")
            print("")
            
            root, content = parse_xml_file(file_path)
            
            if root.tag == 'DeployMetadata':
                result = analyze_deploy_metadata(root)
            elif root.tag == 'ExtensionMetadata':
                result = analyze_extension_metadata(root)
            else:
                print(f"未知元数据类型: {root.tag}")
                sys.exit(1)
            
            report = generate_single_report(file_path, result)
            print(report)
        
        else:
            print(f"错误: 不支持的文件类型 - {file_ext}")
            print("仅支持 .dym, .dymx 和 .zip 文件")
            sys.exit(1)
    
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n[清理] 已删除临时目录")

if __name__ == "__main__":
    main()
