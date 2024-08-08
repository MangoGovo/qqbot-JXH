import json
import random
import re
import requests
import base64
import pandas as pd
import schedule
import asyncio
import threading
import time
from sanic import Sanic
from sanic.log import logger
from request_quote import send_post_request, get_ai_meg
from datetime import datetime, timedelta

app = Sanic('qqbot')
app.ctx.last_ts = {}    # 记录每个人上次触发的时间戳
app.ctx.blocked = set() # 机器人允许使用的人员
app.ctx.admins = set()
app.ctx.blacklist = set()  # 黑名单
app.ctx.scheduled_jobs = []  # 存储所有定时任务
ADMIN_FILE_PATH = './data/admins.json'
BLACKLIST_FILE_PATH = './data/blacklist.json'
SCHEDULED_JOBS_FILE_PATH = './data/scheduled_jobs.json'
# global WS
@app.before_server_start
async def init_flag(app):
    """初始化开关"""
    app.ctx.flag = {
        '机器人': True,
        '回复': True,
        '指令': True,
    }

@app.before_server_start
async def load_admins(app):
    """加载管理员列表到本地内存"""
    try:
        with open(ADMIN_FILE_PATH, 'r+') as f:
            app.ctx.admins = set(json.load(f))
        logger.info(f'管理员列表加载完毕，共 {len(app.ctx.admins)} 个管理员')
    except FileNotFoundError:
        app.ctx.admins = set()
        logger.info('管理员文件未找到，初始化为空列表')

@app.before_server_start
async def load_blacklist(app):
    """加载黑名单到本地内存"""
    try:
        with open(BLACKLIST_FILE_PATH, 'r+') as f:
            app.ctx.blacklist = set(json.load(f))
        logger.info(f'黑名单加载完毕，共 {len(app.ctx.blacklist)} 个用户')
    except FileNotFoundError:
        app.ctx.blacklist = set()
        logger.info('黑名单文件未找到，初始化为空列表')

@app.before_server_start
async def load_botmsg(app):
    """加载机器人回复内容到本地内存"""
    df = pd.read_excel('./data/data.xlsx')

    botmsg = {}
    for _, row in df.iterrows():
        key = row.iloc[0]
        value = row.iloc[1]
        if key in botmsg:
            logger.error(f'key {key} 重复')
        botmsg[key] = value

    logger.info(f'botmsg 关键字加载完毕，共 {len(botmsg)} 条数据')
    app.ctx.botmsg = botmsg

@app.before_server_start
async def load_scheduled_jobs(app):
    """加载定时任务列表到本地内存"""
    try:
        with open(SCHEDULED_JOBS_FILE_PATH, 'r+') as f:
            app.ctx.scheduled_jobs = json.load(f)
        for job in app.ctx.scheduled_jobs:
            schedule_job(job)
        logger.info(f'定时任务列表加载完毕，共 {len(app.ctx.scheduled_jobs)} 个任务')
    except FileNotFoundError:
        app.ctx.scheduled_jobs = []
        logger.info('定时任务文件未找到，初始化为空列表')

def save_admins(app):
    """保存管理员列表到本地文件"""
    with open(ADMIN_FILE_PATH, 'w') as f:
        json.dump(list(app.ctx.admins), f)
    logger.info(f'管理员列表已保存，共 {len(app.ctx.admins)} 个管理员')

def save_blacklist(app):
    """保存黑名单到本地文件"""
    with open(BLACKLIST_FILE_PATH, 'w') as f:
        json.dump(list(app.ctx.blacklist), f)
    logger.info(f'黑名单已保存，共 {len(app.ctx.blacklist)} 个用户')

def save_scheduled_jobs(app):
    """保存定时任务列表到本地文件"""
    with open(SCHEDULED_JOBS_FILE_PATH, 'w') as f:
        json.dump(app.ctx.scheduled_jobs, f)
    logger.info(f'定时任务列表已保存，共 {len(app.ctx.scheduled_jobs)} 个任务')

def init_message(data):
    """初始处理消息体"""
    message_content = data['message']
    ats = set()
    message_parts = []

    for part in message_content:
        if part['type'] == 'text':
            text = part['data'].get('text', '')
            if text:
                message_parts.append(text)
        elif part['type'] == 'at':
            ats.add(part['data']['qq'])

    message = ' '.join(message_parts).strip()
    return message, ats, data

