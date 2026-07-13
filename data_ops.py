"""
博客数据操作：对 TypeScript 数据文件和 Markdown 文件进行增删改
"""

import re, json, os, datetime, yaml
from github_ops import read_file, write_file, delete_file, list_files, commit_and_push

# ─── Projects ────────────────────────────────────────────────────

def list_projects() -> list[dict]:
    """列出所有项目"""
    content = read_file("data/projects.ts")
    return _parse_ts_array(content, "projectsData")

def add_project(name: str, description: str, icon: str, github_url: str, tags: list[str]) -> str:
    content = read_file("data/projects.ts")
    new_id = f"proj_{int(datetime.datetime.now().timestamp()*1000)}"
    entry = f'  {{\n    "id": "{new_id}",\n    "name": "{name}",\n    "githubUrl": "{github_url}",\n    "description": "{description}",\n    "icon": "{icon}",\n    "tags": {json.dumps(tags, ensure_ascii=False)}\n  }},'
    # 在最后一个 ] 前插入
    content = content.rstrip()
    content = content[:-1] + "\n" + entry + "\n" + content[-1]
    write_file("data/projects.ts", content)
    msg = f"chore: add project {name}"
    commit_and_push(["data/projects.ts"], msg)
    return f"已添加项目 [{name}] (id: {new_id})"

def del_project(proj_id: str) -> str:
    content = read_file("data/projects.ts")
    # 匹配包含该 id 的整个对象块
    pattern = re.compile(r'  \{[^}]*?"id":\s*"'+re.escape(proj_id)+r'"[^}]*?\},?\n?', re.DOTALL)
    if not pattern.search(content):
        return f"未找到项目 id={proj_id}"
    content = pattern.sub("", content)
    write_file("data/projects.ts", content)
    commit_and_push(["data/projects.ts"], f"chore: delete project {proj_id}")
    return f"已删除项目 {proj_id}"

def edit_project(proj_id: str, field: str, value: str) -> str:
    content = read_file("data/projects.ts")
    # 找到对象的起始和结束
    pattern = re.compile(r'(\{[^}]*?"id":\s*"'+re.escape(proj_id)+r'"[^}]*?\})', re.DOTALL)
    m = pattern.search(content)
    if not m:
        return f"未找到项目 id={proj_id}"
    obj_str = m.group(1)
    # 替换字段
    field_pattern = re.compile(r'("'+re.escape(field)+r'":\s*)"[^"]*"')
    obj_new = field_pattern.sub(r'\1"'+value.replace('"', '\\"')+'"', obj_str)
    content = content.replace(obj_str, obj_new)
    write_file("data/projects.ts", content)
    commit_and_push(["data/projects.ts"], f"chore: edit project {proj_id} {field}")
    return f"已更新项目 {proj_id} 的 {field}"

# ─── Albums / Photos ────────────────────────────────────────────

def list_albums() -> list[dict]:
    content = read_file("data/albums.ts")
    return _parse_ts_array(content, "albums")

def add_album(title: str, description: str, cover: str, date_str: str) -> str:
    content = read_file("data/albums.ts")
    new_id = f"album_{int(datetime.datetime.now().timestamp())}"
    entry = f'''  {{
    "id": "{new_id}",
    "title": "{title}",
    "description": "{description}",
    "cover": "{cover}",
    "date": "{date_str}",
    "photos": []
  }},'''
    content = content.rstrip()
    content = content[:-1] + "\n" + entry + "\n" + content[-1]
    write_file("data/albums.ts", content)
    commit_and_push(["data/albums.ts"], f"chore: add album {title}")
    return f"已添加相册 [{title}] (id: {new_id})"

