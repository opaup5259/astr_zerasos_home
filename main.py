"""
Zerasos-Home 博客管理系统 - 单文件异步插件
"""
import os, sys, re, logging, asyncio, tempfile, shutil, json, datetime
import yaml
sys.dont_write_bytecode = True
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
for _root, _dirs, _files in os.walk(_PLUGIN_DIR):
    for _d in _dirs:
        if _d == "__pycache__":
            shutil.rmtree(os.path.join(_root, _d), ignore_errors=True)
    for _f in _files:
        if _f.endswith(".pyc"):
            try: os.remove(os.path.join(_root, _f))
            except: pass
from astrbot.api.all import *

# 延迟导入 auto_publish 避免循环引用
_AUTO_PUBLISHER = None

def _get_auto_publisher(context, config):
    global _AUTO_PUBLISHER
    if _AUTO_PUBLISHER is None:
        from auto_publish import AutoPublishService
        _AUTO_PUBLISHER = AutoPublishService(context, config)
    return _AUTO_PUBLISHER

logger = logging.getLogger("astr_zerasos_home")

# ========== Git ==========
_REPO_BRANCH = "main"
_REPO_FULL = "opaup5259/Zerasos-Home"
_WORK_DIR = os.path.join(tempfile.gettempdir(), "zerasos-home-repo")

def _repo_url(user="", token=""):
    if user and token:
        return f"https://{user}:{token}@github.com/{_REPO_FULL}.git"
    return f"https://github.com/{_REPO_FULL}.git"

async def _git(args, cwd=None, user="", token=""):
    cwd = cwd or _WORK_DIR
    url = _repo_url(user, token) if user and token else _repo_url()
    env = os.environ.copy()
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=cwd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env=env
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"git {' '.join(args)} 超时")
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {stderr.decode()[:300]}")
    return stdout.decode()

async def ensure_repo(user="", token=""):
    url = _repo_url(user, token) if user and token else _repo_url()
    if os.path.isdir(os.path.join(_WORK_DIR, ".git")):
        await _git(["remote", "set-url", "origin", url], user=user, token=token)
        await _git(["pull", "origin", _REPO_BRANCH], user=user, token=token)
    else:
        if os.path.isdir(_WORK_DIR):
            shutil.rmtree(_WORK_DIR, ignore_errors=True)
        parent = os.path.dirname(_WORK_DIR)
        os.makedirs(parent, exist_ok=True)
        await _git(["clone", url, _WORK_DIR], cwd=parent, user=user, token=token)

async def commit_push(files, msg, user="", token=""):
    await ensure_repo(user=user, token=token)
    for f in files:
        await _git(["add", f], user=user, token=token)
    await _git(["-c", "user.name=opaup5259", "-c", "user.email=opaup5259@gmail.com",
              "commit", "-m", msg], user=user, token=token)
    await _git(["push", "origin", _REPO_BRANCH], user=user, token=token)

# ========== 文件 ==========
def _read(rel):
    path = os.path.join(_WORK_DIR, rel)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return f.read()
    return ""
def _write(rel, content):
    path = os.path.join(_WORK_DIR, rel); os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(content)
def _delete(rel):
    path = os.path.join(_WORK_DIR, rel)
    if os.path.exists(path): os.remove(path)
def _listdir(rel_dir):
    path = os.path.join(_WORK_DIR, rel_dir)
    if os.path.isdir(path): return sorted(os.listdir(path))
    return []
def _parse_fm(content):
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if m:
        try: return yaml.safe_load(m.group(1)) or {}
        except: pass
    return {}
def _strip_fm(content):
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content
def _ts_array(content, vn):
    m = re.search(r"export\s+(const|let|var)\s+"+re.escape(vn)+r"\s*[=:]\s*(\[[\s\S]*?\]);", content)
    if not m: return []
    a = re.sub(r"//.*?\n", "\n", m.group(2))
    a = re.sub(r",\s*}", "}", a); a = re.sub(r",\s*]", "]", a)
    try: return json.loads(a)
    except: return []

