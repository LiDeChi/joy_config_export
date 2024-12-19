import tkinter.messagebox  # 不这样导入，messageBox用不了
from proton import *
from tkinter import *
from tkinter import filedialog
import platform

# 导表的文件路径，如：xx.xlsx、yy.xlsx
SELECT_FILES_PATH = ()
# 导出的文件路径
EXPORT_FILES_PATH = ''

# 检查操作系统
IS_MAC = platform.system() == 'Darwin'

if not IS_MAC:
    import windnd

# 没有这一段代码，有myWindow.mainloop()情况下，无法捕获异常！！
class TkExceptionHandler:
    def __init__(self, func, subst, widget):
        self.func = func
        self.subst = subst
        self.widget = widget

    def __call__(self, *args):
        if self.subst:
            args = self.subst(*args)
        return self.func(*args)


tkinter.CallWrapper = TkExceptionHandler


def select_file():
    # 多选文件，只显示xlsx后缀的文件（返回多个所选择文件的文件路径组成的元组）
    file_paths = filedialog.askopenfilenames(filetypes=[("EXCEL Files", "*.xlsx")])
    if file_paths:
        print(f"Selected files: {file_paths}")  # 调试信息
        # 保存并在text打印路径
        print_text(file_paths)
    else:
        print("No files selected")  # 调试信息


def drag_file(files):
    if files:
        file_paths = []
        for f in files:
            # gbk避免中文路径乱码，将路径上的\\替换成/（统一格式）
            path = str(f.decode('gbk')).replace('\\', '/')
            if IS_MAC:
                path = path.replace(':', '/')
            file_paths.append(path)
        print(f"Dragged files: {file_paths}")  # 调试信息
        # 保存并在text打印路径
        print_text(file_paths)
    else:
        print("No files dragged")  # 调试信息


def print_text(file_paths):
    global SELECT_FILES_PATH
    if file_paths:
        # 覆盖/保存
        SELECT_FILES_PATH = file_paths
        # 设置text可编辑
        text.config(state='normal')
        # 先清空text文本
        text.delete('1.0', 'end')
        # 打印信息
        for p in file_paths:
            text.insert(INSERT, p)
            text.insert(INSERT, '\n')
        # 设置text不可编辑
        text.config(state='disabled')
    else:
        # 此前已选路径 且 本次没有新的路径，提示"您没有选择任何文件"
        text.config(state='normal')
        text.delete('1.0', 'end')
        text.insert(INSERT, '您没有选择任何文件')
        text.config(state='disabled')
    print('Excel列表：')
    print(SELECT_FILES_PATH)


def export_path(export_lb):
    global EXPORT_FILES_PATH
    file_path = filedialog.askdirectory()
    if file_path != '':
        EXPORT_FILES_PATH = file_path
        export_lb.config(text=file_path)
    print('输出路径：')
    print(EXPORT_FILES_PATH)


