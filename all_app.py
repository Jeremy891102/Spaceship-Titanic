from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, PostbackAction, PostbackEvent, PostbackTemplateAction, URIAction, MessageAction, TemplateSendMessage, ButtonsTemplate,ImageSendMessage
import sqlite3, time
from pandas.io import sql
import yfinance as yf
import ta
import requests
import pandas as pd
import numpy as np
import datetime,time,re
import mplfinance as mpf
from bs4 import BeautifulSoup
from sklearn.linear_model import LinearRegression
import sqlite3
import pyimgur
from matplotlib import use
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pandas.core.frame import DataFrame
import os
from pathlib import Path
import datetime

today = datetime.date.today()
end = today - datetime.timedelta(days=1)
start = end - datetime.timedelta(days=365*3.5)

def get_sql2():
    conn = sqlite3.connect('C:/Users/Jeremy/Fintech_project/fund_data.db')
    cursor = conn.cursor()
    sql = "select Quote_change from fund_data where Date = ? and FundID = ?"
    cursor.execute(sql, ('2022-12-20', 'F0HKG05WWU:FO'))
    rows = cursor.fetchall()
    return rows

def basic_information(msg):
    conn = sqlite3.connect('C:/Users/Jeremy/Fintech_project/fund_data.db')
    cursor = conn.cursor()
    sql = f"select * from fund_data where FundID = '{msg}'"
    cursor.execute(sql)
    rows = cursor.fetchall()
    newList = list(reversed(rows))
    content = (f'FundID: {newList[0][0]}\nDate: {newList[0][1]}\nNet_worth: {newList[0][2]}\nUp_down: {newList[0][3]}\nQuote_change: {newList[0][4]}\n')
    return content

def linebot_draw_fiveline(msg):
    conn = sqlite3.connect('C:/Users/Jeremy/Fintech_project/fund_data.db')
    cursor = conn.cursor()
    sql =f"select * from Strategy_data where Number = '{msg}'"
    cursor.execute(sql)
    data = cursor.fetchall()

    Net_worth = []
    P2SD= []
    P1SD = []
    TL = []
    N2SD = []
    N1SD = []
    for row in data:
        #date.append(row[0])
        Net_worth.append(row[2])
        P2SD.append(row[3])
        P1SD.append(row[4])
        TL.append(row[5])
        N2SD.append(row[6])
        N1SD.append(row[7])
    plt.figure(facecolor = 'white', figsize = (9,3), dpi=100)
    plt.plot(Net_worth)
    plt.plot(P2SD)
    plt.plot(P1SD)
    plt.plot(TL)
    plt.plot(N2SD)
    plt.plot(N1SD)
    plt.title(f"{msg}.TW", color = 'black', fontsize = 24) 
    plt.ylabel("Stock price")
    plt.savefig(f'FIVELINE{msg}.png')
    plt.plot

    CLIENT_ID = "9fa3e553d6f1121"
    PATH = f"FIVELINE{msg}.png"
    im = pyimgur.Imgur(CLIENT_ID)
    uploaded_image = im.upload_image(PATH, title=f"FIVELINE{msg}")
    return uploaded_image.link

def linebot_draw_fivelinebb(msg):
    conn = sqlite3.connect('C:/Users/Jeremy/Fintech_project/fund_data.db')
    cursor = conn.cursor()
    sql =f"select * from Strategy_data where Number = '{msg}'"
    cursor.execute(sql)
    data = cursor.fetchall()

    date = []
    Net_worth = []
    bbh = []
    bbm = []
    bbl = []
    for row in data:
        date.append(row[0])
        Net_worth.append(row[2])
        bbh.append(row[8])
        bbm.append(row[9])
        bbl.append(row[10])

    plt.figure(facecolor = 'white', figsize = (15,5), dpi=100)
    plt.plot(date, Net_worth)
    plt.plot(date, bbh)
    plt.plot(date, bbm)
    plt.plot(date, bbl)
    plt.title(f"{msg}.TW", color = 'black', fontsize = 24) 
    plt.ylabel("Stock price")
    plt.savefig(f'FivelineBB{msg}.png')
    plt.plot

    CLIENT_ID = "9fa3e553d6f1121"
    PATH = f"FivelineBB{msg}.png"
    im = pyimgur.Imgur(CLIENT_ID)
    uploaded_image = im.upload_image(PATH, title=f"FivelineBB{msg}")
    return uploaded_image.link