async def get_message(ws, message_id):
    # 获取信息，并返回一个字典类型的数据msg_data
    ret = {
        'action': 'get_msg',
        'params': {
            'message_id': message_id,
            }
        }
    await ws.send(json.dumps(ret))
    response = await ws.recv()
    return json.loads(response)['data']

async def restart_bot(ws):
    ret = {
        'action': 'set_restart',
        'params': {
            'delay': 200,
            }
    }
    await ws.send(json.dumps(ret))

async def ban(ws, group_id, user_id, duration):
    ret = {
        'action': 'set_group_ban',
        'params': {
            'group_id': int(group_id),
            'user_id': int(user_id),
            'duration': int(duration),
        }
    }
    await ws.send(json.dumps(ret))

async def process_admin_command(ws, message, ats, user_id, is_me, group_id):
    """机器人管理命令"""
    app = Sanic.get_app()
    # logger.info(app.ctx.admins)
    # 检查是否是管理员或者自己
    if user_id not in app.ctx.admins and not is_me:
        return "你没有权限执行此操作"
    msg = None
    
    if message in ['添加管理员', '移除管理员', '移除所有管理员', '所有管理员']:
        msg = await process_adminlist_command(message, ats)
    elif message in ['添加黑名单', '移除黑名单', '移除所有黑名单', '所有黑名单']:
        msg = await process_blacklist_command(message, ats)
    elif message == 'restart':
        await restart_bot(ws)
        msg = "Bot 开始重启"
    elif message[:2] == 'ban':
        msg = []
        for at in ats:
            await ban(ws, group_id, at, int(message[4:]))
            if int(message[4:]) == 0:
                msg.append(f'解除禁言\n: {at}')
            else:
                msg.append(f'禁言: {at} {int(message[4:])}秒\n')
    elif message[:4] == '定时任务':
        # logger.info(message[6:])
        if message[5:7] == '查看':
            msg = await view_scheduled_jobs()
        elif message[5:7] == '添加':
            msg = await add_scheduled_job(message[8:].strip())
        elif message[5:7] == '移除':
            msg = await remove_scheduled_job(int(message[8:].strip()))
    return msg

async def process_adminlist_command(message, ats):
    app = Sanic.get_app()
    msg = None
    if message == '添加管理员':
        msg = []
        for at in ats:
            app.ctx.admins.add(int(at))
            msg.append(f'已添加管理员: {at}')
        msg = '\n'.join(msg)
        save_admins(app)
    elif message == '移除管理员':
        msg = []
        for at in ats:
            app.ctx.admins.discard(int(at))
            msg.append(f'已移除管理员: {at}')
        msg = '\n'.join(msg)
        save_admins(app)
    elif message == '移除所有管理员':
        app.ctx.admins = set()
        msg = "已经移除所有管理员"
        save_admins(app)
    elif message == '所有管理员':
        msg = '\n'.join(map(str, app.ctx.admins))
        if msg == "":
            msg = "~管理员现在只有我自己✌~"
    return msg

async def process_blacklist_command(message, ats):
    """黑名单管理命令"""
    app = Sanic.get_app()
    msg = None
    if message == '添加黑名单':
        msg = []
        for at in ats:
            if int(at) in app.ctx.admins:
                msg.append(f'无法添加管理员 {at} 到黑名单')
            else:
                app.ctx.blacklist.add(int(at))
                msg.append(f'已添加黑名单: {at}')
        msg = '\n'.join(msg)
        save_blacklist(app)
    elif message == '移除黑名单':
        msg = []
        for at in ats:
            app.ctx.blacklist.discard(int(at))
            msg.append(f'已移除黑名单: {at}')
        msg = '\n'.join(msg)
        save_blacklist(app)
    elif message == '移除所有黑名单':
        app.ctx.blacklist = set()
        msg = "已经移除所有黑名单"
        save_blacklist(app)
    elif message == '所有黑名单':
        msg = '\n'.join(map(str, app.ctx.blacklist))
        if msg == "":
            msg = "~黑名单现在是空的~"
    return msg

