# astr_zerasos_home 开发规划

## 现状分析

当前 `astr_zerasos_home` 是一个**人工指令驱动的博客管理插件**，用户通过 `/zh` 命令手动管理 Zerasos-Home 博客的内容。

### 当前能力

| 模块 | 操作方式 | 限制 |
| --- | --- | --- |
| 项目 (Projects) | `/zh projects add/del/edit` | 仅人工操作，单条处理 |
| 相册 (Albums) | `/zh albums add/del`, `/zh photos add` | 仅人工操作，无自动发布 |
| 歌单 (Music) | `/zh music add/del` | 仅人工管理 ID 列表 |
| 说说 (Chatters) | `/zh chatters add/del` | 仅人工发布，格式受限 |
| 动态 (Moments) | `/zh moments add/del` | 仅人工发布 |
| 关于 (About) | `/zh about edit` | 仅人工编辑 |

### 技术架构

```
[/zh 命令] → AstrBot → git pull → 文件CRUD → git commit+push → Vercel部署
```

### 痛点

1. **无自动化**：所有内容需要手动输入，无法联动 LLM 生成内容
2. **无定时任务**：不支持定时发布、自动更新
3. **无平台联动**：无法将 AstrBot 接收到的媒体（图片、消息等）自动同步到博客
4. **无内容生成**：不支持 AI 写说说、AI 配文等
5. **无投稿审核**：群友无法通过 bot 投稿内容到博客

---

## 目标：打造自动化个人博客运营系统

