"""
Zerasos-Home 博客管理系统
通过 GitHub 仓库管理博客内容，Vercel 自动部署
"""

import os, sys, re, logging

sys.dont_write_bytecode = True

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import shutil
# 清除所有子模块的 pyc 缓存，防止 AstrBot 热重载使用旧编译版本
for _root, _dirs, _files in os.walk(_PLUGIN_DIR):
    for _d in _dirs:
        if _d == "__pycache__":
            shutil.rmtree(os.path.join(_root, _d), ignore_errors=True)
    for _f in _files:
        if _f.endswith(".pyc"):
            os.remove(os.path.join(_root, _f))

from astrbot.api.all import *
from astrbot.api.event.filter import EventMessageType

from data_ops import (
    list_projects, add_project, del_project, edit_project,
    list_albums, add_album, del_album, add_photo,
    list_music, add_music, remove_music,
    list_chatters, new_chatter, del_chatter,
    list_moments, new_moment, del_moment,
    get_about, set_about,
)
from github_ops import ensure_repo, WORK_DIR

logger = logging.getLogger("astr_zerasos_home")


@register("astr_zerasos_home", "opaup", "Zerasos-Home 博客管理", "1.0.0")
class ZerasosHomePlugin(Star):

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.admin_ids = set()
        self._enabled = True
        self._load_config()

    def _load_config(self):
        """从配置加载设置"""
        self._enabled = bool(self.config.get("enabled", True))
        ids = self.config.get("admin_ids", [])
        self.admin_ids = set()
        if isinstance(ids, list):
            for uid in ids:
                if uid and str(uid).strip():
                    self.admin_ids.add(str(uid).strip())

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        """检查当前用户是否是管理员"""
        if not self.admin_ids:
            return True
        try:
            uid = str(event.message_obj.sender.user_id)
            return uid in self.admin_ids
        except Exception:
            return False

    def on_config_update(self, config: dict):
        self.config = config or {}
        self._load_config()

    async def terminate(self):
        pass

    # ── QQ 官方 Bot 换行处理 ──

    @staticmethod
    def _br(text: str) -> str:
        """将 \n 替换为 <br /> 适配 QQ 官方 Bot"""
        return str(text).replace("\n", "<br />")

    def _reply(self, event, text: str):
        """生成适配 QQ 官方 Bot 的回复"""
        return event.plain_result(self._br(text))

    # ── 权限检查 ──

    def _check_admin(self, event: AstrMessageEvent):
        if not self._is_admin(event):
            return self._br("你没有权限，请联系管理员")
        return None

    # ── 入口命令 ──

    @command("zh")
    async def zh_router(self, event: AstrMessageEvent):
        """Zerasos-Home 博客管理主入口"""
        text = event.message_str.strip()
        parts = text.split()
        subcmd = parts[1].lower() if len(parts) >= 2 else "help"

        # 插件禁用检查
        if not self._enabled:
            if subcmd == "help":
                yield event.plain_result(self._br(self._help_text()))
            else:
                yield event.plain_result(self._br("插件已禁用，请在配置中将 enabled 设为 true 后重试"))
            return

        # 权限检查：help 不需要管理员
        if subcmd != "help":
            err = self._check_admin(event)
            if err:
                yield event.plain_result(self._br(err))
                return

        if subcmd == "help":
            yield event.plain_result(self._br(self._help_text()))
            return

        # ── projects ──
        if subcmd == "projects" or subcmd == "project":
            yield event.plain_result(self._br(await self._handle_projects(parts)))
            return

        # ── albums / photos ──
        if subcmd in ("albums", "album"):
            yield event.plain_result(self._br(await self._handle_albums(parts)))
            return

        if subcmd == "photos":
            yield event.plain_result(self._br(await self._handle_photos(parts)))
            return

        # ── music ──
        if subcmd == "music":
            yield event.plain_result(self._br(await self._handle_music(parts)))
            return

        # ── chatters ──
        if subcmd in ("chatters", "chatter"):
            yield event.plain_result(self._br(await self._handle_chatters(parts)))
            return

        # ── moments ──
        if subcmd in ("moments", "moment"):
            yield event.plain_result(self._br(await self._handle_moments(parts)))
            return

        # ── about ──
        if subcmd == "about":
            yield event.plain_result(self._br(await self._handle_about(parts)))
            return

        yield event.plain_result(self._br(self._help_text()))

    # ── 帮助信息 ──

    @staticmethod
    def _help_text() -> str:
        return (
            "=== Zerasos-Home 博客管理 ===\n\n"
            "【项目】\n"
            "  /zh projects list                    列出项目\n"
            "  /zh projects add 名称|描述|图标|GitHub链接|标签1,标签2\n"
            "  /zh projects del <id>                删除项目\n"
            "  /zh projects edit <id> <字段> <值>    编辑字段\n"
            "    可用字段: name, description, icon, githubUrl\n\n"
            "【相册/照片墙】\n"
            "  /zh albums list                      列出相册\n"
            "  /zh albums add 标题|描述|封面图URL|日期\n"
            "  /zh albums del <album_id>             删除相册\n"
            "  /zh photos add <album_id>|图URL|描述  添加照片\n\n"
            "【歌单】\n"
            "  /zh music list                       列出歌单\n"
            "  /zh music add <网易云歌曲ID>          添加歌曲\n"
            "  /zh music del <网易云歌曲ID>          移除歌曲\n\n"
            "【说说/云端杂谈】\n"
            "  /zh chatters list                    列出说说\n"
            "  /zh chatters add 标题 | 内容         发布说说\n"
            "  /zh chatters del <文件名>             删除说说\n\n"
            "【杂谈/动态】\n"
            "  /zh moments list                     列出动态\n"
            "  /zh moments add <内容>                发布动态\n"
            "  /zh moments del <moment_id>           删除动态\n\n"
            "【关于】\n"
            "  /zh about                            查看关于\n"
            "  /zh about edit 标题 | 内容           编辑关于\n\n"
            "【注意】\n"
            "  本插件仅限管理员使用，请在插件配置中设置 admin_ids\n"
            "  命令修改后自动提交 GitHub，Vercel 会自动构建部署"
        )

    # ── 项目管理 ──

    async def _handle_projects(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "用法: /zh projects <list|add|del|edit> [...]"
        ensure_repo()
        action = parts[2].lower()

        if action == "list":
            projects = list_projects()
            if not projects:
                return "暂无项目"
            lines = [f"[{p.get('id','?')[:8]}...] {p.get('name','?')}  [{', '.join(p.get('tags',[]))}]" for p in projects]
            return "项目列表:\n" + "\n".join(lines)

        elif action == "add":
            if len(parts) < 4:
                return "用法: /zh projects add 名称|描述|图标|GitHub链接|标签1,标签2"
            args = " ".join(parts[3:]).split("|")
            if len(args) < 5:
                return "请用 | 分隔: 名称|描述|图标|GitHub链接|标签1,标签2"
            return add_project(args[0].strip(), args[1].strip(), args[2].strip(), args[3].strip(), [t.strip() for t in args[4].split(",") if t.strip()])

        elif action == "del":
            if len(parts) < 4:
                return "用法: /zh projects del <id>"
            return del_project(parts[3])

        elif action == "edit":
            if len(parts) < 6:
                return "用法: /zh projects edit <id> <字段> <新值>"
            return edit_project(parts[3], parts[4], " ".join(parts[5:]))

        return "未知操作，可用: list add del edit"

    # ── 相册管理 ──

    async def _handle_albums(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "用法: /zh albums <list|add|del> [...]"
        ensure_repo()
        action = parts[2].lower()

        if action == "list":
            albums = list_albums()
            if not albums:
                return "暂无相册"
            lines = []
            for a in albums:
                photo_count = len(a.get("photos", []))
                lines.append(f"[{a.get('id','?')[:20]}...] {a.get('title','?')} ({photo_count}张)")
            return "相册列表:\n" + "\n".join(lines)

        elif action == "add":
            if len(parts) < 4:
                return "用法: /zh albums add 标题|描述|封面URL|日期"
            args = " ".join(parts[3:]).split("|")
            if len(args) < 4:
                return "请用 | 分隔: 标题|描述|封面URL|日期"
            return add_album(args[0].strip(), args[1].strip(), args[2].strip(), args[3].strip())

        elif action == "del":
            if len(parts) < 4:
                return "用法: /zh albums del <album_id>"
            return del_album(parts[3])

        return "未知操作，可用: list add del"

    async def _handle_photos(self, parts: list[str]) -> str:
        if len(parts) < 3 or parts[2].lower() != "add":
            return "用法: /zh photos add <album_id>|图片URL|描述"
        if len(parts) < 4:
            return "用法: /zh photos add <album_id>|图片URL|描述"
        ensure_repo()
        args = " ".join(parts[3:]).split("|")
        album_id = args[0].strip()
        url = args[1].strip() if len(args) > 1 else ""
        caption = args[2].strip() if len(args) > 2 else ""
        if not url:
            return "请提供图片URL"
        return add_photo(album_id, url, caption)

    # ── 音乐管理 ──

    async def _handle_music(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "用法: /zh music <list|add|del> [...]"
        ensure_repo()
        action = parts[2].lower()

        if action == "list":
            ids = list_music()
            if not ids:
                return "歌单为空"
            return "歌单 (网易云歌曲ID):\n" + "\n".join(f"  {i+1}. {sid}" for i, sid in enumerate(ids))

        elif action == "add":
            if len(parts) < 4:
                return "用法: /zh music add <网易云歌曲ID>"
            return add_music(parts[3])

        elif action == "del" or action == "remove":
            if len(parts) < 4:
                return "用法: /zh music del <网易云歌曲ID>"
            return remove_music(parts[3])

        return "未知操作，可用: list add del"

    # ── 说说管理 ──

    async def _handle_chatters(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "用法: /zh chatters <list|add|del> [...]"
        ensure_repo()
        action = parts[2].lower()

        if action == "list":
            items = list_chatters()
            if not items:
                return "暂无说说"
            lines = [f"  {item['file']} - {item['title']}" for item in items[:20]]
            return f"说说列表 (共{len(items)}篇):\n" + "\n".join(lines)

        elif action == "add":
            if len(parts) < 4:
                return "用法: /zh chatters add 标题 | 内容"
            args = " ".join(parts[3:]).split("|")
            title = args[0].strip() if args else "未命名"
            content = args[1].strip() if len(args) > 1 else "(暂无内容)"
            tags = ["日常"]
            return new_chatter(title, content, tags=tags)

        elif action == "del":
            if len(parts) < 4:
                return "用法: /zh chatters del <文件名>"
            return del_chatter(parts[3])

        return "未知操作，可用: list add del"

    # ── 动态管理 ──

    async def _handle_moments(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "用法: /zh moments <list|add|del> [...]"
        ensure_repo()
        action = parts[2].lower()

        if action == "list":
            items = list_moments()
            if not items:
                return "暂无动态"
            lines = [f"  {item['id']}" for item in items[:20]]
            return f"动态列表 (共{len(items)}条):\n" + "\n".join(lines)

        elif action == "add":
            if len(parts) < 4:
                return "用法: /zh moments add <内容>\n可选在内容中用 |location=位置 |images=图URL1,图URL2"
            text = " ".join(parts[3:])
            location = ""
            images = []
            # 解析位置
            mloc = re.search(r'\|\s*location=(.+?)(?:\||$)', text)
            if mloc:
                location = mloc.group(1).strip()
                text = text.replace(mloc.group(0), "")
            # 解析图片
            mimg = re.search(r'\|\s*images=(.+?)(?:\||$)', text)
            if mimg:
                images = [u.strip() for u in mimg.group(1).split(",") if u.strip()]
                text = text.replace(mimg.group(0), "")
            return new_moment(text.strip(), location=location, images=images)

        elif action == "del":
            if len(parts) < 4:
                return "用法: /zh moments del <moment_id>"
            return del_moment(parts[3])

        return "未知操作，可用: list add del"

    # ── 关于页面管理 ──

    async def _handle_about(self, parts: list[str]) -> str:
        ensure_repo()
        if len(parts) >= 3 and parts[2].lower() == "edit":
            if len(parts) < 4:
                return "用法: /zh about edit 标题 | 内容"
            args = " ".join(parts[3:]).split("|")
            title = args[0].strip() if args else "关于我"
            content = args[1].strip() if len(args) > 1 else ""
            return set_about(title, content)

        about = get_about()
        if not about["content"]:
            return "关于页面暂无内容"
        return f"=== {about['title']} ===\n\n{about['content'][:500]}"