def del_album(album_id: str) -> str:
    content = read_file("data/albums.ts")
    pattern = re.compile(r'  \{[^}]*?"id":\s*"'+re.escape(album_id)+r'"[^}]*?\},?\n?', re.DOTALL)
    if not pattern.search(content):
        return f"未找到相册 id={album_id}"
    content = pattern.sub("", content)
    write_file("data/albums.ts", content)
    commit_and_push(["data/albums.ts"], f"chore: delete album {album_id}")
    return f"已删除相册 {album_id}"

def add_photo(album_id: str, url: str, caption: str = "") -> str:
    content = read_file("data/albums.ts")
    # 找到目标相册
    pattern = re.compile(r'(\{[^}]*?"id":\s*"'+re.escape(album_id)+r'"[^}]*?"photos":\s*\[)([^\]]*)(\])', re.DOTALL)
    m = pattern.search(content)
    if not m:
        return f"未找到相册 id={album_id}"
    prefix = m.group(1)
    existing = m.group(2).strip()
    suffix = m.group(3)
    new_photo = f'\n      {{\n        "url": "{url}",\n        "caption": "{caption}"\n      }},'
    if existing:
        new_content = prefix + existing + new_photo + "\n    " + suffix
    else:
        new_content = prefix + "\n" + new_photo + "\n    " + suffix
    content = pattern.sub(new_content, content, count=1)
    write_file("data/albums.ts", content)
    commit_and_push(["data/albums.ts"], f"chore: add photo to album {album_id}")
    return f"已向相册 {album_id} 添加照片"

# ─── Music ───────────────────────────────────────────────────────

def list_music() -> list[str]:
    content = read_file("siteConfig.ts")
    m = re.search(r'cloudMusicIds:\s*\[([^\]]*)\]', content)
    if not m:
        return []
    raw = m.group(1)
    return re.findall(r'"([^"]+)"', raw)

def add_music(song_id: str) -> str:
    content = read_file("siteConfig.ts")
    existing = list_music()
    if song_id in existing:
        return f"歌曲 {song_id} 已在列表中"
    # 在 cloudMusicIds 数组的最后一个元素前插入
    content = re.sub(
        r'(cloudMusicIds:\s*\[)([^\]]*)(\])',
        lambda m: m.group(1) + m.group(2) + ("," if m.group(2).strip() else "") + f' "{song_id}" ' + m.group(3),
        content
    )
    write_file("siteConfig.ts", content)
    commit_and_push(["siteConfig.ts"], f"chore: add music {song_id}")
    return f"已添加歌曲 ID: {song_id}"

def remove_music(song_id: str) -> str:
    content = read_file("siteConfig.ts")
    if song_id not in list_music():
        return f"歌曲 {song_id} 不在列表中"
    content = re.sub(r',?\s*"'+re.escape(song_id)+r'"', "", content)
    content = re.sub(r'(\[)\s*,', r'\1', content)
    content = re.sub(r',\s*(\])', r'\1', content)
    write_file("siteConfig.ts", content)
    commit_and_push(["siteConfig.ts"], f"chore: remove music {song_id}")
    return f"已移除歌曲 ID: {song_id}"

# ─── Chatters (说说/云端杂谈) ──────────────────────────────────

def list_chatters() -> list[dict]:
    files = list_files("chatters")
    result = []
    for fname in files:
        if not fname.endswith(".md"):
            continue
        content = read_file(f"chatters/{fname}")
        meta = _parse_frontmatter(content)
        result.append({"file": fname, "title": meta.get("title", ""), "date": meta.get("date", "")})
    return sorted(result, key=lambda x: x.get("date", ""), reverse=True)

def new_chatter(title: str, content_body: str, tags: list[str] = None, mood: str = "") -> str:
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = today.split(" ")[0]
    # 避免冲突
    files = [f for f in list_files("chatters") if f.startswith(slug)]
    if files:
        slug += f"-{len(files)}"
    fname = f"{slug}.md"
    meta = {
        "title": title,
        "date": f"'{today}'",
        "tags": tags or [],
        "mood": mood,
        "cover": "",
        "description": ""
    }
    yaml_block = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    full = f"---\n{yaml_block}---\n\n{content_body}\n"
    write_file(f"chatters/{fname}", full)
    commit_and_push([f"chatters/{fname}"], f"chore: add chatter {title}")
    return f"已发布说说 [{title}] -> chatters/{fname}"

