chcp 65001

$env:PATH = ".\ffmpeg\bin;.\python;" + $env:PATH

# 不使用代理
$env:no_proxy = "*"

# 主机和端口绑定，可以按需修改。
$env:host = "0.0.0.0"
$env:port = 2233

# 关于 api key
# api key 可以使用数字和字母，长度限制为最短 8 最长 80。
# 3 次尝试内 api key 正确客户端 ip 会自动加入白名单，3 次错误后则 ip 会被加入黑名单，黑名单后请求会被拒绝 (403)。
# 黑名单和白名单数以及同时尝试连接的 ip 数量限制各为 100，黑名单或白名单到达限制后不再接受除了白名单内的其它 ip 。
# 只有重启才会清空黑名单和白名单。
# 浏览器第一次访问会弹对话框要求输入 api key。
# 输入的 api key 会被保存在浏览器的 local storage，下次使用同一浏览器不用再次输入。
# 请自行修改 api key，不要使用默认的 api key。
$env:api_key = "bili2233"

$env:DEFAULT_LOG_DIR = "日志文件"
$env:DEFAULT_OUT_DIR = "录播文件"

python -m blrec -c settings.toml --open --host $env:host --port $env:port --api-key $env:api_key

pause
