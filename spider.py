import requests
import json
import time
import pymysql
import traceback
from selenium.webdriver import Chrome, ChromeOptions


def getdata():
    url = "https://view.inews.qq.com/g2/getOnsInfo?name=disease_h5"
    url_history = "https://view.inews.qq.com/g2/getOnsInfo?name=disease_other"

    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    res = requests.get(url, headers)
    data = json.loads(json.loads(res.text)["data"])

    res_history = requests.get(url_history, headers)
    data_history = json.loads(json.loads(res_history.text)["data"])
    print(data_history.keys())
    print(data.keys())

    history = {}    # store history data
    for i in data_history["chinaDayList"]:
        #print(i)
        # match time format
        date = "2020." + i["date"]
        format_tmp = time.strptime(date, "%Y.%m.%d")
        date = time.strftime("%Y-%m-%d", format_tmp)
        confirm = i["confirm"]
        suspect = i["suspect"]
        heal = i["heal"]
        dead = i["dead"]
        history[date] = {"confirm": confirm, "suspect": suspect, "heal": heal, "dead": dead}
    for i in data_history["chinaDayAddList"]:
        date = "2020." + i["date"]
        format_tmp = time.strptime(date, "%Y.%m.%d")
        date = time.strftime("%Y-%m-%d", format_tmp)
        confirm = i["confirm"]
        suspect = i["suspect"]
        heal = i["heal"]
        dead = i["dead"]
        history[date].update({"confirm_add": confirm, "suspect_add": suspect, "heal_add": heal, "dead_add": dead})

    details = []
    update_time = data["lastUpdateTime"]
    country_data = data["areaTree"]
    province_data = country_data[0]["children"]
    for each in province_data:
        province_name = each["name"]
        for city in each["children"]:
            city_name = city["name"]
            confirm = city["total"]["confirm"]
            confirm_add = city["today"]["confirm"]
            heal = city["total"]["heal"]
            dead = city["total"]["dead"]
            details.append([update_time, province_name, city_name, confirm, confirm_add, heal, dead])
    print(history)
    #print(details)
    return history, details


# connect and close database
def get_db_conn():
    connect = pymysql.connect(host="localhost", user="root", password="37290950a", db="cov19", charset="utf8", port=3306)
    cursor = connect.cursor()
    return connect, cursor


def close_db_conn(conn, cursor):
    if cursor:
        cursor.close()
    if conn:
        conn.close()


def load_history():
    cursor = None
    connect = None
    try:
        history = getdata()[0]  # get history data
        connect, cursor = get_db_conn()
        sql = "insert into history values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        print(f"{time.asctime()} Start loading history data...")
        for k, v in history.items():
            cursor.execute(sql, [k, v.get("confirm"), v.get("confirm_add"), v.get("suspect"),
                           v.get("suspect_add"), v.get("heal"), v.get("heal_add"),
                           v.get("dead"), v.get("dead_add")])
        connect.commit()
        print(f"{time.asctime()} History data loading done")
    except:
        traceback.print_exc()
    finally:
        close_db_conn(connect, cursor)


def update_history():
    cursor = None
    connect = None
    try:
        history = getdata()[0]
        print(f"{time.asctime()} Start updating history data")
        connect, cursor = get_db_conn()
        sql = "insert into history values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        sql_query = "select confirm from history where date=%s"
        for k, v in history.items():
            if not cursor.execute(sql_query, k):
                cursor.execute(sql, [k, v.get("confirm"), v.get("confirm_add"), v.get("suspect"),
                               v.get("suspect_add"), v.get("heal"), v.get("heal_add"),
                               v.get("dead"), v.get("dead_add")])
        connect.commit()
        print(f"{time.asctime()} History data update done")
    except:
        traceback.print_exc()
    finally:
        close_db_conn(connect, cursor)


def update_details():
    cursor = None
    connect = None
    try:
        details = getdata()[1]   # get details data
        connect, cursor = get_db_conn()     # connect to database
        sql = "insert into details(update_time,province,city,confirm,confirm_add,heal,dead) values(%s,%s,%s,%s,%s,%s,%s)"
        sql_query = "select %s=(select update_time from details order by id desc limit 1)"
        cursor.execute(sql_query, details[0][0])
        if not cursor.fetchone()[0]:
            print(f"{time.asctime()} Start updating details...")
            for item in details:
                cursor.execute(sql, item)
            connect.commit()
            print(f"{time.asctime()} Details updating done!")
        else:
            print(f"{time.asctime()} Details data already update！")
    except:
        traceback.print_exc()
    finally:
        close_db_conn(connect, cursor)


# get hotsearch info from baidu
def get_hotsearch_data():
    option = ChromeOptions()
    option.add_argument("--headless")   # hide browser
    option.add_argument("--no--sandbox")    # linux sandbox
    browser = Chrome(options=option)
    url = "https://voice.baidu.com/act/virussearch/virussearch?from=osari_map&tab=0&infomore=1"
    browser.get(url)
    # get more button simulation
    btn_more = browser.find_element_by_css_selector('#ptab-0 > div > div.VirusHot_1-5-6_32AY4F.VirusHot_1-5-6_2RnRvg > section > div')
    btn_more.click()
    time.sleep(1)

    data = browser.find_elements_by_xpath('//*[@id="ptab-0"]/div/div[1]/section/a/div/span[2]')
    context = [each.text for each in data]
    browser.close()
    #print(context)
    return context


# insert hotsearch data into database
def update_hotsearch():
    cursor = None
    connect = None
    try:
        context = get_hotsearch_data()
        print(f"{time.asctime()} Start updating hot search data")
        connect, cursor = get_db_conn()
        sql = "insert into hotsearch(date,content) values(%s,%s)"
        date = time.strftime("%Y-%m-%d %X")
        for i in context:
            cursor.execute(sql, (date, i))
        connect.commit()
        print(f"{time.asctime()} Hot search data update done")
    except:
        traceback.print_exc()
    finally:
        close_db_conn(connect, cursor)


if __name__ == '__main__':
    pass
    #update_hotsearch()
    #getdata()
    #load_history()
    #update_history()
    #update_details()