dict_from_ETF_list= pd.read_csv("C:/Users/Jeremy/Fintech_project/linebot/ETF_List.csv")
ETF_list = dict_from_ETF_list['Number']

def five_line (data):
    timetrend = list(range(1, data.shape[0]+1))
    data['Date'] = timetrend
    data = data[['Date','Net_worth']]
    data = data.dropna()
    reg = LinearRegression()
    x = data['Date'].to_frame ()
    y = data['Net_worth'].to_frame ()
    reg.fit(x,y)
    a = reg.intercept_
    beta = reg.coef_
    longtrend = a + beta*x
    print(longtrend)
    res = np.array(list(data['Net_worth'])) - np.array(list(longtrend['Date']))
    std = np.std(res, ddof=1) #residual std
    fiveline = pd.DataFrame ()
    fiveline['+2SD'] = longtrend['Date'] + (2*std)
    fiveline['+1SD'] = longtrend['Date'] + (1*std)
    fiveline['TL'] = longtrend['Date']
    fiveline['-1SD'] = longtrend['Date'] - (1*std)
    fiveline['-2SD'] = longtrend['Date'] - (2*std)
    use_fiveline = pd.merge(data,fiveline[['+2SD', '+1SD', 'TL', '-1SD', '-2SD']], left_index=True, right_index=True, how='left')
    pick_fiveline = use_fiveline[['Net_worth','+2SD', '+1SD', 'TL', '-1SD', '-2SD']]
    return pick_fiveline,beta

def stock_price(stock:str):

    data = requests.get(f"https://tw.stock.yahoo.com/fund/history/{stock}")
    soup = BeautifulSoup(data.text)
    price = soup.find('span',{'class':'Fz(40px) Fw(b) Lh(1) C($c-primary-text)'})
    return price.text

etf_data = {}
slope = []
reply = ''

def fiveline():
    conn = sqlite3.connect('C:/Users/Jeremy/Fintech_project/fund_data.db')
    cursor = conn.cursor()
    for i in ETF_list:
        x=0
        print(x)
        print(i)
        sql =f"select * from Strategy_data where Number = '{i}'"
        cursor.execute(sql)
        data = cursor.fetchall()
        df = pd.DataFrame(data)
        df = df.drop([1,8,9,10],axis =1)
        

        df.set_axis(['Date', 'Net_worth', '+2SD','+1SD','TL','-1SD','-2SD'], axis='columns', inplace=True)
        df.set_index('Date', inplace = True)
        df2,beta = five_line(df)
        
        beta = beta.tolist() 
        
        beta = beta[0][0]
       
        slope.append((i,beta)) #(ETF_ID, 斜率)存入slope
       
        etf_data[i] = df2 
        x+=1
        
    slope.sort(key = lambda s: s[1]) #根據斜率排序
    slope.reverse()
    
    recommend_count = recommend_count #推薦個數
    recommended = 0 
    reply = ''
    chosen = []
    for i in slope:
        temp_data = etf_data[i[0]]
        #print('temp data :',temp_data)
        price = stock_price(i[0])
        #print('price :',price)
        if temp_data.iat[-1,-6] < temp_data.iat[-1,-2]:
            reply += i[0]+'.TW低於悲觀線，股票價格 : '+price+'，可買進\n'
            recommended += 1
            chosen.append(i[0])
            if recommended == recommend_count:
                break
            else:continue
            #return reply
        else:continue
        if reply == '':
            return 'none'
    return reply,chosen

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
yourID = 'U0f46bcfb6e02517edca32cf7987f02ac'