# ========== 数据操作 ==========
def list_projects(): return _ts_array(_read("data/projects.ts"), "projectsData")
async def add_project(n,d,i,u,t, user="", token=""):
    c=_read("data/projects.ts"); pid=f"proj_{int(datetime.datetime.now().timestamp()*1000)}"
    e=f'  {{\n    "id": "{pid}",\n    "name": "{n}",\n    "githubUrl": "{u}",\n    "description": "{d}",\n    "icon": "{i}",\n    "tags": {json.dumps(t, ensure_ascii=False)}\n  }},'
    c=c.rstrip()[:-1]+"\n"+e+"\n"+c.rstrip()[-1]; _write("data/projects.ts",c)
    await commit_push(["data/projects.ts"],f"chore: add project {n}",user=user,token=token)
    return f"已添加项目 [{n}]"
async def del_project(pid, user="", token=""):
    c=_read("data/projects.ts"); p=re.compile(r'  \{[^}]*?"id":\s*"'+re.escape(pid)+r'"[^}]*?\},?\n?', re.DOTALL)
    if not p.search(c): return f"未找到项目 {pid}"
    _write("data/projects.ts",p.sub("",c))
    await commit_push(["data/projects.ts"],f"chore: delete project {pid}",user=user,token=token)
    return f"已删除项目 {pid}"
async def edit_project(pid,f,v, user="", token=""):
    c=_read("data/projects.ts"); p=re.compile(r'(\{[^}]*?"id":\s*"'+re.escape(pid)+r'"[^}]*?\})',re.DOTALL)
    m=p.search(c)
    if not m: return f"未找到项目 {pid}"
    n=re.sub(r'("'+re.escape(f)+r'":\s*)"[^"]*"',r'\1"'+v.replace('"','\\"')+'"',m.group(1))
    _write("data/projects.ts",c.replace(m.group(1),n))
    await commit_push(["data/projects.ts"],f"chore: edit project {pid}",user=user,token=token)
    return f"已更新项目 {pid} 的 {f}"
def list_albums(): return _ts_array(_read("data/albums.ts"),"albums")
async def add_album(t,d,cov,dat, user="", token=""):
    c=_read("data/albums.ts"); aid=f"album_{int(datetime.datetime.now().timestamp())}"
    e=f'  {{\n    "id": "{aid}",\n    "title": "{t}",\n    "description": "{d}",\n    "cover": "{cov}",\n    "date": "{dat}",\n    "photos": []\n  }},'
    c=c.rstrip()[:-1]+"\n"+e+"\n"+c.rstrip()[-1]; _write("data/albums.ts",c)
    await commit_push(["data/albums.ts"],f"chore: add album {t}",user=user,token=token)
    return f"已添加相册 [{t}]"
async def del_album(aid, user="", token=""):
    c=_read("data/albums.ts"); p=re.compile(r'  \{[^}]*?"id":\s*"'+re.escape(aid)+r'"[^}]*?\},?\n?',re.DOTALL)
    if not p.search(c): return f"未找到相册 {aid}"
    _write("data/albums.ts",p.sub("",c))
    await commit_push(["data/albums.ts"],f"chore: delete album {aid}",user=user,token=token)
    return f"已删除相册 {aid}"
async def add_photo(aid,url,caption="", user="", token=""):
    c=_read("data/albums.ts"); p=re.compile(r'(\{[^}]*?"id":\s*"'+re.escape(aid)+r'"[^}]*?"photos":\s*\[)([^\]]*)(\])',re.DOTALL)
    m=p.search(c)
    if not m: return f"未找到相册 {aid}"
    pre,ex,suf=m.group(1),m.group(2).strip(),m.group(3)
    np=f'\n      {{\n        "url": "{url}",\n        "caption": "{caption}"\n      }},'
    c=p.sub(pre+ex+np+"\n    "+suf if ex else pre+"\n"+np+"\n    "+suf,c,count=1)
    _write("data/albums.ts",c)
    await commit_push(["data/albums.ts"],f"chore: add photo to album {aid}",user=user,token=token)
    return f"已添加照片到相册 {aid}"
