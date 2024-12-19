"""
备注（一些经历，历史总结就留着参考了）：
2-8和11都是一个问题，最后解决方法在11。所有问题都解决了，就是时长稍微有点误差，时间越短误差越大，因为保持动画流畅，保持了最少绘点数量。
1、现在是汇总时间，然后模拟的速度是 总路程 / 总时间；后面要将每一段按自己单独的时间运行
2、解决模拟期间，插入其他操作包括增加删除点、移动点、绘制，或者重复模拟，介入其他操作时，中断当前的模拟，目前解决方案是模拟由开启和关闭线程控制
3、线程比较麻烦，学到的是循环执行函数，需要关闭时将循环判断的值改为False，如果是单个运行的函数，无法终止（学习例子：线程例子.py）
4、改变思路，动画循环期间，flag设置为False时候终止（return）函数，但要重置参数，避免下次执行有误
5、西八，return也会执行，点多几次模拟就卡的飞起，还是得根源上解决问题
6、思路来了，更新函数的执行由生成器（frames）控制，计时return也会执行那么多次，那么从frames控制次数即可
7、问题又来了，上面方法都是没让动画停止下来，在不断执行模拟函数时候，插入新任务后导致png序列不对（动画不对），原因是鱼动画设置了循环！
8、解决办法，将鱼动画的循环设置为参数，在指定环境下设置为False（不循环了）。不行，运行中修改参数的值，并不会生效。
    用fish_ani.event_source.stop()，但是重置模拟reset_imitate不知道为什么使用了全局参数 还提示未定义fish_ani，
    不管了，只要不是模拟期间再点模拟就不会有问题。figure做个弹窗提示
9、明天解决第1个问题，然后结案。新思路，在生成器里面根据time数组做迭代！-不行改不了interval时间间隔，它是生成时候就设定了的，也是不能中途改。
    根据各段的点数和时间for循环 生成move_ani = animation.FuncAnimation，也是不行。只会执行第一段，其他被销毁并警告
    递归吧，第一个move_ani绘制最后一个点时候，如果总线路还有点那就继续绘制下一段.
10、最后的问题，时间太长时候，刷新率低（因为点数太少），看上去一卡一卡的往前走。感觉在这边根据需求重绘贝塞尔曲线更好（可以根据时间频率设定多少个点）
    未解决，确定了点数多会丝滑一点，但是时间误差更大，因为耗能更多了。
    animation.FuncAnimation是单线程，跟其他任务一起执行，也不擅长渲染，导致效率低刷新率不准确。可以考虑用线程执行画图，提高效率。
    其他替代品：pyqtgraph、okeh库或者Plotly库。pygame
    线程：将两个动画放线程里面，和单独放move到线程里面，都没有提高效率。还是得根据时间频率设定多少个点
    思路：频率固定80ms，时间如10s，需要绘制/更新：10000/80=125个点/次。1000/80=12.5  1/125=0.008  1/12.5=0.08  1/12=0.08333
        1/13=0.07692， 最小时间为1s,但是需要绘制12.5个点，最好保持整数。例如50/100ms
        频率固定50ms，时间如10s，需要绘制/更新：10000/50=200个点/次。1000/50=20  1/200=0.005  1/20=0.05
        结果：OK了，效果很棒，保持最少绘点25个，保证动画流畅。绘制点数 = 时间 / 固定频率 / 2 这样效果会好一点，误差也可以接受。
11、包括不能重复点击【模拟】的问题，其他按钮调用stop_imitate/reset_imitate能停fish动画的循环，但是【模拟】就中断不了
    原因：重复点模拟，也会reset，需要等待鱼动画的frames_generator生效才能停掉动画，但是在frames_generator生效前，下一个动画已经又执行了
    解决了问题8的未定义fish_ani，必须在生成函数后调用，除非全局定义时为None（否则都是未定义），重复模拟会有点卡，至少不会卡帧
12、frame_stop（跟event_source.stop()应该有区别，保留）、is_running（已删除）和frames_generator（保留学习）
    代码写的不太好但不整理了
2024/4/16：
13、使用中，发现是直线时候，动画会回头，即0和-180反复横跳。估计是角度影响，如果发现角度不变，应该不改。
"""
import math
import tkinter.messagebox as mb
import matplotlib.pyplot as plt
from matplotlib import animation, image as mpimg
import numpy as np
from scipy import ndimage
import time

