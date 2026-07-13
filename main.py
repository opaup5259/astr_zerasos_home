"""
Zerasos-Home 博客管理系统
单文件插件，无子模块，避免 .pyc 缓存问题
"""

import os, sys, re, logging, subprocess, tempfile, shutil, json, datetime
import yaml

sys.dont_write_bytecode = True

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

# 清除 .pyc 缓存
for _root, _dirs, _files in os.walk(_PLUGIN_DIR):
    for _d in _dirs:
        if _d == "__pycache__":
            shutil.rmtree(os.path.join(_root, _d), ignore_errors=True)
    for _f in _files:
        if _f.endswith(".pyc"):
            try: os.remove(os.path.join(_root, _f))
            except: pass

from astrbot.api.all import *

logger = logging.getLogger("astr_zerasos_home")

# ========== Git 操作 ==========

_REPO_URL = "https://opaup5259:ghp_Yj…KLyU@github.com/opaup5259/Zerasos-Home.git"
_REPO_BRANCH = "main"
_WORK_DIR = os.path.join(tempfile.gettempdir(), "zerasos-home-repo")


def _git(args, cwd=None):
    cwd = cwd or _WORK_DIR
    env = os.environ.copy()
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {r.stderr[:200]}")
    return r.stdout


def ensure_repo():
    if os.path.isdir(os.path.join(_WORK_DIR, ".git")):
        _git(["pull", "origin", _REPO_BRANCH])
    else:
        if os.path.isdir(_WORK_DIR):
            shutil.rmtree(_WORK_DIR, ignore_errors=True)
        parent = os.path.dirname(_WORK_DIR)
        os.makedirs(parent, exist_ok=True)
        _git(["clone", _REPO_URL, _WORK_DIR], cwd=parent)


def commit_push(files, msg):
    ensure_repo()
    for f in files:
        _git(["add", os.path.relpath(f, _WORK_DIR)])
    _git(["commit", "-m", msg])
    _git(["push", "origin", _REPO_BRANCH])


