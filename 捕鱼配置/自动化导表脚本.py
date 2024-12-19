import os
import subprocess
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime

HISTORY_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history_config.json")
MAX_HISTORY = 10

def get_excel2json_python():
    """获取excel2json环境的Python解释器路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_paths = [
        os.path.join(current_dir, "excel2json_env", "bin", "python"),  # Unix-like systems
        os.path.join(current_dir, "excel2json_env", "Scripts", "python.exe"),  # Windows
    ]
    
    for path in venv_paths:
        if os.path.exists(path):
            return path
    return sys.executable

def process_excel_file(excel_path):
    """处理Excel文件并返回导出路径"""
    try:
        # 设置导出目录为Excel文件所在目录
        export_dir = os.path.dirname(excel_path)
        
        # 获取startui.py的路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        startui_path = os.path.join(current_dir, "配置表转换器", "Excel2JsonCsv", "startui.py")
        
        # 使用excel2json_env的Python来运行startui.py
        python_path = get_excel2json_python()
        env = os.environ.copy()
        env['EXPORT_FORMAT'] = 'both'
        env['EXCEL_PATH'] = excel_path
        
        print(f"\n开始处理文件: {excel_path}")
        result = subprocess.run([python_path, startui_path], 
                              env=env,
                              check=True, 
                              capture_output=True, 
                              text=True)
        
        print(result.stdout)
        
        # 返回导出路径
        client_path = os.path.join(export_dir, 'client')
        server_path = os.path.join(export_dir, 'server')
        return [client_path, server_path]

    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        if isinstance(e, subprocess.CalledProcessError):
            if e.stdout:
                print("标准输出:", e.stdout)
            if e.stderr:
                print("错误输出:", e.stderr)
        return []

def merge_json_files(export_paths, merge_script_path):
    """合并导出的JSON文件"""
    try:
        if not export_paths:
            print("没有找到要合并的文件")
            return False
            
        # 获取client目录路径
        client_path = None
        for path in export_paths:
            if path.endswith('client'):
                client_path = path
                break
        
        if not client_path:
            print("未找到client目录")
            return False
            
        python_path = get_excel2json_python()
        
        # 设置环境变量
        env = os.environ.copy()
        env['EXPORT_DIR'] = client_path
        print(f"设置EXPORT_DIR为: {client_path}")
        
        result = subprocess.run([python_path, merge_script_path], 
                              env=env,
                              check=True, 
                              capture_output=True, 
                              text=True)
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"合并文件失败: {e}")
        if e.stdout:
            print("标准输出:", e.stdout)
        if e.stderr:
            print("错误输出:", e.stderr)
        return False

def load_history():
    """加载历史记录"""
    if os.path.exists(HISTORY_CONFIG):
        with open(HISTORY_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"recent_files": [], "last_updated": ""}

def save_history(file_path):
    """保存历史记录"""
    history = load_history()
    if file_path in history["recent_files"]:
        history["recent_files"].remove(file_path)
    history["recent_files"].insert(0, file_path)
    history["recent_files"] = history["recent_files"][:MAX_HISTORY]
    history["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(HISTORY_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def main():
    root = tk.Tk()
    root.title("配置表自动导出工具")
    root.geometry("600x400")
    
    # 创建主框架
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # 标题标签
    title_label = ttk.Label(main_frame, text="最近处理的文档:", font=('Arial', 12, 'bold'))
    title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
    
    # 创建列表框
    listbox = tk.Listbox(main_frame, width=70, height=15)
    listbox.grid(row=1, column=0, columnspan=2, pady=(0, 10))
    
    # 添加滚动条
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=listbox.yview)
    scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
    listbox.configure(yscrollcommand=scrollbar.set)
    
    # 加载历史记录
    history = load_history()
    for file_path in history["recent_files"]:
        if os.path.exists(file_path):
            listbox.insert(tk.END, file_path)
    
    def process_selected_file():
        selection = listbox.curselection()
        if selection:
            file_path = listbox.get(selection[0])
            if os.path.exists(file_path):
                status_label.config(text="正在处理文件...")
                root.update()
                
                # 处理Excel文件
                export_paths = process_excel_file(file_path)
                if export_paths:
                    # 合并JSON文件
                    merge_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                   "配置表转换器", "Json2Json", 
                                                   "合并Json(记得修改版本号).py")
                    if merge_json_files(export_paths, merge_script_path):
                        save_history(file_path)
                        status_label.config(text=f"处理完成: {os.path.basename(file_path)}")
                    else:
                        status_label.config(text="合并文件失败!")
                else:
                    status_label.config(text="处理文件失败!")
            else:
                status_label.config(text="文件不存在!")
        else:
            status_label.config(text="请先选择一个文件!")

    def select_file():
        file_path = filedialog.askopenfilename(
            title="选择要处理的文件",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if file_path:
            if file_path not in [listbox.get(idx) for idx in range(listbox.size())]:
                listbox.insert(0, file_path)
            # 选择新添加的文件
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(0)
            status_label.config(text="已选择文件: " + os.path.basename(file_path))
    
    # 创建按钮框架
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=2, column=0, columnspan=2, pady=10)
    
    # 添加选择文件按钮
    select_btn = ttk.Button(button_frame, text="选择文件", command=select_file)
    select_btn.pack(side=tk.LEFT, padx=5)
    
    # 添加处理按钮
    process_btn = ttk.Button(button_frame, text="导出并合并选中文件", command=process_selected_file)
    process_btn.pack(side=tk.LEFT, padx=5)
    
    # 添加状态标签
    status_label = ttk.Label(main_frame, text="")
    status_label.grid(row=3, column=0, columnspan=2, pady=5)
    
    root.mainloop()

if __name__ == "__main__":
    main()