# coding=gbk
import tensorflow as tf
import numpy as np
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # ���þ���ȼ�
SAVER_DIR1 = './train_model/chars_Chinese/'
SAVER_DIR2 = './train_model/numbers/'
PROVINCES = (
    "��", "��", "��", "��", "��", "��", "��", "��", "��", "��", "��", "��", "��", "³", "��", "��", "��", "��", "��", "��", "��", "��",
    "��",
    "��", "��", "ԥ", "��", "��", "��", "��", "��")
LETTERS_DIGITS = (
    "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X",
    "Y",
    "Z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9")


# ����������
def conv_layer(inputs, W, b, conv_strides, kernel_size, pool_strides, padding):
    L1_conv = tf.nn.conv2d(inputs, W, strides=conv_strides, padding=padding)  # �������
    L1_relu = tf.nn.relu(L1_conv + b)  # �����RELU
    return tf.nn.max_pool2d(L1_relu, ksize=kernel_size, strides=pool_strides, padding='SAME')


# ����ȫ���Ӻ���
def full_connect(inputs, W, b):
    return tf.nn.relu(tf.matmul(inputs, W) + b)


def ocr(plate_num_imgs, m, n, lens, SAVER_DIR):
    indexs = []
    # print("�������")
    g2 = tf.Graph()
    with g2.as_default():
        x = tf.compat.v1.placeholder(tf.float32,
                                     shape=[None, 1024])  # None��ʾbatch size�Ĵ�С������������κ�������Ϊ��֪����ѵ����ͼƬ����SIZEָͼƬ�Ĵ�С
        y_ = tf.compat.v1.placeholder(tf.float32, shape=[None, lens])  # �����ǩ��ռλ
        x_image = tf.reshape(x, [-1, 32, 32, 1])  # ����һ����ά������

        sess1 = tf.compat.v1.Session(graph=g2)
        saver = tf.compat.v1.train.import_meta_graph("%smodel.ckpt.meta" % SAVER_DIR)
        model_file = tf.train.latest_checkpoint(SAVER_DIR)  # �ҳ�����ģ�������µ�ģ��
        saver.restore(sess1, model_file)

        # ��һ�������
        W_conv1 = sess1.graph.get_tensor_by_name("W_conv1:0")
        b_conv1 = sess1.graph.get_tensor_by_name("b_conv1:0")
        conv_strides = [1, 1, 1, 1]
        kernel_size = [1, 2, 2, 1]
        pool_strides = [1, 2, 2, 1]
        L1_pool = conv_layer(x_image, W_conv1, b_conv1, conv_strides, kernel_size, pool_strides, padding='SAME')
        # �ڶ��������
        W_conv2 = sess1.graph.get_tensor_by_name("W_conv2:0")
        b_conv2 = sess1.graph.get_tensor_by_name("b_conv2:0")
        conv_strides = [1, 1, 1, 1]
        kernel_size = [1, 2, 2, 1]
        pool_strides = [1, 2, 2, 1]
        L2_pool = conv_layer(L1_pool, W_conv2, b_conv2, conv_strides, kernel_size, pool_strides, padding='SAME')
        # ȫ���Ӳ�
        W_fc1 = sess1.graph.get_tensor_by_name("W_fc1:0")
        b_fc1 = sess1.graph.get_tensor_by_name("b_fc1:0")
        h_pool2_flat = tf.reshape(L2_pool, [-1, 8 * 8 * 24])
        h_fc1 = full_connect(h_pool2_flat, W_fc1, b_fc1)
        # dropout
        keep_prob = tf.compat.v1.placeholder(tf.float32)
        h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)
        # readout��
        W_fc2 = sess1.graph.get_tensor_by_name("W_fc2:0")
        b_fc2 = sess1.graph.get_tensor_by_name("b_fc2:0")
        # �����Ż�����ѵ��op
        conv = tf.nn.softmax(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)
        # �볢�Խ����д���ͳ��ƺ���λһ��ʶ����˿��Խ�3-8��Ϊ2-8
        for n in range(m, n):
            img = plate_num_imgs[n]
            height = img.shape[0]
            width = img.shape[1]
            img_data = [[0] * 1024 for i in range(1)]
            for h in range(0, height):
                for w in range(0, width):
                    m = img[h][w]
                    if m > 150:
                        img_data[0][w + h * width] = 1
                    else:
                        img_data[0][w + h * width] = 0

            result = sess1.run(conv, feed_dict={x: np.array(img_data), keep_prob: 1.0})
            max1 = 0
            max2 = 0
            max3 = 0
            max1_index = 0
            max2_index = 0
            max3_index = 0
            for j in range(lens):
                if result[0][j] > max1:
                    max1 = result[0][j]
                    max1_index = j
                    continue
                if (result[0][j] > max2) and (result[0][j] <= max1):
                    max2 = result[0][j]
                    max2_index = j
                    continue
                if (result[0][j] > max3) and (result[0][j] <= max2):
                    max3 = result[0][j]
                    max3_index = j
                    continue
            # print("���ʣ�[%s %0.2f%%]    [%s %0.2f%%]    [%s %0.2f%%]" % (
            #     LETTERS_DIGITS[max1_index], max1 * 100, LETTERS_DIGITS[max2_index], max2 * 100,
            #     LETTERS_DIGITS[max3_index],
            #     max3 * 100))
            if m == 0:
                indexs.append(max1_index)
            elif m == 1:
                indexs.append(max1_index)
        sess1.close()
        return indexs


def main(plate_num_imgs):
    a = ocr(plate_num_imgs, 0, 1, 31, SAVER_DIR1)
    b = ocr(plate_num_imgs, 1, 7, 34, SAVER_DIR2)
    license_num = ""
    for i in range(0, 6):
        license_num += LETTERS_DIGITS[b[i]]
    return PROVINCES[a[0]] + license_num