# 贝塞尔点的列表
x_data = []
y_data = []
# 坐标点
p_list = []
# 时间列表
t_list = []
# 图像区域
global fig
global ax
# 动画变量（不赋值不行）
global move_ani
fish_ani = None
# move动画刷新间隔
MOVE_INTERVAL = 50
# 鱼ID对应播放的序列帧
global FISH_ID
# 存放鱼动画的AxesImage对象
FISH_AXES_IMAGE = None
# 当前鱼的png
global FISH_IMAGE
# 鱼动画位置
FISH_POSITION = {
    'left': 0,  # 默认值都是0，如果没有真实坐标是看不到动画的！
    'right': 0,
    'bottom': 0,
    'top': 0,
    'angle': 0.0,  # 旋转角度，让鱼沿着曲线方向移动
}
# 计时器
global start
# 打印label
global time_label
# 停止播放动画
frame_stop = False


# 每次传3个点进来获取贝塞尔的点，dn代表你要画多少个点
def erjie_beisaier(ls, dn):
    x_d = []  # 贝塞尔曲线的全部x
    y_d = []  # 贝塞尔曲线的全部y
    # 3 5 7 9 先判断个数是否合理
    pnum = len(ls)
    if pnum < 3:
        # 数量不对，返回
        mb.showinfo("提示", "顶点数量错误")
        return
    if dn <= 25:   # 默认最少绘制点数（太少会跳着去）
        dn = 25
    for p in range(0, pnum - 1, 2):  # range(start,stop,step)
        for t in np.arange(0, 1, 1/dn):    # 0.01=100个点  0.004=250个点
            # 按1阶原理，p11_t根据t的值从P0走到P1
            p11_t = (1 - t) * ls[p] + t * ls[p + 1]
            # 按1阶原理，p12_t根据t的值从P1走到P2
            p12_t = (1 - t) * ls[p + 1] + t * ls[p + 2]
            # 按1阶原理，p2_t根据t的值从p11_t到p12_t
            p2_t = (1 - t) * p11_t + t * p12_t
            x_d.append(p2_t[0])
            y_d.append(p2_t[1])
    # 把最后一个点也加上
    x_d.append(ls[-1][0])
    y_d.append(ls[-1][1])
    return x_d, y_d


# move动画的初始函数
def init_move():
    # 开始计时
    global start
    start = time.time() * 1000


# 鱼动画的更新函数（根据已有位置和序列帧序号画图片）
def fish_update(frame):  # 帧
    # print(frame)    # float
    global FISH_AXES_IMAGE, FISH_IMAGE
    # 删除之前的图片
    if FISH_AXES_IMAGE is not None:
        FISH_AXES_IMAGE.remove()
    FISH_IMAGE = mpimg.imread(f"res/fish_{str(FISH_ID).zfill(2)}_{str(int(frame)).zfill(2)}.png")
    # print(f"res/fish_{str(FISH_ID).zfill(2)}_{str(int(frame)).zfill(2)}.png")

    # 另一种方法，没实现保留学习
    # img_offset = OffsetImage(FISH_IMAGE, zoom=0.5)
    # FISH_AXES_IMAGE = AnnotationBbox(img_offset, (300, 300))
    # # ax.add_artist(ab)

    # 先转向下个点
    rotated_img = ndimage.rotate(FISH_IMAGE, FISH_POSITION['angle'], order=0)
    rotated_img = (rotated_img * 255).astype(np.uint8)

    # 显示图片（如果不显示，可能是extent的值都是默认0）
    # ax.imshow(FISH_IMAGE)只会处理数据不会显示，需要plt.show()、plt.draw()或ax.figure.canvas.draw()显示
    FISH_AXES_IMAGE = ax.imshow(rotated_img,
                                extent=[FISH_POSITION['left'], FISH_POSITION['right'], FISH_POSITION['bottom'],
                                        FISH_POSITION['top']],
                                animated=True, zorder=999)      # 需要将贝塞尔曲线也设置zorder，这边才会生效

    # 没有实际作用，只是不返回一个 Artist 对象的Iterable，func=fish_update,会报警告：
    # Expected type '(...) -> Iterable[Artist]', got '(frame: Any) -> None' instead
    # return line,
    return ()