@csrf_exempt
def callback(request):
 
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
 
        try:
            events = parser.parse(body, signature)  # 傳入的事件
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent): # 如果有訊息事件

                if event.message.text == "主選單":
                #if "Help" in event.message.text:
                    line_bot_api.reply_message(  
                        event.reply_token,
                        TemplateSendMessage(
                            alt_text = 'Help Buttons Template',
                            template=ButtonsTemplate(
                                thumbnail_image_url='https://storage.googleapis.com/www-cw-com-tw/article/202112/article-61b108fd8f600.jpg',
                                title='主選單',
                                text='請選擇你需要的功能',
                                actions=[
                                    MessageAction(
                                        label='Using Instructions',
                                        text='輸入 "ETF____" 搜尋該檔基本資訊或策略圖形\n（ETF清單可在 ETF List Link 中找到）'
                                    ),
                                    URIAction(
                                        label='ETF List Link',
                                        uri='https://docs.google.com/spreadsheets/d/16DFZGhIjmhFuQRnz9xc7pD8sFn92Ljzd/edit?usp=share_link&ouid=103564067831742851998&rtpof=true&sd=true'
                                        
                                    MessageAction(
                                        label='Dashboard Link',
                                        text='Dashboard Link'
                                    ),
                                    URIAction(
                                        label='Yahoo Finance Link',
                                        uri='https://tw.stock.yahoo.com/fund/'
                                    )
                                ]
                            )
                        )
                    )
 
                elif "ETF" in event.message.text:
                    msg = event.message.text[4:]
                    #msg = event.message.text.strip("ETF ")
                    line_bot_api.reply_message(
                        event.reply_token,
                        TemplateSendMessage(
                            alt_text = 'Buttons Template',
                            template=ButtonsTemplate(
                                thumbnail_image_url='https://cimg.cnyes.cool/prod/news/3946641/l/872d56244d0152ebe4b4ca9221dd2c35.jpg',
                                title= event.message.text + ' Visualization',
                                text='請選擇想查看的基本資訊或策略圖形',
                                actions=[
                                    MessageAction(
                                        label='Basic Information',
                                        text= basic_information.basic_information(msg)
                                        #text='Basic Information'
                                    ),
                                    URIAction(
                                        label= 'Fiveline',
                                        uri= 'https://i.imgur.com/VZjVFkJ.png'  #這個傳送方法是錯的，要改掉～
                                        #data= drawline.linebot_draw_fiveline(msg)
                                    ),
                                    PostbackAction(
                                        label= 'Fiveline + BBands',
                                        data= '發送 Fiveline + BBands'
                                    )
                                ]
                            )
                        )
                    )
                
                elif event.message.text == "Chosen":
                    pass
                
                elif "recommend" in event.message.text:
                    #etf_id = int(event.message.text)
                    count = event.message.text[10:]
                    #print(count)
                    reply,chosen = recommend.fiveline(int(count))
                    #print(reply)
                    #print(chosen)
                    line_bot_api.reply_message(  
                    event.reply_token,
                    TextSendMessage(text=reply))
                    for i in chosen:
                        print(i)
                        img_url = drawline.linebot_draw_fiveline(i)
                        print(img_url)
                        line_bot_api.push_message(your_ID, ImageSendMessage(
                        original_content_url=img_url,
                        preview_image_url=img_url
                    ))
                        
                elif "fl" in event.message.text:
                    msg = event.message.text[3:]
                    img_url = drawline.linebot_draw_fiveline(msg)
                    
                    line_bot_api.reply_message(  
                    event.reply_token,
                    ImageSendMessage(
                        original_content_url=img_url,
                        preview_image_url=img_url
                    )
                )
                elif "bb" in event.message.text:
                    msg = event.message.text[3:]
                    img_url = drawline.linebot_draw_fivelinebb(msg)
                    
                    line_bot_api.reply_message(  
                    event.reply_token,
                    ImageSendMessage(
                        original_content_url=img_url,
                        preview_image_url=img_url
                    )
                )


                else:
                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                    event.reply_token,
                    TextSendMessage(text= '【 指令輸入錯誤 】\n• 輸入 "主選單" 可搜尋ETF清單以及相關網站連結\n• 輸入 "ETF___(eg. ETF 0050)" 搜尋該檔最新交易日基本資訊或策略圖形，清單可在Help指令的ETF List Link中找到\n• 輸入 "Chosen" 可得最新交易日所推薦的ETF')
                )

            
            if not isinstance(event, MessageEvent):
                pass

        return HttpResponse()
    else:
        return HttpResponseBadRequest()