def _read(rel):
    path = os.path.join(_WORK_DIR, rel)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _write(rel, content):
    path = os.path.join(_WORK_DIR, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _delete(rel):
    path = os.path.join(_WORK_DIR, rel)
    if os.path.exists(path):
        os.remove(path)


def _listdir(rel_dir):
    path = os.path.join(_WORK_DIR, rel_dir)
    if os.path.isdir(path):
        return sorted(os.listdir(path))
    return []


# ========== 数据操作 ==========

def _parse_frontmatter(content):
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if m:
        try: return yaml.safe_load(m.group(1)) or {}
        except: pass
    return {}

def _strip_fm(content):
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content

def _ts_array(content, varname):
    m = re.search(r"export\s+(const|let|var)\s+" + re.escape(varname) + r"\s*[=:]\s*(\[[\s\S]*?\]);", content)
    if not m: return []
    a = re.sub(r"//.*?\n", "\n", m.group(2))
    a = re.sub(r",\s*}", "}", a); a = re.sub(r",\s*]", "]", a)
    try: return json.loads(a)
    except: return []

# --- Projects ---
def list_projects():
    return _ts_array(_read("data/projects.ts"), "projectsData")

def add_project(name, desc, icon, url, tags):
    content = _read("data/projects.ts")
    pid = f"proj_{int(datetime.datetime.now().timestamp()*1000)}"
    entry = f'  {{\n    "id": "{pid}",\n    "name": "{name}",\n    "githubUrl": "{url}",\n    "description": "{desc}",\n    "icon": "{icon}",\n    "tags": {json.dumps(tags, ensure_ascii=False)}\n  }},'
    content = content.rstrip()[:-1] + "\n" + entry + "\n" + content.rstrip()[-1]
    _write("data/projects.ts", content)
    commit_push(["data/projects.ts"], f"chore: add project {name}")
    return f"已添加项目 [{name}]"

def del_project(pid):
    content = _read("data/projects.ts")
    pat = re.compile(r'  \{[^}]*?"id":\s*"'+re.escape(pid)+r'"[^}]*?\},?\n?', re.DOTALL)
    if not pat.search(content): return f"未找到项目 {pid}"
    _write("data/projects.ts", pat.sub("", content))
    commit_push(["data/projects.ts"], f"chore: delete project {pid}")
    return f"已删除项目 {pid}"

def edit_project(pid, field, value):
    content = _read("data/projects.ts")
    pat = re.compile(r'(\{[^}]*?"id":\s*"'+re.escape(pid)+r'"[^}]*?\})', re.DOTALL)
    m = pat.search(content)
    if not m: return f"未找到项目 {pid}"
    old = m.group(1)
    new = re.sub(r'("'+re.escape(field)+r'":\s*)"[^"]*"', r'\1"'+value.replace('"','\\"')+'"', old)
    _write("data/projects.ts", content.replace(old, new))
    commit_push(["data/projects.ts"], f"chore: edit project {pid}")
    return f"已更新项目 {pid} 的 {field}"

# --- Albums ---
def list_albums():
    return _ts_array(_read("data/albums.ts"), "albums")

def add_album(title, desc, cover, date):
    content = _read("data/albums.ts")
    aid = f"album_{int(datetime.datetime.now().timestamp())}"
    entry = f'  {{\n    "id": "{aid}",\n    "title": "{title}",\n    "description": "{desc}",\n    "cover": "{cover}",\n    "date": "{date}",\n    "photos": []\n  }},'
    content = content.rstrip()[:-1] + "\n" + entry + "\n" + content.rstrip()[-1]
    _write("data/albums.ts", content)
    commit_push(["data/albums.ts"], f"chore: add album {title}")
    return f"已添加相册 [{title}]"

def del_album(aid):
    content = _read("data/albums.ts")
    pat = re.compile(r'  \{[^}]*?"id":\s*"'+re.escape(aid)+r'"[^}]*?\},?\n?', re.DOTALL)
    if not pat.search(content): return f"未找到相册 {aid}"
    _write("data/albums.ts", pat.sub("", content))
    commit_push(["data/albums.ts"], f"chore: delete album {aid}")
    return f"已删除相册 {aid}"

def add_photo(aid, url, caption=""):
    content = _read("data/albums.ts")
    pat = re.compile(r'(\{[^}]*?"id":\s*"'+re.escape(aid)+r'"[^}]*?"photos":\s*\[)([^\]]*)(\])', re.DOTALL)
    m = pat.search(content)
    if not m: return f"未找到相册 {aid}"
    p, e, s = m.group(1), m.group(2).strip(), m.group(3)
    np = f'\n      {{\n        "url": "{url}",\n        "caption": "{caption}"\n      }},'
    content = pat.sub(p + e + np + "\n    " + s if e else p + "\n" + np + "\n    " + s, content, count=1)
    _write("data/albums.ts", content)
    commit_push(["data/albums.ts"], f"chore: add photo to album {aid}")
    return f"已添加照片到相册 {aid}"

# --- Music ---
def list_music():
    content = _read("siteConfig.ts")
    m = re.search(r"cloudMusicIds:\s*\[([^\]]*)\]", content)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []

def add_music(sid):
    content = _read("siteConfig.ts")
    if sid in list_music(): return f"歌曲 {sid} 已在列表"
    content = re.sub(r'(cloudMusicIds:\s*\[)', lambda m: m.group(1) + f' "{sid}",', content)
    _write("siteConfig.ts", content)
    commit_push(["siteConfig.ts"], f"chore: add music {sid}")
    return f"已添加歌曲 {sid}"

def remove_music(sid):
    content = _read("siteConfig.ts")
    content = re.sub(r',?\s*"'+re.escape(sid)+r'"', "", content)
    content = re.sub(r'(\[)\s*,', r'\1', content)
    content = re.sub(r',\s*(\])', r'\1', content)
    _write("siteConfig.ts", content)
    commit_push(["siteConfig.ts"], f"chore: remove music {sid}")
    return f"已移除歌曲 {sid}"

# --- Chatters ---
def list_chatters():
    files = _listdir("chatters")
    res = []
    for f in files:
        if not f.endswith(".md"): continue
        meta = _parse_frontmatter(_read(f"chatters/{f}"))
        res.append({"file": f, "title": meta.get("title", ""), "date": meta.get("date", "")})
    return sorted(res, key=lambda x: x.get("date", ""), reverse=True)

def new_chatter(title, body, tags=None):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = now.split(" ")[0]
    files = [f for f in _listdir("chatters") if f.startswith(slug)]
    if files: slug += f"-{len(files)}"
    fname = f"{slug}.md"
    meta = {"title": title, "date": f"'{now}'", "tags": tags or ["日常"], "mood": "", "cover": "", "description": ""}
    full = "---\n" + yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    _write(f"chatters/{fname}", full)
    commit_push([f"chatters/{fname}"], f"chore: add chatter {title}")
    return f"已发布说说 [{title}]"

def del_chatter(fname):
    full = f"chatters/{fname}"
    if not os.path.exists(os.path.join(_WORK_DIR, full)): return f"未找到 {fname}"
    _delete(full)
    commit_push([full], f"chore: delete chatter {fname}")
    return f"已删除说说 {fname}"

# --- Moments ---
def list_moments():
    files = _listdir("moments")
    res = []
    for f in files:
        if not f.endswith(".md"): continue
        meta = _parse_frontmatter(_read(f"moments/{f}"))
        res.append({"file": f, "id": meta.get("id",""), "date": meta.get("date","")})
    return sorted(res, key=lambda x: x.get("date",""), reverse=True)

def new_moment(body, location="", images=None):
    now = datetime.datetime.now()
    mid = f"moment-{int(now.timestamp()*1000)}"
    ds = now.strftime("%Y-%m-%dT%H:%M:%S.")+f"{now.microsecond//1000:03d}Z"
    fname = f"{mid}.md"
    meta = {"id": mid, "date": f"'{ds}'", "location": location, "images": images or []}
    full = "---\n" + yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    _write(f"moments/{fname}", full)
    commit_push([f"moments/{fname}"], "chore: add moment")
    return f"已发布动态 {mid}"

def del_moment(mid):
    files = _listdir("moments")
    t = [f for f in files if mid in f]
    if not t: return f"未找到动态 {mid}"
    fname = t[0]
    _delete(f"moments/{fname}")
    commit_push([f"moments/{fname}"], f"chore: delete moment {fname}")
    return f"已删除动态 {fname}"

# --- About ---
def get_about():
    c = _read("app/about/about.md")
    if not c: return {"title":"","content":""}
    m = _parse_frontmatter(c)
    b = _strip_fm(c).strip()
    return {"title": m.get("title",""), "content": b}

def set_about(title, body):
    meta = {"title": title, "date": f"'{datetime.datetime.now().strftime('%Y-%m-%d')}'", "tags": [], "mood": "", "cover": "", "description": ""}
    full = "---\n" + yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False) + "---\n\n" + body + "\n"
    _write("app/about/about.md", full)
    commit_push(["app/about/about.md"], "chore: update about")
    return "关于页面已更新"


