import pandas as pd


def load_botmsg():
    """加载机器人回复内容到本地内存"""
    df = pd.read_excel('data.xls')
    
    botmsg = {}
    for _, row in df.iterrows():
        key = row[0]
        # value = row[1].replace('\\n', '\n')
        value = row[1]
        if key in botmsg:
            print(f'key {key} 重复')
        botmsg[key] = value
    
    print(f'botmsg 关键字加载完毕，共 {len(botmsg)} 条数据')
    # app.ctx.botmsg = botmsg
    print(botmsg["地址"])
load_botmsg()