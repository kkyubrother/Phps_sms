# -*- coding: utf-8 -*-
''' Php school SMS module

This module send sms to Phps.
:original: www.phps.kr
'''

import re
import datetime
from typing import List
from collections import namedtuple

from requests import get as req_get, post as req_post
from phpserialize import loads as php_loads


IP_CHECK_URL    = 'https://api.ipify.org'
SERVER_URL      = 'https://sms.phps.kr/lib/send.sms'
SERVER_ENCODING = 'euc-kr'

PATTERN_NUM = re.compile(r'^(?P<num0>0\d0)?[\s\-\.]?(?P<num1>\d{3,4})[\s\-\.]?(?P<num2>\d{4})$')


class SMSError(Exception):
    message = None

    def __init__(self, message: str):
        self.message = message

class SMSData(namedtuple('SMSData', ['tr_to', 'tr_txtmsg'])):
    """SMS 정보입니다.

    :param tr_to: 메시지를 받는 사람의 번호(수신자 번호)
    :param tr_txtmsg: 메시지 내용
    """
    pass


class SMS():
    """SMS 전송용 모듈입니다.

    :param tr_id: 서비스를 이용하기 위한 SMS ID (신청시 등록한 계정ID)
    :param tr_key: SMS 서비스를 이용하기위한 인증키, [SMS호스팅관리]-[SMS접속정보]에서 확인가능
    :param tr_from: 메시지에 보낸사람으로 표시되는 번호(발신자 번호)
    :param tr_ip: 전송할 서버의 ip, 기본값은 'https://api.ipify.org'을 통해 가져옴

    :raises SMSError: 입력값이 잘못됨
    """
    __tr_id = None
    __tr_key = None
    __tr_from = None
    __tr_ip = None
    __data = None

    def __init__(self, tr_id: str, tr_key: str, tr_from: str, tr_ip: str=None) -> None:
        self.__tr_id    = tr_id
        self.__tr_key   = tr_key
        self.__tr_from  = tr_from
        self.__data     = list()

        if tr_ip is None:
            self.__tr_ip = req_get(IP_CHECK_URL).text
        else:
            self.__tr_ip = tr_ip

    def add(self, tr_to: str, tr_txtmsg: str, auto_slice: bool=False) -> None:
        """메시지를 추가한다

        :param tr_to: 메시지를 받는 사람의 번호(수신자 번호)
        :param tr_txtmsg: 메시지 내용
        :param auto_slice: 90byte 초과일 때 자동으로 끊어 보낸다. 기본값은 False

        :raises SMSError: 올바르지 않은 수신자 번호
        :raises SMSError: 메시지 내용이 없다
        :raises SMSError: 메세지가 너무 길다(auto_slice가 False일 때 한정)
        """
        tr_to = _valid_tr_to(tr_to=tr_to)

        txt_bytes = tr_txtmsg.strip().encode(SERVER_ENCODING)

        if len(txt_bytes) == 0:
            raise SMSError('tr_txtmsg is empty.')

        elif len(txt_bytes) > 90:
            if not auto_slice:
                raise SMSError('tr_txtmsg is too long.')

            for txt_bytes in _slice_tr_txtmsg(tr_txtmsg=tr_txtmsg):
                self.__data.append(SMSData(tr_to, txt_bytes))

        else:
            self.__data.append(SMSData(tr_to, txt_bytes))

    def get(self) -> List[SMSData]:
        """추가한 메시지 목록을 가져온다.

        :return: 추가된 메시지 내역
        :rtype: List[SMSData]
        """
        return [SMSData(to, txt.decode(SERVER_ENCODING)) for to, txt in self.__data]

    def view(self) -> dict:
        """현재 상태를 확인한다.

        :return: 서버 응답 내역
        :rtype: dict
        """
        datas = {
            'adminuser': self.__tr_id,
            'authkey': self.__tr_key,
            'type': 'view',
        }
        res = req_post(SERVER_URL, data=datas)
        return _decode_response(res.content)

    def cancel(self, tr_num: int) -> dict:
        """보내기로 예약한 메시지를 취소한다.

        :param tr_num: 예약 메시지 번호

        :return: 서버 응답 내역
        :rtype: dict
        """
        d = datetime.datetime.now() + datetime.timedelta(days=1)

        datas    = {
            'adminuser':    self.__tr_id,
            'authkey':      self.__tr_key,
            'date':         d.strftime('%Y-%m-%d %H:%M:%S'),
            'tr_num':       tr_num
        }

        res = req_post(SERVER_URL, data=datas)
        return _decode_response(res.content)

    def send(self, tr_date: datetime.datetime=None, tr_comment: str=None) -> List[dict]:
        """메시지를 발송한다.

        :param tr_date: 해당 일시에 발송한다.
        :param tr_comment: 해당 발송에 대해 메모한다.

        :return: 서버 응답 내역
        :rtype: List[dict]
        """
        if not self.__data:
            raise SMSError('no data')
        
        if tr_date is None:
            tr_date_str = 0

        elif tr_date < (datetime.datetime.now() +  datetime.timedelta(minutes=3)):
            raise SMSError("Message reservation must be longer than 3 minutes.")

        else:
            tr_date_str = tr_date.strftime('%Y-%m-%d %H:%M:%S')
        
        if tr_comment is None:
            tr_comment = ''

        elif isinstance(tr_comment, str):
            tr_comment = tr_comment.encode(SERVER_ENCODING)

        result_list = list()
        for tr_to, tr_msgtxt_enc in self.__data:
            post    = {
                'adminuser':    self.__tr_id,
                'authkey':      self.__tr_key,
                'rphone':       self.__tr_from,
                'phone':    tr_to,
                'sms':      tr_msgtxt_enc,
                'date':     tr_date_str,
                'msg':      tr_comment,
                'ip':       self.__tr_ip,
            }

            res = req_post(SERVER_URL, data=post)
            result_list.append(_decode_response(res.content))

        self.__data.clear()
        return result_list