# ========== 插件主类 ==========

@register("astr_zerasos_home", "opaup", "Zerasos-Home 博客管理", "1.0.6")
class ZerasosHomePlugin(Star):

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.admin_ids = set()
        self._enabled = True
        self._load_config()

    def _load_config(self):
        self._enabled = bool(self.config.get("enabled", True))
        ids = self.config.get("admin_ids", [])
        self.admin_ids = set()
        if isinstance(ids, list):
            for uid in ids:
                if uid and str(uid).strip():
                    self.admin_ids.add(str(uid).strip())

    def _is_admin(self, event):
        if not self.admin_ids:
            return True
        try:
            return str(event.message_obj.sender.user_id) in self.admin_ids
        except:
            return False

    def on_config_update(self, config: dict):
        self.config = config or {}
        self._load_config()

    async def terminate(self):
        pass

    @staticmethod
    def _br(text):
        return str(text).replace("\n", "<br />")

    @command("zh")
    async def zh_router(self, event: AstrMessageEvent):
        text = event.message_str.strip()
        parts = text.split()
        subcmd = parts[1].lower() if len(parts) >= 2 else "help"

        if subcmd != "help":
            if not self._is_admin(event):
                yield event.plain_result(self._br("你没有权限"))
                return
            if not self._enabled:
                yield event.plain_result(self._br("插件已禁用"))
                return

        if subcmd == "help":
            yield event.plain_result(self._br(
                "=== Zerasos-Home 博客管理 ===<br/><br/>"
                "【项目】<br/>"
                "  /zh projects list                    列项目<br/>"
                "  /zh projects add 名称|描述|图标|URL|标签1,标签2<br/>"
                "  /zh projects del <id><br/>"
                "  /zh projects edit <id> <字段> <值><br/>"
                "    字段: name, description, icon, githubUrl<br/><br/>"
                "【相册】<br/>"
                "  /zh albums list                      列相册<br/>"
                "  /zh albums add 标题|描述|封面URL|日期<br/>"
                "  /zh albums del <id><br/>"
                "  /zh photos add <album_id>|图URL|描述  添加照片<br/><br/>"
                "【歌单】<br/>"
                "  /zh music list                       列歌单<br/>"
                "  /zh music add <网易云ID><br/>"
                "  /zh music del <网易云ID><br/><br/>"
                "【说说】<br/>"
                "  /zh chatters list                    列说说<br/>"
                "  /zh chatters add 标题 | 内容          发布<br/>"
                "  /zh chatters del <文件名><br/><br/>"
                "【动态】<br/>"
                "  /zh moments list                     列动态<br/>"
                "  /zh moments add 内容 [定位] [图片]<br/>"
                "  /zh moments del <id><br/><br/>"
                "【关于】<br/>"
                "  /zh about                            查看<br/>"
                "  /zh about edit 标题 | 内容           编辑<br/><br/>"
                "修改后自动提交 GitHub，Vercel 自动构建部署"
            ))
            return

        try:
            if subcmd in ("projects", "project"):
                yield event.plain_result(self._br(await self._cmd_projects(parts)))
            elif subcmd in ("albums", "album"):
                yield event.plain_result(self._br(await self._cmd_albums(parts)))
            elif subcmd == "photos":
                yield event.plain_result(self._br(await self._cmd_photos(parts)))
            elif subcmd == "music":
                yield event.plain_result(self._br(await self._cmd_music(parts)))
            elif subcmd in ("chatters", "chatter"):
                yield event.plain_result(self._br(await self._cmd_chatters(parts)))
            elif subcmd in ("moments", "moment"):
                yield event.plain_result(self._br(await self._cmd_moments(parts)))
            elif subcmd == "about":
                yield event.plain_result(self._br(await self._cmd_about(parts)))
            else:
                yield event.plain_result(self._br("未知指令，/zh help 查看帮助"))
        except Exception as e:
            logger.exception("指令执行异常")
            yield event.plain_result(self._br(f"执行出错: {str(e)[:200]}"))

    async def _cmd_projects(self, parts):
        if len(parts) < 3: return "用法: /zh projects <list|add|del|edit>"
        ensure_repo()
        a = parts[2].lower()
        if a == "list":
            ps = list_projects()
            if not ps: return "暂无项目"
            return "项目列表:\n" + "\n".join(f"[{p.get('id','?')[:8]}...] {p.get('name','?')}" for p in ps)
        if a == "add":
            if len(parts) < 4: return "用法: /zh projects add 名称|描述|图标|URL|标签1,标签2"
            args = " ".join(parts[3:]).split("|")
            if len(args) < 5: return "请用 | 分隔 5 项"
            return add_project(args[0].strip(), args[1].strip(), args[2].strip(), args[3].strip(), [t.strip() for t in args[4].split(",") if t.strip()])
        if a == "del":
            if len(parts) < 4: return "用法: /zh projects del <id>"
            return del_project(parts[3])
        if a == "edit":
            if len(parts) < 6: return "用法: /zh projects edit <id> <字段> <新值>"
            return edit_project(parts[3], parts[4], " ".join(parts[5:]))
        return "可用: list add del edit"

    async def _cmd_albums(self, parts):
        if len(parts) < 3: return "用法: /zh albums <list|add|del>"
        ensure_repo()
        a = parts[2].lower()
        if a == "list":
            als = list_albums()
            if not als: return "暂无相册"
            return "相册列表:\n" + "\n".join(f"[{al.get('id','?')[:20]}...] {al.get('title','?')} ({len(al.get('photos',[]))}张)" for al in als)
        if a == "add":
            if len(parts) < 4: return "用法: /zh albums add 标题|描述|封面URL|日期"
            args = " ".join(parts[3:]).split("|")
            if len(args) < 4: return "请用 | 分隔 4 项"
            return add_album(args[0].strip(), args[1].strip(), args[2].strip(), args[3].strip())
        if a == "del":
            if len(parts) < 4: return "用法: /zh albums del <id>"
            return del_album(parts[3])
        return "可用: list add del"

    async def _cmd_photos(self, parts):
        if len(parts) < 4 or parts[2].lower() != "add":
            return "用法: /zh photos add <album_id>|图URL|描述"
        ensure_repo()
        args = " ".join(parts[3:]).split("|")
        if len(args) < 2: return "请提供 album_id 和 URL"
        return add_photo(args[0].strip(), args[1].strip(), args[2].strip() if len(args) > 2 else "")

    async def _cmd_music(self, parts):
        if len(parts) < 3: return "用法: /zh music <list|add|del>"
        ensure_repo()
        a = parts[2].lower()
        if a == "list":
            ids = list_music()
            return "歌单为空" if not ids else "歌单:\n" + "\n".join(f"  {i+1}. {sid}" for i, sid in enumerate(ids))
        if a == "add":
            if len(parts) < 4: return "用法: /zh music add <网易云ID>"
            return add_music(parts[3])
        if a in ("del","remove"):
            if len(parts) < 4: return "用法: /zh music del <网易云ID>"
            return remove_music(parts[3])
        return "可用: list add del"

    async def _cmd_chatters(self, parts):
        if len(parts) < 3: return "用法: /zh chatters <list|add|del>"
        ensure_repo()
        a = parts[2].lower()
        if a == "list":
            items = list_chatters()
            return "暂无说说" if not items else "说说:\n" + "\n".join(f"  {i['file']} - {i['title']}" for i in items[:20])
        if a == "add":
            if len(parts) < 4: return "用法: /zh chatters add 标题 | 内容"
            args = " ".join(parts[3:]).split("|")
            title = args[0].strip() or "未命名"
            body = args[1].strip() if len(args) > 1 else "(暂无)"
            return new_chatter(title, body)
        if a == "del":
            if len(parts) < 4: return "用法: /zh chatters del <文件名>"
            return del_chatter(parts[3])
        return "可用: list add del"

    async def _cmd_moments(self, parts):
        if len(parts) < 3: return "用法: /zh moments <list|add|del>"
        ensure_repo()
        a = parts[2].lower()
        if a == "list":
            items = list_moments()
            return "暂无动态" if not items else "动态:\n" + "\n".join(f"  {i['id']}" for i in items[:20])
        if a == "add":
            if len(parts) < 4: return "用法: /zh moments add <内容>"
            text = " ".join(parts[3:])
            loc = ""
            imgs = []
            ml = re.search(r'\|\s*location=(.+?)(?:\||$)', text)
            if ml: loc = ml.group(1).strip(); text = text.replace(ml.group(0), "")
            mi = re.search(r'\|\s*images=(.+?)(?:\||$)', text)
            if mi: imgs = [u.strip() for u in mi.group(1).split(",") if u.strip()]; text = text.replace(mi.group(0), "")
            return new_moment(text.strip(), location=loc, images=imgs)
        if a == "del":
            if len(parts) < 4: return "用法: /zh moments del <id>"
            return del_moment(parts[3])
        return "可用: list add del"

    async def _cmd_about(self, parts):
        ensure_repo()
        if len(parts) >= 3 and parts[2].lower() == "edit":
            if len(parts) < 4: return "用法: /zh about edit 标题 | 内容"
            args = " ".join(parts[3:]).split("|")
            title = args[0].strip() or "关于我"
            body = args[1].strip() if len(args) > 1 else ""
            return set_about(title, body)
        about = get_about()
        if not about["content"]: return "关于页面暂无内容"
        return f"=== {about['title']} ===\n\n{about['content'][:500]}"