def del_chatter(filename: str) -> str:
    path = f"chatters/{filename}"
    if not os.path.exists(os.path.join(WORK_DIR, path)):
        return f"未找到文件 {path}"
    delete_file(path)
    commit_and_push([path], f"chore: delete chatter {filename}")
    return f"已删除说说 {filename}"

# ─── Moments (杂谈/动态) ───────────────────────────────────────

def list_moments() -> list[dict]:
    files = list_files("moments")
    result = []
    for fname in files:
        if not fname.endswith(".md"):
            continue
        content = read_file(f"moments/{fname}")
        meta = _parse_frontmatter(content)
        result.append({"file": fname, "id": meta.get("id", ""), "date": meta.get("date", "")})
    return sorted(result, key=lambda x: x.get("date", ""), reverse=True)

def new_moment(content_body: str, location: str = "", images: list[str] = None) -> str:
    now = datetime.datetime.now()
    moment_id = f"moment-{int(now.timestamp() * 1000)}"
    date_str = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    fname = f"{moment_id}.md"
    meta = {
        "id": moment_id,
        "date": f"'{date_str}'",
        "location": location,
        "images": images or []
    }
    yaml_block = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    full = f"---\n{yaml_block}---\n\n{content_body}\n"
    write_file(f"moments/{fname}", full)
    commit_and_push([f"moments/{fname}"], f"chore: add moment")
    return f"已发布动态 {moment_id}"

def del_moment(moment_id: str) -> str:
    files = list_files("moments")
    target = [f for f in files if moment_id in f]
    if not target:
        return f"未找到动态 {moment_id}"
    fname = target[0]
    delete_file(f"moments/{fname}")
    commit_and_push([f"moments/{fname}"], f"chore: delete moment {fname}")
    return f"已删除动态 {fname}"

# ─── About ───────────────────────────────────────────────────────

def get_about() -> dict:
    content = read_file("app/about/about.md")
    if not content:
        return {"title": "", "content": ""}
    meta = _parse_frontmatter(content)
    body = _strip_frontmatter(content)
    return {"title": meta.get("title", ""), "content": body.strip()}

def set_about(title: str, body: str) -> str:
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    meta = {"title": title, "date": f"'{today}'", "tags": [], "mood": "", "cover": "", "description": ""}
    yaml_block = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    full = f"---\n{yaml_block}---\n\n{body}\n"
    write_file("app/about/about.md", full)
    commit_and_push(["app/about/about.md"], "chore: update about page")
    return "关于页面已更新"

# ─── 工具函数 ──────────────────────────────────────────────────

def _parse_ts_array(content: str, var_name: str) -> list[dict]:
    """从 TypeScript 文件中提取数组内容（简易解析）"""
    m = re.search(r'export\s+(const|let|var)\s+' + re.escape(var_name) + r'\s*[=:]\s*(\[[\s\S]*?\]);', content)
    if not m:
        return []
    array_str = m.group(2)
    # 将 TS 对象转为 JSON 兼容格式（去掉注释、尾逗号）
    array_str = re.sub(r'//.*?\n', '\n', array_str)
    array_str = re.sub(r',\s*}', '}', array_str)
    array_str = re.sub(r',\s*\]', ']', array_str)
    try:
        return json.loads(array_str)
    except json.JSONDecodeError:
        return []

def _parse_frontmatter(content: str) -> dict:
    """解析 Markdown 文件的 YAML frontmatter"""
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}

def _strip_frontmatter(content: str) -> str:
    """去掉 Markdown 文件的 frontmatter"""
    m = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
    if m:
        return content[m.end():]
    return content
