#!/usr/local/bin/python
# -*- coding: utf-8 -*-


import libs.common as common
import sys
import time
import pandas as pd
import numpy as np
import math
import tushare as ts
from sqlalchemy.types import NVARCHAR
from sqlalchemy import inspect
import datetime
import heapq
import stockstats

"""
SELECT `date`, `code`, `name`, `changepercent`, `trade`, `open`, `high`, `low`, 
                `settlement`, `volume`, `turnoverratio`, `amount`, `per`, `pb`, `mktcap`, `nmc` 
    FROM stock_data.ts_today_all where `date` = 20171106 and trade > 0 and trade <= 20
and `code` not like '002%' and `code` not like '300%'  and `name` not like '%st%'

"""


def stat_index_all(tmp_datetime):
    datetime_str = (tmp_datetime).strftime("%Y-%m-%d")
    datetime_int = (tmp_datetime).strftime("%Y%m%d")
    print("datetime_str:", datetime_str)
    print("datetime_int:", datetime_int)

    # 查询今日满足股票数据。剔除数据：创业板股票数据，中小板股票数据，所有st股票
    # #`code` not like '002%' and `code` not like '300%'  and `name` not like '%st%'
    sql_1 = """ 
            SELECT `date`, `code`, `name`, `changepercent`, `trade`, `open`, `high`, `low`, 
                `settlement`, `volume`, `turnoverratio`, `amount`, `per`, `pb`, `mktcap`, `nmc` 
            FROM stock_data.ts_today_all WHERE `date` = %s and `trade` > 0 and `open` > 0 and trade <= 20 
                and `code` not like %s and `code` not like %s and `name` not like %s limit 10
            """
    print(sql_1)
    data = pd.read_sql(sql=sql_1, con=common.engine(), params=[datetime_int, '002%', '300%', '%st%'])
    data = data.drop_duplicates(subset="code", keep="last")
    print("########data[trade]########:", len(data))
    # print(data["trade"])

    # 使用 trade 填充数据
    stock_guess = pd.DataFrame({
        "date": data["date"], "code": data["code"], "5d": data["trade"],
        "10d": data["trade"], "20d": data["trade"], "60d": data["trade"], "5-10d": data["trade"],
        "5-20d": data["trade"], "return": data["trade"], "mov_vol": data["trade"]
    }, index=data.index.values)

    stock_guess = stock_guess.apply(apply_guess, axis=1)  # , axis=1)
    print(stock_guess.head())
    # stock_guess.astype('float32', copy=False)
    stock_guess.drop('date', axis=1, inplace=True)  # 删除日期字段，然后和原始数据合并。

    # print(stock_guess["5d"])

    data_new = pd.merge(data, stock_guess, on=['code'], how='left')
    print("#############")

    # 使用pandas 函数 ： https://pandas.pydata.org/pandas-docs/stable/api.html#id4
    data_new["return"] = data_new["return"].mul(100)  # 扩大100 倍方便观察
    data_new["mov_vol"] = data_new["mov_vol"].mul(100)

    data_new = data_new.round(2)  # 数据保留2位小数

    # 删除老数据。
    del_sql = " DELETE FROM `stock_data`.`guess_indicators_daily` WHERE `date`= %s " % datetime_int
    # common.insert(del_sql)

    print(data_new.head())
    # data_new["down_rate"] = (data_new["trade"] - data_new["wave_mean"]) / data_new["wave_base"]
    # common.insert_db(data_new, "guess_indicators_daily", False, "`date`,`code`")

    # 进行左连接.
    # tmp = pd.merge(tmp, tmp2, on=['company_id'], how='left')


# http://wiki.mbalib.com/wiki/CR%E6%8C%87%E6%A0%87 价格动量指标
# CR跌穿a、b、c、d四条线，再由低点向上爬升160时，为短线获利的一个良机，应适当卖出股票。
# CR跌至40以下时，是建仓良机。而CR高于300~400时，应注意适当减仓。
# 'cr','cr-ma1','cr-ma2','cr-ma3'

def apply_guess(tmp):
    date = tmp["date"]
    code = tmp["code"]
    date_end = datetime.datetime.strptime(date, "%Y%m%d")
    date_start = (date_end + datetime.timedelta(days=-200)).strftime("%Y-%m-%d")
    date_end = date_end.strftime("%Y-%m-%d")
    print(code, date_start, date_end)
    # open, high, close, low, volume, price_change, p_change, ma5, ma10, ma20, v_ma5, v_ma10, v_ma20, turnover
    # 使用缓存方法。加快计算速度。
    stock = common.get_hist_data_cache(code, date_start, date_end)

    stock = pd.DataFrame({"close": stock["close"]}, index=stock.index.values)
    stock = stock.sort_index(0)  # 将数据按照日期排序下。

    # print(stock.head(10))

    stock["date"] = stock.index.values  # 增加日期列。
    stock = stock.sort_index(0)  # 将数据按照日期排序下。
    # print(stock) [186 rows x 14 columns]
    # 初始化统计类
    # stockStat = stockstats.StockDataFrame.retype(pd.read_csv('002032.csv'))
    stockStat = stockstats.StockDataFrame.retype(stock)

    # print(stock["mov_vol"].tail())
    # print(stock["return"].tail())
    # print("stock[10d].tail(1)", stock["10d"].tail(1).values[0])
    # 10d    20d  5-10d  5-20d     5d    60d    code      date  mov_vol  return
    # tmp = list([stock["10d"].tail(1).values[0], stock["20d"].tail(1).values[0], stock["5-10d"].tail(1).values[0],
    #             stock["5-20d"].tail(1).values[0], stock["5d"].tail(1).values[0], stock["60d"].tail(1).values[0],
    #             code, date, stock["mov_vol"].tail(1).values[0], stock["return"].tail(1).values[0]])
    # # print(tmp)
    # return tmp


# main函数入口
if __name__ == '__main__':
    # 使用方法传递。
    tmp_datetime = common.run_with_args(stat_index_all)
