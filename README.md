# Astr_Zerasos_Home

Zerasos-Home 博客管理系统 —— AstrBot 插件

通过 GitHub → Vercel 链路管理 [Zerasos-Home](https://github.com/opaup5259/Zerasos-Home) 博客的全部内容。

## 功能

| 模块 | 支持操作 |
|---|---|
| 项目 (Projects) | 列表 / 添加 / 删除 / 编辑 |
| 相册 (Albums / 照片墙) | 列表 / 添加 / 删除 / 添加照片 |
| 歌单 (Music) | 列表 / 添加 / 删除 (网易云音乐 ID) |
| 说说 (Chatters / 云端杂谈) | 列表 / 发布 / 删除 |
| 动态 (Moments) | 列表 / 发布 / 删除 |
| 关于 (About) | 查看 / 编辑 |

任何修改自动提交 GitHub → Vercel 自动构建部署。

## 安装

将 `astr_zerasos_home` 文件夹放入 AstrBot 的 `plugins/` 目录。

## 配置

```yaml
astr_zerasos_home:
  enabled: true                # 插件总开关
  admin_ids:                   # 仅允许这些用户使用（不设则开放）
    - "你的QQ号"
    - "其他管理员QQ号"
```

`enabled: false` 即可在 AstrBot 插件页面临时禁用。

## 使用

```
/zh help                       查看帮助

/zh projects list              列项目
/zh projects add 名称|描述|图标|URL|标签1,标签2
/zh projects del <id>
/zh projects edit <id> <字段> <值>

/zh albums list                列相册
/zh albums add 标题|描述|封面URL|日期
/zh albums del <id>
/zh photos add <album_id>|图URL|描述

/zh music list                 列歌单
/zh music add <网易云歌曲ID>
/zh music del <网易云歌曲ID>

/zh chatters list              列说说
/zh chatters add 标题 | 内容
/zh chatters del <文件名>

/zh moments list               列动态
/zh moments add <内容>
/zh moments del <moment_id>

/zh about                      查看关于
/zh about edit 标题 | 内容
```

## 工作原理

```
用户 (/zh 指令) → AstrBot → git pull → 修改数据文件 → git commit + push
       ↓
   Vercel 自动构建 → 博客更新
```

数据文件：
- `data/projects.ts` — 项目列表
- `data/albums.ts` — 相册数据
- `siteConfig.ts` — 歌单 ID、全局配置
- `chatters/*.md` — 说说（Markdown + frontmatter）
- `moments/*.md` — 动态（Markdown + frontmatter）
- `app/about/about.md` — 关于页面

## 依赖

- PyYAML

## 许可证

MIT
