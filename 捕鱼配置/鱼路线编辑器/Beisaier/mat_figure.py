"""
    matplotlib控件绘图
    有点尴尬，参考的PathPatch例子和2阶贝塞尔绘图例子，都是用多维数组，但我感觉可以不用（现在是我参考2阶贝塞尔自己做的）
    两种数组切换不方便，ndarray也不够array好用（可能前者效率更高？）

    重绘时避免旧数据影响画面（axes每次绘制都会将line保存起来）：
    1、每次重绘都是先还原原始的bg（未绘制时的空白背景），但是模拟时候，ax会把所有line都显示出来了
    2、解决上面问题在每次绘制，都将之前的line删除
"""
import tkinter as tk
# 对话框所需的库
import tkinter.messagebox as mb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backend_bases import MouseButton
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import mat_animation

# 计为顶点命中的最大像素距离
epsilon = 10
# 鼠标点击的点
clickpoint = None
# 顶点list
plist = []
# 时间list
tlist = [1]   # 默认第一段路线的时间
# 贝塞尔点的列表
xdata = []
ydata = []
# 全局figure
global fig
# 全局axes
global global_ax
# 全局canvas
global global_canvas
# 全局background(保存未画图时候bg)
global background
# 全局输出路径text
global path_text
# 背景图地址（用于半屏全屏切换）
global bg_addr


# 绘制贝塞尔曲线
def draw_erjie_beisaier(ls):
    global xdata, ydata, global_ax
    xdata = []  # 贝塞尔曲线的全部x
    ydata = []  # 贝塞尔曲线的全部y
    # 3 5 7 9 先判断个数是否合理
    pnum = len(ls)
    if (pnum - 3) % 2 != 0:
        # 数量不对，返回
        mb.showinfo("提示", "顶点数量错误")
        return
    for p in range(0, pnum - 1, 2):  # range(start,stop,step)
        for t in np.arange(0, 1, 0.01):    # 0.01=100个点  0.004=250个点
            # 按1阶原理，p11_t根据t的值从P0走到P1
            p11_t = (1 - t) * ls[p] + t * ls[p + 1]
            # 按1阶原理，p12_t根据t的值从P1走到P2
            p12_t = (1 - t) * ls[p + 1] + t * ls[p + 2]
            # 按1阶原理，p2_t根据t的值从p11_t到p12_t
            p2_t = (1 - t) * p11_t + t * p12_t
            xdata.append(p2_t[0])
            ydata.append(p2_t[1])
    # print(type(global_ax.lines))
    # print(len(global_ax.lines))
    # axes对象的lines属性会保存绘图时产生的所有线。如果你希望删除axes对象上所有的线，可以遍历ArtistList，使用remove方法逐一删除
    # 先将ax之前绘制的line删除
    if len(global_ax.lines) > 1:
        for l in global_ax.lines:
            l.remove()
    # 画出贝塞尔曲线
    line, = global_ax.plot(xdata, ydata, 'k', zorder=2)  # plt.plot(x, y, 'g')   ax/plt都可以画 , animated=True
    global_ax.draw_artist(line)


# 绘制顺序顶点连线
def draw_verts_line(ls):
    pnum = len(ls)
    if (pnum - 3) % 2 != 0:
        # 数量不对，返回
        return
    x, y = zip(*ls)
    line, = global_ax.plot(x, y, 'g', marker='o', markerfacecolor='r')
    global_ax.draw_artist(line)


# 添加顶点
def add_point():
    global plist, global_ax
    # 重新绘制（将输入框的内容读取）
    draw_point()
    x, y = plist[-1]
    plist.append(np.array([x + 50, y]))
    plist.append(np.array([x + 50, y + 50]))
    tlist.append(1)
    # 画出贝塞尔曲线
    draw_erjie_beisaier(plist)
    # 按顺序画出顶点连线
    draw_verts_line(plist)
    # 将结果显示到屏幕上
    global_canvas.blit(global_ax.bbox)
    # 打印路径顶点到text
    print_path()


