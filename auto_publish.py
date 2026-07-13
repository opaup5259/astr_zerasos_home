"""
Auto-publish module — LLM 驱动的说说自动发布 + 定时调度
独立模块，main.py 仅为入口
"""
import asyncio
import datetime
import logging
import random
import re
from typing import Optional, Tuple

logger = logging.getLogger("astr_zerasos_home.auto_publish")

# ========== 简单 cron 匹配器（5字段：分 时 日 月 周）==========
def _match_cron(expr: str, dt: datetime.datetime) -> bool:
    if not expr or expr.strip() == "" or expr.strip().startswith("#"):
        return False
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    fields = [dt.minute, dt.hour, dt.day, dt.month, dt.weekday()]
    for part, val in zip(parts, fields):
        if not _match_field(part.strip(), val):
            return False
    return True

def _match_field(field: str, val: int) -> bool:
    if field == "*":
        return True
    # 处理逗号分隔
    if "," in field:
        return any(_match_single(p.strip(), val) for p in field.split(","))
    return _match_single(field, val)

def _match_single(field: str, val: int) -> bool:
    # 步进: */5, 1-10/2
    if "/" in field:
        base, step = field.split("/", 1)
        step = int(step)
        if base == "*":
            return val % step == 0
        if "-" in base:
            lo, hi = map(int, base.split("-"))
            return lo <= val <= hi and (val - lo) % step == 0
        return val >= int(base) and (val - int(base)) % step == 0
    # 范围: 1-5
    if "-" in field:
        lo, hi = map(int, field.split("-"))
        return lo <= val <= hi
    # 精确
    return int(field) == val


