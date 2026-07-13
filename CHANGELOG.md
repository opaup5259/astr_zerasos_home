# Changelog

## [1.0.38] - 2026-07-13
### Fixed
- 读操作（list）不再调用 ensure_repo，避免 git pull 覆盖本地改动导致歌单为空

## [1.0.37] - 2026-07-13
### Changed
- ensure_repo 多代理保底：gh-proxy.com → gh.dpik.top → hk.gh-proxy.com → edgeone.gh-proxy.com → 直连
- 每个代理依次尝试，失败自动切换下一个

## [1.0.36] - 2026-07-13
### Fixed
- 移除 ensure_repo 中的 git pull（国内服务器网络不稳），clone 改用 --depth 1

## [1.0.35] - 2026-07-13
### Fixed
- pull/clone 走 gh-proxy.com 代理，解决国内服务器 GnuTLS 连接失败

## [1.0.34] - 2026-07-13
### Fixed
- 修复 list 命令返回"歌单为空"：读操作不应调用 ensure_repo（git pull 覆盖了本地未推送的改动）

## [1.0.33] - 2026-07-13
### Fixed
- 修复 `from main import` 在 AstrBot 运行时导致 `attempted relative import` 错误

## [1.0.32] - 2026-07-13
### Fixed
- 移除 music_mgr.py 外部导入，内联到 main.py（解决服务器上没有该文件的问题）

## [1.0.31] - 2026-07-13
### Fixed
- 修复 list 命令返回 coroutine object（缺少 await）

## [1.0.30] - 2026-07-13
### 重大重构
- 歌单统一为 songList 格式，网易云 + B站混合排序
- 新增 /zh music list 显示统一歌单（含序号）
- 新增 /zh music wyy add/del [标题] 管理网易云歌曲
- 新增 /zh music bili add/del [标题] 管理B站歌曲
- 新增 /zh music sort <序号1> <序号2> 交换排序
- 新增 /zh music title <序号> <标题> 修改自定义标题
- B站视频支持自定义标题，添加时可指定
- 默认使用视频标题，有自定义标题则显示自定义
- 新增独立模块 music_mgr.py（统一歌单管理逻辑）
- 帮助命令已更新

## [1.0.28] - 2026-07-13
### Fixed
- 修复 list_bili_music 正则中多余的反斜杠导致匹配失败

## [1.0.27] - 2026-07-13
### 新增
- B站音源支持：/zh music bili add/del <BV号>
- 歌单 list 同时显示网易云ID和B站BV号

### 博客变更（外部）
- siteConfig.ts 新增 bilibiliIds 字段
- 新增 /api/music/bilibili 路由，从 B站 DASH 流拉取纯音频
- 音乐 API 增加 proxy fallback 获取播放地址

## [1.0.26] - 2026-07-13
### Fixed
- 修复 git push 因服务器 gh-proxy url.insteadOf 配置导致推送被吞的问题
- push 时使用完整 URL + HEAD:main 直推 + 临时禁用 url.insteadOf

## [1.0.25] - 2026-07-13
### Fixed
- 修复 git commit 因服务器缺少 user.name/user.email 配置而失败
- 在 commit_push 中通过 git -c 参数内联指定 Author 信息

## [1.0.24] - 2026-07-13
### Fixed
- 修复 _conf_schema.json 使用 object/sub 嵌套配置导致 AstrBot 加载失败
- 配置拍平：auto_publish 改为 auto_publish_enabled / auto_publish_cron / auto_publish_llm_prompt 三个独立字段

## [1.0.23] - 2026-07-13
### Fixed
- 修复 _conf_schema.json 中 admin_ids 缺少 items 字段导致 AstrBot 加载失败（KeyError: 'items'）

## [1.0.22] - 2026-07-13
### Fixed
- 修复 _conf_schema.json 中 auto_publish 配置类型错误：dict → object（AstrBot 不支持 dict 类型）

## [1.0.21] - 2026-07-13
### Fixed
- 修复 commit_push 中 os.path.relpath 路径计算错误导致 git add 失败 (#1)

### Changed
- README.md 移除 QQ 群链接
- 版本号 1.0.20 → 1.0.21

## [1.0.20] - 2026-07-13
### 新增
- 新增自动发布说说功能（LLM 驱动）
- 新增独立模块 auto_publish.py（遵循 main.py 仅入口原则）
- 新增 /zh ai publish 指令（管理员强制触发自动发布）
- 新增 /zh ai status 查看自动发布状态
- 新增 /zh config auto_publish 查看配置
- 新增 auto_publish 配置段：enabled / cron / llm_prompt
- 新增后台定时调度器，支持 Cron 表达式定时发布
- 新增 LLM 生成说说时的日期/季节上下文注入
- 新增 LLM 不可用时的备用随机生成逻辑

### Changed
- main.py 中新增 _init_auto_publisher 自动发布初始化
- _conf_schema.json 新增 auto_publish 嵌套配置
- 帮助命令增加 AI 发布和配置查看相关说明

## [1.0.12] - 2026-07-13
### 新增
- 新增 _conf_schema.json 支持 WebUI 配置
- 新增完整开发文档 README.md
- GitHub 凭据改为从 WebUI 配置读取

## [1.0.0] - 2026-07-13

- 首个版本发布
- 支持项目管理（增删改查）
- 支持相册/照片墙管理
- 支持歌单管理（网易云音乐）
- 支持说说/云端杂谈管理
- 支持动态管理
- 支持关于页面编辑
- 命令权限控制（仅管理员可用）
- 配置开关支持临时禁用