def export_file():
    # 先验证必要参数
    if not SELECT_FILES_PATH:
        update_message("请先选择Excel文件")
        return
    if EXPORT_FILES_PATH == '':
        update_message("未选择保存路径")
        return

    try:
        # 客户端参数设置
        ctext = Context()
        ctext.path = SELECT_FILES_PATH  # -p Excel文件路径
        ctext.folder = EXPORT_FILES_PATH + '/client'  # -f Json输出目录
        ctext.format = 'json'  # -e 格式：format, json or xml or lua or ycl
        ctext.sign = 'c'  # -s 控制该列是否导出，默认全部导出（client被我改成c）
        ctext.extension = ''  # -t 文件后缀，例如：heroTemplate.json
        ctext.objseparator = ','  # -r 对象字段的分隔符，默认为";"，你可以用它来改变
        ctext.codegenerator = None  # -c 一个文件路径，将excel结构保存为json
        ctext.multiprocessescount = 1  # -m 使用多进程计数导出，默认为 cpu 计数
        exportfiles(ctext)

        # 服务端参数设置
        stext = Context()
        stext.path = SELECT_FILES_PATH  # -p Excel文件路径
        stext.folder = EXPORT_FILES_PATH + '/server'  # -f Json输出目录
        stext.format = 'json'  # -e 格式：format, json or xml or lua or ycl
        stext.sign = 's'  # -s 控制该列是否导出，默认全部导出（server被我改成s）
        stext.extension = ''  # -t 文件后缀，例如：heroConfig.json
        stext.objseparator = ','  # -r 对象字段的分隔符，默认为";"，你可以用它来改变
        stext.codegenerator = None  # -c 一个文件路径('schemaserver.json')，将excel结构保存为json（服务端用此再生成HeroTemplate.cs代码，改为None则不会导出）
        stext.multiprocessescount = 1  # -m 使用多进程计数导出，默认为 cpu 计数（None为默认开启12个线程，这里额外打开12个ui窗口，所以改为单线程）
        update_message('所有配置表导出成功！')
        print("All operation finish successful!!!")
    except Exception as e:
        error_message = f'导出失败，错误信息：\n{str(e)}'
        update_message(error_message)
        print("导表错误信息：", error_message)


def update_message(message):
    message_text.config(state='normal')
    message_text.delete('1.0', END)
    message_text.insert(END, message)
    message_text.config(state='disabled')
    myWindow.update_idletasks()  # 强制更新GUI


def main():
    global message_text, myWindow, text
    try:
        # 创建主窗口
        myWindow = Tk()
        myWindow.title("EXCEL2JSON转换器")
        
        width = 480
        height = 450  # 增加高度以容纳新的消息区域
        screenwidth = myWindow.winfo_screenwidth()
        screenheight = myWindow.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        myWindow.geometry(alignstr)
        myWindow.resizable(width=True, height=True)

        # 创建一个frame窗体对象，用来包裹标签
        frame = Frame(myWindow, relief=SUNKEN, borderwidth=2, width=450, height=250)
        # 在水平、垂直方向上填充窗体
        frame.pack(side=TOP, fill=BOTH, expand=1)

        # 输出文件路径的text文本
        text = Text(myWindow)
        text.place(x=105, y=10, width=350, height=100)

        # 选择文件按钮
        select_btn = Button(myWindow, text='选择文件', command=select_file)
        select_btn.place(x=10, y=10, width=90, height=25)

        # 导出路径的label文本
        export_lb = Label(myWindow, text='您没有选择任何目录')
        export_lb.place(x=105, y=115, width=350, height=25)

        # 导出结果的label文本
        result_lb = Label(myWindow, text='导出结果：')
        result_lb.place(x=10, y=185, width=90, height=25)

        # 导出路径按钮
        path_btn = Button(myWindow, text='导出路径', command=lambda: export_path(export_lb))
        path_btn.place(x=10, y=115, width=90, height=25)

        # 导出按钮
        export_btn = Button(myWindow, text='导 出 Json', bg='#87CEFA', command=export_file)
        export_btn.place(x=10, y=150, width=460, height=25)

        # 添加新的文本区域用于显示消息
        message_text = Text(myWindow, wrap=WORD, state='disabled', bg='#F0F0F0')
        message_text.place(x=10, y=300, width=460, height=100)

        # 添加滚动条
        scrollbar = Scrollbar(myWindow, command=message_text.yview)
        scrollbar.place(x=470, y=300, height=100)
        message_text.config(yscrollcommand=scrollbar.set)

        if not IS_MAC:
            # 拖拽事件（text为触发的控件，可以拖拽多文件）
            windnd.hook_dropfiles(text, func=drag_file)

        # 进入消息循环
        myWindow.mainloop()
    except Exception as e:
        error_message = f'初始化失败，错误信息：\n{str(e)}'
        print(error_message)
        if 'message_text' in globals():
            update_message(error_message)
        # 保持界面不关闭
        myWindow.mainloop()


if __name__ == '__main__':
    main()