str1 = '1193,609,750,616,628,392,time=4.0,544,235,413,205,time=2.0,160,141,-56,-20,time=4.0'


def kill_time():
    global str1
    start = str1.find('t')
    if start == -1:
        return
    end = str1.find(',', start)
    if end == -1:
        re_str = str1[start - 1:]
    else:
        re_str = str1[start - 1:end]
    str1 = str1.replace(re_str, '')
    if str1.find('t') != -1:
        kill_time()


kill_time()
str_list = str1.split(',')
road = ''
for i in range(0, len(str_list), 2):
    road = ''.join([road, '{' + str_list[i] + ' ' + str_list[i + 1] + '} '])

print(road)
