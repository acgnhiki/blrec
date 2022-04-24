@echo off
chcp 65001

set PATH=.\ffmpeg\bin;.\python;%PATH%

@REM 不使用代理
set no_proxy=*

@REM 主机和端口绑定，可以按需修改。
set host=0.0.0.0
set port=2233

@REM 关于 api key

@REM api key 可以使用数字和字母，长度限制为最短 8 最长 80。

@REM 3 次尝试内 api key 正确客户端 ip 会自动加入白名单，3 次错误后则 ip 会被加入黑名单，黑名单后请求会被拒绝 (403)。

@REM 黑名单和白名单数以及同时尝试连接的 ip 数量限制各为 100，黑名单或白名单到达限制后不再接受除了白名单内的其它 ip 。

@REM 只有重启才会清空黑名单和白名单。

@REM 浏览器第一次访问会弹对话框要求输入 api key。

@REM 输入的 api key 会被保存在浏览器的 local storage，下次使用同一浏览器不用再次输入。

@REM 请自行修改 api key，不要使用默认的 api key。
set api_key=bili2233

set DEFAULT_LOG_DIR=日志文件
set DEFAULT_OUT_DIR=录播文件

python -m blrec -c settings.toml --open --host %host% --port %port% --api-key %api_key%

pause
