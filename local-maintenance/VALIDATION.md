# 本地实验结果（2026-10-21）

上游基线：`acc9740fa`；补丁仅改 `RegionUtils.isIsChinaMainlandNetwork()`。

- Temurin JDK 25.0.4.1，项目 Gradle Wrapper 9.8.0。
- `:HMCL:makeExecutables :HMCL:test` 成功，首次构建耗时 3 分 18 秒。
- HMCL 测试报告：236 项，0 失败、0 错误、10 跳过（226 项实际执行）。
- 产物级地区检查：设置 Asia/Shanghai、简体中文地区；机器地区判断仍为大陆，
  网络地区禁用条件连续 100 次均为 false；禁止 URL 请求时也通过。
- 使用生成 JAR 内的 `NetworkUtils` 和 `FileDownloadTask`，获取 Mojang 官方版本清单、
  1.21.1 元数据与客户端 JAR。客户端大小 26,836,906 字节，下载器 SHA-1 检查及大小检查通过。
  测试入口先初始化 `.local/download-probe/cache`；未初始化时的缓存异常属于测试入口遗漏。
- `git diff --check`、补丁反向应用检查通过。

## 产物

`HMCL/build/libs/HMCL-3.17.local-downloads.unofficial-acc9740.exe`

SHA-256：`f970b1408ee3b55b82880651c269a5fd53aeba1612ccb36eb87a93ae0e64f099`

`HMCL/build/libs/HMCL-3.17.local-downloads.unofficial-acc9740.jar`

SHA-256：`ad655c10604ef6f02d96f0236307186a6df1e5f8f772a8b5c7ae1da03c7f6164`

## 验证边界

已证明修改可编译、测试通过、产物地区判断符合预期，且官方客户端文件能经 HMCL 下载器下载。
尚未操作启动器界面，也未完成包含全部资源、依赖库的完整游戏安装和实际游戏启动。
这不是完整端到端安装验证。未测试第三方镜像、Mod 下载或微软登录。
自行构建默认不含微软 OAuth App ID 和 CurseForge API Key，相关功能需单独配置验证。

实验日志：`.local/build.log`；客户端测试文件：`.local/download-probe/minecraft-1.21.1-client.jar`。
地区及下载探针源码：`.local/RegionProbe.java`、`.local/DownloadProbe.java`；
本次 Python 入口：`.local/probe.py`，参数为空执行地区探针，参数 `DownloadProbe` 执行下载探针。
`.local` 不入版本控制，保留本机运行环境和实验数据；维护补丁位于本目录。