async def process_test_command(ws, data):
    """处理 /test 命令"""
    message_content = data.get("message", [])
    if message_content[0].get("type") == "reply":
        msg = await get_message(ws, message_content[0]['data']['id'])
        return json.dumps(msg, indent=4, ensure_ascii=False)
    return json.dumps(data, indent=4, ensure_ascii=False)

def generate_q_message(data):
    # 生成quote消息体
    user_nickname = data['sender']['nickname']
    msg = {
        "user_nickname": user_nickname,
    }
    message = ""
    image = []
    for msg_part in data['message']:
        if msg_part['type'] == "text":
            if msg_part['data']['text'] is not None:
                message += msg_part['data']['text']
        elif msg_part['type'] == "image":
            image.append(msg_part['data']['file'])
    if message:
        msg["message"] = message
    if image:
        msg["image"] = image
    return msg

async def process_q_command(ws, data):
    message_content = data.get("message", [])
    if message_content[0].get("type") == "reply":
        q_data = await get_message(ws, message_content[0]['data']['id']) # /q 引用的消息内容
        requests_body = generate_q_message(q_data)
        requests_body['user_id'] = q_data['sender']['user_id']
        q_message_content = q_data.get("message", [])
        q_message_mention_data = None
        if q_message_content[0].get("type") == "reply":
            q_message_mention_data = await get_message(ws, q_message_content[0]['data']['id']) # /q 引用的消息引用的消息
            requests_body['reply'] = generate_q_message(q_message_mention_data)
        url = 'http://quote:5000/base64/'
        pic = send_post_request(url, requests_body)
        msg = {
            "type": "image",
            "data": {
                "file": pic
            }
        }
        return msg

def key_word(message):
    key = message.lower().replace('()', '').strip()
    msg = app.ctx.botmsg.get(key)
    return msg

async def process_ai_command(message):
    json_data = {
        'msg': message,
    }
    url = 'http://rag:5005/ask/'
    reponse = get_ai_meg(url, json_data)
    logger.info(reponse)
    return reponse['data']['response']

async def view_scheduled_jobs():
    app = Sanic.get_app()
    if not app.ctx.scheduled_jobs:
        return "~当前没有定时任务~"
    msg = "当前定时任务列表:\n"
    now = datetime.now()
    for i, job in enumerate(app.ctx.scheduled_jobs):
        job_time = datetime.strptime(job['time'], '%H:%M').time()
        if job['type'] == '每天':
            scheduled_time = datetime.combine(now, job_time)
            if scheduled_time < now:
                scheduled_time += timedelta(days=1)
        elif job['type'] == '单次':
            scheduled_time = datetime.combine(now, job_time)
        
        time_remaining = scheduled_time - now
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        msg += f"{i + 1}. {job['description']} (剩余时间: {hours}小时{minutes}分钟)\n"
    return msg


async def send_group_message(group_id, job_message, tag):
    ret = {
        'action': 'send_group_msg',
        'params': {
            'group_id': int(group_id),
            'message': job_message,
            }
        }
    await WS.send(json.dumps(ret))
    
    # 找到任务并移除
    app = Sanic.get_app()
    job_to_remove = None
    for job in app.ctx.scheduled_jobs:
        if job['tag'] == tag:
            job_to_remove = job
            break
    if job_to_remove and job_to_remove['type'] == '单次':
        app.ctx.scheduled_jobs.remove(job_to_remove)
        save_scheduled_jobs(app)

    schedule.clear(tag)


