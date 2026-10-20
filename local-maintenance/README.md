# 本地下载功能实验

上游：https://github.com/HMCL-dev/HMCL

基线：`acc9740fa`（2026-10-21 拉取），包含 #7017 和 #7020。

## 补丁范围

仅将 `RegionUtils.isIsChinaMainlandNetwork()` 改为返回 `false`。
两处下载页面不再进入地区禁用分支，初始化不再请求 ipwho.is。
机器地区判断、镜像源选择、账号验证及下载器保持上游行为。
上游网络检测私有代码暂时保留，以缩小同步冲突范围。

`region-downloads.patch` 是独立源码补丁，便于移植和审核。

## 构建

使用 JDK 17 或更高版本。当前实验使用项目 `.local/jdk` 内的便携 JDK。
用 Python 执行 `local-maintenance/build.py`；也可设置 JAVA_HOME 后运行。
脚本将 Gradle 缓存和日志放到 `.local`，生成 unofficial 类型、
`3.17.local-downloads.unofficial-<上游短哈希>` 版本。
输出在 `HMCL/build/libs`。构建日志在 `.local/build.log`。

源码补丁不是完整下载成功的证据。必须进一步确认构建、启动、页面可用，
并在隔离的游戏目录里完成一次真实 Minecraft 安装和文件校验。
不需要输入微软账号密码进行下载页面实验。

本次实际执行结果与验证边界见 [VALIDATION.md](VALIDATION.md)。

## 长期维护方式

验证通过后，建立个人 Fork，将官方仓库设为 upstream，个人仓库设为 origin。
保留干净的上游 main，补丁放在单独维护分支，并提交源码补丁和本目录文件。
每次更新先记录旧上游 SHA 和当前补丁提交，再 fetch upstream，
在临时验证分支上 rebase 到 upstream/main，检查全部地区判断调用点。
不要在有未保存修改的工作区执行 rebase，也不要使用强制覆盖或自动解决冲突。

如果选择在新上游分支重放补丁，先运行：

```text
git apply --check local-maintenance/region-downloads.patch
git apply local-maintenance/region-downloads.patch
```

已应用补丁时不要重复 apply。检查失败必须人工复核上游是否新增限制点；
成功后重新构建并做真实安装验证。保留上一版可用产物及对应源码 SHA。
不要通过官方自动更新覆盖本地构建；更新应走上述重建流程。

GitHub 自动更新和发布配置见 [ACTIONS.md](ACTIONS.md)。
原版权和许可文件保持完整；公开分发前需核对项目说明中的附加条款。
