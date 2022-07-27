# -*- coding: utf-8 -*-
import math
import sys
import socket
import cv2
import datetime
import numpy as np

from PyQt5.QtGui import QPixmap
import pyttsx3
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5 import QtCore, QtWidgets

from tensoflow import main
import mysql


class BackendThread(QObject):
    # 通过类成员对象定义信号
    update_date = pyqtSignal(str)

    def pretreatment(self, img):
        """
        摄像头图片预处理
        :param img: 摄像头图片
        :return: 车牌轮廓List
        """
        img = img.copy()
        #  img = cv2.resize(img, (640, 480))  # 调整尺寸
        lower_blue = np.array([100, 110, 80])
        upper_blue = np.array([130, 255, 255])
        imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  # 转换颜色空间 BGR--HSV
        mask = cv2.inRange(imgHSV, lower_blue, upper_blue)
        # cv2.imshow("1", mask)
        # cv2.waitKey(0)
        Matrix = np.ones((15, 15), np.uint8)
        img_edge1 = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, Matrix)  # 开闭操作
        img_edge2 = cv2.morphologyEx(img_edge1, cv2.MORPH_OPEN, Matrix)
        # cv2.imshow("1", img_edge1)
        # cv2.waitKey(0)
        contours, hierarchy = cv2.findContours(img_edge2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)  # 只检测外轮廓
        return contours

    def bubblesort(self, arr):
        """
        排序函数
        :param arr:车牌轮廓点集
        :return: 适合处理的车牌轮廓点集
        """
        a = len(arr)
        for i in range(1, a):
            for j in range(0, a - i):
                if arr[j][0][0] > arr[j + 1][0][0]:
                    arr[j][0][0], arr[j + 1][0][0] = arr[j + 1][0][0], arr[j][0][0]  # 交换x
                    arr[j][0][1], arr[j + 1][0][1] = arr[j + 1][0][1], arr[j][0][1]  # 交换 Y
        # print(arr)
        if arr[0][0][1] > arr[1][0][1]:
            arr[0][0][0], arr[1][0][0] = arr[1][0][0], arr[0][0][0]
            arr[0][0][1], arr[1][0][1] = arr[1][0][1], arr[0][0][1]
        if arr[a - 2][0][1] > arr[a - 1][0][1]:
            arr[a - 2][0][0], arr[a - 1][0][0] = arr[a - 1][0][0], arr[a - 2][0][0]
            arr[a - 2][0][1], arr[a - 1][0][1] = arr[a - 1][0][1], arr[a - 2][0][1]

        # print(arr)
        return arr

    def lr_sort(self, xs, crop_images):
        """
        分割字符图片排序
        :param xs: 字符最小外接矩形轮廓点X
        :param crop_images: 字符图片List
        :return:返回正序字符图片List
        """
        for j in range(len(xs)):
            for i in range(len(xs) - 1):
                if xs[i] > xs[i + 1]:
                    temp = xs[i]
                    xs[i] = xs[i + 1]
                    xs[i + 1] = temp
                    temp2 = crop_images[i]
                    crop_images[i] = crop_images[i + 1]
                    crop_images[i + 1] = temp2
        return crop_images

    def get_plate(self, img):
        """
        车牌粗定位及矫正
        :param img:摄像头图片
        :return: 矫正车牌图片
        """
        contours = self.pretreatment(img)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2000:
                peri = cv2.arcLength(cnt, True)  # 闭合轮廓
                approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)  # 轮廓近似
                # print(approx)
                approx = self.bubblesort(approx)  # 冒泡排序
                # print(approx)
                point_num = len(approx)  # 获取轮廓点的个数
                point_set_0 = np.float32(
                    [approx[0][0], approx[1][0], approx[point_num - 2][0], approx[point_num - 1][0]])  # 透视投影前的关键点
                point_set_1 = np.float32([[0, 0], [0, 140], [440, 0], [440, 140]])  # 透视投影后的关键点
                # 变换矩阵
                mat = cv2.getPerspectiveTransform(point_set_0, point_set_1)
                # 投影变换
                lic = cv2.warpPerspective(img, mat, (440, 140))  # 投影完成图
                # cv2.drawContours(img, cnt, -1, (0, 255, 0), 3)  # 描绘
                # cv2.circle(img, (348, 374), 10, (0, 0, 255))
                return True, lic
        return False

    def accurate_crop_plate(self, img):
        """
        精确定位字符以及字符裁剪
        :param img: 车牌粗定位图
        :return: 车牌字符图片
        """
        img = img.copy()
        img = cv2.resize(img, (440, 140))
        lower_blue = np.array([100, 110, 80])
        upper_blue = np.array([130, 255, 255])
        imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(imgHSV, lower_blue, upper_blue)
        Matrix = np.ones((5, 5), np.uint8)
        img_edge1 = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, Matrix)  # 开闭操作
        img_edge2 = cv2.morphologyEx(img_edge1, cv2.MORPH_OPEN, Matrix)

        contours, hierarchy = cv2.findContours(img_edge2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2000:
                # peri = cv2.arcLength(cnt, True)  # 闭合轮廓
                # approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)  # 轮廓近似
                x, y, w, h = cv2.boundingRect(cnt)
                # cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                num_img = img[y:y + h, x:x + w]
                # cv2.imshow("1", num_img)
                return True, num_img
        return False

    def crop_nums_img(self, img):
        """
        字符分割函数
        :param img:精确定位车牌图
        :return: 返回正序车牌字符图片
        """
        img = img.copy()
        img = cv2.resize(img, (440, 140))
        # lower_blue = np.array([0, 0, 0])
        # upper_blue = np.array([255, 80, 255])
        # imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # mask = cv2.inRange(imgHSV, lower_blue, upper_blue)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        Matrix = np.ones((10, 10), np.uint8)
        img_edge1 = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, Matrix)  # 开闭操作
        Matrix = np.ones((5, 5), np.uint8)
        img_edge2 = cv2.morphologyEx(img_edge1, cv2.MORPH_OPEN, Matrix)

        contours, hierarchy = cv2.findContours(img_edge2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        xs = []
        nums = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 1000:
                # print(area)
                # cv2.drawContours(img, cnt, -1, (255, 0, 0), 3)
                peri = cv2.arcLength(cnt, True)  # 闭合轮廓
                approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)  # 轮廓近似
                x, y, w, h = cv2.boundingRect(approx)  # 左上角点坐标以及宽高
                # cv2.rectangle(img, (x-5, y-5), (x+w, y + h), (255, 0, 0), 2)
                num_img = mask[y - 5:y + h + 5, x - 5:x + w + 5]  # 从灰度图中裁剪出每个字符
                num_img = cv2.copyMakeBorder(num_img, 5, 5, 3, 3, borderType=cv2.BORDER_CONSTANT, value=0)
                num_img = cv2.resize(num_img, (32, 32), interpolation=cv2.INTER_AREA)  # 改变输出字符图片大小
                xs.append(x)
                nums.append(num_img)
        crop_images = self.lr_sort(xs, nums)
        return crop_images

    # 处理业务逻辑
    def run(self):
        count = 0  # 识别十次若相同则发送到服务端
        plate = ""  # 存车牌号
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('192.168.232.135', 8888))  # 连接服务端
        except Exception as E:
            print(E)
        while True:
            try:
                receive_encode = s.recv(777777)  # 接收的字节数 最大值 2147483647 （31位的二进制）
                nparr = np.fromstring(receive_encode, dtype='uint8')
                img_decode = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                img_decode = cv2.cvtColor(img_decode, cv2.COLOR_BGR2RGB)

                img = cv2.cvtColor(img_decode, cv2.COLOR_BGR2RGB)
                # cv2.imshow('1', img)
                # cv2.waitKey(1)
                flag, lic = self.get_plate(img)
                flag2, nums = self.accurate_crop_plate(lic)
                if flag and flag2:
                    nums_img = self.crop_nums_img(nums)
                    plate_new = main(nums_img)
                    if plate == plate_new:
                        count += 1
                        print(count)
                        if count == 10:
                            # self.lb_img.setScaledContents(True)
                            self.update_date.emit(str(plate_new))
                            count = 0
                            plate = ""
                    else:
                        plate = plate_new
            except Exception as E:
                count = 0
                plate = ""