# 删除顶点
def del_point():
    global plist, global_ax, tlist
    # 重新绘制（将输入框的内容读取）
    draw_point()
    # 小于等于3个点时候不能删
    if len(plist) <= 3:
        mb.showinfo("提示", "删除失败，最少保留3个点")
        return
    plist = plist[:-2]
    tlist = tlist[:-1]
    # 还原背景
    global_canvas.restore_region(background)
    # 画出贝塞尔曲线
    draw_erjie_beisaier(plist)
    # 按顺序画出顶点连线
    draw_verts_line(plist)
    # 将结果显示到屏幕上
    global_canvas.blit(global_ax.bbox)
    # 打印路径顶点到text
    print_path()


# 根据路径text内容重绘曲线
def draw_point():
    global plist, global_ax, path_text, tlist
    # 先停掉模拟
    stop_imitate()
    tlist = []
    contents = path_text.get('1.0', tk.END)  # <class 'str'> '[[100,600,300,300,600,100,1]]'
    # 删除多余格式
    # 100,600,300,300,600,100,1,1200,200,800,300,1
    contents = contents.replace('[', '').replace(']', '').replace('\n', '')
    try:
        # 将str类型转换为ndarray型的数据
        # contents = '100,600,300,300,600,100,800,300'
        # l = np.fromstring(contents, dtype=int, sep=',').reshape(-1, 2)  # reshape将1维6列(不指定行,2列)  如果是(3,2)代表3行2列
        """
        100,600,300,300,600,100,800,300在np.fromstring和reshape之后：
        [[100 600]
         [300 300]
         [600 100]
         [800 300]]
        """
        # 上面是字符串变为二维数组，这里改为一维数组变为二维数组
        cl = contents.split(',')    # [100,600,300,300,600,100,1,1200,200,800,300,1]
        n = len(cl)  # 7 12 17 22 这些位置都是时间
        # 直接从后面往前pop
        while n >= 7:
            # 把时间都收集到time列表
            tlist.insert(0, int(cl[n - 1]))   # 按顺序排放
            # 再从数组里删除时间元素
            cl.pop(n - 1)
            n = n - 5
        # cl=['100', '600', '300', '300', '600', '100', '1225', '-21', '1445', '434', '1200', '200', '800', '300']
        l = np.array(cl).astype('int').reshape(-1, 2)
        # print(l)
    except Exception as e:
        print("输入格式错误，转换不了ndarray：")
        print(e)
        mb.showinfo("提示", "输入格式错误")
        return
    if (len(l) - 3) % 2 != 0:
        # 数量不对，返回
        mb.showinfo("提示", "顶点数量或输入格式有误")
        return
    # l:<class 'numpy.ndarray'>  plist:<class 'list'>  所以不能直接赋值plist = l
    plist.clear()
    for p in l:
        plist.append(p)
    # 还原背景
    global_canvas.restore_region(background)
    # 画出贝塞尔曲线
    draw_erjie_beisaier(plist)
    # 按顺序画出顶点连线
    draw_verts_line(plist)
    # 将结果显示到屏幕上
    global_canvas.blit(global_ax.bbox)
    # 打印路径顶点到text
    print_path()


# 除指定字符
def delete_char(string, position):
    if len(string) > position >= 0:
        new_str = string[:position] + string[position + 1:]
        return new_str
    else:
        print("Invalid position")


# text框打印路径
def print_path():
    global plist
    # 先清空text文本
    path_text.delete('1.0', 'end')
    # 文本框输出顶点信息
    """ 修改导出格式：
    {{1193,609,750,616,628,392,4},{544,235,413,205,2},{160,141,-56,-20,4}} 
    大括号相当于中括号，导出时候是数组。
    list[0]={1193,609,750,616,628,392,4} 代表3个点，画2阶贝塞尔，4代表该线路的行走时间
    list[1]={544,235,413,205,2} 结合前一个点(628,392)，画2阶贝塞尔，2代表该段线路的行走时间
    """
    points_list = np.array(plist).tolist()  # [[100, 600], [260, 247], [600, 100], [1200, 200], [800, 300]]
    list_len = len(points_list)
    points_str = ''
    start = 0
    end = 3
    num = 1  # 段数，用于判断第几个time
    while end <= list_len:
        points_str = print_format(points_list[start:end], points_str, num)
        start = end
        end += 2
        num += 1
    # print(points_str)
    path_text.insert(tk.INSERT, '[' + points_str + ']')


