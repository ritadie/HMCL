# GitHub 自动更新与发布

工作流：`.github/workflows/local-downloads-release.yml`。

每 6 小时（UTC 00:23、06:23、12:23、18:23，北京时间 08:23、14:23、20:23、02:23）
检查官方 main。也可从 Actions 手动 Run workflow；修改维护脚本或补丁也会触发。
GitHub 定时调度可能延迟，不保证准点。

工作流在发布说明中以“上游 SHA + 维护仓库 SHA”为更新识别标记。
版本号使用 `3.17.0-local.5` 这样的格式，末位来自 Actions 运行序号；
tag 为 `v3.17.0-local.5`，标题和 EXE 内部版本、文件名保持一致。
主次版本从上游 `config/project.properties` 读取，local 表明这是修改版；
它不是对应的官方发布编号。已有相同源码和维护配置的正式发布则跳过，
失败的构建会在下一次重试。未完成的草稿发布会补传文件后再公开。
补丁不能干净应用、构建失败、测试失败时不会发布。上游源码在隔离目录检出，
维护仓库不会被上游覆盖，也不需要机器人向默认分支推送同步提交。

发布仅包含 EXE 和 GitHub 自动生成的 Source code (zip/tar.gz)。
发布标签指向当次编译的完整修改版源码快照，保证两个源码归档与 EXE 对应。
版本类型是 unofficial，版本号含 local。
每版作为本仓库的普通 Release 并标记 Latest，仓库首页可直接显示版本入口。
标题注明“修改版”，保留历史版本；不会替换官方仓库的发布。
构建任务只有只读权限，发布任务才有 contents:write，用于推送源码标签和创建 Release。
源码 Git bundle 与发布说明只用于工作流内部传递，不作为 Release 附件。

## 启用

1. 将本地源码和维护文件推送到自己的 GitHub 仓库。不要推送 `.local` 或本地缓存。
2. 工作流必须在默认分支；在 Actions 页面启用仓库 Actions 和该工作流。
   Fork 的定时工作流默认可能未启用，需要手动启用。
3. 手动运行 `Unofficial upstream build and release`，确认首个 Release 生成。
4. 之后自动定时检查。可在仓库 Actions 查看失败原因和测试报告。

不需要个人访问令牌，使用 GitHub 自动提供的 GITHUB_TOKEN。
仓库/组织策略需要允许工作流的 contents:write 权限用于创建 Release。
无需开启“允许创建和批准 Pull Request”。

可选 Repository Secrets：`MICROSOFT_AUTH_ID`、`CURSEFORGE_API_KEY`。
未配置时程序仍可构建，但微软登录和 CurseForge 功能未验证。
不要复用官方项目私密凭据。

GitHub 对公开仓库可能在 60 天无仓库活动后停用定时工作流。
届时需要在 Actions 手动重新启用；本工作流不会通过无意义提交规避平台停用。
参考：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

只新增这一套维护发布流程。上游已有 Java CI 等工作流仍可能在推送时执行；
若使用完整 Fork，可在 Actions 页面按需要禁用额外工作流以减少重复构建。
