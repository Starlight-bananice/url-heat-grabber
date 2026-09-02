# 链接热度抓取工具

一个适用于 macOS 和 Windows 的图形化链接处理工具。它可以批量判断链接是否可访问，并按需抓取今日头条、抖音等页面的点赞、评论、收藏、分享、播放/阅读等互动数据。

这是一个面向内部使用的工具。普通使用者只需要下载对应系统的压缩包，不需要安装 Python、Selenium 或 ChromeDriver。

## 一、下载哪个版本

打开 [GitHub Releases](https://github.com/Starlight-bananice/url-heat-grabber/releases)，选择最新版本：

| 电脑 | 下载文件 | 适用范围 |
| --- | --- | --- |
| Apple Silicon Mac | 文件名包含 `macOS-arm64` | M1、M2、M3、M4 等芯片 |
| Windows 电脑 | 文件名包含 `windows-x64` | Windows 10/11 64 位 |

如果不确定 Mac 芯片类型：点击左上角苹果菜单 →“关于本机”。显示“芯片”为 Apple 的，下载 macOS arm64 版本；显示“处理器”为 Intel 的，当前版本不能直接使用。

## 二、macOS 第一次打开

### 1. 下载并解压

1. 下载文件名包含 `macOS-arm64` 的 ZIP 文件。
2. 双击 ZIP 解压。
3. 解压后应看到 `链接热度抓取.app`。
4. 可以把它拖到“应用程序”文件夹，也可以直接放在“下载”文件夹。

### 2. 解除 macOS 下载隔离

由于当前版本是内部使用的 ad-hoc 签名版本，macOS 第一次打开时可能提示“Apple 无法验证……”。右键“打开”仍可能无法通过，这时请按下面步骤操作：

1. 打开“终端”：按 `Command + 空格`，搜索“终端”，按回车。
2. 复制下面三行命令到终端，按回车：

   ```bash
   APP="$HOME/Downloads/链接热度抓取.app"
   xattr -dr com.apple.quarantine "$APP"
   open "$APP"
   ```

3. 如果你把应用放在“应用程序”文件夹，使用下面的命令：

   ```bash
   APP="/Applications/链接热度抓取.app"
   xattr -dr com.apple.quarantine "$APP"
   open "$APP"
   ```

4. 如果应用在其他位置，把 `APP=` 后面的路径改成实际路径。最简单的方法是：先输入 `xattr -dr com.apple.quarantine `（最后有一个空格），再把 `链接热度抓取.app` 从 Finder 拖到终端窗口，最后按回车。
5. 看到程序窗口后，说明打开成功。以后通常可以直接双击运行。

这条命令只移除当前 Mac 对这个应用副本的下载隔离标记。请仅对本仓库 Releases 下载、并确认来源可靠的文件执行，不要对来源不明的应用执行。

### 3. macOS 常见提示

- 如果终端提示“找不到文件”，说明 `APP` 路径不正确，请按上面的拖拽方式重新填路径。
- 如果程序没有窗口，先从程序坞完全退出，再重新运行。
- 首次处理链接时可能需要联网准备浏览器组件，请不要立刻强制退出。

## 三、Windows 第一次打开

### 1. 下载并解压

1. 下载文件名包含 `windows-x64` 的 ZIP 文件。
2. 右键 ZIP →“全部解压缩”→“解压”。
3. 打开解压后的文件夹，双击 `链接热度抓取.exe`。

### 2. 处理 Windows 安全提示

如果 Windows Defender SmartScreen 显示“Windows 已保护你的电脑”：

1. 先确认文件是从本仓库的 Releases 下载的。
2. 点击“更多信息”。
3. 点击“仍要运行”。

Windows 版本不需要安装 Python、Selenium 或 ChromeDriver。首次运行或 Chrome 更新后可能需要联网准备浏览器组件。

## 四、准备要处理的链接

每个链接占一行。可以使用以下任一种方式：

### 方式 A：直接粘贴

打开程序后，把链接复制到窗口中间的“链接”文本框，每行一个链接。

### 方式 B：导入 TXT 或 CSV

新建一个 TXT 或 CSV 文件，每行放一个链接，例如：

```text
https://www.toutiao.com/article/示例链接1
https://www.douyin.com/video/示例链接2
```

点击程序中的“选择并加载”，选择文件即可。

### 方式 C：导入 XLSX

把链接放在 Excel 文件的第一列，然后点击“选择并加载”。程序默认读取第一列的非空内容；如果第一行是“链接”这样的表头，也建议删掉表头，避免把表头当成一条待处理内容。

## 五、第一次使用：按界面逐项填写

打开程序后，按照从上到下的顺序操作：

### 第 1 步：选择输入文件

点击“选择并加载”，选择 TXT、CSV 或 XLSX 文件。

加载成功后，中间的大文本框会显示链接数量和内容。也可以不选择文件，直接把链接粘贴到文本框。

### 第 2 步：确认输出目录

“输出目录”是结果 Excel 的保存位置。默认位置是：

- macOS：`~/Documents/链接热度抓取/`
- Windows：`C:\Users\你的用户名\Documents\链接热度抓取\`

如果要换位置，点击“选择目录”。

### 第 3 步：选择处理模式

- **链接 + 互动数**：判断链接并尽量抓取互动数据，处理时间较长；需要点赞、评论等数据时选择此项。
- **仅判断链接**：只判断链接能否打开，速度更快；只需要筛查链接时选择此项。

第一次测试建议先使用“仅判断链接”，用少量链接确认程序可以正常运行。

### 第 4 步：设置验证码辅助

通常不需要勾选“验证码辅助”。只有内部流程明确要求使用验证码平台时才勾选：

1. 勾选“验证码辅助”。
2. 填写账号和密码。
3. 确认账号有权限并且余额/服务可用。

账号信息只写入当前电脑的 URLHeat 配置目录，不会提交到 GitHub；但它仍属于敏感信息，请不要在截图、日志或反馈消息中公开。

### 第 5 步：设置断点续跑

“从上次进度继续”默认勾选，建议保持勾选。任务中断、电脑休眠或浏览器出错后，再次导入同一批链接并点击开始，程序会尽量跳过已经完成的内容。

如果你希望完整重新处理一批链接，可以取消勾选后再开始。

### 第 6 步：设置头条并发

“头条并发”建议保持默认值 `2`：

- `1`：最稳，速度较慢；
- `2`：推荐设置；
- `3`：速度更快，但更容易遇到页面或平台限制。

抖音并发固定为 `1`，这是为了降低连续请求触发风控的概率，不需要手动调整。

### 第 7 步：开始处理

点击“开始处理”。运行日志会显示当前进度，例如 `已完成 20/100`。

处理过程中：

- 不要频繁点击“开始处理”；
- 不要同时启动多个本程序窗口；
- 可以点击“停止（完成当前页后停止）”安全停止；
- 停止后请等待日志显示结果已经保存，再关闭窗口。

## 六、查看结果

处理完成后，点击“打开结果目录”，或直接打开之前设置的输出目录。

结果是 Excel 文件，文件名通常类似：

```text
链接判断结果_2026-09-02__15-30-00.xlsx
```

常见列包括：

- 链接
- 链接状态
- 点赞
- 评论/回复
- 收藏
- 分享/转发
- 播放/阅读

有些页面需要登录、加载失败或受到平台限制，对应互动数据可能为空；这不一定代表链接本身失效。

## 七、出错后怎么处理

### 出现 `WebDriverException`

这通常表示浏览器驱动、浏览器页面或目标页面在本次请求中没有正常响应。建议按以下顺序处理：

1. 等待几分钟，不要立即连续重跑。
2. 确认网络正常，Chrome 可以手动打开。
3. 关闭其他正在大量打开页面的自动化程序。
4. 重新导入同一批链接，保持“从上次进度继续”勾选。
5. 将“头条并发”改为 `1` 后再次运行。

### 提示找不到 ChromeDriver

正常情况下不需要手动下载 ChromeDriver。程序会使用 Selenium Manager 自动匹配或准备驱动。请先确认网络可用；如果公司网络限制下载，优先安装并打开系统 Google Chrome 后再运行。

### 只有部分链接失败

不同平台的登录状态、页面结构、访问频率和反爬限制不同。保留断点续跑，降低并发，分批处理，通常比一次性反复重跑全部链接更稳。

## 八、程序保存的本机文件

程序不会把运行数据写进应用安装包内部，主要数据目录为：

- macOS：`~/Library/Application Support/URLHeat/`
- Windows：`%APPDATA%\URLHeat\`

这里可能包含输入链接、进度、日志、验证码配置和 Selenium 浏览器缓存。多人共用电脑时，请注意该目录中的信息。

## 九、浏览器和 ChromeDriver

程序内置 Selenium，并使用 [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/) 管理浏览器驱动：

- 系统已有 Google Chrome 时，优先使用系统 Chrome；
- 没有可用 Chrome 时，首次运行可能准备 stable Chrome for Testing；
- Chrome 更新后通常不需要手动重新下载 ChromeDriver；
- 首次运行或浏览器组件缺失时需要联网。

## 十、开发者构建

### macOS arm64

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./build_macos.sh
```

输出：

- `dist/链接热度抓取.app`
- `dist/链接热度抓取-macOS-arm64.zip`

### Windows x64

在 Windows PowerShell 中执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
.\build_windows.ps1
```

输出：

- `dist\链接热度抓取.exe`
- `dist\链接热度抓取-windows-x64.zip`

也可以在 GitHub Actions 中手动运行 `Build Windows x64`。留空 Release 标签时只生成 Actions 构建产物；填写 Release 标签后会自动上传到对应 Release。

## 十一、项目文件

| 文件 | 作用 |
| --- | --- |
| `app.py` | 图形界面、文件选择、任务控制和日志显示 |
| `engine.py` | 链接读取、浏览器处理、断点续跑和结果导出 |
| `UrlHeat.spec` | macOS PyInstaller 配置 |
| `UrlHeat-windows.spec` | Windows x64 PyInstaller 配置 |
| `build_macos.sh` | macOS 构建脚本 |
| `build_windows.ps1` | Windows 构建脚本 |
| `.github/workflows/build-windows.yml` | GitHub Actions Windows 构建流程 |

## 数据与使用边界

- 不要把真实链接、账号、密码、日志、断点文件或结果文件提交到 GitHub。
- 不要把 Apple Developer 证书、私钥或其他凭据提交到仓库。
- 程序没有配置自动把用户结果上传到第三方；网络访问用于目标页面处理以及 Selenium Manager 准备浏览器组件。
- 本仓库当前未附带开源许可证，公开仓库不等于授予商业使用或再分发权。
