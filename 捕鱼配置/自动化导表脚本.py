import os
import subprocess
import sys
import time
import re

def get_venv_python():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_paths = [
        os.path.join(current_dir, "excel2json_env", "bin", "python"),  # Unix-like systems
        os.path.join(current_dir, "excel2json_env", "Scripts", "python.exe"),  # Windows
        "/Users/mac/miniconda3/envs/excel2json_env/bin/python",  # Conda environment
    ]
    
    for path in venv_paths:
        if os.path.exists(path):
            return path
    return sys.executable

def run_script(script_path):
    """运行脚本并返回输出"""
    try:
        python_path = get_venv_python()
        result = subprocess.run([python_path, script_path], 
                              check=True, capture_output=True, text=True)
        print(result.stdout)
        
        # 从输出中提取导出路径
        export_paths = []
        for line in result.stdout.split('\n'):
            if '成功导出到:' in line:
                path = line.split('成功导出到:')[1].strip()
                export_paths.append(path)
        
        return export_paths
        
    except subprocess.CalledProcessError as e:
        print(f"运行脚本 {script_path} 时出错: {e}")
        if e.stdout:
            print("标准输出:", e.stdout)
        if e.stderr:
            print("错误输出:", e.stderr)
        sys.exit(1)

def wait_for_file_unlock(file_path, timeout=10):
    """等待文件解锁"""
    print(f"等待文件解锁: {file_path}")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 尝试以写入模式打开文件
            with open(file_path, 'a+b') as f:
                f.close()
            print(f"文件已解锁: {file_path}")
            return True
        except (IOError, PermissionError):
            print(f"文件仍然被锁定，等待...")
            time.sleep(1)
    print(f"等待文件解锁超时: {file_path}")
    return False

def merge_json_files(export_paths, merge_script_path):
    """合并指定路径的JSON文件"""
    for json_path in export_paths:
        if json_path.endswith('.json'):
            # 等待文件解锁
            if not wait_for_file_unlock(json_path):
                print(f"无法处理被锁定的文件: {json_path}")
                continue
                
            export_dir = os.path.dirname(json_path)
            print(f"\n开始处理导出目录: {export_dir}")
            
            # 检查目录中是否有json文件
            json_files = [f for f in os.listdir(export_dir) 
                        if f.endswith('.json') and f != 'exported_data.json']
            print(f"目录中的JSON文件: {json_files}")
            
            if json_files:
                print("开始合并JSON文件...")
                time.sleep(2)  # 额外等待2秒，确保文件完全写入
                
                # 将导出目录作为参数传递给合并脚本
                env = os.environ.copy()
                env['EXPORT_DIR'] = export_dir  # 直接使用export_dir
                print(f"设置环境变量EXPORT_DIR: {env['EXPORT_DIR']}")
                
                try:
                    print(f"执行合并脚本: {merge_script_path}")
                    print(f"导出目录: {export_dir}")
                    result = subprocess.run([get_venv_python(), merge_script_path], 
                                env=env, check=True, capture_output=True, text=True)
                    if result.stdout:
                        print(f"合并脚本输出: {result.stdout}")
                    if result.stderr:
                        print(f"合并脚本错误: {result.stderr}")
                    print("JSON合并完成!")
                except subprocess.CalledProcessError as e:
                    print(f"合并脚本执行失败: {e}")
                    print(f"错误输出: {e.stderr}")

def main():
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"当前脚本目录: {current_dir}")
    
    # 获取并打印使用的Python解释器路径
    python_path = get_venv_python()
    print(f"使用的Python解释器: {python_path}")
    
    # 定义要运行的脚本路径
    startui_path = os.path.join(current_dir, "配置表转换器", "Excel2JsonCsv", "startui.py")
    merge_json_path = os.path.join(current_dir, "配置表转换器", "Json2Json", "合并Json(记得修改版本号).py")
    print(f"startui路径: {startui_path}")
    print(f"合并脚本路径: {merge_json_path}")
    
    # 运行 startui.py 导出 JSON 和 CSV
    print("\n开始运行 startui.py...")
    # 设置环境变量来控制导出格式
    os.environ['EXPORT_FORMAT'] = 'both'  # 可以是 'json', 'csv', 或 'both'
    
    # 运行导出脚本并获取导出路径
    export_paths = run_script(startui_path)
    
    # 立即处理导出的文件
    if export_paths:
        merge_json_files(export_paths, merge_json_path)
        print("\n所有文件处理完成!")
    else:
        print("\n没有找到导出的文件")

if __name__ == "__main__":
    main()