# ========== 歌单（统一管理，见 music_mgr.py） ==========
async def list_music(user="", token=""):
    from music_mgr import format_list
    from main import ensure_repo
    await ensure_repo(user=user, token=token)
    return format_list()

async def add_music(sid, user="", token=""):
    from music_mgr import do_add
    return await do_add("wyy", sid, "", user=user, token=token)

async def remove_music(sid, user="", token=""):
    from music_mgr import do_remove
    return await do_remove("wyy", sid, user=user, token=token)

async def add_bili_music(bvid, title="", user="", token=""):
    from music_mgr import do_add
    return await do_add("bili", bvid, title, user=user, token=token)

async def remove_bili_music(bvid, user="", token=""):
    from music_mgr import do_remove
    return await do_remove("bili", bvid, user=user, token=token)

async def swap_music(idx1, idx2, user="", token=""):
    from music_mgr import do_swap
    return await do_swap(idx1, idx2, user=user, token=token)

async def set_music_title(idx, title, user="", token=""):
    from music_mgr import do_title
    return await do_title(idx, title, user=user, token=token)

def list_chatters():
    res=[]
    for f in _listdir("chatters"):
        if not f.endswith(".md"): continue
        m=_parse_fm(_read(f"chatters/{f}")); res.append({"file":f,"title":m.get("title",""),"date":m.get("date","")})
    return sorted(res,key=lambda x:x.get("date",""),reverse=True)
async def new_chatter(title,body,tags=None, user="", token=""):
    now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"); slug=now.split(" ")[0]
    fs=[f for f in _listdir("chatters") if f.startswith(slug)]
    if fs: slug+=f"-{len(fs)}"
    meta={"title":title,"date":f"'{now}'","tags":tags or ["日常"],"mood":"","cover":"","description":""}
    full="---\n"+yaml.dump(meta,allow_unicode=True,default_flow_style=False,sort_keys=False)+"---\n\n"+body+"\n"
    _write(f"chatters/{slug}.md",full)
    await commit_push([f"chatters/{slug}.md"],f"chore: add chatter {title}",user=user,token=token)
    return f"已发布说说 [{title}]"
async def del_chatter(fname, user="", token=""):
    full=f"chatters/{fname}"
    if not os.path.exists(os.path.join(_WORK_DIR,full)): return f"未找到 {fname}"
    _delete(full); await commit_push([full],f"chore: delete chatter {fname}",user=user,token=token)
    return f"已删除说说 {fname}"
def list_moments():
    res=[]
    for f in _listdir("moments"):
        if not f.endswith(".md"): continue
        m=_parse_fm(_read(f"moments/{f}")); res.append({"file":f,"id":m.get("id",""),"date":m.get("date","")})
    return sorted(res,key=lambda x:x.get("date",""),reverse=True)
async def new_moment(body,location="",images=None, user="", token=""):
    now=datetime.datetime.now(); mid=f"moment-{int(now.timestamp()*1000)}"
    ds=now.strftime("%Y-%m-%dT%H:%M:%S.")+f"{now.microsecond//1000:03d}Z"
    meta={"id":mid,"date":f"'{ds}'","location":location,"images":images or []}
    full="---\n"+yaml.dump(meta,allow_unicode=True,default_flow_style=False,sort_keys=False)+"---\n\n"+body+"\n"
    _write(f"moments/{mid}.md",full)
    await commit_push([f"moments/{mid}.md"],"chore: add moment",user=user,token=token)
    return f"已发布动态 {mid}"
async def del_moment(mid, user="", token=""):
    files=_listdir("moments"); t=[f for f in files if mid in f]
    if not t: return f"未找到动态 {mid}"
    _delete(f"moments/{t[0]}")
    await commit_push([f"moments/{t[0]}"],f"chore: delete moment {t[0]}",user=user,token=token)
    return f"已删除动态 {t[0]}"
def get_about():
    c=_read("app/about/about.md")
    if not c: return {"title":"","content":""}
    m=_parse_fm(c); return {"title":m.get("title",""),"content":_strip_fm(c).strip()}
