@echo off
chcp 65001

set PATH=.\ffmpeg\bin;.\python;%PATH%

REM 不使用代理
set no_proxy=*

REM 默认本地主机和端口绑定
set host=localhost
set port=2233

REM 服务器主机和端口绑定，去掉注释并按照自己的情况修改。
REM set host=0.0.0.0
REM set port=80

set DEFAULT_LOG_DIR=日志文件
set DEFAULT_OUT_DIR=录播文件

python -m blrec -c settings.toml --open --host %host% --port %port%

pause
