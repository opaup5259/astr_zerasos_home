"""
Unified music manager — 统一管理网易云 + B站歌单
支持排序、自定义标题、混合展示
"""
import re, json, logging

logger = logging.getLogger("astr_zerasos_home.music_mgr")

def _raw_text():
    from main import _read
    return _read("siteConfig.ts")

def _write_text(t):
    from main import _write
    _write("siteConfig.ts", t)

def parse_song_list(raw: str) -> list:
    """解析 songList 数组，兼容旧格式 cloudMusicIds + bilibiliIds"""
    # 尝试 songList
    m = re.search(r"songList:\s*(\[[\s\S]*?\])", raw)
    if m:
        a = m.group(1)
        a = re.sub(r"//.*?\n", "\n", a)
        a = re.sub(r",\s*}", "}", a)
        a = re.sub(r",\s*]", "]", a)
        try:
            songs = json.loads(a)
            if isinstance(songs, list):
                return songs
        except:
            pass
    # 兼容旧格式 — 合并 cloudMusicIds + bilibiliIds
    songs = []
    m1 = re.search(r"cloudMusicIds:\s*\[([^\]]*)\]", raw)
    if m1:
        for sid in re.findall(r'"([^"]+)"', m1.group(1)):
            songs.append({"type": "wyy", "id": sid, "title": ""})
    m2 = re.search(r"bilibiliIds:\s*\[([^\]]*)\]", raw)
    if m2:
        for bvid in re.findall(r'"([^"]+)"', m2.group(1)):
            songs.append({"type": "bili", "id": bvid, "title": ""})
    return songs

def make_song_list_text(songs: list) -> str:
    """生成 songList 的 TS 代码片段"""
    lines = ["  songList: ["]
    for s in songs:
        entry = json.dumps(s, ensure_ascii=False)
        lines.append(f"    {entry},")
    lines.append("  ],")
    return "\n".join(lines)

# ========== 公开接口 ==========

def list_all() -> list:
    songs = parse_song_list(_raw_text())
    return list(enumerate(songs))

def get_by_index(idx: int):
    songs = parse_song_list(_raw_text())
    if 0 <= idx < len(songs):
        return songs[idx]
    return None

def format_list() -> str:
    """格式化歌单文本"""
    songs = parse_song_list(_raw_text())
    if not songs:
        return "歌单为空"
    lines = []
    for i, s in enumerate(songs):
        src = "网易云" if s.get("type") == "wyy" else "B站"
        tid = s.get("title", "") or ""
        tag = f" [{tid}]" if tid else ""
        lines.append(f"  {i+1}. [{src}] {s['id']}{tag}")
    return "歌单:\n" + "\n".join(lines)

async def do_add(stype: str, sid: str, title: str = "", user="", token="") -> str:
    from main import ensure_repo, commit_push
    raw = _raw_text()
    songs = parse_song_list(raw)
    for s in songs:
        if s["type"] == stype and s["id"] == sid:
            src = "网易云" if stype == "wyy" else "B站"
            return f"{src} {sid} 已在列表"
    songs.append({"type": stype, "id": sid, "title": title})
    new_text = _inject_song_list(raw, songs)
    _write_text(new_text)
    await ensure_repo(user=user, token=token)
    await commit_push(["siteConfig.ts"], "chore: update playlist", user=user, token=token)
    src = "网易云" if stype == "wyy" else "B站"
    return f"已添加{src} [{sid}]"

async def do_remove(stype: str, sid_or_idx: str, user="", token="") -> str:
    from main import ensure_repo, commit_push
    raw = _raw_text()
    songs = parse_song_list(raw)
    # 按序号
    try:
        idx = int(sid_or_idx) - 1
        if 0 <= idx < len(songs):
            removed = songs.pop(idx)
            new_text = _inject_song_list(raw, songs)
            _write_text(new_text)
            await ensure_repo(user=user, token=token)
            await commit_push(["siteConfig.ts"], "chore: update playlist", user=user, token=token)
            src = "网易云" if removed["type"] == "wyy" else "B站"
            return f"已删除 {src} [{removed['id']}]"
    except ValueError:
        pass
    # 按 ID
    for i, s in list(enumerate(songs)):
        if s["id"] == sid_or_idx:
            removed = songs.pop(i)
            new_text = _inject_song_list(raw, songs)
            _write_text(new_text)
            await ensure_repo(user=user, token=token)
            await commit_push(["siteConfig.ts"], "chore: update playlist", user=user, token=token)
            src = "网易云" if removed["type"] == "wyy" else "B站"
            return f"已删除 {src} [{removed['id']}]"
    return f"未找到 {sid_or_idx}"

async def do_swap(idx1: int, idx2: int, user="", token="") -> str:
    from main import ensure_repo, commit_push
    raw = _raw_text()
    songs = parse_song_list(raw)
    if not (0 <= idx1 < len(songs) and 0 <= idx2 < len(songs)):
        return "序号超出范围"
    songs[idx1], songs[idx2] = songs[idx2], songs[idx1]
    new_text = _inject_song_list(raw, songs)
    _write_text(new_text)
    await ensure_repo(user=user, token=token)
    await commit_push(["siteConfig.ts"], "chore: update playlist", user=user, token=token)
    return f"已交换第 {idx1+1} 位和第 {idx2+1} 位"

async def do_title(idx: int, title: str, user="", token="") -> str:
    from main import ensure_repo, commit_push
    raw = _raw_text()
    songs = parse_song_list(raw)
    if not (0 <= idx < len(songs)):
        return "序号超出范围"
    songs[idx]["title"] = title
    new_text = _inject_song_list(raw, songs)
    _write_text(new_text)
    await ensure_repo(user=user, token=token)
    await commit_push(["siteConfig.ts"], "chore: update playlist", user=user, token=token)
    src = "网易云" if songs[idx]["type"] == "wyy" else "B站"
    return f"已设置第 {idx+1} 位 ({src} {songs[idx]['id']}) 标题为「{title}」"

# ========== 内部 ==========

def _inject_song_list(raw: str, songs: list) -> str:
    """在 siteConfig.ts 中替换或插入 songList"""
    new_block = make_song_list_text(songs)
    if "songList:" in raw:
        return re.sub(r"\s*songList:\s*\[[\s\S]*?\],", "\n" + new_block, raw)
    # 在 cloudMusicIds 后插入
    pos = raw.rfind("cloudMusicIds:")
    if pos >= 0:
        end = raw.find("\n", pos)
        return raw[:end+1] + "\n" + new_block + raw[end+1:]
    # 在最前面插入
    pos = raw.find("export const siteConfig = {")
    if pos >= 0:
        end = raw.find("{", pos) + 1
        return raw[:end] + "\n" + new_block + raw[end:]
    return raw
