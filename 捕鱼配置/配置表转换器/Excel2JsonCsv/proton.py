# encoding=utf-8
'''
Copyright YANG Huan (sy.yanghuan@gmail.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import sys

if sys.version_info < (3, 0):
    print('python version need more than 3.x')
    sys.exit(1)

import os
import string
import collections
import codecs
import getopt
import re
import json
import traceback
import multiprocessing
import xml.etree.ElementTree as ElementTree
import xml.dom.minidom as minidom
import sxl
import pandas as pd
import logging

# 配置日志记录
logging.basicConfig(filename='export_log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 添加初始日志记录以确认代码执行
logging.info("开始导出流程...")


# 将数据填入parent（exportitemsheet-item）OrderedDict对象中
def fillvalue(parent, name, value, isschema):
    if isinstance(parent, list):  # 如果parent是数组，就appendvalue进去
        parent.append(value)
    else:  # 如果parent是有序字典，就parent[name] = value
        if isschema and not re.match(r'^_|[a-zA-Z]\w*$', name):
            raise ValueError('%s is a illegal identifier' % name)
        # 就执行这句
        parent[name] = value


def getindex(infos, name):
    return next((i for i, j in enumerate(infos) if j == name), -1)


def getcellvalue(value):
    return str(value) if value is not None else ''


def getscemainfo(typename, description):
    if isinstance(typename, BindType):
        typename = typename.typename
    return [typename, description] if description else [typename]


def getexportmark(sheetName):
    p = re.search(r'\|[' + string.whitespace + r']*(_|[a-zA-Z]\w+)', sheetName)
    return p.group(1) if p else False


def issignmatch(signarg, sign):
    if signarg is None:
        return True
    return True if [s for s in re.split(r'[/\\, :]', sign) if s in signarg] else False


def isoutofdate(srcfile, tarfile):
    return not os.path.isfile(tarfile) or os.path.getmtime(srcfile) > os.path.getmtime(tarfile)


def gerexportfilename(root, format_, folder):
    filename = root + '.' + format_
    return os.path.join(folder, filename)


def splitspace(s):  # s: 'int Id'
    return re.split(r'[' + string.whitespace + r']+', s.strip())


def buildbasexml(parent, name, value):
    value = str(value)
    if parent.tag == name + 's':
        element = ElementTree.Element(name)
        element.text = value
        parent.append(element)
    else:
        parent.set(name, value)


def buildlistxml(parent, name, list_):
    element = ElementTree.Element(name)
    parent.append(element)
    for v in list_:
        buildxml(element, name[:-1], v)


def buildobjxml(parent, name, obj):
    element = ElementTree.Element(name)
    parent.append(element)

    for k, v in obj.items():
        buildxml(element, k, v)


def buildxml(parent, name, value):
    if isinstance(value, int) or isinstance(value, float) or isinstance(value, str):
        buildbasexml(parent, name, value)

    elif isinstance(value, list):
        buildlistxml(parent, name, value)

    elif isinstance(value, dict):
        buildobjxml(parent, name, value)


def savexml(record):
    book = ElementTree.ElementTree()
    book.append = lambda e: book._setroot(e)
    buildxml(book, record.root, record.obj)

    xmlstr = ElementTree.tostring(book.getroot(), 'utf-8')
    dom = minidom.parseString(xmlstr)
    with codecs.open(record.exportfile, 'w', 'utf-8') as f:
        dom.writexml(f, '', '  ', '\n', 'utf-8')

    print('save %s from %s in %s' % (record.exportfile, record.sheet.name, record.path))


def newline(count):
    return '\n' + '  ' * count


def tolua(obj, indent=1):
    if isinstance(obj, int) or isinstance(obj, float) or isinstance(obj, str):
        yield json.dumps(obj, ensure_ascii=False)
    else:
        yield '{'
        islist = isinstance(obj, list)
        isfirst = True
        for i in obj:
            if isfirst:
                isfirst = False
            else:
                yield ','
            yield newline(indent)
            if not islist:
                k = i
                i = obj[k]
                yield k
                yield ' = '
            for part in tolua(i, indent + 1):
                yield part
        yield newline(indent - 1)
        yield '}'


def toycl(obj, indent=0):
    islist = isinstance(obj, list)
    for i in obj:
        yield newline(indent)
        if not islist:
            k = i
            i = obj[k]
            yield k
        if isinstance(i, int) or isinstance(i, float) or isinstance(i, str):
            if not islist:
                yield ' = '
            yield json.dumps(i, ensure_ascii=False)
        else:
            if not islist:
                yield ' '
            yield '{'
            for part in toycl(i, indent + 1):
                yield part
            yield newline(indent)
            yield '}'


class BindType:
    def __init__(self, type_):
        self.typename = type_

    def __eq__(self, other):
        return self.typename == other


class Record:
    def __init__(self, path, sheet, exportfile, root, item, obj, exportmark):
        self.path = path  # 'G:/work/tools/Excel2Json/hero222.xlsx'
        self.sheet = sheet  # <sxl.sxl.Worksheet object at 0x000001F926AF7A50>
        self.exportfile = exportfile  # 'G:/work/tools/Excel2Json/导出JSON/client\\HerosTemplate.json'
        self.root = root  # 'HerosTemplate'
        self.item = item  # 'Hero'
        self.setobj(obj)  # obj:(OrderedDict(), [OrderedDict([('Id', 1), ('Name', '奥丁'), ('Weapons', [1001])]),
        # OrderedDict([('Id', 2), ('Name', '托尔'), ('Weapons', [1003, 1004, 1005])])])
        self.exportmark = exportmark  # 'Hero'

    def setobj(self, obj):
        self.schema = obj[0] if obj else None
        self.obj = obj[1] if obj else None


class Constraint:
    def __init__(self, mark, filed):
        self.mark = mark
        self.field = filed


# 2024/5/15:将新类型改为已有类型
def reset_type_value(value):
    num = value.count("=")
    value_copy = value.replace(" ", "")
    tlist = []
    # [Id=10001,Count=10,Time=60]
    for i in range(num):
        if len(tlist) == 0:
            idx1 = 1
        else:
            idx1 = 0
        idx2 = value_copy.find("=")
        t = value_copy[idx1:idx2]
        tlist.append(t)  # 添加到数组的末尾，所以顺序没错
        value_copy = value_copy[value_copy.find(",") + 1:]
    type_ = "{"
    for idx, t in enumerate(tlist):
        value = value.replace(t, "").replace("=", "")
        # 最后一次循环
        if idx == len(tlist) - 1:
            s = "}"
        else:
            s = ","
        type_ = type_ + "int " + t + s
    return type_, value


def reset_type_values(value):
    value = value.replace('],[', '];[')
    valuelist = value[1:-1].split(';')  # ['[Id=10001,Count=10]', '[Id=10002,Count=20]', '[Id=10003,Count=30]']
    value, type_ = '[', ''
    for idx, v in enumerate(valuelist):
        val = reset_type_value(v)[1]
        # 最后一次循环
        if idx == len(valuelist) - 1:
            type_ = reset_type_value(v)[0] + '[]'
            s = "]"
        else:
            s = ","
        value += val + s
        # print(value)  # [[10001,10],[10002,20],[10003,30]]  <class 'str'>
        # print(type_)  # {int Id,int Count}[]
    return type_, value


class Exporter:
    configsheettitles = ('name', 'value', 'type', 'sign', 'description')
    spacemaxrowcount = 3

    def __init__(self, context):
        self.context = context
        self.records = []

    def checkstringescape(self, t, v):
        return v if not v or not 'string' in t else v.replace('\\n', '\n').replace('\\,', '\0').replace(
            '\\' + self.context.objseparator, '\a')

    def stringescape(self, s):
        return s.replace('\0', ',').replace('\a', self.context.objseparator)

    """
    2024/2/20 重新整理：
    序号	类型	字段名称	字段内容	备注
    1	int	id	1	
    2	float	weight	20.5
    3	string	name	奥丁	
    4	int[]	weapon	[1001,1002]	 一维数组
    5	int[][]	weapons	[[1001,1002],[1005]]  二维数组
    6	{int Id,int Count}	bag	[10001,10]	一个对象
    7	{int Id,int Count}[]	bags [[10001,10],[10002,20]]  对象数组

    2024/5/15 新增（代替6和7）：
    8   obj  award   [Id=10001,Count=10]     一个对象
    9   obj[] awards  [[Id=10001,Count=10],[Id=10002,Count=20]]   对象数组
    PS：6和7字段固定了。8和9key可以为Id，也可以为其他，同字段下可以不同数量的键值对总扩展更好，值默认int即可
        尽量新增，而不改变之前已有的类型
    """

    # 根据设定获取字段的类型，例如：将'xxx[]'或'xxx[][]'判为'list'、'{xxx}'判为'obj'
    def gettype(self, type_):  # 对象数组：'{int Id;int Count}[]'
        if type_[-2] == '[' and type_[-1] == ']':
            return 'list'
        if type_[0] == '{' and type_[-1] == '}':  # 对象数组:'{int Id;int Count}'。第一次发现是list时候basetype = type_[:-2]已经去掉了[]
            return 'obj'
        if type_ in ('int', 'double', 'string', 'bool', 'long', 'float'):
            return type_

        p = re.search(r'(int|string|long)[' + string.whitespace + r']*\((\S+)\.(\S+)\)', type_)
        if p:
            type_ = BindType(p.group(1))
            type_.mark = p.group(2)
            type_.field = p.group(3)
            return type_

        raise ValueError('%s is not a legal type' % type_)

    # 建表list
    def buildlistexpress(self, parent, type_, name, value, isschema):
        # 是否符合格式，否则导出失败
        if value[0] != '[' or value[-1] != ']':
            raise Exception('配置数组必须外包[]，错误值： %s' % value)

        basetype = type_[:-2]  # 对象数组：'{int Id;int Count}'   一维数组：'int'  二维数组：'int[]'
        
        # 添加对空数组的处理
        if value == '[]':
            fillvalue(parent, name, [], isschema)
            return
        
        # 对象数组，跳转buildobjexpress处理
        if self.gettype(basetype) == 'obj':
            self.buildobjexpress(parent, type_, name, value, isschema)
        else:
            list_ = []
            if self.gettype(basetype) == 'list':
                # 二维数组
                value = value.replace('],[', '];[')
                valuelist = value[1:-1].split(';')  # ['[101,102]', '[103]']
                for v in valuelist:
                    self.buildlistexpress(list_, basetype, name, v, isschema)
            else:
                valuelist = value.strip('[]').split(',')
                # 添加对空字符串的处理
                if valuelist == ['']:
                    valuelist = []
                for v in valuelist:
                    self.buildexpress(list_, basetype, name, v)
            fillvalue(parent, name, list_, isschema)

    # 建表obj
    def buildobjexpress(self, parent, type_, name, value, isschema):
        # type_: '{int Id,int Count}[]'  name='bag'  value='10001,10' parent:[]
        # 是否符合格式，否则导出失败
        if value[0] != '[' or value[-1] != ']':
            raise Exception('配置数组必须外包[]，错误： %s' % value)

        list_ = []
        # 创建一个字典对象，和普通的字典不同，OrderedDict字典会记住插入键值对的顺序
        obj = collections.OrderedDict()
        # if value.find('],[') != -1:
        if self.gettype(type_) == 'list':
            # 二维数组
            value = value.replace('],[', '];[')
            valuelist = value[1:-1].split(';')  # ['[10001,10]', '[10002,100]']
            for v in valuelist:
                self.buildobjexpress(list_, type_[:-2], name, v, isschema)
            # 数组用list_
            fillvalue(parent, name, list_, isschema)
        else:
            # obj = collections.OrderedDict()
            # 字段名类型（对象类型数组）：['int Id', 'int Count']
            fieldnamestypes = type_.strip('{}').split(self.context.objseparator)

            fieldValues = value.strip('[]').split(self.context.objseparator)  # ['10001', '10']
            for i in range(0, len(fieldnamestypes)):
                if i < len(fieldValues):
                    fieldtype, fieldname = splitspace(fieldnamestypes[i])  # fieltype='int'  fieldname='Id'
                    self.buildexpress(obj, fieldtype, fieldname, fieldValues[i])
            # 单对象用obj（看好parent是谁）
            fillvalue(parent, name, obj, isschema)

    # 建表base
    def buildbasexpress(self, parent, type_, name, value, isschema):
        # parent: OrderedDict() / []    OrderedDict继承自dict，位于collections包，是有顺序的字典，它可以维护添加key-value对的顺序
        typename = self.gettype(type_)  # 'int', 'string'
        if isschema:
            value = getscemainfo(typename, value)
        else:
            if typename != 'string' and value.isspace():
                return

            if typename == 'int' or typename == 'long':
                # 修改起因Excel公式=0.3*0.7*10000=21000被读取为20999.999，导出为20999
                # 2024/5/16:之前盲目+0.1，导致负数有误,例如：-5导出为-4
                # print("before:" + value)
                # 将字符串转换为浮点数
                float_value = float(value)
                # 向上取整（浮点数自动向下取整的特性，然后通过判断小数部分是否大于 0 来确定是否需要加一）
                if float_value >= 0:
                    value = int(float_value) + (float_value > int(float_value))
                else:
                    value = int(float_value) - (float_value < int(float_value))

                # value = int(math.ceil(float(value)))     # 不想再导入包导致包体变大
                # value = int(float(value))     # 原代码
                # print("after:", value)
            elif typename == 'double' or typename == 'float':
                value = float(value)
            elif typename == 'string':
                if value.endswith('.0'):  # may read is like "123.0"
                    try:
                        value = str(int(float(value)))
                    except ValueError:
                        value = self.stringescape(str(value))
                else:
                    value = self.stringescape(str(value))
            elif typename == 'bool':
                try:
                    value = int(float(value))
                    value = False if value == 0 else True
                except ValueError:
                    value = value.lower()
                    if value in ('false', 'no', 'off'):
                        value = False
                    elif value in ('true', 'yes', 'on'):
                        value = True
                    else:
                        raise ValueError('%s is a illegal bool value' % value)
        # 将数据填入parent（exportitemsheet-item）OrderedDict对象中
        fillvalue(parent, name, value, isschema)

    # 建表导航（list、obj、base）
    def buildexpress(self, parent, type_, name, value, isschema=False):
        # 根据设定获取字段的类，例如：将'xxx[]'或'xxx[][]'判为'list'、'{xxx}'判为'obj'
        # 20240515：新增类型obj 和 obj[]
        typename = self.gettype(type_)  # 'int' / 'string' / 'list'
        if typename == 'list':
            # list 调用 buildlistexpress，里将字符串 拆分为 单独的 int/string，然后再调用buildexpress。所以最终都是走buildbasexpress。
            self.buildlistexpress(parent, type_, name, value, isschema)
        elif typename == 'obj':
            self.buildobjexpress(parent, type_, name, value, isschema)
        else:
            self.buildbasexpress(parent, type_, name, value, isschema)

    def getrootname(self, exportmark, isitem):
        return exportmark + (self.context.extension or '') if isitem else exportmark + (
                self.context.extension or '')

    # 导出 操作Excel（核心方法）
    def export(self, path):
        self.path = path
        data = sxl.Workbook(self.path)
        cout = None

        for sheetname in [i for i in data.sheets if type(i) is str]:  # sheetname: '英雄|Hero'
            self.sheetname = sheetname
            exportmark = getexportmark(sheetname)  # exportmark: 'Hero'
            if exportmark:
                sheet = data.sheets[
                    sheetname]  # sheet: <sxl.sxl.Worksheet object at 0x000001FD89A6B7D0>  sheet.name='英雄|Hero'
                coutmark = sheetname.endswith('<<')  # coutmark: False
                configtitleinfo = self.getconfigsheetfinfo(sheet)  # configtitleinfo: None
                if not configtitleinfo:
                    root = self.getrootname(exportmark, not coutmark)  # root: 'HerosTemplate'  /  'HerosConfig'
                    item = exportmark  # 'Hero'
                else:
                    root = self.getrootname(exportmark, False)
                    item = None

                if not cout:
                    self.checksheetname(self.path, sheetname, root)
                    # 生成导出文件的名称，exportfile：'G:/work/tools/Excel2Json/导出JSON/client\\HerosTemplate.json'
                    exportfile = gerexportfilename(root, self.context.format, self.context.folder)

                    # 移除时间比较，直接导出
                    if True:  # 每次都导出
                        try:
                            # 导出逻辑
                            if True:  # 每次都导出
                                if item:
                                    exportobj = self.exportitemsheet(sheet)
                                else:
                                    exportobj = self.exportconfigsheet(sheet, configtitleinfo)

                            # 记录导出信息
                            self.records.append(Record(self.path, sheet, exportfile, root, item, exportobj, exportmark))

                            # 打印导出路径
                            print(f"成功导出到: {exportfile}")
                        except Exception as e:
                            print(f"导出过程中发生错误: {e}")

                else:
                    if item:
                        exportobj = self.exportitemsheet(sheet)
                        cout[0][item + 's'] = [[exportobj[0]]]
                        obj = exportobj[1]
                        if obj:
                            cout[1][item + 's'] = obj
                    else:
                        exportobj = self.exportconfigsheet(sheet, configtitleinfo)
                        cout[0].update(exportobj[0])
                        obj = exportobj[1]
                        if obj:
                            cout[1].update(obj)

        return self.saves()

    def getconfigsheetfinfo(self, sheet):
        titles = sheet.head(1)[0]

        nameindex = getindex(titles, self.configsheettitles[0])
        valueindex = getindex(titles, self.configsheettitles[1])
        typeindex = getindex(titles, self.configsheettitles[2])
        signindex = getindex(titles, self.configsheettitles[3])
        descriptionindex = getindex(titles, self.configsheettitles[4])

        if nameindex != -1 and valueindex != -1 and typeindex != -1:
            return (nameindex, valueindex, typeindex, signindex, descriptionindex)
        else:
            return None

    # 导出并返回对象：schemaobj = collections.OrderedDict()
    def exportitemsheet(self, sheet):
        # 先获取Excel的前四行
        rows = iter(sheet.rows)
        descriptions = next(rows)  # ['索引', '名称', '武器']
        names = next(rows)  # ['Id', 'Name', 'Weapon']
        types = next(rows)  # ['int', 'string', 'int[]'] 对象数组：['{int Id;int Count}[]']
        signs = next(rows)  # ['server/client', 'client', 'server/client']

        # 根据types有多少列去导表（其实Excel有很多列，空None也会存在ncols里，这个以后可以优化）
        ncols = len(types)  # 3
        #
        titleinfos = []
        schemaobj = collections.OrderedDict()

        try:
            # 制作 titleinfos = [('int', 'Id', True), ('string', 'Name', True), ('int[]', 'Weapon', True)] （类型+字段名+True）
            for colindex in range(ncols):
                type_ = getcellvalue(types[colindex]).strip()  # 'int' / 'string' / 'int[]'  对象数组：'{int Id;int Count}[]'
                name = getcellvalue(names[colindex]).strip()  # 'Id'  / 'Name'   / 'Weapon'
                # 判断 sign 的默认值/合法性 ['server/client', 'client', 'server/client']
                signmatch = issignmatch(self.context.sign, getcellvalue(signs[colindex]).strip())  # True
                titleinfos.append((type_, name, signmatch))

                # codegenerator=None，不生成程序代码，跳过
                if self.context.codegenerator:
                    if type_ and name and signmatch:
                        self.buildexpress(schemaobj, type_, name, descriptions[colindex], True)

        except Exception as e:
            e.args += (
                '%s has a title error, %s at %d column in %s' % (sheet.name, (type_, name), colindex + 1, self.path),
                '')
            raise e

        list_ = []
        # 根据titleinfos里面元组的True和False，是否被next读取。例如：[('int', 'Id', False), ('string', 'Name', True)]，则Id不能被读取，Name可以。
        hasexport = next((i for i in titleinfos if i[0] and i[1] and i[2]), False)  # ('int', 'Id', True)
        if hasexport:
            try:
                # 空行计数
                spacerowcount = 0
                self.rowindex = 3
                # 遍历数据行（第五行开始）
                for row in rows:  # [1.0, '奥丁', '1001'] / [2.0, '托尔', '1003,1004,1005']  Excel21000读取为20999.999999999996
                    self.rowindex += 1

                    # item有顺序的字典，用来接收数据
                    item = collections.OrderedDict()
                    # 第五行 第一个数据
                    firsttext = getcellvalue(row[0]).strip()  # '1.0' / '2.0'
                    if not firsttext:
                        spacerowcount += 1
                        if spacerowcount >= self.spacemaxrowcount:  # if space row is than max count, skil follow rows
                            break

                    # 第个数据空或者‘#’开头，跳过该行
                    if not firsttext or firsttext[0] == '#':  # current line skip
                        continue

                    # 第一个数据‘!’开头
                    skiptokenindex = None
                    if firsttext[0] == '!':
                        nextpos = firsttext.find('!', 1)
                        if nextpos >= 2:
                            signtoken = firsttext[1: nextpos]
                            if issignmatch(self.context.sign, signtoken.strip()):
                                continue
                            else:
                                skiptokenindex = len(signtoken) + 2

                    # 按列数循环 准备导表 例如：将 Name 和 奥丁，根据类型string ，最后转为item = OrderedDict([('Name', '奥丁')])
                    for self.colindex in range(ncols):
                        signmatch = titleinfos[self.colindex][2]  # True
                        # titleinfos=[('{int Id;int Count}[]', 'Bag', True), ('int[]', 'Weapon', True),
                        # ('int', 'Id', True), ('string', 'Name', True)]
                        if signmatch:
                            # 获取具体的字段名、类型和对应的值（可以从这里开始仔细看代码）
                            type_ = titleinfos[self.colindex][0]  # 'int' / 'string' / 'int[]'
                            name = titleinfos[self.colindex][1]  # 'Id'  / 'Name'   / 'Weapon'
                            # '1.0' / '奥丁' / '1001'   or   '2.0' / '托尔' / '1003,1004,1005'
                            value = getcellvalue(row[self.colindex])

                            # 2024/5/15:新增 obj 和 obj[]，等同于 {} 和 {}[]
                            # 在这里将新类型重新整理为原来的类型：
                            # 1、obj -> {int Id,int Count} :  [Id=10001,Count=10] ->  [10001,10]
                            if type_ == 'obj' and len(value) > 0:
                                # 传value进去，在里面修改不会影响外面的值
                                type_, value = reset_type_value(value)

                            # 2、obj[] -> {int Id,int Count}[] :
                            #                   [[Id=10001,Count=10],[Id=10002,Count=20]] ->  [[10001,10],[10002,20]]
                            if type_ == 'obj[]' and len(value) > 0:
                                type_, value = reset_type_values(value)

                            print(type_)
                            print(value)
                            print("----------------")

                            if skiptokenindex and self.colindex == 0:
                                value = value.lstrip()[skiptokenindex:]

                            # ★参数无误，开始建表 大概流程 buildexpress（分类建表）-[buildlistexpress（列表）,buildobjexpress（对象）,
                            # buildbaseexpress（基础，可重复利用）]-fillvalue（结果塞进item字典）
                            if type_ and name and value:
                                # ★上面定义了item为有顺序的字典，用来接收数据
                                self.buildexpress(item, type_, name, self.checkstringescape(type_, value))
                        spacerowcount = 0

                    if item:
                        list_.append(item)

            except Exception as e:
                e.args += ('%s has a error in %d row %d(%s) column in %s' % (
                    sheet.name, self.rowindex + 1, self.colindex + 1, name, self.path), '')
                raise e

        return (schemaobj, list_)

    def exportconfigsheet(self, sheet, titleindexs):
        rows = iter(sheet.rows)
        next(rows)

        nameindex = titleindexs[0]
        valueindex = titleindexs[1]
        typeindex = titleindexs[2]
        signindex = titleindexs[3]
        descriptionindex = titleindexs[4]

        schemaobj = collections.OrderedDict()
        obj = collections.OrderedDict()

        try:
            spacerowcount = 0
            self.rowindex = 0
            for row in rows:
                self.rowindex += 1
                name = getcellvalue(row[nameindex]).strip()
                value = getcellvalue(row[valueindex])
                type_ = getcellvalue(row[typeindex]).strip()
                description = getcellvalue(row[descriptionindex]).strip()

                if signindex > 0:
                    sign = getcellvalue(row[signindex]).strip()
                    if not issignmatch(self.context.sign, sign):
                        continue

                if not name and not value and not type_:
                    spacerowcount += 1
                    if spacerowcount >= self.spacemaxrowcount:
                        break  # if space row is than max count, skil follow rows
                    continue

                if name and type_:
                    if (name[0] != '#'):  # current line skip
                        if self.context.codegenerator:
                            self.buildexpress(schemaobj, type_, name, description, True)
                        if value:
                            self.buildexpress(obj, type_, name, self.checkstringescape(type_, value))
                    spacerowcount = 0

        except Exception as e:
            e.args += ('%s has a error in %d row (%s, %s, %s) in %s' % (
                sheet.name, self.rowindex + 1, type_, name, value, self.path), '')
            raise e

        return (schemaobj, obj)

    def saves(self):
        schemas = []
        for r in self.records:
            if r.obj:
                self.save(r)

                if self.context.codegenerator:  # has code generator
                    schemas.append(
                        {'path': r.path, 'exportfile': r.exportfile, 'root': r.root, 'item': r.item or r.exportmark,
                         'schema': r.schema})

        return schemas

    def save(self, record):
        if not record.obj:
            return

        if not os.path.isdir(self.context.folder):
            os.makedirs(self.context.folder)

        if self.context.format == 'json':
            jsonstr = json.dumps(record.obj, ensure_ascii=False, indent=2)
            with codecs.open(record.exportfile, 'w', 'utf-8') as f:
                f.write(jsonstr)
            print('save %s from %s in %s' % (record.exportfile, record.sheet.name, record.path))

        elif self.context.format == 'xml':
            if record.item:
                record.obj = {record.item + 's': record.obj}
            savexml(record)

        elif self.context.format == 'lua':
            luastr = "".join(tolua(record.obj))
            with codecs.open(record.exportfile, 'w', 'utf-8') as f:
                f.write('return ')
                f.write(luastr)
            print('save %s from %s in %s' % (record.exportfile, record.sheet.name, record.path))

        elif self.context.format == 'ycl':
            g = toycl(record.obj)
            next(g)  # skip first newline
            yclstr = "".join(g)
            with codecs.open(record.exportfile, 'w', 'utf-8') as f:
                f.write(yclstr)
            print('save %s from %s in %s' % (record.exportfile, record.sheet.name, record.path))

    def checksheetname(self, path, sheetname, root):
        r = next((r for r in self.records if r.root == root), False)
        if r:
            raise ValueError('%s in %s is already defined in %s' % (root, path, r.path))


# 导出多个文件（startui.py过来）
def exportfiles(context):
    paths = context.path
    schemas = []

    def append(result):
        schemas.extend(result)

    try:
        # 单线程执行
        for path in paths:
            # ★开始导出
            result = Exporter(context).export(path)
            append(result)
    except Exception as e:
        print('导表出错：')
        print(e)
        # 导表错误：把错误传给上层，用于界面展示
        raise e

    # schemas图式，这里是空的[]
    if schemas:
        # 将excel结构保为json('schemaserver.json')，就是方便程序使用配置表的代码。这里配置了跳过。
        if context.codegenerator:
            schemasjson = json.dumps(schemas, ensure_ascii=False, indent=2)
            dir = os.path.dirname(context.codegenerator)
            if dir and not os.path.isdir(dir):
                os.makedirs(dir)
            with codecs.open(context.codegenerator, 'w', 'utf-8') as f:
                f.write(schemasjson)

        exports = []
        for schema in schemas:
            exportfile = schema['exportfile']
            r = next((r for r in exports if r['exportfile'] == exportfile), False)
            if r:
                # errors.append('%s in %s is already defined in %s' % (schema['root'], schema['path'], r['path']))
                os.remove(exportfile)
                # 不知道错，也是丢给上层
                raise Exception('%s in %s is already defined in %s' % (schema['root'], schema['path'], r['path']))
            else:
                exports.append(schema)

    print("Export finsish successful!!!")


# 新增：服务端需要csv格式配置表（不在已有基础上改了，自己弄还更方便）
# 遇到问题：直接打开Excel另存为csv时候，会将FALSE/TRUE导出为False/True，导致数据不对
def exportfilescsv(context):
    paths = context.path
    try:
        for path in paths:
            logging.info("处理文件: %s", path)
            xls = pd.ExcelFile(path)
            sheet_names = xls.sheet_names
            logging.info("Excel文件中的sheet名称: %s", sheet_names)
            for sname in sheet_names:
                logging.info("正在处理sheet: %s", sname)
                if '|' in sname:
                    export_name = 'cfg_' + sname.split('|')[1].strip()
                    exportfile = os.path.join(context.folder, f"{export_name}.csv")  # 定义exportfile
                    logging.info("导出文件名: %s", exportfile)

                    # 读取第一行以获取列信息
                    df = pd.read_excel(path, sheet_name=sname, header=None, skiprows=3, nrows=1)
                    row_values = df.iloc[0].tolist()
                    logging.info("读取到的列信息: %s", row_values)

                    export_list = [i for i, v in enumerate(row_values) if 's' in str(v)]
                    logging.info("可导出的列索引: %s", export_list)

                    if len(export_list) == 0:
                        logging.warning("没有可导出的列，跳过sheet: %s", sname)
                        continue
                    
                    df = pd.read_excel(path, sheet_name=sname, header=None, skiprows=[2, 3], usecols=export_list)
                    logging.info("读取到的行数: %d，导出文件名: %s", len(df), exportfile)
                    
                    if len(df) < 2:
                        raise ValueError("配置有误，至少包含2行。")
                    
                    df.iloc[0], df.iloc[1] = df.iloc[1].copy(), df.iloc[0].copy()
                    logging.info("交换了前两行数据。")

                    if not os.path.isdir(context.folder):
                        os.makedirs(context.folder)
                        logging.info("创建导出文件夹: %s", context.folder)

                    df.to_csv(exportfile, encoding='utf-8', index=False, header=False)
                    logging.info("成功导出到: %s", exportfile)
    except Exception as e:
        logging.error('导表出错：%s', e)
        raise e
    logging.info("Export finish successful!!!")

    # 确保所有日志信息都写入文件
    logging.shutdown()


class Context:
    '''usage python proton.py [-p filelist] [-f outfolder] [-e format]
  Arguments
  -p      : input excel files, use , or ; or space to separate
  -f      : out folder
  -e      : format, json or xml or lua or ycl

  Options
  -s      ：sign, controls whether the column is exported, defalut all export
  -t      : suffix, export file suffix
  -r      : the separator of object field, default is ; you can use it to change
  -m      : use the count of multiprocesses to export, default is cpu count
  -c      : a file path, save the excel structure to json
            the external program uses this file to automatically generate the read code
  -h      : print this help message and exit

  https://github.com/yanghuan/proton'''


if __name__ == '__main__':
    print('argv:', sys.argv)
    opst, args = getopt.getopt(sys.argv[1:], 'p:f:e:s:t:r:m:c:h')

    context = Context()
    context.path = None
    context.folder = '.'
    context.format = 'json'
    context.sign = None
    context.extension = None
    context.objseparator = ';'
    context.codegenerator = None
    context.multiprocessescount = None

    for op, v in opst:
        if op == '-p':
            context.path = v
        elif op == '-f':
            context.folder = v
        elif op == '-e':
            context.format = v.lower()
        elif op == '-s':
            context.sign = v
        elif op == '-t':
            context.extension = v
        elif op == '-r':
            context.objseparator = v
        elif op == '-m':
            context.multiprocessescount = int(v) if v is not None else None
        elif op == '-c':
            context.codegenerator = v
        elif op == '-h':
            print(Context.__doc__)
            sys.exit()

    if not context.path:
        print(Context.__doc__)
        sys.exit(2)

    exportfiles(context)