class AutoPublishService:
    """自动发布说说服务 — LLM 生成内容 + 定时调度"""

    DEFAULT_PROMPT = (
        "你是一个生活博主，正在运营个人博客。"
        "请根据当前日期和场景，写一条简短的「说说」（类似QQ空间说说/朋友圈/微博）。\n\n"
        "要求：\n"
        "1. 真实自然，有生活气息，带个人特色\n"
        "2. 字数50~200字，不要太正式\n"
        "3. 可以是有趣的观察、生活中的小事、感悟、吐槽等\n\n"
        "回复格式（严格遵循）：\n"
        "第一行：标题（一句话概括，不超过20字）\n"
        "空一行\n"
        "第三行起：正文内容"
    )

    def __init__(self, context, config: dict = None):
        self.context = context
        self.config = config or {}
        self._task: Optional[asyncio.Task] = None
        self._enabled = False
        self._cron = "30 8 * * *"
        self._prompt = self.DEFAULT_PROMPT
        self._user = ""
        self._token = ""
        self._load_config()

    def _load_config(self):
        self._enabled = bool(self.config.get("auto_publish_enabled", False))
        self._cron = str(self.config.get("auto_publish_cron", "30 8 * * *")).strip()
        prompt = str(self.config.get("auto_publish_llm_prompt", "")).strip()
        self._prompt = prompt or self.DEFAULT_PROMPT

    def on_config_update(self, config: dict):
        self.config = config or {}
        self._load_config()

    def set_credentials(self, user: str, token: str):
        """设置 GitHub 凭据"""
        self._user = user or ""
        self._token = token or ""

    # ========== LLM 生成 ==========

    def _get_date_context(self) -> str:
        now = datetime.datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        wd = weekdays[now.weekday()]
        season = "春" if 3 <= now.month <= 5 else "夏" if 6 <= now.month <= 8 else "秋" if 9 <= now.month <= 11 else "冬"
        return (
            f"当前日期：{now.year}年{now.month}月{now.day}日 {wd}\n"
            f"季节：{season}天\n"
            f"时间：{now.hour}:{now.minute:02d}"
        )

    async def _call_llm(self, prompt: str, system_prompt: str = None, kb_query: str = "", debug_info: list = None) -> str:
        """调用 AstrBot LLM Provider 生成内容，可选知识库增强"""
        kb_used = False
        kb_count = 0
        try:
            provider = self.context.get_using_provider()
            if provider is None:
                logger.warning("未找到可用的 LLM Provider，使用备用生成")
                if debug_info is not None:
                    debug_info.append("⚠️ LLM Provider 不可用，使用备用模板")
                return self._fallback_generate()

            # 知识库检索
            kb_context = ""
            if kb_query and hasattr(self.context, 'kb_manager') and self.context.kb_manager:
                try:
                    kb_names = ["通用知识库", "助手知识库", "泽拉索斯"]
                    result = await self.context.kb_manager.retrieve(
                        query=kb_query,
                        kb_names=kb_names,
                        top_k_fusion=10,
                        top_m_final=5,
                    )
                    if result and result.get("chunks"):
                        texts = []
                        for c in result["chunks"]:
                            texts.append(f"[{c.get('kb_name','?')}] {c.get('content','')}")
                        if texts:
                            kb_context = "\n\n以下是与当前主题相关的知识库内容，请参考：\n" + "\n---\n".join(texts)
                            kb_used = True
                            kb_count = len(texts)
                            logger.info(f"知识库检索到 {kb_count} 条相关内容")
                except Exception as e:
                    logger.warning(f"知识库检索失败: {e}")
                    if debug_info is not None:
                        debug_info.append(f"⚠️ 知识库检索失败: {str(e)[:100]}")

            sp = system_prompt or "你是一个有个人特色的生活博主，擅长写简短有趣的「说说」。"
            if kb_context:
                sp += "\n\n你可以参考以下背景知识来生成内容，但不要直接复制。" + kb_context

            if debug_info is not None:
                if kb_used:
                    debug_info.append(f"📚 知识库已检索: 匹配到 {kb_count} 条相关内容")
                else:
                    debug_info.append("ℹ️ 知识库: 未检索到相关内容")

            result = await provider.text_chat(
                prompt=prompt,
                system_prompt=sp,
            )
            if hasattr(result, "completion_text") and result.completion_text:
                return result.completion_text
            if isinstance(result, str):
                return result
            return str(result)
        except ImportError:
            logger.warning("AstrBot LLM API 不可用，使用备用生成")
            if debug_info is not None:
                debug_info.append("⚠️ LLM API 不可用，使用备用模板")
            return self._fallback_generate()
        except Exception as e:
            logger.exception(f"LLM 调用失败: {e}")
            if debug_info is not None:
                debug_info.append(f"⚠️ LLM 调用失败: {str(e)[:100]}")
            return self._fallback_generate()

    def _fallback_generate(self) -> str:
        """LLM 不可用时的备用生成"""
        now = datetime.datetime.now()
        templates = [
            f"今日日常\n\n{now.month}月{now.day}日，普通的一天也要好好过。生活就是由这些平凡的日子组成的。",
            f"随手记\n\n{now.month}/{now.day} 打卡。日子平淡但充实，继续加油。",
            f"日常\n\n{now.month}月{now.day}日，{['周一摸鱼','周二努力','周三坚持','周四快到了','周五期待','周末愉快','周日休整'][now.weekday()]}。",
            f"碎碎念\n\n{now.year}年{now.month}月{now.day}日，今天天气{'不错' if random.random()>0.5 else '一般'}，心情{'还行' if random.random()>0.5 else '不错'}。",
            f"日常随想\n\n今天翻了一下博客，发现好久没写说说了。{now.month}月{now.day}日，记录一下此刻的心情。",
        ]
        return random.choice(templates)

    def parse_llm_output(self, text: str) -> Tuple[str, str]:
        """解析 LLM 输出为 (title, body)"""
        lines = text.strip().split("\n")
        title = "日常说说"
        body = text.strip()

        # 找第一个空行分隔
        split_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "":
                split_idx = i
                break

        if split_idx and split_idx > 0:
            title = lines[0].strip()
            body = "\n".join(lines[split_idx + 1:]).strip()
        else:
            # 没有空行分隔时，第一行作标题，其余作正文
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()

        # 清理标题
        title = re.sub(r'^["\'「『]+|["\'」』]+$', '', title).strip()
        # 限制长度
        if len(title) > 50:
            title = title[:50]
        # 确保有内容
        if not title:
            title = "日常说说"
        max_body = 1000
        if len(body) > max_body:
            body = body[:max_body]
        if not body:
            body = "(暂无内容)"
        return title, body

    # 不同类型的内容提示词模板
    PROMPTS = {
        "shuoshuo": (
            "你是一个生活博主，正在运营个人博客。\n"
            "请根据当前日期和场景，写一条简短的「说说」（类似QQ空间说说/朋友圈）。\n\n"
            "要求：\n"
            "1. 真实自然，有生活气息，带个人特色\n"
            "2. 字数20~100字，简洁有趣\n"
            "3. 可以是有趣的观察、生活中的小事、感悟、吐槽等\n\n"
            "回复格式（严格遵循）：\n"
            "第一行：标题（一句话概括，不超过20字）\n"
            "空一行\n"
            "第三行起：正文内容"
        ),
        "zatan": (
            "你是一个生活博主，正在运营个人博客。\n"
            "请根据当前日期和场景，写一段「杂谈」内容（类似博客随笔/聊天讨论）。\n\n"
            "要求：\n"
            "1. 自然随意，像和朋友聊天一样\n"
            "2. 字数100~400字，可以深入一些\n"
            "3. 可以聊聊最近的想法、见闻、读书/观影感受、技术感悟等\n\n"
            "回复格式（严格遵循）：\n"
            "第一行：标题（一句话概括，不超过30字）\n"
            "空一行\n"
            "第三行起：正文内容"
        ),
        "blog": (
            "你是一个博主，正在撰写个人博客文章。\n"
            "请根据当前日期和场景，写一篇完整的「博客文章」。\n\n"
            "要求：\n"
            "1. 有清晰的主题和结构，可以带小标题\n"
            "2. 字数400~1200字，内容充实\n"
            "3. 可以是技术分享、生活感悟、深度讨论等\n"
            "4. 风格自然，不要太正式\n\n"
            "回复格式（严格遵循）：\n"
            "第一行：标题（不超过40字）\n"
            "空一行\n"
            "第三行起：正文内容（支持Markdown格式）"
        ),
    }

    SYSTEM_PROMPTS = {
        "shuoshuo": "你是一个热爱生活的年轻人，喜欢记录身边的小事。语气轻松、幽默、真实。",
        "zatan": "你是一个有思想的博主，喜欢和读者聊天分享。语气自然，像朋友间的交谈。",
        "blog": "你是一个技术博主，善于将自己的思考和经验写成有价值的文章。文字流畅，有深度。",
    }

    async def generate_chatter(self, content_type: str = "shuoshuo", debug_info: list = None) -> Tuple[str, str]:
        """生成一条内容（说说/杂谈/博客）"""
        from datetime import datetime
        date_ctx = self._get_date_context()
        prompt_template = self.PROMPTS.get(content_type, self.PROMPTS["shuoshuo"])
        system_prompt = self.SYSTEM_PROMPTS.get(content_type, self.SYSTEM_PROMPTS["shuoshuo"])
        prompt = f"{date_ctx}\n\n{prompt_template}"

        if debug_info is not None:
            debug_info.append(f"📅 日期上下文: {date_ctx}")

        # 天气查询 - 尝试获取天气信息
        weather_info = ""
        try:
            import urllib.request, json as _json
            w_req = urllib.request.urlopen("https://wttr.in/?format=%C|%t|%h|%w", timeout=5)
            w_raw = w_req.read().decode("utf-8").strip()
            w_parts = w_raw.split("|")
            if len(w_parts) >= 2:
                weather_info = f"\n当前天气：{w_parts[0]}，温度{w_parts[1]}"
        except:
            pass

        # 根据类型构建知识库查询关键词
        kb_query_map = {
            "shuoshuo": f"今天{weather_info} 日常 生活 心情 趣事",
            "zatan": f"最近的热门话题 日常 思考 感悟 生活 见闻",
            "blog": "技术 分享 教程 经验 思考 观点",
        }
        kb_query = kb_query_map.get(content_type, "")
        # 将天气信息拼进 prompt
        if weather_info:
            prompt += f"\n\n{weather_info}"

        text = await self._call_llm(prompt, system_prompt=system_prompt, kb_query=kb_query, debug_info=debug_info)
        title, body = self.parse_llm_output(text)
        type_label = {"shuoshuo": "说说", "zatan": "杂谈", "blog": "博客文章"}
        logger.info(f"LLM 生成{type_label.get(content_type, '内容')}: [{title}] ({len(body)}字)")
        if debug_info is not None:
            debug_info.append(f"✍️ 已生成: [{title}] ({len(body)}字)")
        return title, body

    # ========== 发布逻辑 ==========

    async def _publish_to_blog(self, title: str, body: str, content_type: str = "shuoshuo") -> str:
        """调用 main.py 的函数发布内容到博客"""
        from .main import new_chatter, new_blog_post
        if content_type == "blog":
            return await new_blog_post(title, body, user=self._user, token=self._token)
        return await new_chatter(title, body, user=self._user, token=self._token, chatter_type=content_type)

    async def force_run(self, content_type: str = "shuoshuo") -> str:
        """强制运行一次自动发布（用于管理员指令和定时任务）"""
        type_label = {"shuoshuo": "说说", "zatan": "杂谈", "blog": "博客文章"}
        label = type_label.get(content_type, "内容")
        debug_info = []
        try:
            # 标记使用的 prompt/persona
            prompt_template = self.PROMPTS.get(content_type, self.PROMPTS["shuoshuo"])
            system_prompt = self.SYSTEM_PROMPTS.get(content_type, self.SYSTEM_PROMPTS["shuoshuo"])
            debug_info.append(f"🤖 角色/人格: {system_prompt[:60]}…" if len(system_prompt) > 60 else f"🤖 角色/人格: {system_prompt}")
            debug_info.append(f"📝 提示词: {prompt_template[:100]}…" if len(prompt_template) > 100 else f"📝 提示词: {prompt_template}")
            
            # 标记知识库查询关键词
            kb_query_map = {
                "shuoshuo": "今天 日常 生活 心情 趣事",
                "zatan": "最近的热门话题 日常 思考 感悟 生活 见闻",
                "blog": "技术 分享 教程 经验 思考 观点",
            }
            kb_q = kb_query_map.get(content_type, "")
            debug_info.append(f"🔍 知识库检索关键词: {kb_q}")
            
            title, body = await self.generate_chatter(content_type=content_type, debug_info=debug_info)
            result = await self._publish_to_blog(title, body, content_type=content_type)
            log_msg = f"自动{label}发布成功: [{title}]"
            logger.info(log_msg)
            return (
                f"✅ 自动{label}已发布\n\n"
                f"📌 {title}\n\n"
                f"{body[:300]}{'…' if len(body) > 300 else ''}\n\n"
                f"─── 调试信息 ───\n"
                + "\n".join(debug_info) + "\n"
                f"─── 发布结果 ───\n{result}"
            )
        except Exception as e:
            logger.exception(f"自动发布失败 (type={content_type})")
            debug_info.append(f"❌ 错误: {str(e)[:100]}")
            return f"❌ 自动{label}发布失败: {str(e)[:200]}"

    # ========== 定时调度 ==========

    def start_scheduler(self, user: str = "", token: str = ""):
        """启动后台定时调度器"""
        self._user = user or self._user
        self._token = token or self._token
        # 取消已有任务
        self.stop_scheduler()
        if not self._enabled or not self._cron:
            logger.info("自动发布调度器未启动（已禁用或 cron 为空）")
            return
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"🚀 自动发布调度器已启动 (cron: {self._cron})")

    def stop_scheduler(self):
        """停止调度器"""
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            logger.info("自动发布调度器已停止")

    async def _scheduler_loop(self):
        """后台循环，每分钟检查 cron 表达式"""
        while True:
            try:
                now = datetime.datetime.now()
                if _match_cron(self._cron, now):
                    logger.info(f"⏰ 定时触发自动发布 (cron: {self._cron})")
                    result = await self.force_run()
                    logger.info(f"定时发布结果: {result[:100]}")
                    # 休眠避免同一分钟内重复触发
                    await asyncio.sleep(62)
                else:
                    await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("调度器被取消")
                break
            except Exception as e:
                logger.error(f"调度器循环错误: {e}")
                await asyncio.sleep(60)
