import sys
import os
import asyncio
import uiautomation as auto
import time
from . import save
from .save import save_txt
import re

from function.config import MIN_LENGTH, MAX_SAVED_SENTENCES

last_full_text = ""

def lc_detect() -> bool:
    try:
        auto.SetGlobalSearchTimeout(0.5)
        desktop = auto.GetRootControl()
        captions_window = desktop.Control(
            searchDepth=1,
            ClassName="LiveCaptionsDesktopWindow",
            timeout=0.2
        )
        if captions_window.Exists(0):
            print("Live Captions Found")
            return True
        else:
            print("Live Captions Not Found")
            return False
    except Exception as e:
        print(f"Live Captions Not Found: {str(e)[:50]}...")
        return False

def get_prefix(text: str, n_words: int = 10) -> str:
    words = text.split()
    if len(words) >= n_words:
        return ' '.join(words[:n_words])
    else:
        return text[:n_words] if len(text) >= n_words else text

def format_text_with_newlines(text: str) -> str:
    """
    在句号、问号、感叹号等句子结束符后添加换行符，
    """
    # 匹配中英文句号、问号、感叹号（包括中文全角），其后可跟空格
    pattern = r'([。！？.!?])(?![ \t]*\n)'  # 标点后不紧跟换行（允许空格）
    return re.sub(pattern, r'\1\n', text)

async def hook(filename, exit_event):
    global last_full_text

    cached_text = None
    cached_prefix = None

    try:
        if not lc_detect():
            return False

        desktop = auto.GetRootControl()
        captions_window = desktop.Control(
            searchDepth=1,
            ClassName="LiveCaptionsDesktopWindow"
        )
        await asyncio.sleep(1)
        captions_scrollviewer = captions_window.Control(
            searchDepth=5,
            AutomationId="CaptionsScrollViewer",
            ClassName="ScrollViewer"
        )

        print("Start capture with prefix‑based stability detection...")
        print("Formatting: newline after sentence-ending punctuation.")

        while not exit_event.is_set():
            current_text = captions_scrollviewer.Name.strip()
            if not current_text:
                await asyncio.sleep(0.5)
                continue

            last_full_text = current_text

            if len(current_text) <= 15:
                await asyncio.sleep(0.25)
                continue

            current_prefix = get_prefix(current_text, 10)

            if cached_prefix is None:
                cached_prefix = current_prefix
                cached_text = current_text
            else:
                if current_prefix == cached_prefix:
                    cached_text = current_text
                else:
                    if cached_text is not None:
                        # 保存前格式化：在句号、问号、感叹号后加换行
                        formatted = format_text_with_newlines(cached_text)
                        print(f"[SAVE] {formatted[:50]}...")
                        await save_txt(filename, (time.time(), formatted))
                    cached_prefix = current_prefix
                    cached_text = current_text

            await asyncio.sleep(0.25)

    except Exception as e:
        print(f"Exceptions Caught: {e}")
        return False

    finally:
        if cached_text is not None:
            formatted = format_text_with_newlines(cached_text)
            print(f"[SAVE ON EXIT] {formatted[:50]}...")
            await save_txt(filename, (time.time(), formatted))

        print("[EXIT] Done!")
