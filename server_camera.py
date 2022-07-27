import socket
import struct

import numpy as np
import cv2
import threading
import time
import sys



class Raspberry_server():
    def __init__(self):
        print('This is Socket-Server:Raspberry')
        host = '172.20.10.2'
        port = 8888
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # 设置画面的宽度
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)  # 设置画面的高度
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket模式设置
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 防止socket server重启后端口被占用
            self.s.bind((host, port))  # 绑定套字节
            self.s.listen(5)  # 设置监听连接请求
        except socket.error as msg:
            print(msg)
        print('Waiting Socket-Client:Computer Connection')
        while True:
            self.conn, self.address = self.s.accept()
            t = threading.Thread(target=self.send_camera, args=(self.conn, self.address))
            t.start()
    
    def send_camera(self, conn, address):
        print('Accept New Connection from {0}'.format(address))
        while True:
            ret, frame = self.cap.read()  # 读取摄像头视频
            #self.recognition(frame)
            img_encode = cv2.imencode('.jpg', frame)[1]  # 将视频每一帧编码为.jpg格式
            data_encode = np.array(img_encode)  # 将图片数据保存
            str_encode = data_encode.tostring()  # 转为string形式用于socket传输
            encode_len = str(len(str_encode))
            print('img size : %s' % encode_len)  # 打印图片信息大小
            try:
                conn.send(str_encode)  # 发送图片的encode码
            except Exception as e:
                print(e)
            time.sleep(0.05)
        conn.close()

    def recognition(self, frame):
        data = decode(frame)
        for d in data:
            r_data = d.data.decode('utf-8')
            if r_data is not None:
                print(r_data)
                data = r_data.encode()
                data_length = struct.pack('i', len(data))
                self.s.send(data_length)
                self.s.send(data)
            #cv2.imshow("cap", frame)
            #if cv2.waitKey(100) & 0xff == ord('q'):
                #break
        #self.cap.release()
        #cv2.destroyAllWindows()
        self.s.close()

if  __name__=='__main__':
    raspberry=Raspberry_server()
    raspberry.send_camera()
