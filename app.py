import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_world():
    return "hello world!"

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
        elif event.message.text.startswith("電車遅延"):

            # 路線判定 - 東急線
            if "東横" in event.message.text:
                line_id = 26001
            elif "目黒線" in event.message.text:
                line_id = 26002
            elif "田園都市線" in event.message.text:
                line_id = 26003
            elif "大井町線" in event.message.text:
                line_id = 26004
            elif "池上線" in event.message.text:
                line_id = 26005
            elif "多摩川線" in event.message.text:
                line_id = 26006
            else:
                message = "未登録路線です"

            if line_id > 0:
                delay_time = tokyu_delay(line_id)
                message = "遅延証明 : {}分遅れています".format(delay_time)

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
    #line_bot_api.reply_message(
    #    event.reply_token,
    #    TextSendMessage(text=event.message.text))

def tokyu_delay(line_id):
    import urllib
    import urllib.request
    import json
    import datetime

    # URIスキーム
    server = 'delay-certificate.tokyuapp.com'
    target_date = datetime.date.today().strftime("%Y%m%d")
    target_time = datetime.datetime.today().strftime("%H")

    if int(target_time) < 10:
        time_zone="first_half"
    else:
        time_zone="second_half"

    url = 'https://{}/{}/up/{}/{}.json'.format(server, line_id, target_date,time_zone)

    # URIパラメータのデータ 
    #param = {
    #    'key1': 'value1',
    #    'key2': 'value2'
    #}

    # URIパラメータの文字列の作成
    #paramStr = urllib.urlencode(param)
    paramStr = ""

    # 読み込むオブジェクトの作成
    readObj = urllib.request.urlopen(url + paramStr)

    # webAPIからのJSONを取得
    response = json.loads(readObj.read())

    return response['delay']

if __name__ == "__main__":
    app.run()
