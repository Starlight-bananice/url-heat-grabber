# 链接热度抓取（macOS）

这是一个面向普通 macOS 用户的图形界面版本。最终用户不需要单独安装 Python、Selenium 或 ChromeDriver。

## 浏览器与 Driver

程序内置 Selenium 和 Selenium Manager：

- 如果系统已有 Google Chrome，程序使用系统 Chrome，并自动匹配 Driver；
- 如果系统没有 Chrome，程序首次运行时尝试由 Selenium Manager 准备 stable Chrome for Testing；
- Driver 和浏览器缓存放在 `~/Library/Application Support/URLHeat/selenium-cache`；
- 首次运行需要联网，之后优先使用本地缓存。

## 使用方法

1. 双击 `链接热度抓取.app`。
2. 选择或粘贴 TXT、CSV、XLSX 链接。
3. 选择处理模式并点击“开始处理”。
4. 结果默认保存在 `~/Documents/链接热度抓取/`。

用户数据、进度、日志和缓存不写入 `.app` 内部。

## 本地构建

当前构建脚本面向 Apple Silicon（arm64）macOS。构建机需要 Python 3.13、Tkinter 和联网环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./build_macos.sh
```

构建结果：

- `dist/链接热度抓取.app`
- `dist/链接热度抓取-macOS-arm64.zip`

Intel Mac 需要在 Intel 构建环境中单独打包。发布前应在一台没有 Python、Selenium、ChromeDriver 的干净 Mac 上测试首次启动和浏览器准备流程。

当前本地构建为 ad-hoc 签名，适合验证；面向普通用户公开分发前，还需要使用 Apple Developer ID 签名并完成公证，否则 macOS 可能显示来源未验证提示。

不要把真实链接、验证码账号、密码、日志或结果文件提交到公开仓库。