# 鱼移动的更新函数（每次更新点的时候都删了当前的图片，又重新画一个） —— 因为刷新率不同，避免更新了几个点，但鱼动画才读取了1个，画面会卡顿掉帧
# 这种方式并不会影响多少时间误差，偏差主要在绘点的数量和刷新率上
def move_update(pnum):  # 帧
    # print(pnum)
    global FISH_AXES_IMAGE, FISH_IMAGE, x_data, y_data, time_label
    if len(x_data) < 1 or FISH_AXES_IMAGE is None:
        return
    # 计算角度（最后一个点时候不变）
    if len(x_data) > 1:
        FISH_POSITION['angle'] = angle(x_data[0], x_data[1], y_data[0], y_data[1])

    # 设定图片中心的坐标
    x_center, y_center = x_data[0], y_data[0]
    x_data.pop(0)
    y_data.pop(0)

    # 删除之前的图片
    if FISH_AXES_IMAGE is not None:
        FISH_AXES_IMAGE.remove()

    # 先转向下个点
    # 为了尽可能减少失真，选择适当的插值方法。参数order设置为0表示使用最邻近插值，1表示使用双线性插值，3表示使用三次样条插值。
    # 设置reshape=False保证输出图像和输入图像大小一致，但是！！导致读取不了旋转了的图片的尺寸，只能读取默认原来的
    rotated_img = ndimage.rotate(FISH_IMAGE, FISH_POSITION['angle'], order=0)
    # Clipping input data to the valid range for imshow with RGB data ([0..1] for floats or [0..255] for integers).
    # 使用 RGB 数据将输入数据剪切到 imshow 的有效范围（对于浮点数为 [0..1]，对于整数为 [0..255]）
    # 解决办法：将图像转换到 np.uint8缩放后 [0, 255] range 将忽略此警告    plt.imshow((out * 255).astype(np.uint8))
    rotated_img = (rotated_img * 255).astype(np.uint8)

    height, width = rotated_img.shape[:2]  # height, width, _ = img.shape
    FISH_POSITION['left'] = x_center - width / 2
    FISH_POSITION['right'] = x_center + width / 2
    FISH_POSITION['bottom'] = y_center - height / 2
    FISH_POSITION['top'] = y_center + height / 2
    # 显示图片
    # left：代表图像的左边界x坐标。right：代表图像的右边界x坐标。bottom：代表图像的底部边界y坐标。top：代表图像的顶部边界y坐标。
    FISH_AXES_IMAGE = ax.imshow(rotated_img,
                                extent=[FISH_POSITION['left'], FISH_POSITION['right'], FISH_POSITION['bottom'],
                                        FISH_POSITION['top']],
                                animated=True, zorder=999)
    # 更新图像的位置
    # FISH_AXES_IMAGE.set_extent([FISH_POSITION['left'], FISH_POSITION['right'], FISH_POSITION['bottom'],
    #                             FISH_POSITION['top']])

    # current = time.time() * 1000
    # print(f'***********当前已运行时间: {int(current - start)}毫秒')

    # 当前分段点已跑完
    if len(x_data) == 1:
        current = time.time() * 1000
        txt = time_label.cget("text") + f'{int(current-start)}毫秒\n'
        time_label.config(text=txt)
        print(f'当前已运行时间: {int(current-start)}毫秒')
        fish_move()

    # 所有点已跑完，打印运行总时长，停止动画，设置状态
    if len(x_data) == 1 and len(t_list) == 0:
        print('本次导航已结束！')
        # 最后一帧停止播放循环的动画
        if fish_ani is not None:
            fish_ani.event_source.stop()

    # 返回是免除警告，没有实际作用
    return ()


# 计算角度
def angle(x0, x1, y0, y1):
    # 对边长度
    dline = x1 - x0
    # 邻边长度
    lline = y1 - y0
    # 使用atan2函数来计算角度的弧度值
    angle_radians = math.atan2(abs(dline), abs(lline))  # math.atan2(对边长度,邻边长度)
    # 将弧度值转换成度
    angle_degrees = math.degrees(angle_radians)
    # 根据象限还原真实角度
    # 第一象限
    if dline > 0 and lline > 0:
        return 180 - angle_degrees
    # 第二象限
    if dline < 0 < lline:
        return 180 + angle_degrees
    # 第三象限
    if dline < 0 and lline < 0:
        return 360 - angle_degrees
    # 第四象限
    return angle_degrees


# 中断模拟并重置数据
def reset_imitate():
    global FISH_AXES_IMAGE, FISH_IMAGE, FISH_POSITION, start, frame_stop, x_data, y_data, t_list, time_label, fish_ani
    x_data = []  # 当前段需要绘制的点
    y_data = []
    # 时间列表
    t_list = []
    # 删除之前的图片
    if FISH_AXES_IMAGE is not None:
        FISH_AXES_IMAGE.remove()
    FISH_AXES_IMAGE = None
    # 当前鱼的png
    FISH_IMAGE = ''
    # 鱼动画位置
    FISH_POSITION = {
        'left': 0,  # 默认值都是0，如果没有真实坐标是看不到动画的！
        'right': 0,
        'bottom': 0,
        'top': 0,
        'angle': 0.0,  # 旋转角度，让鱼沿着曲线方向移动
    }
    # 计时器
    start = 0
    # 关闭动画
    frame_stop = True
    # 这里无法关闭鱼动画的repeat，只好弹窗提示不要再点
    if fish_ani is not None:
        fish_ani.event_source.stop()    # 不明白为什么这里, fish_ani会被判定为 未定义（要在imitate生成了fish_ani之后调用，否则报错）
    # del fish_ani


