import json

import requests


def send_post_request(url, data, content_type='application/json'):
    """
    发送POST请求并返回响应内容
    
    :param url: 请求的URL
    :param data: 要发送的数据，字典格式
    :param content_type: 请求的Content-Type，默认为'application/json'
    :return: 响应的文本内容
    """
    headers = {'Content-Type': content_type}
    response = requests.request("POST", url, headers=headers, json=[data])
    return "base64://" + response.text  # 返回响应的文本内容
