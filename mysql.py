import pymysql


def conMysql():
    try:
        conn = pymysql.connect(host='platedata.mysql.rds.aliyuncs.com', user='js_admin', password='Jsst233_',
                               db='cardata', port=3306, charset='utf8')
        cursor = conn.cursor()
        # print("数据库连接成功！")
        return conn, cursor
    except Exception as r:
        print("出错或无网络!!!")


# # 表结构
# sql7 = "desc test1;"
# cursor.execute(sql7)
# r = cursor.fetchall()
# print(r)
def insert_table1(plate_num, input_time, output_time, fee):
    conn, cursor = conMysql()
    sql1 = "select count(*) from test1 where plate_num='" + plate_num + "'"
    cursor.execute(sql1)
    ret1 = cursor.fetchmany(1)
    counts = ret1[0][0] + 1  # 当前车库内的该车记录+1
    sql = "insert into test1 (counts,plate_num,input_time,output_time,fee)values(%s,%s,%s,%s,%s)"
    values = (counts, plate_num, input_time, output_time, fee)
    cursor.execute(sql, values)
    conn.commit()

    cursor.close()
    conn.close()
    # print("插入成功！")


def insert_table2(plate_num, parking_sum, fee_sum, input_time, output_time):
    conn, cursor = conMysql()
    sql = "insert into test2 (plate_num, parking_sum, fee_sum, input_time,output_time)values(%s,%s,%s,%s,%s)"
    values = (plate_num, parking_sum, fee_sum, input_time, output_time)
    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()


def delbyplate_num(plate_num):
    conn, cursor = conMysql()
    sql = "delete from test1 where plate_num = '" + plate_num + "'"
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()


#  print("删除成功！")


def selectbyplate_num(plate_num):
    """
    :param plate_num:
    :return:ret1 该车test1所有记录 ；count 该车车费为0的记录；ret3 为该车未出库记录
    """
    conn, cursor = conMysql()
    sql1 = "select * from test1 where plate_num = '" + plate_num + "'"
    sql2 = "select count(*) from test1 where plate_num = '" + plate_num + "'" + "and fee ='" + str(0.0) + "'"
    sql3 = "select * from test1 where plate_num = '" + plate_num + "'" + "and fee ='" + str(0.0) + "'"
    cursor.execute(sql1)
    ret1 = cursor.fetchmany(1)
    cursor.execute(sql2)
    ret2 = cursor.fetchmany(1)
    count = ret2[0][0]
    cursor.execute(sql3)
    ret3 = cursor.fetchmany(1)
    cursor.close()
    conn.close()
    # print("查询成功！")
    return ret1, ret3, count




def selectfromtext2(plate_num):
    conn, cursor = conMysql()
    # sql = "SELECT * FROM test1"
    sql = "select * from test2 where plate_num = '" + plate_num + "'"
    cursor.execute(sql)
    ret = cursor.fetchall()
    ret_len = len(ret)
    cursor.close()
    conn.close()
    # print("查询成功！")
    return ret, ret_len


def selectALL(table):
    conn, cursor = conMysql()
    # sql = "SELECT * FROM test1"
    sql = "select * from " + table
    cursor.execute(sql)
    ret = cursor.fetchall()
    ret_len = len(ret)
    cursor.close()
    conn.close()
    #  print("查询全部成功！")
    return ret, ret_len


def update_t1(plate_num, output_time, fee):
    conn, cursor = conMysql()
    sql = "update test1 set output_time='" + output_time + "'" + ",fee='" + fee + "'" + ",counts = counts+1 where " \
                                                                                        "plate_num ='" + plate_num + \
          "'" + "and fee = '" + str(0.0) + "'"
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()


#  print("更新成功")
def update_t2(plate_num, output_time):
    conn, cursor = conMysql()
    sql1 = "select sum(fee) from test1 where plate_num =" + "'" + plate_num + "'"
    cursor.execute(sql1)
    ret = cursor.fetchmany(1)
    sql2 = "update test2 set output_time='" + output_time + "'" + ",fee_sum ='" + str(ret[0][0]) + \
           "'" + ",parking_sum = parking_sum+1 where plate_num ='" + plate_num + "'"
    cursor.execute(sql2)

    conn.commit()
    cursor.close()
    conn.close()

#  print("更新成功")
