import requests
import json

def send_post_request(url, data, content_type='application/json'):
    """
    发送POST请求并返回响应内容
    
    :param url: 请求的URL
    :param data: 要发送的数据，字典格式
    :param content_type: 请求的Content-Type，默认为'application/json'
    :return: 响应的文本内容
    """
    # try:
    headers = {'Content-Type': content_type}
    # data = json.dumps(data, ensure_ascii= False).encode('utf-8')
        # if content_type == 'application/json':
            # data = json.dumps(data, ensure_ascii=False)
            
        # 打印实际发送的请求
    response = requests.request("POST", url, headers=headers, json=[data])
        # response.raise_for_status()  # 检查请求是否成功
    return "base64://" + response.text  # 返回响应的文本内容
        # return response.content
    # except requests.exceptions.HTTPError as http_err:
    #     print(f"HTTP error occurred: {http_err}")
    # except Exception as err:
    #     print(f"An error occurred: {err}")
    #     return None

def get_ai_meg(url, data, content_type='application/json'):
    headers = {'Content-Type': content_type}
    # data = json.dumps(data, ensure_ascii= False)
    response = requests.request("POST", url, headers=headers, json=data)
    response = json.loads(response.text)
    return response
if __name__ == '__main__':
    # url = 'http://server.zerohzzzz.top:5004/base64/'  # 替换为你的API URL
    # json_data = {
    #     "user_id": 3190381602,
    #     "user_nickname": "Zerohzzzz",
    #     "message": "找不同"
    # }
    # # data = json.dumps(json_data, ensure_ascii= False)
    # response_content = send_post_request(url, json_data)
    # print(response_content)
    url = 'http://rag:5005/ask/'
    json_data = {
        'msg' : "你好"
    }
    data = json.dumps(json_data, ensure_ascii= False)
    response_content = get_ai_meg(url, json_data)
    print(response_content)
