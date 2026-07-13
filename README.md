# 泽拉索斯·HOME（astr_zerasos_home）

基于 XinghuisamaBlogs 的 Zerasos-Home 博客管理系统 —— AstrBot 插件。通过 GitHub → Vercel 链路管理 [Zerasos-Home](https://github.com/opaup5259/Zerasos-Home) 博客的全部内容，支持项目、相册、歌单、说说、动态、关于页面的增删改查。

## 架构概览

```
用户 (/zh 指令) → AstrBot → git clone/pull → 修改数据文件 → git commit + push
       ↓
   GitHub 仓库更新 → Vercel 自动构建 → 博客更新
```

插件不依赖本地 daemon 或数据库，所有数据持久化在 GitHub 仓库的 TypeScript 和 Markdown 文件中。

## 功能概览

| 模块 | 支持操作 | 数据文件 |
|---|---|---|
| 项目 (Projects) | 列表 / 添加 / 删除 / 编辑 | `data/projects.ts` |
| 相册 (Albums / 照片墙) | 列表 / 添加 / 删除 / 添加照片 | `data/albums.ts` |
| 歌单 (Music) | 列表 / 添加 / 删除（网易云音乐 ID） | `siteConfig.ts`（`cloudMusicIds` 字段） |
| 说说 (Chatters / 云端杂谈) | 列表 / 发布 / 删除 | `chatters/*.md`（Markdown + YAML frontmatter） |
| 动态 (Moments) | 列表 / 发布 / 删除 | `moments/*.md`（Markdown + YAML frontmatter） |
| 关于 (About) | 查看 / 编辑 | `app/about/about.md` |

## 安装

要求 AstrBot `>=4.16,<5`。

1. 将本仓库放入 AstrBot 的插件目录：

```bash
cd /AstrBot/data/plugins/
git clone https://github.com/opaup5259/astr_zerasos_home.git
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 重启 AstrBot，或在管理面板重新加载插件。
4. 在 QQ 私聊或群聊发送 `/zh help` 查看可用指令。

## 配置

插件配置通过 AstrBot WebUI 或 `astrbot.yaml` 中的 `_conf_schema.json` 定义。

### 配置项

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `true` | 插件总开关；关闭后所有 `/zh` 指令（除 help 外）返回"插件已禁用" |
| `admin_ids` | `list` | `["525915186"]` | 管理员 ID 列表。仅这些用户可执行管理指令。留空则开放所有人 |
| `github_user` | `string` | `"opaup5259"` | GitHub 用户名，用于推送到博客仓库 |
| `github_token` | `string` | `""` | GitHub 个人访问令牌（需 `repo` 权限），用于 git clone/pull/push 认证 |

### GitHub 访问配置

服务器需先配置 git 凭据，插件才能推送变更：

```bash
git config --global user.name "opaup5259"
git config --global user.email "opaup5259@gmail.com"
git config --global credential.helper store
echo 'https://opaup5259:你的Token@github.com' > ~/.git-credentials
chmod 600 ~/.git-credentials
```

如果服务器无法直连 `github.com:443`（如位于中国），可配置镜像：

```bash
git config --global url."https://gh-proxy.com/https://github.com/".insteadOf "https://github.com/"
```

注意：镜像仅支持 clone/fetch，push 仍需直连或 Token 认证。

## 数据格式

插件管理的博客数据均存储在 GitHub 仓库 `opaup5259/Zerasos-Home` 中。

### 项目 (projects.ts)

```typescript
export const projectsData: Project[] = [
  {
    "id": "proj_1700000000000",
    "name": "项目名称",
    "githubUrl": "https://github.com/xxx/xxx",
    "description": "项目描述",
    "icon": "🔬",
    "tags": ["标签1", "标签2"]
  }
];
```

### 相册 (albums.ts)

```typescript
export const albums: Album[] = [
  {
    "id": "album_1700000000",
    "title": "相册标题",
    "description": "相册描述",
    "cover": "https://xxx.com/cover.jpg",
    "date": "2026.01",
    "photos": [
      { "url": "https://xxx.com/photo.jpg", "caption": "照片描述" }
    ]
  }
];
```

### 歌单 (siteConfig.ts)

```typescript
cloudMusicIds: ["1809646618", "3361076230"]
```

歌曲 ID 来自网易云音乐。前端 `/api/music` 路由调用 `music.163.com/api/song/detail/` 获取歌曲信息。

### 说说 (chatters/*.md)

```markdown
---
title: 说说标题
date: '2026-07-13 03:00:01'
tags:
- 日常
mood: 思考
cover: https://xxx.com/cover.jpg
description: ''
---

说说正文内容...
```

### 动态 (moments/*.md)

```markdown
---
id: "moment-1700000000000"
date: "2026-07-13T14:00:00.000Z"
location: "江西省 南昌市"
images:
  - 'https://xxx.com/photo.jpg'
---

动态正文内容
```

### 关于 (about.md)

```markdown
---
title: 关于我
date: '2026-07-13'
tags: []
mood: ''
cover: https://xxx.com/cover.jpg
description: ''
---

个人简介正文...
```

## 命令

### `/zh help`

查看帮助信息，列出所有可用命令及用法。

### 项目管理

| 命令 | 说明 |
| --- | --- |
| `/zh projects list` | 列出所有项目 |
| `/zh projects add 名称\|描述\|图标\|URL\|标签1,标签2` | 添加项目 |
| `/zh projects del <id>` | 删除项目（按 id） |
| `/zh projects edit <id> <字段> <值>` | 编辑项目字段 |
| | 可用字段: `name`, `description`, `icon`, `githubUrl` |

### 相册/照片管理

| 命令 | 说明 |
| --- | --- |
| `/zh albums list` | 列出所有相册 |
| `/zh albums add 标题\|描述\|封面URL\|日期` | 添加相册 |
| `/zh albums del <album_id>` | 删除相册 |
| `/zh photos add <album_id>\|图URL\|描述` | 向相册添加照片 |

### 歌单管理

| 命令 | 说明 |
| --- | --- |
| `/zh music list` | 列出所有歌曲 ID |
| `/zh music add <网易云歌曲ID>` | 添加歌曲 |
| `/zh music del <网易云歌曲ID>` | 移除歌曲 |

### 说说管理

| 命令 | 说明 |
| --- | --- |
| `/zh chatters list` | 列出所有说说 |
| `/zh chatters add 标题 \| 内容` | 发布新说说（`|` 分隔标题和正文） |
| `/zh chatters del <文件名>` | 删除指定说说 |

### 动态管理

| 命令 | 说明 |
| --- | --- |
| `/zh moments list` | 列出所有动态 |
| `/zh moments add 内容 \|location=位置 \|images=图URL1,图URL2` | 发布新动态 |
| `/zh moments del <moment_id>` | 删除动态 |

### 关于页面

| 命令 | 说明 |
| --- | --- |
| `/zh about` | 查看关于页面 |
| `/zh about edit 标题 \| 内容` | 编辑关于页面 |

## 命令参数约定

- `|`（竖线）用作多参数分隔符
- `<id>` 表示项目/相册的唯一标识符，可在 list 命令中查看
- 网易云歌曲 ID 为纯数字，可在网易云音乐网页版歌曲 URL 中获取（`id=xxxxx`）
- 说说/动态的内容支持多行文本（通过空格分隔的命令参数传入）
- 动态支持可选的 `location` 和 `images` 扩展参数

## 工作流程

### 读操作（无需 Git 推送）

```
命令 → ensure_repo() → 读取本地仓库文件 → 解析 TS/JSON/YAML → 返回格式化文本
```

### 写操作（涉及 Git 推送）

```
命令 → ensure_repo() → git pull 最新 → 修改文件 → _write() → git add + commit + push
     → GitHub 更新 → Vercel 自动部署 → 博客更新
```

写操作对数据文件直接做字符串替换或 JSON/正则解析插入，不涉及 TypeScript 编译器或构建流程。修改粒度到字段级别（如 `edit_project`）。

## 文件结构

```
astr_zerasos_home/
├── __init__.py              # 包入口
├── main.py                  # 单文件插件（模块内联所有逻辑）
│   ├── Git 异步操作          # asyncio.create_subprocess_exec
│   ├── 文件读写与解析         # _read, _write, _parse_fm, _ts_array
│   ├── 数据操作函数           # 各模块 CRUD
│   └── ZerasosHomePlugin     # AstrBot Star 子类 + @command("zh") 路由
├── metadata.yaml            # 插件元信息
├── _conf_schema.json        # WebUI 配置字段定义
├── requirements.txt         # 依赖: PyYAML
├── CHANGELOG.md
└── README.md
```

## 关键实现细节

### 异步 Git 操作

所有 git 命令通过 `asyncio.create_subprocess_exec` 执行，避免阻塞 AstrBot 事件循环：

```python
async def _git(args, cwd=None):
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
```

### 仓库路径

工作目录使用系统临时目录：`os.path.join(tempfile.gettempdir(), "zerasos-home-repo")`

### Token 安全

GitHub Token 通过 `self.config`（AstrBot 插件配置）传入，在 `_repo_url()` 中嵌入到 HTTPS URL 中：

```python
def _repo_url(user="", token=""):
    if user and token:
        return f"https://{user}:{token}@github.com/opaup5259/Zerasos-Home.git"
    return f"https://github.com/opaup5259/Zerasos-Home.git"
```

### QQ 官方 Bot 适配

所有回复文本的 `\n` 替换为 `<br />`，适配 QQ 官方 Bot Markdown 渲染。

### 权限控制

```python
def _is_admin(self, event):
    if not self.admin_ids: return True
    return str(event.message_obj.sender.user_id) in self.admin_ids
```

- `help` 指令不需要管理员权限
- 其余所有修改指令需要管理员

### WebUI 配置

`_conf_schema.json` 定义 AstrBot WebUI 中可编辑的配置字段，支持以下类型：
- `string` — 文本输入
- `list` — 列表输入
- `bool` — 开关

## 数据目录

运行数据默认写入 AstrBot 分配的临时目录：

- `/tmp/zerasos-home-repo/` — git 工作目录，包含博客仓库完整副本
- 每次写操作前执行 `git pull` 确保最新

## 排障

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `git pull origin main 失败: GnuTLS recv error` | 服务器无法直连 GitHub | 配置镜像：`git config --global url."https://gh-proxy.com/https://github.com/".insteadOf "https://github.com/"` |
| `_run_git() missing ...` | 热重载加载旧 `.pyc` 缓存 | 删除 `__pycache__` 后重启 AstrBot |
| 指令无响应 | `asyncio` 被同步操作阻塞 | 确保所有 `_git` 调用使用 `await` |
| WebUI 显示"这个插件没有配置" | 缺少 `_conf_schema.json` | 在插件目录添加 `_conf_schema.json` |
| "你没有权限" | 当前 QQ 号不在 `admin_ids` 中 | 在配置中添加 QQ 号 |
| Git push 失败 | Token 过期或服务器无法直连 GitHub | 更新 `github_token` 或配置镜像 |
| Vercel 不更新 | GitHub Webhook 未触发 | 检查 Vercel 项目是否已连接 GitHub 仓库 |

## LLM 工具

暂无。当前版本仅通过 `/zh` 命令体系操作，未暴露 LLM tools。（计划未来支持）

## 版本历史

参见 `CHANGELOG.md`。
