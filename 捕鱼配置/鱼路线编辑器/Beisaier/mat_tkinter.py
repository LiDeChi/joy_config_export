"""
    主程序文件，负责程序的启动与结束和窗体的大致设置。
"""
import tkinter as tk
import mat_figure
import os
import sys
import matplotlib.image as mpimg


def source_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


cd = source_path('')
os.chdir(cd)


def win_w_h(root):
    """
        控制窗口的大小和出现的位置
    :param root:
    :return: 窗口的大小和出现的位置
    """
    # 设置标题：
    win.title("路线编辑器")
    # 获取屏幕的大小;
    screen_height = root.winfo_screenheight()
    screen_width = root.winfo_screenwidth()
    # 窗体的大小
    win_width = 0.6 * screen_width
    win_height = 0.65 * screen_height
    # 窗体出现的位置：控制的是左上角的坐标
    show_width = (screen_width - win_width) / 2
    show_height = (screen_height - win_height) / 2
    # 设置窗口是否可变长、宽，True：可变，False：不可变
    win.resizable(width=False, height=False)
    # 返回窗体 坐标
    return win_width, win_height, show_width, show_height


def addpoints():
    mat_figure.add_point()


def delpoints():
    mat_figure.del_point()


def drawpoints():
    mat_figure.draw_point()


def big_imitate():
    mat_figure.imitate(imitate_time_lb, 2, 10)   # fishid,frames 鱼资源id和帧数


def small_imitate():
    mat_figure.imitate(imitate_time_lb, 1, 10)


def change_bg():
    mat_figure.changebg(var.get())


win = tk.Tk()
# 大小 位置
win.geometry("%dx%d+%d+%d" % (win_w_h(win)))

# 创建一个容器, 没有画布时的背景
frame1 = tk.Frame(win, bg="#c0c0c0")
frame1.place(relx=0, rely=0, relwidth=1, relheight=1)

# 输出路径的label文本
path_lb = tk.Label(win, text='输出路径：', bg="#c0c0c0")
path_lb.place(relx=0.063, rely=0.86, relwidth=0.05, relheight=0.03)

# 输出路径的text文本
path_txt = tk.Text(frame1)
# path_txt.insert(tk.INSERT, '您没有选择任何文件')
path_txt.place(relx=0.119, rely=0.86, relwidth=0.75, relheight=0.1)

# 添加按钮
add_btn = tk.Button(win, text='添加点', bg='#87CEFA', command=addpoints)
add_btn.place(relx=0.4, rely=0.03, relwidth=0.08, relheight=0.05)

# 删除按钮
del_btn = tk.Button(win, text='删除点', bg='#87CEFA', command=delpoints)
del_btn.place(relx=0.5, rely=0.03, relwidth=0.08, relheight=0.05)

# 创建一个IntVar变量来踪选择
var = tk.IntVar()
var.set(1)

# 创建单选按钮
radio1 = tk.Radiobutton(win, text="全屏", variable=var, value=1, command=change_bg)
radio2 = tk.Radiobutton(win, text="半屏", variable=var, value=2, command=change_bg)
radio1.place(relx=0.6, rely=0.03, relwidth=0.06, relheight=0.05)
radio2.place(relx=0.65, rely=0.03, relwidth=0.06, relheight=0.05)

# 绘制按钮
draw_btn = tk.Button(win, text='绘制', bg='#87CEFA', command=drawpoints)
draw_btn.place(relx=0.88, rely=0.86, relwidth=0.08, relheight=0.05)

# 模拟说明的label文本
# imitate_lb = tk.Label(win, text=' 模拟速度与实际有偏差，\n每段线路最好保持6s以上', bg="#c0c0c0")   # anchor="w"向西/左对齐
# imitate_lb.place(relx=0.87, rely=0.38, relwidth=0.12, relheight=0.1)

# 模拟时长的label文本
imitate_time_lb = tk.Label(win, text='实际模拟时长：\n', bg="#c0c0c0", anchor="n")   # anchor="w"向西/左对齐
imitate_time_lb.place(relx=0.87, rely=0.62, relwidth=0.12, relheight=0.1)

# 大鱼模拟按钮
big_imitate_btn = tk.Button(win, text='模拟(大鱼)', bg='#cc4125', command=big_imitate)
big_imitate_btn.place(relx=0.88, rely=0.48, relwidth=0.08, relheight=0.05)

# 小鱼模拟按钮
small_imitate_btn = tk.Button(win, text='模拟(小鱼)', bg='#f1c232', command=small_imitate)
small_imitate_btn.place(relx=0.88, rely=0.55, relwidth=0.08, relheight=0.05)

# ��放matplotlib画板
frame2 = tk.Frame(win, bg="#808080")
frame2.place(relx=0.12, rely=0.1, relwidth=0.75, relheight=0.75)

# 刷新窗口（win、frame可以获取真实宽高，而不是初始值1）
win.update()
# 调用控件模块
mat_figure.figure_main(path_txt, frame2)

# 进入消息循环
win.mainloop()
