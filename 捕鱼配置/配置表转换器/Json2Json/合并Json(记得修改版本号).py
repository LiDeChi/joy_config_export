# -*- coding: utf-8 -*-
"""
版本修改记录：
v1.0.0 - 初始版本
v1.0.1 - 2024-12-19 添加从环境变量获取导出目录的功能
v1.0.2 - 2024-12-19 添加调试信息，简化目录处理逻辑
"""

import json
import os
import sys

# 打印所有环境变量，用于调试
print("所有环境变量:", dict(os.environ))

# 获取导出目录路径
export_dir = os.environ.get('EXPORT_DIR')
if not export_dir:
    print("错误：未设置EXPORT_DIR环境变量")
    sys.exit(1)

print("导出目录:", export_dir)

# 确保导出目录存在
if not os.path.exists(export_dir):
    print(f"错误：导出目录不存在: {export_dir}")
    sys.exit(1)

# 切换到导出目录
try:
    os.chdir(export_dir)
    print(f"成功切换到目录: {export_dir}")
except Exception as e:
    print(f"切换目录时出错: {e}")
    sys.exit(1)

# 获取当前工作目录
current_directory = os.getcwd()
print("当前工作目录:", current_directory)

# 指定需要搜索的文件后缀
suffix = ".json"

# 列出具有特定后缀的文件名
try:
    files_with_suffix = [f for f in os.listdir(current_directory)
                        if os.path.isfile(os.path.join(current_directory, f)) and f.endswith(suffix)]
    print("JSON文件列表:", files_with_suffix)
except Exception as e:
    print(f"列出文件时出错: {e}")
    sys.exit(1)

version_file = 'version.json'
print("版本文件路径:", os.path.join(current_directory, version_file))

# 判断版本文件是否存在，不存在则生成一个默认版本号的文件
if not os.path.exists(version_file):
    data = {
        'version': '1.0.2'  # 更新版本号
    }
    try:
        with open(version_file, 'w', encoding='UTF-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print("生成默认版本文件")
    except Exception as e:
        print(f"创建版本文件时出错: {e}")
        sys.exit(1)

# 先获取版本号
try:
    with open(version_file, 'r', encoding='UTF-8') as f:
        data = json.load(f)
    print("版本数据:", data)
except Exception as e:
    print(f"读取版本文件时出错: {e}")
    sys.exit(1)

def trim_strings_in_json(obj):
    if isinstance(obj, dict):
        return {k: trim_strings_in_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [trim_strings_in_json(item) for item in obj]
    elif isinstance(obj, str):
        return obj.strip()
    return obj

# 合并所有JSON文件的数据
for file in files_with_suffix:
    if file == 'exported_data.json' or file == version_file:
        continue
    try:
        print(f"正在处理文件: {file}")
        with open(file, 'r', encoding='UTF-8') as f:
            loaded_data = json.load(f)
            # 清理数据中的空白字符
            cleaned_data = trim_strings_in_json(loaded_data)
            data[file.split('.')[0]] = cleaned_data
        print(f"成功处理文件: {file}")
    except Exception as e:
        print(f"处理文件 {file} 时出错: {e}")
        sys.exit(1)

# 指定输出文件路径及名称
output_file = 'exported_data.json'
print("输出文件路径:", os.path.join(current_directory, output_file))

# 打开文件并将数据写入其中
try:
    with open(output_file, 'w', encoding='UTF-8') as file:
        json.dump(data, file, ensure_ascii=False)
    print("成功导出JSON文件！")
except Exception as e:
    print(f"写入输出文件时出错: {e}")
    sys.exit(1)