def print_format(ls, s, n):
    if len(ls) == 3:
        s = ''.join([s, '['])
    else:
        s = ''.join([s, ',['])
    for pp in ls:
        for p in pp:
            s = ''.join([s, str(p) + ','])
    # 把时间加入每一段的末尾
    s = ''.join([s, str(tlist[n - 1]) + ']'])
    return s


# 线路模拟
def imitate(imitate_time_lb, fishid, frames):
    # 上一次模拟未完成，不能再点击模拟（解除了，虽然重复绘制会有点卡）
    # if mat_animation.is_running:
    #     mb.showinfo("提示", "正在模拟，可以进行其他操作，但不能同时模拟多个")
    #     return
    # 重新绘制（将输入框的内容读取）
    draw_point()
    mat_animation.imitate(imitate_time_lb, fishid, frames, fig, global_ax, plist, tlist)


# 停止模拟
def stop_imitate():
    if not mat_animation.frame_stop:    # 值为true代表重置过，那就没必要再重置
        mat_animation.reset_imitate()


# 根据半屏和全屏更换背景图
def changebg(bg):
    global background, global_canvas, global_ax, plist
    if bg == 2:
        addr = 'res/bgm.png'
    else:
        addr = 'res/bg.png'
    img = mpimg.imread(addr)
    original_size = img.shape
    global_ax.images[0].set_data(img)   # 此处不用再翻转
    global_ax.images[0].set_extent([0, original_size[1], 0, original_size[0]])  # 设置新背景图的范围

    # 清除之前的图形对象（如果用此方法，会将ax在figure_main()中其他设置也清除了）
    # global_ax.clear()

    # 删除之前的曲线
    for line in global_ax.lines:
        line.remove()

    fig.canvas.draw_idle()

    # 更新画布上的背景图
    global_canvas.draw()
    global_canvas.blit(global_ax.bbox)

    # 重新保存背景
    background = global_canvas.copy_from_bbox(global_ax.bbox)

    # 画出贝塞尔曲线（当前）
    draw_erjie_beisaier(plist)
    # 按顺序画出顶点连线
    draw_verts_line(plist)


# 按下鼠标（根据点击位置获取顶点）
def on_button_press(event):
    global clickpoint
    if (event.inaxes is None
            or event.button != MouseButton.LEFT):
        return
    info = {'index': None, 'distance': None}
    for i in range(len(plist)):
        d = np.sqrt((plist[i][0] - event.xdata) ** 2 + (plist[i][1] - event.ydata) ** 2)
        # 先判断距离是否超限
        if d > epsilon:
            continue
        # 第一次填充
        if info['index'] is None:
            info['index'] = i
            info['distance'] = d
        # 距离更短
        elif d < info['distance']:
            info['index'] = i
            info['distance'] = d
    clickpoint = info['index']
    # if clickpoint is not None:
    #     print('on_button_press:')
    #     print(clickpoint)
    #     print(np.array(plist[clickpoint], dtype=np.int16).tolist())


# 释放鼠标（松开左键，释放顶点 None）
def on_button_release(event):
    global clickpoint
    if event.button != MouseButton.LEFT:
        return
    clickpoint = None
    # print('on_button_release')
    # print(clickpoint)


# 移动鼠标（只要在画布内移动鼠标都会调用，只是绝大部分都是return而已）
def on_mouse_move(event):
    global clickpoint, global_canvas, background
    if (clickpoint is None
            or event.inaxes is None
            or event.button != MouseButton.LEFT):
        return
    # 重新绘制（将输入框的内容读取）
    draw_point()
    # 移动时候鼠标的坐标点 更新到 之前选中的点
    plist[clickpoint][0] = int(event.xdata)
    plist[clickpoint][1] = int(event.ydata)
    # print(np.array(plist[clickpoint]).tolist())
    # print(np.array(plist).tolist())
    # 先还原背景（不含贝塞尔曲线和顶点连线）
    global_canvas.restore_region(background)
    # 画出贝塞尔曲线
    draw_erjie_beisaier(plist)
    # bl.set_data(zip(*plist))  # 另一种方式，将plot返回的line，set了新点，然后再draw_artist
    # print(bl.get_path())
    # axes.draw_artist(bl)
    # 按顺序画出顶点连线
    draw_verts_line(plist)
    # 将结果显示到屏幕上
    global_canvas.blit(global_ax.bbox)
    # 打印路径顶点到text
    print_path()