def _valid_tr_to(tr_to: str) -> str:
    """tr_to를 확인하고 올바른 형식을 반환한다.

    :param tr_to: 수신자 휴대폰 번호

    :raises SMSError: 올바르지 않은 전화번호

    :return: 올바른 형식의 전화번호
    :rtype: str
    """

    num_res = PATTERN_NUM.match(tr_to.strip())

    if not num_res:
        raise SMSError(f"`{tr_to}` is not correct number.")

    num_dict = num_res.groupdict()
    num0 = num_dict['num0'] if num_dict.get('num0') else '010'
    return num0 + '-' + num_dict['num1'] + '-' + num_dict['num2']


def _slice_tr_txtmsg(tr_txtmsg: str) -> List[bytes]:
    """tr_txtmsg를 길이에 맞게 잘라 반환한다.

    :param tr_txtmsg: 메시지 본문

    :return: 자르고 인코딩된 메시지 본문
    :rtype: List[bytes]
    """
    txt_list = list(tr_txtmsg)
    temp_sliced = list()
    popped = list()

    while txt_list:
        popped.append(txt_list.pop(0))

        if len(popped) > 44:
            t = ''.join(popped)
            e = t.encode(SERVER_ENCODING)
            l = len(e)
            if l == 89 or l == 90:
                temp_sliced.append(e)
                popped.clear()

    if popped:
        temp_sliced.append((''.join(popped)).encode(SERVER_ENCODING))

    return temp_sliced

def _decode_response(content: bytes) -> dict:
    r = dict()
    for k, v in php_loads(content).items():
        try:
            k = k.decode('utf-8')
        except AttributeError:
            pass
        try:
            v = v.decode('utf-8')
        except AttributeError:
            pass
        r[k] = v
    return r
