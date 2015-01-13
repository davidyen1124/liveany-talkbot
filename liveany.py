from time import time
import json
import re

import requests
import websocket


def on_message(ws, message):
    print(message)
    if message == '3probe':
        # if message is 3probe, send 5 to socket
        ws.send('5')
    elif '42["say"' in message:
        # 42["say","msg"] is what user sends to us
        m = re.search('42\["say","(.+?)"\]', message)
        if m:
            # send what he say
            ws.send('42["say","{}"]'.format(m.group(1)))
    elif '42["close",null]' in message:
        # 42["close",null] means user left
        ws.close()


def on_error(ws, error):
    print(error)


def on_close(ws):
    print('### closed ###')


def on_open(ws):
    # if connection is opened, send 2probe to start chat
    ws.send('2probe')


def get_token():
    '''Get SID so we can connect to websocket'''
    url = 'http://ws.liveany.com:18089/socket.io/'
    # without referer, server won't sending any information
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.69 Safari/537.36',
        'Referer': 'http://www.liveany.com/web.php',
    }
    params = {
        'lang': 'zh-tw',
        'platform': 'web',
        'EIO': '3',
        'transport': 'polling',
        't': '{}-0'.format(int(time() * 1000))
    }
    res = requests.get(url, params=params, headers=headers)
    # first five words are useless
    data = json.loads(res.text[5:])
    # get sid
    return data.get('sid')


def main():
    # get sid so we can connect to websocket
    sid = get_token()
    # connect websocket to liveany
    ws = websocket.WebSocketApp(
        'ws://ws.liveany.com:18089/socket.io/?lang=zh-tw&platform=web&EIO=3&transport=websocket&sid={}'.format(
            sid),
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()

if __name__ == '__main__':
    while True:
        main()