async def add_scheduled_job(message):
    app = Sanic.get_app()
    parts = message.split()
    if len(parts) < 4:
        return "格式错误，应为: 定时任务 添加 <每天|单次> <时间> <群聊ID> <消息内容>"
    job_type, time_str, group_id, job_message = parts[0], parts[1], parts[2], ' '.join(parts[3:])
    if job_type not in ["每天", "单次"]:
        return "任务类型错误，应为: 每天 或 单次"

    job_desc = f"{job_type} {time_str} 发送消息到群 {group_id}: {job_message}"
    job = {"description": job_desc, "type": job_type, "time": time_str, "message": job_message, "group_id": int(group_id)}

    loop = asyncio.get_event_loop()

    tag = f"{job_type}_{time_str}_{group_id}_{random.randint(1, 10000)}"
    job['tag'] = tag
    if job_type == "每天":
        schedule.every().day.at(time_str).do(lambda: asyncio.run_coroutine_threadsafe(send_group_message(int(group_id), job_message, tag), loop)).tag(tag)
    elif job_type == "单次":
        schedule.every().day.at(time_str).do(lambda: asyncio.run_coroutine_threadsafe(send_group_message(int(group_id), job_message, tag), loop)).tag(tag)

    app.ctx.scheduled_jobs.append(job)
    save_scheduled_jobs(app)
    return f"定时任务已添加: {job_desc}"


async def remove_scheduled_job(job_index):
    app = Sanic.get_app()
    if job_index < 1 or job_index > len(app.ctx.scheduled_jobs):
        return "无效的任务编号"

    job = app.ctx.scheduled_jobs.pop(job_index - 1)
    schedule.clear(job['tag'])

    save_scheduled_jobs(app)
    return f"定时任务已移除: {job['description']}"

def schedule_job(job):
    """根据任务数据调度任务"""
    group_id = job['group_id']
    job_message = job['message']
    logger.info(job['group_id'])
    logger.info(job['message'])

    loop = asyncio.get_event_loop()

    tag = job.get('tag', f"{job['type']}_{job['time']}_{group_id}_{random.randint(1, 10000)}")
    if job['type'] == "每天":
        logger.info(job['type'])
        schedule.every().day.at(job['time']).do(lambda: asyncio.run_coroutine_threadsafe(send_group_message(group_id, job_message, tag), loop)).tag(tag)
    elif job['type'] == "单次":
        logger.info(job['type'])
        schedule.every().day.at(job['time']).do(lambda: asyncio.run_coroutine_threadsafe(send_group_message(group_id, job_message, tag), loop)).tag(tag)

@app.websocket('/qqbot')
async def qqbot(request, ws):
    global WS
    WS = ws
    # schedule.run_pending()
    app = request.app
    while True:
        schedule.run_pending()
        data = await ws.recv()
        data = json.loads(data)
        is_me = False
        # 判断是不是自己发的信息
        if 'user_id' in data and 'self_id' in data:
            is_me = data['user_id'] == data['self_id']
        user_id = data.get('user_id')
        # 检查用户是否在黑名单中
        if user_id in app.ctx.blacklist:
            continue
        # 机器人关闭时，仅自己可用
        if app.ctx.flag['机器人'] is False:
            if not is_me:
                continue

        msg = None
        if data.get('message_type') == 'group' and data.get('raw_message'):
            message, ats, data = init_message(data)
            group_id = data['group_id']
            if message == '/test':
                await send_group_message(group_id, "ddd", 'test_tag')
                # if user_id in app.ctx.admins:
                #     msg = await process_test_command(ws, data)
                # else:
                #     msg = "~你好像没有权限执行该项操作耶~"
            elif message == '/q':
                msg = await process_q_command(ws, data)
            elif message[:6] == '/admin':
                msg = await process_admin_command(ws, message[7:], ats, user_id, is_me, group_id)
            elif message[:3] == '/ai' and not is_me:
                msg = await process_ai_command(message[4:])
            elif message == '/reload':
                await load_botmsg(app)
                msg = "重载成功"
            if msg is None and not is_me:
                msg = key_word(message)
        elif data.get('post_type') == 'notice' and data.get('notice_type') == 'group_increase':
            group_id = data['group_id']
            msg = [
                {
                    "type": "at",
                    "data": {
                        "qq": str(data['user_id'])
                    },
                },
                {
                    "type": "text",
                    "data": {
                        "text": "欢迎来到浙江工业大学，精弘网络欢迎各位的到来！\n输入 菜单 获取精小弘机器人的菜单 哦！\n请及时修改群名片\n格式如下：专业/大类+姓名"
                    }
                }
            ]
        if msg:
            ret = {
                'action': 'send_group_msg',
                'params': {
                    'group_id': group_id,
                    'message': msg,
                }
            }
            await ws.send(json.dumps(ret))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, auto_reload=True, workers=7)
