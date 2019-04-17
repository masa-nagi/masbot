import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import urllib
import urllib.parse
import urllib.request
import json
import datetime
import gzip
import io
import requests

app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)
line_user_id = os.environ["LINE_USER_ID"]

@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/push", methods=['POST'])
def push_message():

    request_message = request.get_data(as_text=True)

    if request_message == "morning":
        messages = TextSendMessage(text=f"おはよう")
        line_bot_api.push_message(line_user_id, messages=messages)
    elif request_message == "trash":
        message = trash_info()
        if len(message) > 0:
            messages = TextSendMessage(text=message)
            line_bot_api.push_message(line_user_id, messages=messages)

    return 'OK'

@app.route("/webhook", methods=['POST'])
def webhook():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # webhook test
    if event.reply_token == '00000000000000000000000000000000':
        return ;

    if event.type == "message":
        if (event.message.text == "やあ") or (event.message.text == "こんにちは"):
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text='やあ'+ chr(0x10002D)),
                ]
            )
        #elif (event.message.text == "東横") or (event.message.text == "東横遅延"):
        elif event.message.text.startswith("電車遅延") \
          or event.message.text.startswith("遅延"):

            # 路線判定 - 東急線
            if "東横" in event.message.text:
                line_name = "toyoko"
            elif "目黒" in event.message.text:
                line_name = "meguro"
            elif "田園都市" in event.message.text:
                line_name = "dento"
            elif "大井町" in event.message.text:
                line_name = "oimachi"
            elif "池上" in event.message.text:
                line_name = "ikegami"
            elif "多摩川" in event.message.text:
                line_name = "tamagawa"
            else:
                return

            if len(line_name) > 0:
                message = tokyu_delay(line_name)

            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text=message),
                ]
            )
        elif (event.message.text == "天気"):
            message = weather_info()

            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text=message),
                ]
            )

        else:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="ごめんなさい、何を言っているかわかりません"+ chr(0x100029) + chr(0x100098)),
                ]
            )

def weather_info():
    url = 'http://weather.livedoor.com/forecast/webservice/json/v1?city=140010'
    api_data = requests.get(url).json()

    response = ''
    for weather in api_data['forecasts']:
        weather_date = weather['dateLabel']
        weather_forecasts = weather['telop']
        response += weather_date + ':' + weather_forecasts + '\n'

    response += '\n'
    response += api_data["description"]["text"]
    return response

def trash_info():

    # 0: 月, 1: 火, 2: 水, 3: 木, 4: 金, 5: 土, 6: 日
    trash_list = {
        0: 'ビン・缶・ペットボトル',
        1: '資源ごみ',
        4: 'プラごみ',
        5: '資源ごみ',
    }

    weekday = datetime.datetime.now().weekday()

    if weekday in trash_list:
        response = '今日は{}の日だよ'.format(trash_list[weekday])
    else:
        response = ''

    return response


def tokyu_delay(line_name):

    # 路線ID取得
    line_id_list = { "toyoko": 26001,
                     "meguro": 26002,
                     "dento": 26003,
                     "oimachi": 26004,
                     "ikegami": 26005,
                     "tamagawa": 26006 }

    line_id = line_id_list[line_name]

    # URIスキーム
    server = 'delay-certificate.tokyuapp.com'
    target_date = datetime.date.today().strftime("%Y%m%d")
    target_time = datetime.datetime.today().strftime("%H")

    if int(target_time) < 10:
        time_zone="first_half"
    else:
        time_zone="second_half"

    cert_url = 'https://{}/{}/up/{}/{}.json'.format(server, line_id, target_date,time_zone)
    delay_url = 'https://tokyu-tid.s3.amazonaws.com/delays.json'

    # URIパラメータのデータ 
    #param = {
    #    'key1': 'value1',
    #    'key2': 'value2'
    #}

    # URIパラメータの文字列の作成
    #param_str = urllib.urlencode(param)
    param_str = ""

    # 読み込むオブジェクトの作成
    cert_response = urllib.request.urlopen(cert_url + param_str)

    delay_response = urllib.request.urlopen(delay_url + param_str)
    raw_data = delay_response.read()
    file_object = io.BytesIO(raw_data)
    delay_message = json.loads(gzip.GzipFile(fileobj=file_object).read())

    cert_message = json.loads(cert_response.read())

    response = "遅延証明: 最大{}分の遅れが発生しています\n".format(cert_message['delay'])
    response += "最新の遅延情報では{}分の遅れが出ているようです".format(delay_message[line_name])

    return response

if __name__ == "__main__":
    app.run()
