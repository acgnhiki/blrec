# Bilibili Live Streaming Recorder (blrec)

这是一个前后端分离的 B 站直播录制工具。前端使用了响应式设计，可适应不同的屏幕尺寸；后端是用 Python 写的，可以跨平台运行。

这个工具是自动化的，会自动完成直播的录制, 在出现未处理异常时会发送通知，空间不足能够自动回收空间，还有详细日志记录，因此可以长期无人值守运行在服务器上。

## 屏幕截图

![webapp](https://user-images.githubusercontent.com/33854576/128959800-451d03e7-c9f9-4732-ac90-97fdb6b88972.png)

![terminal](https://user-images.githubusercontent.com/33854576/128959819-70d72937-65da-4c15-b61c-d2da65bf42be.png)

## 功能

- 自动完成直播录制
- 同步保存弹幕
- 自动修复时间戳问题：跳变、反跳等。
- 直播流参数改变自动分割文件，避免出现花屏等问题。
- 流中断自动拼接且支持 **无缝** 拼接，不会因网络中断而使录播文件片段化。
- `flv` 文件添加关键帧等元数据，使定位播放和拖进度条不会卡顿。
- 可选录制的画质
- 可自定义文件保存路径和文件名
- 支持按文件大小或时长分割文件
- 支持转换 `flv` 为 `mp4` 格式（需要安装 `ffmpeg`）
- 硬盘空间检测并支持空间不足自动删除旧录播文件。
- 事件通知（支持邮箱、`ServerChan`、`pushplus`）
- `Webhook`（可配合 `REST API` 实现录制控制，录制完成后压制、上传等自定义需求）

## 先决条件

    Python 3.8+
    ffmpeg (如果需要转换 flv 为 mp4)

## 安装

- 通过 pip 或者 pipx 安装

    `pip install blrec` 或者 `pipx install blrec`

    使用的一些库需要自己编译，Windows 没安装 C / C++ 编译器会安装出错，
    参考 [Python Can't install packages](https://stackoverflow.com/questions/64261546/python-cant-install-packages) 先安装好 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)。

- 免安装绿色版

    Windows 64 位系统用户也可以用打包好的免安装绿色版，下载后解压运行 `run.bat` 即可。

    下载

    - Releases: https://github.com/acgnhiki/blrec/releases
    - 网盘: https://gooyie.lanzoui.com/b01om2zte  密码: 2233

## 更新

- 通过 pip 或者 pipx 安装的用以下方式更新

    `pip install blrec --upgrade` 或者 `pipx upgrade blrec`

- 免安装绿色版

    - 下载并解压新版本
    - 确保旧版本已经关闭退出以避免之后出现端口冲突
    - 把旧版本的设置文件 `settings.toml` 复制并覆盖新版本的设置文件
    - 运行新版本的 `run.bat`

## 卸载

- 通过 pip 或者 pipx 安装的用以下方式卸载

    `pip uninstall blrec` 或者 `pipx uninstall blrec`

- 免安装绿色版

    删除解压后的文件夹

## 使用方法

### 使用默认设置文件和保存位置

在命令行终端里执行 `blrec` ，然后浏览器访问 `http://localhost:2233`。

设置文件为 `toml` 文件，默认位置在 `~/.blrec/settings.toml`。默认录播文件保存位置为当前工作目录 `.`。

### 指定设置文件和保存位置

`blrec -c path/to/settings.toml -o dirpath/to/save/files`

如果指定的设置文件不存在会自动创建。通过命令行参数指定保存位置会覆盖掉设置文件的设置。

### 绑定主机和端口

默认为本地运行，主机和端口绑定为： `localhost:2233`

需要外网访问，把主机绑定到 `0.0.0.0`，端口绑定则按照自己的情况修改。

例如：`blrec --host 0.0.0.0 --port 8000`

### 安全保障

指定 `SSL` 证书使用 **https** 协议并指定 `api key` 可防止被恶意访问和泄漏设置里的敏感信息

例如：`blrec --key-file path/to/key-file --cert-file path/to/cert-file --api-key bili2233`

如果指定了 api key，浏览器第一次访问会弹对话框要求输入 api key。

输入的 api key 会被保存在浏览器的 `local storage` 以避免每次都得输入

如果在不信任的环境下，请使用浏览器的隐式模式访问。

## 作为 ASGI 应用运行

    uvicorn blrec.web:app

或者

    hypercorn blrec.web:app

作为 ASGI 应用运行，参数通过环境变量指定。

- `config` 指定设置文件
- `out_dir` 指定保存位置
- `api_key` 指定 `api key`

### bash

    config=path/to/settings.toml out_dir=path/to/dir api_key=******** uvicorn blrec.web:app --host 0.0.0.0 --port 8000

### cmd

    set config=D:\\path\\to\\config.toml & set out_dir=D:\\path\\to\\dir & set api_key=******** uvicorn blrec.web:app --host 0.0.0.0 --port 8000

## Webhook

程序在运行过程中会触发一些事件，如果是支持 `webhook` 的事件，就会给所设置的 `webhook` 网络地址发送 POST 请求。

关于支持的事件和 `POST` 请求所发送的数据，详见 wiki。

## REST API

后端 `web` 框架用的是 `FastApi` , 要查看自动生成的交互式 `API` 文档，访问 `http://localhost:2233/docs` （默认主机和端口绑定）。

## Progressive Web App（PWA）

前端其实是一个渐进式网络应用，可以通过地址栏右侧的图标安装，然后像原生应用一样从桌面启动运行。

**注意：PWA 要在本地访问或者在 `https` 下才支持。**

---

## 常见问题

[FAQ](FAQ.md)

## 更新日志

[CHANGELOG](CHANGELOG.md)

---

## Thanks

[![JetBrains Logo (Main) logo](https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.svg)](https://jb.gg/OpenSource)
