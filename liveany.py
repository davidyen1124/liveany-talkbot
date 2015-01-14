from time import time
import json
import re
from multiprocessing.pool import ThreadPool
from time import time, sleep

import requests
from websocket import create_connection, WebSocketTimeoutException
from redis import Redis

redis = Redis()

LIVEANY_URL = 'http://ws.liveany.com:18089/socket.io/'
WS_URL = 'ws://ws.liveany.com:18089/socket.io/?lang=zh-tw&platform=web&EIO=3&transport=websocket&sid={}'


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
        't': '{}-0'.format(int(time() * 1000))
    }
    res = requests.get(LIVEANY_URL, params=params, headers=headers)
    # first five words are useless
    data = json.loads(res.text[5:])
    # get sid
    return data.get('sid')


def bot(i):
    '''A bot that get and send messages.'''
    # record how many messages has been sent
    msg_count = 0

    # save current time before connection to server
    start_time = time()

    # connect to server
    ws = create_connection(WS_URL.format(get_token()))
    # set timeout as one second, so it won't block in recv()
    ws.settimeout(1)

    # initialize connection with anonymous
    ws.send('2probe')
    message = ws.recv()
    if message == '3probe':
        ws.send('5')
    print(i, 'start')

    # send hello to user
    ws.send('42["say","{}"]'.format('哈囉'))

    # get messages in infinity loop
    while True:
        # if is_disconnect is 1, then close the connection
        if redis.get('is_disconnect') == b'1':
            ws.close()
            break

        # get message that we should send
        first = redis.get('first')
        second = redis.get('second')
        if i == '0' and first:
            # convert byte string to unicode string
            first = first.decode('utf-8')
            # send message to user
            ws.send('42["say","%s"]' % (first))
            # clear first in redis
            redis.delete('first')
            print('1:', first)
        if i == '1' and second:
            # convert byte string to unicode string
            second = second.decode('utf-8')
            # send message to user
            ws.send('42["say","%s"]' % (second))
            # clear second in redis
            redis.delete('second')
            print('2:', second)

        # if user hasn't sent more that three messages,
        # and they don't speak for thrity seconds then disconnect!
        if msg_count < 3 and time() - start_time > 30:
            ws.close()
            redis.set('is_disconnect', '1')
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
                    redis.set('second', m.group(1))
                elif i == '1':
                    # update message for first
                    redis.set('first', m.group(1))
            msg_count += 1
        elif '42["close",null]' in message:
            # close connection
            ws.close()
            redis.set('is_disconnect', '1')
            break


def main():
    # delete first, second, is_disconnect in redis
    redis.delete('first')
    redis.delete('second')
    redis.set('is_disconnect', '0')

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