# 生成器frames（就是动画执行更新函数的次数）
def frames_generator(times):
    global frame_stop, fish_ani
    for i in range(1, times + 1):
        if frame_stop:
            return
        yield i


# 分段根据自己的点数和时间模拟
def fish_move():
    global x_data, y_data, p_list, t_list, move_ani, fig
    if len(t_list) < 1 or len(p_list) < 1:
        return
    # 每段多少个点（erjie_beisaier会有下限值）
    dnum = int(t_list[0] * 1000 / MOVE_INTERVAL / 2)
    x_data, y_data = erjie_beisaier(p_list[:3], dnum)
    print(f'播放时间：{t_list[0]}，绘制点数：{len(x_data)}，刷新率：{MOVE_INTERVAL}毫秒')
    p_list.pop(0)
    p_list.pop(0)
    t_list.pop(0)

    # 鱼在指定时间内跑完贝塞尔曲线的动画
    move_ani = animation.FuncAnimation(
        fig=fig,
        func=move_update,
        # frames=np.linspace(1, len(x_data), num=len(x_data)),  # 这里填写贝塞尔曲线的点数（所需更新的次数），即跑完所有点
        # frames=len(x_data),  # 可以直接这样写
        frames=frames_generator(len(x_data)),
        init_func=init_move(),
        # 用interval算时间的话，不能过小，因为还取决于你代码量和计算机的运行速度，本机设置5ms时候，实际运行20+ms
        # 所以10秒运行200-400个点（interval=50/25） 时长大概多1-2s，但如果运行2000个点（interval=5）时长是46s
        # interval=t * 1000 / dnum,  # 需求：在10秒内将200个点的贝塞尔曲线跑完  刷新频率 = 多久跑1个点 = 10000 / 200 = 50 ，单位：ms
        interval=MOVE_INTERVAL,     # 改成固定刷新率，根据时间/刷新率 去绘制对应点数，适量的点数不至于动画卡顿
        repeat=False,  # 设置重复
        cache_frame_data=False  # 禁用缓存（当frames参数指定为一个生成器函数时，系统在运行时无法预知生成器将会生成多少个帧，
        # 这可能会导致缓存在内存中无限制地增长，所以会禁用帧数据的缓存，并且发出这个警告信息）
    )


# 线路模拟(思路：做两个动画FuncAnimation，一个是播放鱼的序列帧；另一个是将鱼在指定时间内跑完贝塞尔曲线)
def imitate(imitate_time_lb, fishid, frames, figure, axes, pl, runtime):
    global FISH_ID, fig, ax, move_ani, fish_ani, frame_stop, p_list, t_list, time_label
    # 赋值（不加move_ani, fish_ani变量，代码报错不执行）
    FISH_ID = fishid
    fig = figure
    ax = axes
    p_list = pl.copy()
    t_list = runtime.copy()
    frame_stop = False  # 保证开始时，值为False
    time_label = imitate_time_lb
    # 重置一下文本内容
    time_label.config(text='实际模拟时长：\n')

    # 递归方法将分段绘制点（因为动画func的更新函数不能传参，都用了全局）
    fish_move()

    # 鱼序列帧的动画
    fish_ani = animation.FuncAnimation(
        fig=fig,
        func=fish_update,
        # frames=np.linspace(1, frames, num=frames),  # 参数：start=序列的起始值, stop=序列的终止值, num=生成的样本数量,默认值是50
        frames=frames_generator(frames),
        # init_func=init_img(),
        # 鱼的刷新间隔比move间隔大，会丢点，即显示会卡顿（掉帧）
        # 比较好的做法还是在move那更新set点（set时候应该可以及时更新位置吧？）
        interval=80,  # 每隔多少时间生成一帧图像，单位是ms
        repeat=True,  # 设置重复
        cache_frame_data=False
    )
    # 有这句代码才会进入更新函数，而不会弹窗
    plt.draw()

    # 有这句代码才会进入更新函数，但会弹窗
    # plt.show()



