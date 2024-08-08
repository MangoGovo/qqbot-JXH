# 精小弘 bot

## 介绍

-   使用的是 [Lagrange.OneBot](https://github.com/LagrangeDev/Lagrange.Core)
-   开箱即用，使用 docker 一键启动，使用的是反向 websocket
-   逻辑代码位于 [`ws/server.py`](ws/server.py) 文件
-   配置文件是 [`bot/appsettings.json`](bot/appsettings.json)

## 首次启动

```bash
docker compose up
```

然后扫码登录即可，会登录到 linux 平台

## 使用说明

### 基本指令

-   `/test`: 测试命令，管理员可用。
-   `/q`: 引用消息并生成图片。
-   `/ai <message>`: 调用 AI 接口处理消息。

### 管理命令

这些命令需要管理员权限。

-   `/admin 添加管理员 @user`: 添加管理员。
-   `/admin 移除管理员 @user`: 移除管理员。
-   `/admin 移除所有管理员`: 移除所有管理员。
-   `/admin 所有管理员`: 显示所有管理员。

-   `/admin 添加黑名单 @user`: 添加用户到黑名单。
-   `/admin 移除黑名单 @user`: 从黑名单中移除用户。
-   `/admin 移除所有黑名单`: 移除所有黑名单用户。
-   `/admin 所有黑名单`: 显示所有黑名单用户。

-   `/admin ban <duration> @user`: 禁言用户指定时间（秒）。
-   `/admin restart`: 重启机器人。

### 定时任务命令

这些命令需要管理员权限。

-   `/admin 定时任务 查看`: 查看当前定时任务列表。
-   `/admin 定时任务 添加 <每天|单次> <时间> <群聊ID> <消息内容>`: 添加定时任务。
-   `/admin 定时任务 移除 <任务编号>`: 移除指定的定时任务。

### 特殊命令

-   `/reload`: 重新加载机器人回复内容。
-   `bot`: 测试机器人在线情况