class Ui_Form(object):
    def setupUi(self, Form):

        Form.setObjectName("Form")
        Form.resize(1025, 609)
        self.btn_star = QtWidgets.QPushButton(Form)
        self.btn_star.setGeometry(QtCore.QRect(40, 30, 93, 28))
        self.btn_star.setObjectName("btn_star")
        self.lb_platenums = QtWidgets.QLabel(Form)
        self.lb_platenums.setGeometry(QtCore.QRect(220, 20, 431, 51))
        self.lb_platenums.setObjectName("lb_platenums")
        self.lb_time = QtWidgets.QLabel(Form)
        self.lb_time.setGeometry(QtCore.QRect(770, 40, 221, 21))
        self.lb_time.setObjectName("lb_time")
        self.btn_selectbyplatenums = QtWidgets.QPushButton(Form)
        self.btn_selectbyplatenums.setGeometry(QtCore.QRect(40, 550, 93, 28))
        self.btn_selectbyplatenums.setObjectName("btn_selectbyplatenums")
        self.txt_platenums = QtWidgets.QTextEdit(Form)
        self.txt_platenums.setGeometry(QtCore.QRect(190, 540, 281, 41))
        self.txt_platenums.setObjectName("txt_platenums")
        self.lb_img = QtWidgets.QLabel(Form)
        self.lb_img.setGeometry(QtCore.QRect(670, 20, 51, 51))
        self.lb_img.setText("")
        self.lb_img.setObjectName("lb_img")
        self.scrollArea = QtWidgets.QScrollArea(Form)
        self.scrollArea.setGeometry(QtCore.QRect(10, 90, 1001, 441))
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 978, 418))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.mysql_list = QtWidgets.QTableWidget(self.scrollAreaWidgetContents)
        self.mysql_list.setGeometry(QtCore.QRect(0, 0, 981, 421))
        self.mysql_list.setMouseTracking(False)
        self.mysql_list.setObjectName("mysql_list")
        self.mysql_list.setColumnCount(5)
        self.mysql_list.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.mysql_list.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.mysql_list.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.mysql_list.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.mysql_list.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.mysql_list.setHorizontalHeaderItem(4, item)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.txt_platenums = QtWidgets.QTextEdit(Form)
        self.txt_platenums.setGeometry(QtCore.QRect(190, 540, 281, 41))
        self.txt_platenums.setObjectName("txt_platenums")

        self.lb_img = QtWidgets.QLabel(Form)
        self.lb_img.setGeometry(QtCore.QRect(670, 20, 51, 51))
        self.lb_img.setText("")
        self.lb_img.setObjectName("lb_img")

        # self.btn_change = QtWidgets.QPushButton(Form)
        # self.btn_change.setGeometry(QtCore.QRect(910, 560, 93, 28))
        # self.btn_change.setObjectName("btn_change")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

        # 创建线程
        self.thread = QThread()
        self.backend = BackendThread()
        # 连接信号
        self.backend.update_date.connect(self.handleDisplay)
        self.backend.moveToThread(self.thread)
        # 开始线程
        self.thread.started.connect(self.backend.run)
        self.thread.start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.flash_time)
        self.timer.start()

        self.btn_star.clicked.connect(self.setItem_select)
        self.btn_selectbyplatenums.clicked.connect(self.selectby_platenum)
        # self.btn_change.clicked.connect(self.change_plateNUM)
        # self.count = 0
    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "车牌识别系统客户端"))
        self.btn_star.setText(_translate("Form", "查询"))
        self.lb_platenums.setText(_translate("Form",
                                             "<html><head/><body><p align=\"center\"><span style=\" "
                                             "font-size:14pt;\">车牌号</span></p></body></html>"))
        self.lb_time.setText(_translate("Form", "Time"))
        self.btn_selectbyplatenums.setText(_translate("Form", "查询"))
        item = self.mysql_list.horizontalHeaderItem(0)
        item.setText(_translate("Form", "停车次数"))
        item = self.mysql_list.horizontalHeaderItem(1)
        item.setText(_translate("Form", "车牌号"))
        item = self.mysql_list.horizontalHeaderItem(2)
        item.setText(_translate("Form", "入库时间"))
        item = self.mysql_list.horizontalHeaderItem(3)
        item.setText(_translate("Form", "出库时间"))
        item = self.mysql_list.horizontalHeaderItem(4)
        item.setText(_translate("Form", "停车费"))

        # self.btn_change.setText(_translate("Form", "change"))

    def flash_time(self):
        Time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.lb_time.setText(Time)
        try:
            if self.txt_platenums.toPlainText() == "OPEN":
                self.lb_img.setPixmap(QPixmap("open.jpg"))
                self.lb_img.setScaledContents(True)
            else:
                self.lb_img.setPixmap(QPixmap("close.jpg"))
                self.lb_img.setScaledContents(True)
        except Exception as E:
            pass

    def handleDisplay(self, data):  # 当服务器收到信息才会执行
        """
        当PC接收到信息时刷新lb_platenums控件，并刷新表格信息
        :param data:
        :return:
        """
        _translate = QtCore.QCoreApplication.translate
        self.lb_platenums.setText(_translate("Form",
                                             "<html><head/><body><p align=\"center\"><span style=\" font-size:14pt;\">"
                                             + data +
                                             "</span></p></body></html>"))
        self.setItem("test1")
        self.letin()

    def countfee(self, plate_nums):  # 计费
        """
        识别到车辆出库信息后进行计费并存入表
        :param plate_nums:
        :return:
        """
        p1, p2, count = mysql.selectbyplate_num(plate_nums)
        t1 = p2[0][2]
        t2 = datetime.datetime.now()
        a = t2 - t1
        fee = (math.fabs(a.days * 24 * 60) + math.fabs(a.seconds / 60)) / 30
        if fee * 3 % 1 != 0:
            fee = int(fee) + 1
        mysql.update_t1(plate_nums, t2.strftime('%Y-%m-%d %H:%M:%S'), str(fee))
        try:
            mysql.update_t2(plate_nums, t2.strftime('%Y-%m-%d %H:%M:%S'))
        except Exception as E:
            print(E)
            print("countfee")

    def letin(self):  # 入出库
        """
        入出库函数，防止重复录入
        :return:
        """
        try:
            Time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            plate_nums = self.lb_platenums.text()
            plate_nums = plate_nums[68:-25]
            # 初始化
            pt = pyttsx3.init()
            # 说什么
            pt.say("欢迎," + plate_nums)
            # 开始说吧
            pt.runAndWait()
            # print(plate_nums)
            p, p2, count = mysql.selectbyplate_num(plate_nums)
            print(count)
            if len(p) == 0:  # 第一次停车录入
                print("第一次")
                mysql.insert_table1(plate_nums, Time, None, 0.0)
                mysql.insert_table2(plate_nums, 0, 0.0, Time, None)
            elif count == 0:  # 没有未出库记录
                mysql.insert_table1(plate_nums, Time, None, 0.0)
            elif count == 1:  # 有未出库记录
                self.countfee(plate_nums)
            self.setItem("test1")
            self.txt_platenums.setText("OPEN")
        except Exception as E:
            print(E)
            print("letin")
        # print(E)

    def setItem(self, table):
        """
        写入表格信息
        :return:
        """
        data, data_len = mysql.selectALL(table)
        self.mysql_list.setRowCount(data_len)
        for i in range(0, len(data)):
            for j in range(0, 5):
                item = QTableWidgetItem(str(data[i][j]))  # 将各种数据格式统一为字符串方便写入Items中
                self.mysql_list.setItem(i, j, item)

    def selectby_platenum(self):
        try:
            _translate = QtCore.QCoreApplication.translate
            item = self.mysql_list.horizontalHeaderItem(0)
            item.setText(_translate("Form", "车牌号"))
            item = self.mysql_list.horizontalHeaderItem(1)
            item.setText(_translate("Form", "停车次数"))
            item = self.mysql_list.horizontalHeaderItem(2)
            item.setText(_translate("Form", "总车费"))
            item = self.mysql_list.horizontalHeaderItem(3)
            item.setText(_translate("Form", "最近一次入库"))
            item = self.mysql_list.horizontalHeaderItem(4)
            item.setText(_translate("Form", "最近一次出库"))
            self.btn_star.setText("车库信息表")
            self.setItem("test2")
            platenums = self.txt_platenums.toPlainText()
            data, data_len = mysql.selectfromtext2(platenums)  # 表2为停车记录
            # print(data, data_len)
            self.mysql_list.setRowCount(data_len)
            for i in range(0, len(data)):
                for j in range(0, 5):
                    item = QTableWidgetItem(str(data[i][j]))  # 将各种数据格式统一为字符串方便写入Items中
                    self.mysql_list.setItem(i, j, item)
        except Exception as E:
            print(E)

    def setItem_select(self):
        _translate = QtCore.QCoreApplication.translate
        if self.btn_star.text() == "车库信息表":
            item = self.mysql_list.horizontalHeaderItem(0)
            item.setText(_translate("Form", "停车次数"))
            item = self.mysql_list.horizontalHeaderItem(1)
            item.setText(_translate("Form", "车牌号"))
            item = self.mysql_list.horizontalHeaderItem(2)
            item.setText(_translate("Form", "入库时间"))
            item = self.mysql_list.horizontalHeaderItem(3)
            item.setText(_translate("Form", "出库时间"))
            item = self.mysql_list.horizontalHeaderItem(4)
            item.setText(_translate("Form", "停车费"))
            self.btn_star.setText("停车记录表")
            self.setItem("test1")
        else:
            item = self.mysql_list.horizontalHeaderItem(0)
            item.setText(_translate("Form", "车牌号"))
            item = self.mysql_list.horizontalHeaderItem(1)
            item.setText(_translate("Form", "停车次数"))
            item = self.mysql_list.horizontalHeaderItem(2)
            item.setText(_translate("Form", "总车费"))
            item = self.mysql_list.horizontalHeaderItem(3)
            item.setText(_translate("Form", "最近一次入库"))
            item = self.mysql_list.horizontalHeaderItem(4)
            item.setText(_translate("Form", "最近一次出库"))
            self.btn_star.setText("车库信息表")
            self.setItem("test2")

    # def change_plateNUM(self):
    #
    #     if self.count == 4:
    #         count = 0
    #     else:
    #         plate_nums = ["赣F6A677", "川A69M96", "冀J00002", "晋LYN668"]
    #         self.lb_platenums.setText(plate_nums[self.count])
    #         self.letin()
    #         self.count += 1


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(widget)
    widget.show()
    sys.exit(app.exec_())