async def set_about(title,body, user="", token=""):
    meta={"title":title,"date":f"'{datetime.datetime.now().strftime('%Y-%m-%d')}'","tags":[],"mood":"","cover":"","description":""}
    full="---\n"+yaml.dump(meta,allow_unicode=True,default_flow_style=False,sort_keys=False)+"---\n\n"+body+"\n"
    _write("app/about/about.md",full)
    await commit_push(["app/about/about.md"],"chore: update about",user=user,token=token)
    return "关于页面已更新"

# ========== 插件主类 ==========
@register("astr_zerasos_home", "opaup", "Zerasos-Home 博客管理 - GitHub + Vercel 一键管理", "1.0.12")
class ZerasosHomePlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.admin_ids = set()
        self._enabled = True
        self._github_user = ""
        self._github_token = ""
        self._auto_publisher = None
        self._load_config()
        self._init_auto_publisher()

    def _load_config(self):
        self._enabled = bool(self.config.get("enabled", True))
        self._github_user = str(self.config.get("github_user", "") or "")
        self._github_token = str(self.config.get("github_token", "") or "")
        ids = self.config.get("admin_ids", [])
        self.admin_ids = set()
        if isinstance(ids, list):
            for uid in ids: self.admin_ids.add(str(uid).strip())

    def _is_admin(self, event):
        if not self.admin_ids: return True
        try: return str(event.message_obj.sender.user_id) in self.admin_ids
        except: return False

    def on_config_update(self, config: dict):
        self.config = config or {}; self._load_config()
        self._init_auto_publisher()

    async def terminate(self):
        if self._auto_publisher:
            self._auto_publisher.stop_scheduler()

    @staticmethod
    def _br(t): return str(t).replace("\n","<br />")

    def _init_auto_publisher(self):
        """初始化自动发布服务"""
        try:
            if self._auto_publisher is None:
                from auto_publish import AutoPublishService
                self._auto_publisher = AutoPublishService(self.context, self.config)
            else:
                self._auto_publisher.on_config_update(self.config)
            self._auto_publisher.set_credentials(self._github_user, self._github_token)
            self._auto_publisher.start_scheduler(self._github_user, self._github_token)
        except Exception as e:
            logger.warning(f"自动发布服务初始化失败: {e}")

    @command("zh")
    async def zh_router(self, event: AstrMessageEvent):
        text=event.message_str.strip(); parts=text.split(); subcmd=parts[1].lower() if len(parts)>=2 else "help"
        if subcmd!="help":
            if not self._is_admin(event): yield event.plain_result(self._br("你没有权限")); return
            if not self._enabled: yield event.plain_result(self._br("插件已禁用")); return
        if subcmd=="help":
            yield event.plain_result(self._br("=== Zerasos-Home 博客管理 ===<br/><br/>【项目】<br/>  /zh projects list<br/>  /zh projects add 名称|描述|图标|URL|标签1,标签2<br/>  /zh projects del <id><br/>  /zh projects edit <id> <字段> <值><br/><br/>【相册】<br/>  /zh albums list<br/>  /zh albums add 标题|描述|封面URL|日期<br/>  /zh albums del <id><br/>  /zh photos add <album_id>|图URL|描述<br/><br/>【歌单】<br/>  /zh music list            查看全部歌单（含序号）<br/>  /zh music wyy add <ID> [标题]  添加网易云歌曲<br/>  /zh music wyy del <ID或序号>  删除<br/>  /zh music bili add <BV号> [标题]  添加B站视频<br/>  /zh music bili del <BV号或序号>  删除<br/>  /zh music sort <序号1> <序号2>  交换排序<br/>  /zh music title <序号> <标题>  修改标题<br/><br/>【说说】<br/>  /zh chatters list<br/>  /zh chatters add 标题 | 内容<br/>  /zh chatters del <文件名><br/><br/>【动态】<br/>  /zh moments list<br/>  /zh moments add 内容<br/>  /zh moments del <id><br/><br/>【关于】<br/>  /zh about<br/>  /zh about edit 标题 | 内容<br/><br/>【AI 自动发布】<br/>  /zh ai publish - 强制运行一次自动发布说说<br/>  /zh ai status - 查看自动发布状态<br/><br/>【配置】<br/>  /zh config auto_publish - 查看自动发布配置<br/><br/>修改后自动提交 GitHub"))
            return
        try:
            user=self._github_user; token=self._github_token
            if subcmd in("projects","project"):
                yield event.plain_result(self._br(await self._cmd_projects(parts,user,token)))
            elif subcmd in("albums","album"):
                yield event.plain_result(self._br(await self._cmd_albums(parts,user,token)))
            elif subcmd=="photos":
                yield event.plain_result(self._br(await self._cmd_photos(parts,user,token)))
            elif subcmd=="music":
                yield event.plain_result(self._br(await self._cmd_music(parts,user,token)))
            elif subcmd in("chatters","chatter"):
                yield event.plain_result(self._br(await self._cmd_chatters(parts,user,token)))
            elif subcmd in("moments","moment"):
                yield event.plain_result(self._br(await self._cmd_moments(parts,user,token)))
            elif subcmd=="about":
                yield event.plain_result(self._br(await self._cmd_about(parts,user,token)))
            elif subcmd=="ai":
                yield event.plain_result(self._br(await self._cmd_ai(parts,user,token)))
            elif subcmd=="config":
                yield event.plain_result(self._br(await self._cmd_config(parts)))
            else:
                yield event.plain_result(self._br("未知指令，/zh help 查看帮助"))
        except Exception as e:
            logger.exception("指令异常")
            yield event.plain_result(self._br(f"出错: {str(e)[:300]}"))

    async def _cmd_projects(self,parts,user="",token=""):
        if len(parts)<3: return "用法: /zh projects <list|add|del|edit>"
        await ensure_repo(user=user,token=token); a=parts[2].lower()
        if a=="list":
            ps=list_projects()
            return "暂无项目" if not ps else "项目列表:\n"+"\n".join(f"[{p.get('id','?')[:8]}...] {p.get('name','?')}" for p in ps)
        if a=="add":
            if len(parts)<4: return "用法: /zh projects add 名称|描述|图标|URL|标签1,标签2"
            args=" ".join(parts[3:]).split("|")
            if len(args)<5: return "请用 | 分隔 5 项"
            return await add_project(args[0].strip(),args[1].strip(),args[2].strip(),args[3].strip(),[t.strip() for t in args[4].split(",") if t.strip()],user=user,token=token)
        if a=="del":
            if len(parts)<4: return "用法: /zh projects del <id>"
            return await del_project(parts[3],user=user,token=token)
        if a=="edit":
            if len(parts)<6: return "用法: /zh projects edit <id> <字段> <新值>"
            return await edit_project(parts[3],parts[4]," ".join(parts[5:]),user=user,token=token)

    async def _cmd_albums(self,parts,user="",token=""):
        if len(parts)<3: return "用法: /zh albums <list|add|del>"
        await ensure_repo(user=user,token=token); a=parts[2].lower()
        if a=="list":
            als=list_albums()
            return "暂无相册" if not als else "相册列表:\n"+"\n".join(f"[{al.get('id','?')[:20]}...] {al.get('title','?')} ({len(al.get('photos',[]))}张)" for al in als)
        if a=="add":
            if len(parts)<4: return "用法: /zh albums add 标题|描述|封面URL|日期"
            args=" ".join(parts[3:]).split("|")
            if len(args)<4: return "请用 | 分隔 4 项"
            return await add_album(args[0].strip(),args[1].strip(),args[2].strip(),args[3].strip(),user=user,token=token)
        if a=="del":
            if len(parts)<4: return "用法: /zh albums del <id>"
            return await del_album(parts[3],user=user,token=token)

    async def _cmd_photos(self,parts,user="",token=""):
        if len(parts)<4 or parts[2].lower()!="add": return "用法: /zh photos add <album_id>|图URL|描述"
        await ensure_repo(user=user,token=token)
        args=" ".join(parts[3:]).split("|")
        if len(args)<2: return "请提供 album_id 和 URL"
        return await add_photo(args[0].strip(),args[1].strip(),args[2].strip() if len(args)>2 else "",user=user,token=token)

    async def _cmd_music(self,parts,user="",token=""):
        if len(parts)<3: return "用法: /zh music <list|wyy|bili|sort|title>"
        await ensure_repo(user=user,token=token); a=parts[2].lower()
        if a=="list":
            return await list_music(user=user,token=token)
        if a in("wyy","163","netease"):
            return await self._cmd_music_wyy(parts,user,token)
        if a=="bili":
            return await self._cmd_music_bili(parts,user,token)
        if a=="sort":
            if len(parts)<5: return "用法: /zh music sort <序号1> <序号2>"
            try:
                i1=int(parts[3])-1; i2=int(parts[4])-1
                return await swap_music(i1,i2,user=user,token=token)
            except ValueError:
                return "序号必须是数字"
        if a=="title":
            if len(parts)<5: return "用法: /zh music title <序号> <标题>"
            try:
                idx=int(parts[3])-1; title=" ".join(parts[4:])
                return await set_music_title(idx,title,user=user,token=token)
            except ValueError:
                return "序号必须是数字"
        return "用法: /zh music <list|wyy|bili|sort|title>"

    async def _cmd_music_wyy(self,parts,user="",token=""):
        if len(parts)<4: return "用法: /zh music wyy <add|del> <ID> [标题]"
        a=parts[3].lower()
        if a=="add":
            if len(parts)<5: return "用法: /zh music wyy add <ID> [标题]"
            sid=parts[4]; title=" ".join(parts[5:]) if len(parts)>5 else ""
            return await add_music(sid,user=user,token=token)
        if a in("del","remove"):
            if len(parts)<5: return "用法: /zh music wyy del <ID或序号>"
            return await remove_music(parts[4],user=user,token=token)
        return "用法: /zh music wyy <add|del>"

    async def _cmd_music_bili(self,parts,user="",token=""):
        if len(parts)<4: return "用法: /zh music bili <add|del> <BV号> [标题]"
        a=parts[3].lower()
        if a=="add":
            if len(parts)<5: return "用法: /zh music bili add <BV号> [标题]"
            bvid=parts[4]; title=" ".join(parts[5:]) if len(parts)>5 else ""
            return await add_bili_music(bvid,title,user=user,token=token)
        if a in("del","remove"):
            if len(parts)<5: return "用法: /zh music bili del <BV号或序号>"
            return await remove_bili_music(parts[4],user=user,token=token)
        return "用法: /zh music bili <add|del>"

    async def _cmd_music_wyy(self,parts,user="",token=""):
        if len(parts)<4: return "用法: /zh music wyy <add|del> <ID> [标题]"
        a=parts[3].lower()
        if a=="add":
            if len(parts)<5: return "用法: /zh music wyy add <ID> [标题]"
            sid=parts[4]; title=" ".join(parts[5:]) if len(parts)>5 else ""
            return await add_music(sid,user=user,token=token)
        if a in("del","remove"):
            if len(parts)<5: return "用法: /zh music wyy del <ID或序号>"
            return await remove_music(parts[4],user=user,token=token)
        return "用法: /zh music wyy <add|del>"

    async def _cmd_music_bili(self,parts,user="",token=""):
        if len(parts)<4: return "用法: /zh music bili <add|del> <BV号> [标题]"
        a=parts[3].lower()
        if a=="add":
            if len(parts)<5: return "用法: /zh music bili add <BV号> [标题]"
            bvid=parts[4]; title=" ".join(parts[5:]) if len(parts)>5 else ""
            return await add_bili_music(bvid,title,user=user,token=token)
        if a in("del","remove"):
            if len(parts)<5: return "用法: /zh music bili del <BV号或序号>"
            return await remove_bili_music(parts[4],user=user,token=token)
        return "用法: /zh music bili <add|del>"

    async def _cmd_chatters(self,parts,user="",token=""):
        if len(parts)<3: return "用法: /zh chatters <list|add|del>"
        await ensure_repo(user=user,token=token); a=parts[2].lower()
        if a=="list":
            items=list_chatters(); return "暂无说说" if not items else "说说:\n"+"\n".join(f"  {i['file']} - {i['title']}" for i in items[:20])
        if a=="add":
            if len(parts)<4: return "用法: /zh chatters add 标题 | 内容"
            args=" ".join(parts[3:]).split("|"); title=args[0].strip() or "未命名"; body=args[1].strip() if len(args)>1 else "(暂无)"
            return await new_chatter(title,body,user=user,token=token)
        if a=="del":
            if len(parts)<4: return "用法: /zh chatters del <文件名>"
            return await del_chatter(parts[3],user=user,token=token)

    async def _cmd_moments(self,parts,user="",token=""):
        if len(parts)<3: return "用法: /zh moments <list|add|del>"
        await ensure_repo(user=user,token=token); a=parts[2].lower()
        if a=="list":
            items=list_moments(); return "暂无动态" if not items else "动态:\n"+"\n".join(f"  {i['id']}" for i in items[:20])
        if a=="add":
            if len(parts)<4: return "用法: /zh moments add <内容>"
            text=" ".join(parts[3:]); loc=""; imgs=[]
            ml=re.search(r'\|\s*location=(.+?)(?:\||$)',text)
            if ml: loc=ml.group(1).strip(); text=text.replace(ml.group(0),"")
            mi=re.search(r'\|\s*images=(.+?)(?:\||$)',text)
            if mi: imgs=[u.strip() for u in mi.group(1).split(",") if u.strip()]; text=text.replace(mi.group(0),"")
            return await new_moment(text.strip(),location=loc,images=imgs,user=user,token=token)
        if a=="del":
            if len(parts)<4: return "用法: /zh moments del <id>"
            return await del_moment(parts[3],user=user,token=token)

    async def _cmd_about(self,parts,user="",token=""):
        await ensure_repo(user=user,token=token)
        if len(parts)>=3 and parts[2].lower()=="edit":
            if len(parts)<4: return "用法: /zh about edit 标题 | 内容"
            args=" ".join(parts[3:]).split("|"); title=args[0].strip() or "关于我"; body=args[1].strip() if len(args)>1 else ""
            return await set_about(title,body,user=user,token=token)
        about=get_about()
        return "关于页面暂无内容" if not about["content"] else f"=== {about['title']} ===\n\n{about['content'][:500]}"

    async def _cmd_ai(self,parts,user="",token=""):
        """AI 相关指令"""
        if len(parts)<3: return "用法: /zh ai <publish|status>"
        a=parts[2].lower()
        if a=="publish":
            # 强制运行一次自动发布
            if self._auto_publisher is None:
                return "自动发布服务未初始化"
            self._auto_publisher.set_credentials(user, token)
            return await self._auto_publisher.force_run()
        if a=="status":
            if self._auto_publisher is None:
                return "自动发布服务未初始化"
            status_info = []
            status_info.append(f"启用: {'✅' if self._auto_publisher._enabled else '❌'}")
            status_info.append(f"Cron: {self._auto_publisher._cron}")
            status_info.append(f"调度器运行中: {'✅' if (self._auto_publisher._task and not self._auto_publisher._task.done()) else '❌'}")
            return "\n".join(status_info)
        return "用法: /zh ai <publish|status>"

    async def _cmd_config(self,parts):
        """查看配置"""
        if len(parts)<3: return "用法: /zh config <字段>"
        a=parts[2].lower()
        if a=="auto_publish":
            lines=["=== 自动发布配置 ==="]
            lines.append(f"  启用: {self.config.get('auto_publish_enabled',False)}")
            lines.append(f"  Cron: {self.config.get('auto_publish_cron','30 8 * * *')}")
            prompt=self.config.get('auto_publish_llm_prompt','')
            lines.append(f"  自定义Prompt: {'有' if prompt else '无（使用默认）'}")
            return "\n".join(lines)
        return f"未知配置字段: {a}"
