# 链接热度抓取（macOS）

一个面向内部使用的 macOS 图形化链接热度抓取工具，支持批量读取今日头条、抖音链接并导出互动数据。程序已经打包为独立应用，使用者无需安装 Python、Selenium 或 ChromeDriver。

## 适用范围

- 当前发布包适用于 Apple Silicon Mac（arm64，M1/M2/M3/M4）。
- 本项目为内部工具，当前采用 ad-hoc 签名，不做 Apple Developer ID 签名和公证。
- 从 GitHub Release 下载后，macOS 可能将应用标记为“来自身份不明的开发者”。这是 Gatekeeper 的下载隔离提示，不代表程序一定包含恶意代码。

## 下载与首次运行

从 [Releases](https://github.com/Starlight-bananice/url-valid-mac/releases) 下载最新的 macOS arm64 ZIP，解压后按下面步骤首次打开。

### 解除下载隔离

1. 将 `链接热度抓取.app` 解压到“下载”文件夹，或记住它的实际位置。
2. 打开“终端”，执行以下命令：

   ```bash
   APP="$HOME/Downloads/链接热度抓取.app"
   xattr -dr com.apple.quarantine "$APP"
   open "$APP"
   ```

   如果应用不在“下载”文件夹，将 `APP=` 后面的路径替换成实际路径。例如应用位于桌面时：

   ```bash
   xattr -dr com.apple.quarantine "$HOME/Desktop/链接热度抓取.app"
   open "$HOME/Desktop/链接热度抓取.app"
   ```

3. 应用成功打开后，后续通常可以直接双击运行。

这条命令只移除当前电脑上这个已确认来源应用的下载隔离标记。请仅对本仓库 Release 下载、并由内部人员确认过的安装包执行，不要对来源不明的应用执行。

如果终端提示找不到文件，请检查应用名称和实际路径；可以把 `链接热度抓取.app` 从 Finder 拖到终端窗口，自动填入正确路径。

## 使用方法

1. 启动 `链接热度抓取.app`。
2. 选择 TXT、CSV 或 XLSX 文件，程序默认读取第一列链接；也可以直接粘贴链接。
3. 选择处理模式：
   - **链接 + 互动数据**：抓取链接状态、标题和可获取的互动数据；
   - **仅链接状态**：只判断链接是否可访问，速度更快。
4. 根据需要勾选验证码账号配置和断点续跑，然后点击“开始处理”。
5. 结果默认保存到：

   ```text
   ~/Documents/链接热度抓取/
   ```

程序会在用户目录保存进度、日志和浏览器缓存，不会把这些内容写进 `.app` 内部。批量任务中断后，可以使用断点续跑继续处理未完成链接。

## 浏览器与 Driver

程序内置 Selenium，并使用 [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/) 管理浏览器驱动：

- 如果系统已有 Google Chrome，优先使用系统 Chrome，并自动匹配对应 Driver；
- 如果系统没有 Chrome，首次运行时会尝试准备 stable Chrome for Testing；
- 首次运行或 Chrome 更新后可能需要联网；
- Driver 和浏览器缓存位于：

  ```text
  ~/Library/Application Support/URLHeat/selenium-cache
  ```

使用者不需要手动下载或更新 ChromeDriver。若公司网络限制下载，建议先使用已安装并可正常打开的 Google Chrome。

## 项目结构

| 文件 | 说明 |
| --- | --- |
| `app.py` | Tkinter 图形界面、文件选择、任务控制和日志显示 |
| `engine.py` | 链接读取、浏览器处理、断点续跑和结果导出逻辑 |
| `UrlHeat.spec` | PyInstaller macOS 应用打包配置 |
| `build_macos.sh` | 构建 arm64 `.app` 和 ZIP 的脚本 |
| `requirements-build.txt` | 构建所需 Python 依赖 |
| `settings.example.txt` | 配置文件示例 |

## 本地构建

当前构建脚本面向 Apple Silicon（arm64）macOS。构建机需要 Python、Tkinter 和联网环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./build_macos.sh
```

构建结果：

- `dist/链接热度抓取.app`
- `dist/链接热度抓取-macOS-arm64.zip`

Intel Mac 需要在 Intel 构建环境中单独打包。构建完成后，建议在没有 Python、Selenium 和 ChromeDriver 的干净 Mac 上测试首次启动、解除隔离和浏览器准备流程。

## 内部数据与安全

- 不要把真实链接、验证码账号、密码、日志、断点文件或结果文件提交到 GitHub。
- 验证码账号信息仅用于本机运行配置，程序不会将其写入仓库。
- 不要把 Apple Developer 证书、私钥或其他凭据提交到项目中。
- 本项目未配置自动联网上传用户数据；网络访问仅用于目标链接处理和 Selenium Manager 的浏览器组件准备。

## 许可证

当前仓库未附带开源许可证，默认不授予公开再分发、修改或商业使用权。如需对外开源，请先补充明确的许可证和使用范围。
