#!/usr/bin/env python3.3

from time import time
import json
import re
from multiprocessing.pool import ThreadPool
from time import time, sleep

import requests
from websocket import create_connection, WebSocketTimeoutException
from colorama import Fore

LIVEANY_URL = 'http://60.199.193.88:6007/socket.io/'
WS_URL = 'ws://60.199.193.88:6007/socket.io/?lang=zh-tw&platform=web&EIO=3&transport=websocket&sid={}'

first = None
second = None
is_disconnect = False


def get_token():
    '''Get SID so we can get token and connect to websocket'''
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
        't': '{}-2'.format(int(time() * 1000))
    }
    res = requests.get(LIVEANY_URL, params=params, headers=headers)
    # first five words are useless
    data = json.loads(res.text[5:])
    # get sid
    return data.get('sid')


def bot(i):
    '''A bot that get and send messages.'''
    global first
    global second
    global is_disconnect

    # record how many messages has been sent
    msg_count = 0

    # record how many times user sends hi
    hi_count = 0

    # save current time before connection to server
    start_time = time()


    sid = get_token()
    # connect to server
    # set timeout as one second, so it won't block in recv()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.69 Safari/537.36',
        'Referer': 'http://www.liveany.com/web.php',
    }
    params = {
        'lang': 'zh-tw',
        'platform': 'web',
        'EIO': '3',
        'transport': 'polling',
        't': '{}-1'.format(int(time() * 1000)),
        'sid': sid
    }
    res = requests.get(LIVEANY_URL, params=params, headers=headers)
    ws = create_connection(WS_URL.format(sid))
    ws.settimeout(1)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.69 Safari/537.36',
        'Referer': 'http://www.liveany.com/web.php',
    }
    params = {
        'lang': 'zh-tw',
        'platform': 'web',
        'EIO': '3',
        'transport': 'polling',
        't': '{}-2'.format(int(time() * 1000)),
        'sid': sid
    }
    res = requests.post(LIVEANY_URL, params=params, headers=headers,data='12:42["room",0]')
    # dont know what is '12:42["room",0]'
    # initialize connection with anonymous
    ws.send('2probe')
    message = ws.recv()
    if message == '3probe':
        ws.send('5')
    print(i+1, 'start')

    # send hello to user
    ws.send('42["say","{}"]'.format('哈囉'))

    # get messages in infinity loop
    while True:
        # close connection if is_disconnect is true
        if is_disconnect:
            ws.close()
            break

        # get message that we should send
        if i == '0' and first:
            # send message to user
            ws.send('42["say","%s"]' % (first))
            print(Fore.RED + '1:', first)
            first = None
        if i == '1' and second:
            # send message to user
            ws.send('42["say","%s"]' % (second))
            print(Fore.GREEN + '2:', second)
            second = None

        # if user hasn't sent more that three messages,
        # and they don't speak for thrity seconds then disconnect!
        if msg_count < 3 and time() - start_time > 30:
            ws.close()
            is_disconnect = True
            break

        if time() - start_time > 1200:
            ws.close()
            is_disconnect = True
            break            

        # if both users send more than 20 hi in conversation,
        # maybe two thread matchs together
        if hi_count >= 20:
            ws.close()
            is_disconnect = True
            break

        # receive message, if encounter timeout then start again
        try:
            message = ws.recv()
        except WebSocketTimeoutException:
            continue

        # set current time again
        start_time = time()
        if '42["say"' in message:
            # user sends us message
            m = re.search('42\["say","(.+?)"\]', message)
            if m:
                if i == '0':
                    # update message for second
                    second = m.group(1)
                elif i == '1':
                    # update message for first
                    first = m.group(1)
                # if message is 哈囉, add one to hi_count
                if m.group(1) == '哈囉':
                    hi_count += 1
            msg_count += 1
        elif '42["close",null]' in message:
            # close connection
            ws.close()
            is_disconnect = True
            break


def main():
    # clear text color
    print(Fore.RESET)

    global first
    first = None
    global second
    second = None
    global is_disconnect
    is_disconnect = False

    # create a pool
    pool = ThreadPool(2)
    # start first user
    pool.apply_async(bot, '0')
    # start second user after one second,
    # so they won't match together
    sleep(1)
    pool.apply_async(bot, '1')

    # close pool and wait for them to disconnect
    pool.close()
    pool.join()

if __name__ == '__main__':
    while True:
        main()