参考 [QzoneUltra](https://github.com/diaomin66/astrbot_plugin_qzone_ultra) 的设计模式，将 `astr_zerasos_home` 从"手动管理工具"升级为"自动运营系统"。

### 核心设计原则

1. **LLM 驱动内容生成** — LLM 写说说、写动态描述、配文
2. **定时任务 + 事件触发** — 自动发布、自动更新
3. **平台联动** — 从 QQ 群聊/私聊自动提取内容发布到博客
4. **投稿审核** — 群友投稿 → 管理员审核 → 自动发布到博客
5. **增量同步** — 只推送变更的文件，减少 git 操作

---

## 第一阶段：自动化内容发布

### 1. 定时说说发布（参考 QzoneUltra `trigger.publish_cron`）

```
定时 Cron 触发 → LLM 生成今日说说内容 → 写入 chatters/*.md → git push → Vercel 部署
```

**配置设计：**
```yaml
triggers:
  publish_cron: "30 8 * * *"      # 每天早上 8:30 自动发说说
  moment_cron: "0 12 * * *"       # 每天中午 12 点自动发动态
  news_cron: "0 18 * * *"         # 每天晚上 6 点新闻说说
```

**LLM 联动：**
- 定时触发 → LLM 根据当前日期、天气、日程生成说说文案
- 支持自定义 prompt 模板
- 生成内容写入 Markdown 文件

### 2. 自动评论与互动（参考 QzoneUltra `trigger.comment_cron`）

```
定时 Cron 触发 → 抓取博客最新说说 → LLM 生成评论 → 通过 API 发布
```

**讨论方向：**
- 博客自己的说说需要评论吗？（博客没有评论系统，目前是 Gitalk）
- 还是说 bot 自动在博客上"评论"相当于发新说说？

### 3. 图片自动发布

```
收到图片消息 → 自动上传到 COS → 生成相册条目或动态 → git push
```

**流程：**
1. 用户/管理员发送图片到 bot
2. bot 接收图片，下载到本地
3. 自动上传到腾讯云 COS（`opa-1316532755` 的 `zarasos-home` 目录）
4. 生成相册条目或动态（包含图片 URL + LLM 配文）
5. push 到 GitHub → Vercel 部署

**配置设计：**
```yaml
cos:
  secret_id: "AKID7M…"
  secret_key: "hMDvUtXzEKNMHELJ6kCveHpIcljVWPAo"
  bucket: "opa-1316532755"
  region: "ap-guangzhou"
  base_path: "zarasos-home"
  
auto_album:
  enabled: false                    # 是否自动创建相册
  target_album_id: ""               # 指定相册 ID，空则自动创建新相册
```

---

## 第二阶段：LLM 内容生成

### 1. AI 写说说（参考 QzoneUltra `llm_publish_post`）

```
/zh ai write 今天天气真好 → LLM 生成 → 预览 → 确认发布
```

**指令设计：**
| 命令 | 说明 |
| --- | --- |
| `/zh ai write <主题>` | LLM 生成说说文案并预览 |
| `/zh ai write <主题> \| auto` | LLM 生成后直接发布 |
| `/zh ai comment <主题>` | LLM 生成动态文案 |

**配置设计：**
```yaml
llm:
  provider_id: ""                   # 使用的 LLM provider，空则用当前会话
  write_prompt: "你是一个个人博客博主，请根据以下主题写一段简短的说说……"
  moment_prompt: "请根据以下内容生成一条朋友圈风格的动态……"
  temperature: 0.85
```

### 2. AI 配文

```python
# 伪代码
async def auto_caption(image_url: str) -> str:
    """根据图片生成配文"""
    prompt = "请为这张图片写一段适合发布在个人博客上的配文，风格轻松自然"
    caption = await llm.generate(prompt, image=image_url)
    return caption
```

### 3. AI 摘要生成

```python
async def auto_summary(content: str) -> str:
    """为长篇内容生成摘要"""
    prompt = "请为以下内容生成一段 100 字以内的摘要"
    return await llm.generate(prompt, content=content)
```

---

## 第三阶段：投稿与审核系统（参考 QzoneUltra 表白墙）

### 1. 群友投稿到博客

```
群友发送"投稿 xxx" → BOT 接收 → 存入待审核队列 → 管理员审核 → 发布到博客
```

**指令设计：**
| 命令 | 权限 | 说明 |
| --- | --- | --- |
| `投稿 <内容> [图片]` | 所有人 | 投稿到博客的说说/动态 |
| `匿名投稿 <内容>` | 所有人 | 匿名投稿 |
| `看稿 [稿件ID]` | 管理员 | 查看待审核稿件 |
| `过稿 <稿件ID>` | 管理员 | 审核通过并发布到博客 |
| `拒稿 <稿件ID> [原因]` | 管理员 | 拒绝稿件 |

**数据流：**
```
投稿 → AstrBot 本地 JSON 存储（待审核列表）
  → 管理员"过稿" → LLM 润色 → 写入 chatters/*.md → git push → 博客更新
```

### 2. 投稿存储

使用 AstrBot 分配的 `data_dir` 存储待审核稿件：

```json
// data/pending_reviews.json
{
  "reviews": [
    {
      "id": "rev_1700000000",
      "type": "chatter",          // chatter | moment | photo
      "content": "投稿内容",
      "images": ["url1", "url2"],
      "author": "用户昵称",
      "anonymous": false,
      "created_at": "2026-07-13 15:00:00",
      "status": "pending"         // pending | approved | rejected
    }
  ]
}
```

---

## 第四阶段：平台联动与事件驱动

### 1. QQ 群消息 → 博客内容

```
群聊消息 → AstrBot 事件 → 关键词/概率触发 → LLM 处理 → 发布到博客
```

**场景示例：**
- 群聊中分享了好照片 → bot 自动保存到博客相册
- 群聊中有趣的对话 → bot 自动写成说说
- 检测到节日/特殊日期 → bot 自动发布节日说说

### 2. 外部 API 集成

```
第三方 API（天气/新闻/GitHub） → 定时任务 → LLM 撰写 → 发布
```

**场景示例：**
- 每日天气播报 → 自动生成天气说说
- GitHub repo 更新 → 自动发布项目更新动态
- RSS 订阅 → 自动抓取并发布

---

## 第五阶段：优化与运维

### 1. Git 操作优化

当前问题：每次写操作都 `git pull + commit + push`，效率低且容易冲突。

**优化方案：**
- 引入 git stash / rebase 策略处理冲突
- 批量操作合并为单次 commit
- 失败重试机制

### 2. 错误处理与回滚

- Git 操作失败自动重试（最多 3 次）
- 文件写入前备份原内容
- 推送失败时保留本地修改，不丢失数据

### 3. 日志与监控

- 记录每次推送的 commit hash
- 记录每次 LLM 生成的内容（用于调试）
- 定时检查 GitHub 仓库状态

---

## 优先级路线图

| 阶段 | 功能 | 优先级 | 预估复杂度 |
| --- | --- | --- | --- |
| P0 | LLM 生成说说内容 | ⭐⭐⭐ | 低（复用 AstrBot LLM） |
| P0 | 定时发布 Cron 任务 | ⭐⭐⭐ | 中（AstrBot cron 支持） |
| P1 | 照片自动上传到 COS | ⭐⭐⭐ | 中（需 COS SDK） |
| P1 | 投稿审核系统 | ⭐⭐⭐ | 中（本地 JSON 存储） |
| P2 | AI 配文 + 图片理解 | ⭐⭐ | 中（多模态 LLM） |
| P2 | 事件驱动自动发布 | ⭐⭐ | 高（需要设计触发机制） |
| P3 | Git 操作优化 | ⭐ | 中 |
| P3 | 外部 API 集成（天气/新闻） | ⭐ | 中 |

---

## 技术参考

### QzoneUltra 可借鉴的设计

| QzoneUltra 特性 | 可借鉴到 astr_zerasos_home |
| --- | --- |
| `trigger.publish_cron` 定时发布 | 定时发说说/动态到博客 |
| `llm_publish_post` LLM 写说说 | LLM 生成博客内容 |
| `trigger.comment_cron` 自动评论 | 自动更新博客内容 |
| 投稿审核工作流 | 群友投稿到博客 |
| `_conf_schema.json` 配置系统 | ✅ 已有 |
| 中文命令体系 | ✅ 已有 `/zh` 体系 |
| `pillowmd` 渲染 | 不需要（博客前端渲染） |

### 技术差异

| 维度 | QzoneUltra | astr_zerasos_home |
| --- | --- | --- |
| 目标平台 | QQ 空间 | 自建博客 (Vercel) |
| 数据存储 | QQ 空间服务器 | GitHub 仓库文件 |
| 发布方式 | QQ 空间 API | Git push → Vercel 构建 |
| 媒体存储 | QQ 空间/CDN | 腾讯云 COS |
| 渲染 | 本地 pillowmd | 博客前端 Next.js |