def figure_main(ptext, frame):
    # contents = ptext.get('1.0', tk.END)
    # print(contents)
    global global_ax, global_canvas, background, path_text, fig
    # 将figure设置为frame大小
    width = frame.winfo_width() / 100
    height = frame.winfo_height() / 100
    # 创建整个图形窗口
    fig = plt.figure(figsize=(width, height), dpi=100, facecolor='beige')  # 米黄色
    # 创建绘图区域
    global_ax = fig.subplots()
    # Windows系统中，常用中文默认字体'SimHei'
    plt.rcParams['font.sans-serif'] = ['SimHei']
    # 用来正常显示负号
    plt.rcParams['axes.unicode_minus'] = False
    # Axes的标题
    global_ax.set_title('拖拽红点调整线路，模拟时长有偏差属于正常', fontsize=10)
    # Axes的横坐标
    global_ax.set_xlim(-200, 1534)
    # 这里设置了从-200到1534，间距为50的刻度
    global_ax.set_xticks(range(-200, 1535, 100))
    # Axes的纵坐标
    global_ax.set_ylim(-200, 900)
    # 这里设置了间距为50的刻度
    global_ax.set_yticks(range(-200, 900, 100))
    # 添加背景图
    img = mpimg.imread('res/bg.png')
    # 图片上下翻转
    plt.imshow(img[::-1])
    # plt.imshow(img)
    # 中间件映射
    global_canvas = FigureCanvasTkAgg(fig, frame)  # 将图表对象和Tkinter窗口关联起来
    # 中间件draw到Figure上的图
    global_canvas.draw()  # 将绘图命令应用于画布并将其更新
    # 获取到中间件上的图，并且pack到UI组件frame上
    global_canvas.get_tk_widget().pack()  # get_tk_widget()方法获取Tkinter的绘图窗口，并使用pack()方法将其放置在Tkinter窗口中
    # 层级应该是frame->canvas-?>fig->ax

    # 初始化3个点
    p0 = np.array([100, 600])
    p1 = np.array([300, 300])
    p2 = np.array([600, 100])
    plist.append(p0)
    plist.append(p1)
    plist.append(p2)
    # 获得默认背景
    # Axes.bbox是一个属性，用于获取表示Axes对象边界框的Bounding Box（bbox）。Bounding Box是一个矩形区域，包围了Axes对象的内容，包括坐标轴、图表、标签等
    background = global_canvas.copy_from_bbox(global_ax.bbox)  # canvas.copy_from_bbox()方法从指定的bbox区域复制像素数据到画布中
    # 画出贝塞尔曲线
    draw_erjie_beisaier(plist)

    # canvas.restore_region()方法允许你从后备缓冲区中恢复之前保存的特定区域，以便在需要时重新绘制该区域，而无需重新绘制整个图形
    # canvas.restore_region(bg)
    #  blit() 方法来更新显示的内容，而不必重新绘制整个图形，提高图形的显示效率
    # canvas.blit(ax.bbox)

    # Axes.draw_artist() 方法用于绘制指定的艺术家（Artist）对象。艺术家对象包括图形中的各种元素，如线条、文本、图像等。
    # 通过调用Axes.draw_artist() 方法，可以只重新绘制指定的艺术家对象，而不必重新绘制整个图形
    # 例如：line=ax.plot(x,y)，ax.plot(x, y_new) 是绘制了2条线，如果ax.draw_artist(line)就是重绘line这条线

    # 按顺序画出顶点连线
    draw_verts_line(plist)
    # 绑定事件（本来是交互都放在一个类，然后传入ax，由axes.figure.canvas绑定事件，可能是2个Canvas导致self会乱，无法触发self事件）
    global_canvas.mpl_connect('button_press_event', lambda event: on_button_press(event))  # 按下鼠标
    global_canvas.mpl_connect('button_release_event', lambda event: on_button_release(event))  # 释放鼠标
    global_canvas.mpl_connect('motion_notify_event', lambda event: on_mouse_move(event))  # 鼠标移动

    # 打印路径顶点到text
    path_text = ptext
    print_path()

    # 会单独显示figure界面
    # plt.show()

