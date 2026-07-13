"""
GitHub 操作封装：克隆、拉取、提交、推送 Zerasos-Home 博客仓库
"""

import os, subprocess, tempfile, shutil, logging

logger = logging.getLogger("astr_zerasos_home")

REPO_URL = "git@github.com:opaup5259/Zerasos-Home.git"
REPO_BRANCH = "main"
WORK_DIR = os.path.join(tempfile.gettempdir(), "zerasos-home-repo")


def ensure_repo() -> str:
    """确保本地仓库存在，返回工作目录路径"""
    if os.path.isdir(os.path.join(WORK_DIR, ".git")):
        # 拉取最新
        _run_git(["pull", "origin", REPO_BRANCH], WORK_DIR)
    else:
        # 清理残留
        if os.path.isdir(WORK_DIR):
            shutil.rmtree(WORK_DIR, ignore_errors=True)
        os.makedirs(WORK_DIR, exist_ok=True)
        parent = os.path.dirname(WORK_DIR)
        _run_git(["clone", REPO_URL, WORK_DIR], parent)
    return WORK_DIR


def commit_and_push(files: list[str], message: str) -> str:
    """提交并推送指定文件，返回日志"""
    ensure_repo()
    log_lines = []

    for f in files:
        rel = os.path.relpath(f, WORK_DIR)
        _run_git(["add", rel], WORK_DIR)
        log_lines.append(f"  added: {rel}")

    _run_git(["commit", "-m", message], WORK_DIR)
    log_lines.append(f"  commit: {message}")

    result = _run_git(["push", "origin", REPO_BRANCH], WORK_DIR)
    log_lines.append(f"  push: {result.strip()}")
    return "\n".join(log_lines)


def read_file(rel_path: str) -> str:
    """读取仓库内文件"""
    path = os.path.join(WORK_DIR, rel_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write_file(rel_path: str, content: str):
    """写入仓库内文件"""
    path = os.path.join(WORK_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def delete_file(rel_path: str):
    """删除仓库内文件"""
    path = os.path.join(WORK_DIR, rel_path)
    if os.path.exists(path):
        os.remove(path)


def list_files(rel_dir: str) -> list[str]:
    """列出目录下所有文件名"""
    path = os.path.join(WORK_DIR, rel_dir)
    if os.path.isdir(path):
        return sorted(os.listdir(path))
    return []


def _run_git(args: list[str], cwd: str) -> str:
    """执行 git 命令"""
    cmd = ["git"] + args
    env = os.environ.copy()
    # 确保 SSH 能找到 key
    ssh_key = os.path.expanduser("~/.ssh/id_rsa")
    if os.path.exists(ssh_key):
        env.setdefault("GIT_SSH_COMMAND", "ssh -o StrictHostKeyChecking=no")
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败:\nstdout: {r.stdout}\nstderr: {r.stderr}")
    logger.debug(f"git {' '.join(args)} 成功: {r.stdout[:200]}")
    return r.stdout
