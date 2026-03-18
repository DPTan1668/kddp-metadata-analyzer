#!/usr/bin/env python3
"""金蝶元数据分析器 - 解析 dym/dymx 文件"""
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import json

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
        # 处理嵌套的 XML
        data_str = ET.tostring(data_xml, encoding='unicode')
        result["DataXml预览"] = data_str[:500] + "..." if len(data_str) > 500 else data_str
        
        # 递归提取表单/实体元数据
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
    
    # 查找所有 JsPlugins/Plugin 路径
    for plugin in element.iter('Plugin'):
        plugin_info = {}
        for child in plugin:
            plugin_info[child.tag] = child.text if child.text else ""
        
        if plugin_info:
            # 格式化启用状态
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
    
    # 基本属性
    for attr in ['Id', 'Number', 'TargetId', 'TargetNumber', 'Version']:
        elem = root.find(attr)
        if elem is not None and elem.text:
            result["基本属性"][attr] = elem.text
    
    # 扩展内容
    extensions = root.find('Extensions')
    if extensions is not None:
        for ext in extensions:
            ext_info = {
                "类型": ext.tag,
                "内容": ET.tostring(ext, encoding='unicode')[:200]
            }
            result["扩展内容"].append(ext_info)
    
    return result

def generate_report(file_path, analysis_result):
    """生成分析报告"""
    report = []
    report.append("=" * 60)
    report.append("金蝶元数据分析报告")
    report.append("=" * 60)
    report.append("")
    report.append(f"[文件] {file_path}")
    report.append(f"[时间] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 基本属性
    if "基本属性" in analysis_result:
        report.append("[基本信息]")
        report.append("-" * 40)
        for k, v in analysis_result["基本属性"].items():
            report.append(f"  {k}: {v}")
        report.append("")
    
    # 版本信息
    if "版本信息" in analysis_result:
        report.append("[版本信息]")
        report.append("-" * 40)
        for k, v in analysis_result["版本信息"].items():
            report.append(f"  {k}: {v}")
        report.append("")
    
    # 设计元数据
    if "设计元数据" in analysis_result and analysis_result["设计元数据"]:
        report.append("[设计元数据]")
        report.append("-" * 40)
        for i, meta in enumerate(analysis_result["设计元数据"], 1):
            report.append(f"\n  [{i}] {meta.get('类型', 'Unknown')}")
            report.append(f"      编号: {meta.get('编号', 'N/A')}")
            report.append(f"      模型类型: {meta.get('模型类型说明', meta.get('模型类型', 'N/A'))}")
            report.append(f"      ISV: {meta.get('ISV', 'N/A')}")
            report.append(f"      开发类型: {meta.get('DevType说明', meta.get('DevType', 'N/A'))}")
            
            if meta.get('继承路径'):
                path_parts = meta['继承路径'].split(',')
                report.append(f"      继承层级: {len(path_parts)} 级")
            
            # JS 插件
            if meta.get('JS插件'):
                report.append(f"      JS插件: {len(meta['JS插件'])} 个")
                for plugin in meta['JS插件']:
                    status = plugin.get('状态', '')
                    report.append(f"        - {plugin.get('ClassName', 'N/A')} ({status})")
            
            # 字段配置
            if meta.get('字段配置'):
                report.append(f"      列表字段: {len(meta['字段配置'])} 个")
                for col in meta['字段配置'][:3]:
                    report.append(f"        - {col.get('显示名称', 'N/A')} ({col.get('字段ID', 'N/A')})")
                if len(meta['字段配置']) > 3:
                    report.append(f"        ... 还有 {len(meta['字段配置']) - 3} 个字段")
        
        report.append("")
    
    # 插件汇总
    all_plugins = []
    if "设计元数据" in analysis_result:
        for meta in analysis_result["设计元数据"]:
            all_plugins.extend(meta.get('JS插件', []))
    
    if all_plugins:
        report.append("[JS 插件汇总]")
        report.append("-" * 40)
        for i, plugin in enumerate(all_plugins, 1):
            report.append(f"  [{i}] {plugin.get('ClassName', 'N/A')}")
            report.append(f"      标识: {plugin.get('FPK', 'N/A')}")
            report.append(f"      用途: {plugin.get('SourceName', 'N/A')}")
            report.append(f"      状态: {plugin.get('状态', 'N/A')}")
        report.append("")
    
    report.append("=" * 60)
    report.append("分析完成")
    report.append("=" * 60)
    
    return "\n".join(report)

def main():
    # 设置 UTF-8 输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("用法: python kingdee_metadata.py <dym或dymx文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        sys.exit(1)
    
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ['.dym', '.dymx']:
        print(f"错误: 不支持的文件类型 - {file_ext}")
        print("仅支持 .dym 和 .dymx 文件")
        sys.exit(1)
    
    print(f"正在分析: {file_path}")
    print("")
    
    try:
        root, content = parse_xml_file(file_path)
        
        # 根据根元素判断元数据类型
        if root.tag == 'DeployMetadata':
            result = analyze_deploy_metadata(root)
        elif root.tag == 'ExtensionMetadata':
            result = analyze_extension_metadata(root)
        else:
            print(f"未知元数据类型: {root.tag}")
            sys.exit(1)
        
        # 生成报告
        report = generate_report(file_path, result)
        print(report)
        
        # 输出 JSON 格式（供程序调用）
        # print("\n--- JSON 输出 ---")
        # print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"解析错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
