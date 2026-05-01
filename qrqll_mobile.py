"""
QRQLL Mobile — 单文件版
KivyMD 桌面/Android 客户端，Flask 服务端内嵌
"""

import os
import sys
import json
import time
from threading import Thread, Lock
from typing import Dict, Optional
from datetime import datetime
from socket import socket, AF_INET, SOCK_DGRAM

# ============================================================
# Kivy 配置 — 在 kivy 完全导入前配置字体和渲染
# ============================================================
from kivy.config import Config as _KivyConfig
_KivyConfig.set("graphics", "multisamples", "0")
_KivyConfig.set("graphics", "maxfps", "30")

# 查找中文字体并设为 kivy 全局默认字体
_LANG_FONT = None
_common_fonts = [
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/DroidSansFallback.ttf",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/NotoSansSC-Regular.ttf",
]
_local_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansSC-Regular.otf")
_font_path = _local_font if os.path.exists(_local_font) else next((f for f in _common_fonts if os.path.exists(f)), None)
if _font_path:
    from kivy.core.text import LabelBase as _LabelBase
    _LabelBase.register(name="LangFont", fn_regular=_font_path)
    _LANG_FONT = "LangFont"
    # 设为 Kivy 全局默认字体链 — 确保 MDTextField hint_text 等底层文本也使用中文字体
    _KivyConfig.set("kivy", "default_font", ["LangFont", "Roboto", "data/fonts/DejaVuSans.ttf"])

# ============================================================
# werkzeug 兼容性补丁
# ============================================================
import werkzeug.urls
if not hasattr(werkzeug.urls, "url_quote"):
    from urllib.parse import quote
    werkzeug.urls.url_quote = quote

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.utils import platform as kivy_platform
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.bottomnavigation import (
    MDBottomNavigation, MDBottomNavigationItem
)
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import (
    MDList, TwoLineIconListItem, IconLeftWidget
)
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.gridlayout import MDGridLayout

Window.softinput_mode = "below_target"

# ============================================================
# Flask 服务端
# ============================================================

HOMEWORK_DATA = [
    {"id": "1867975578577879042", "name": "百度搜索（横屏版）", "lessonName": "搜索", "url": "https://baidu.com", "scale": 0.5, "orientation": "landscape"},
    {"id": "1867975578577879043", "name": "百度搜索（竖屏版）", "lessonName": "搜索", "url": "https://baidu.com", "scale": 0.5, "orientation": "portrait"},
]
ENABLE_CLOSE_HW = False
ENABLE_LOGGING = False
ENABLE_LOG_HEADERS = False
LAST_SHUTDOWN_CLICK = 0
_server_thread: Optional[Thread] = None
_server_running = False
_server_lock = Lock()


def get_resources_dir() -> str:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(app_dir, "resources")
    os.makedirs(res_dir, exist_ok=True)
    return res_dir

RESOURCES_DIR = get_resources_dir()

from flask import Flask, jsonify, request, send_from_directory
from waitress import serve

app = Flask(__name__)


@app.after_request
def log_request(response):
    if ENABLE_LOGGING:
        now = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
        proto = request.environ.get("SERVER_PROTOCOL", "HTTP/1.1")
        print(f'{request.remote_addr} - - [{now}] "{request.method} {request.full_path} {proto}" {response.status_code} -')
        if ENABLE_LOG_HEADERS:
            print("-" * 40)
            for k, v in request.headers.items():
                print(f"{k}: {v}")
            print("-" * 40)
    return response


def ok(result=None, message=""):
    return jsonify({"status": 0, "message": message, "result": result if result is not None else {}})


def get_param(name: str, default: str = "") -> str:
    return request.args.get(name, default) if request.args.get(name) is not None else request.form.get(name, default)


def build_homework_list_dynamic(page_index: int, page_size: int):
    start = page_index * page_size
    end = start + page_size
    items = HOMEWORK_DATA[start:end]
    return ok({"total": len(HOMEWORK_DATA), "pageIndex": page_index, "pageSize": page_size, "results": items})


def build_homework_list_static():
    return ok({"results": HOMEWORK_DATA, "total": len(HOMEWORK_DATA)})


def close_homework(homework_id: str):
    old_len = len(HOMEWORK_DATA)
    HOMEWORK_DATA[:] = [hw for hw in HOMEWORK_DATA if hw.get("id") != homework_id]
    return ok(message="删除成功" if len(HOMEWORK_DATA) < old_len else "未找到该作业")


def close_homework_all():
    global ENABLE_CLOSE_HW
    if ENABLE_CLOSE_HW:
        HOMEWORK_DATA.clear()
        return ok(message="已关闭所有作业")
    return ok(message="close_homework 功能未启用")


def get_host_ip() -> str:
    """获取本机局域网 IP"""
    try:
        s = socket(AF_INET, SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ------------------------------------------------------------------
# API 路由
# ------------------------------------------------------------------

@app.route("/api/v1/close_hw/close", methods=["POST"])
def api_close_homework():
    data = request.json or {}
    if data.get("homeworkId"):
        return close_homework(data["homeworkId"])
    return close_homework_all()


@app.route("/api/v1/close_hw/list", methods=["GET"])
def api_homework_list():
    try:
        pi = int(request.args.get("pageIndex", 0))
        ps = int(request.args.get("pageSize", 0))
    except ValueError:
        pi = ps = 0
    if ps > 0:
        return build_homework_list_dynamic(pi, ps)
    return build_homework_list_static()


@app.route("/api/v1/sync/resource", methods=["POST"])
def api_resource_upload():
    if "resource" not in request.files:
        return ok(message="未上传文件")
    file = request.files["resource"]
    dest = os.path.join(get_resources_dir(), file.filename)
    file.save(dest)
    return ok(message=f"文件已保存: {file.filename}")


@app.route("/api/v1/sync/list", methods=["GET"])
def api_resource_list():
    try:
        files = os.listdir(get_resources_dir())
    except Exception:
        files = []
    items = []
    for f in files:
        fpath = os.path.join(get_resources_dir(), f)
        items.append({"name": f, "size": os.path.getsize(fpath) if os.path.isfile(fpath) else 0})
    return ok(items)


@app.route("/api/v1/sync/resource/<filename>", methods=["GET"])
def api_resource_download(filename: str):
    return send_from_directory(get_resources_dir(), filename, as_attachment=True)


@app.route("/api/v1/config/course/key/closeHW/", methods=["GET"])
def api_close_hw_push():
    pi = int(request.args.get("pageIndex", 0))
    ps = int(request.args.get("pageSize", 0))
    return build_homework_list_dynamic(pi, ps) if ps > 0 else build_homework_list_static()


@app.route("/api/v1/config/course/set", methods=["POST"])
def api_course_set():
    data = request.json or {}
    for item in data:
        HOMEWORK_DATA.append(item)
    return ok(HOMEWORK_DATA, message="配置已更新")


@app.route("/api/v1/sync/resource/batch", methods=["POST"])
def api_resource_batch_upload():
    for f in request.files.getlist("resource"):
        f.save(os.path.join(get_resources_dir(), f.filename))
    return ok(message="批量上传完成")


@app.route("/api/v1/shutdown", methods=["POST"])
def api_shutdown():
    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
    os._exit(0)
    return ok(message="服务器已关闭")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return ok(message="QRQLL Mobile API Server")


def _run_server():
    global _server_running
    _server_running = True
    serve(app, host="0.0.0.0", port=2417)
    _server_running = False


def start_server() -> bool:
    global _server_thread
    with _server_lock:
        if _server_running:
            return False
        _server_thread = Thread(target=_run_server, daemon=True)
        _server_thread.start()
        time.sleep(0.3)
        return True


def is_server_running() -> bool:
    return _server_running

# ============================================================
# 提示（Android 原生 Toast，PC 打印）
# ============================================================

def _toast(msg):
    try:
        if kivy_platform == "android":
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Toast = autoclass("android.widget.Toast")
            Toast.makeText(PythonActivity.mActivity, msg, Toast.LENGTH_SHORT).show()
        else:
            print(f"[提示] {msg}")
    except Exception:
        print(f"[提示] {msg}")


# ============================================================
# KivyMD App
# ============================================================

class QRQLLMobileApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_started = False
        self.hw_list = []
        self.dialog = None

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # 设置 Kivy 全局默认字体 + KivyMD 主题字体
        if _LANG_FONT:
            for k, v in self.theme_cls.font_styles.items():
                if isinstance(v, (list, tuple)) and len(v) >= 1 and k != "Icon":
                    try:
                        v[0] = _LANG_FONT
                    except Exception:
                        pass

        kv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kv", "qrqll.kv")
        if os.path.exists(kv_path):
            Builder.load_file(kv_path)

        return self._build_main_layout()

    def _build_main_layout(self):
        bg = self.theme_cls.bg_normal
        layout = MDBoxLayout(orientation="vertical", md_bg_color=bg)

        toolbar = MDTopAppBar(
            title="QRQLL Mobile",
            md_bg_color=self.theme_cls.primary_color,
            specific_text_color="#FFFFFF",
            left_action_items=[],
        )
        layout.add_widget(toolbar)

        nav = MDBottomNavigation(panel_color=bg)

        tab_res = MDBottomNavigationItem(name="resources", text="资源文件", icon="folder")
        self.resources_content = self._build_resources_tab()
        tab_res.add_widget(self.resources_content)
        nav.add_widget(tab_res)

        tab_hw = MDBottomNavigationItem(name="homework", text="上网配置", icon="web")
        self.hw_content = self._build_homework_tab()
        tab_hw.add_widget(self.hw_content)
        nav.add_widget(tab_hw)

        tab_set = MDBottomNavigationItem(name="settings", text="设置", icon="cog")
        self.settings_content = self._build_settings_tab()
        tab_set.add_widget(self.settings_content)
        nav.add_widget(tab_set)

        layout.add_widget(nav)
        return layout

    # ---------- Tab 1: 资源 ----------

    def _build_resources_tab(self):
        box = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        btn_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_row.add_widget(MDRaisedButton(text="添加文件", icon="file-plus", on_release=self.on_add_resource))
        btn_row.add_widget(MDRaisedButton(text="刷新列表", icon="refresh", on_release=self.on_refresh_resources))
        box.add_widget(btn_row)
        scroll = MDScrollView()
        self.resources_list_widget = MDList()
        scroll.add_widget(self.resources_list_widget)
        box.add_widget(scroll)
        Clock.schedule_once(lambda dt: self.refresh_resources_list(), 0.5)
        return box

    def on_add_resource(self, instance):
        try:
            if kivy_platform == "android":
                _toast("Android 上请通过电脑传输文件到 resources 目录")
                return
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            fpath = filedialog.askopenfilename(title="选择资源文件")
            root.destroy()
            if fpath:
                import shutil
                shutil.copy2(fpath, os.path.join(get_resources_dir(), os.path.basename(fpath)))
                self.refresh_resources_list()
                _toast(f"已添加: {os.path.basename(fpath)}")
        except Exception as e:
            _toast(f"添加失败: {e}")

    def on_refresh_resources(self, instance):
        self.refresh_resources_list()
        _toast("已刷新")

    def refresh_resources_list(self):
        self.resources_list_widget.clear_widgets()
        try:
            files = sorted(os.listdir(get_resources_dir()))
        except Exception:
            files = []
        if not files:
            self.resources_list_widget.add_widget(MDLabel(text="没有资源文件\n通过电脑传输文件到 resources 目录", halign="center", theme_text_color="Secondary", size_hint_y=None, height=dp(80)))
            return
        for fname in files:
            fpath = os.path.join(get_resources_dir(), fname)
            size = os.path.getsize(fpath) if os.path.isfile(fpath) else 0
            sz = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            item = TwoLineIconListItem(text=fname, secondary_text=sz, on_release=lambda x, fn=fname: self.on_delete_resource(fn))
            item.add_widget(IconLeftWidget(icon="file"))
            self.resources_list_widget.add_widget(item)

    def on_delete_resource(self, fname):
        try:
            os.remove(os.path.join(get_resources_dir(), fname))
            self.refresh_resources_list()
            _toast(f"已删除: {fname}")
        except Exception as e:
            _toast(f"删除失败: {e}")

    # ---------- Tab 2: 上网配置 ----------

    def _build_homework_tab(self):
        box = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        btn_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_row.add_widget(MDRaisedButton(text="添加上网", icon="plus", on_release=self.on_add_homework))
        btn_row.add_widget(MDRaisedButton(text="导出 JSON", icon="file-export", on_release=self.on_export_homework))
        btn_row.add_widget(MDRaisedButton(text="导入 JSON", icon="file-import", on_release=self.on_import_homework))
        box.add_widget(btn_row)
        scroll = MDScrollView()
        self.hw_list_widget = MDList()
        scroll.add_widget(self.hw_list_widget)
        box.add_widget(scroll)
        Clock.schedule_once(lambda dt: self.refresh_hw_list(), 0.5)
        return box

    def on_add_homework(self, instance):
        self.show_hw_editor(None)

    def on_export_homework(self, instance):
        try:
            if kivy_platform == "android":
                p = os.path.join(get_resources_dir(), "homework_config.json")
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(HOMEWORK_DATA, f, ensure_ascii=False, indent=2)
                _toast("已导出到 resources 目录")
                return
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="homework_config.json")
            root.destroy()
            if fp:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(HOMEWORK_DATA, f, ensure_ascii=False, indent=2)
                _toast("已导出")
        except Exception as e:
            _toast(f"导出失败: {e}")

    def on_import_homework(self, instance):
        try:
            if kivy_platform == "android":
                _toast("请通过电脑上传 JSON 到 resources 目录")
                return
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            fp = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
            root.destroy()
            if fp:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                HOMEWORK_DATA.clear()
                HOMEWORK_DATA.extend(data)
                self.refresh_hw_list()
                _toast(f"已导入 {len(data)} 项")
        except Exception as e:
            _toast(f"导入失败: {e}")

    def refresh_hw_list(self):
        self.hw_list_widget.clear_widgets()
        if not HOMEWORK_DATA:
            self.hw_list_widget.add_widget(MDLabel(text="没有上网配置\n点击「添加上网」新建", halign="center", theme_text_color="Secondary", size_hint_y=None, height=dp(80)))
            return
        for idx, hw in enumerate(HOMEWORK_DATA):
            ori = hw.get("orientation", "portrait")
            item = TwoLineIconListItem(
                text=hw.get("name", "未命名"),
                secondary_text=f"{hw.get('url','')} | {'横屏' if ori=='landscape' else '竖屏'} x{hw.get('scale',1.0)}",
                on_release=lambda x, i=idx: self.on_edit_homework(i),
            )
            item.add_widget(IconLeftWidget(icon="rotate-3d" if ori == "landscape" else "cellphone"))
            self.hw_list_widget.add_widget(item)

    def on_edit_homework(self, idx):
        self.show_hw_editor(idx, HOMEWORK_DATA[idx])

    def show_hw_editor(self, idx, hw=None):
        is_new = idx is None
        hw = hw or {"name": "", "url": "", "scale": 0.5, "orientation": "landscape"}
        if self.dialog:
            self.dialog.dismiss()
        nf = MDTextField(text=hw["name"], hint_text="名称", helper_text="例: 百度搜索（横屏版）", helper_text_mode="on_focus")
        uf = MDTextField(text=hw["url"], hint_text="URL", helper_text="例: https://baidu.com", helper_text_mode="on_focus")
        sf = MDTextField(text=str(hw.get("scale", 0.5)), hint_text="缩放 (0.1~1.0)", helper_text="例: 0.5", helper_text_mode="on_focus")
        ol = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48))
        lb = MDRaisedButton(text="横屏", on_release=lambda x: setattr(self, "_cur_ori", "landscape"))
        pb = MDRaisedButton(text="竖屏", on_release=lambda x: setattr(self, "_cur_ori", "portrait"))
        if hw.get("orientation") == "portrait":
            pb.md_bg_color = self.theme_cls.primary_color
        else:
            lb.md_bg_color = self.theme_cls.primary_color
        ol.add_widget(lb); ol.add_widget(pb)
        self._cur_ori = hw.get("orientation", "landscape")
        ct = MDBoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None, height=dp(320))
        ct.add_widget(nf); ct.add_widget(uf); ct.add_widget(sf); ct.add_widget(ol)
        self.dialog = MDDialog(
            title="编辑上网配置" if not is_new else "添加上网配置",
            type="custom", content_cls=ct,
            buttons=[
                MDFlatButton(text="删除" if not is_new else "取消", on_release=lambda x: self._hw_delete(idx) if not is_new else self.dialog.dismiss()),
                MDFlatButton(text="保存", on_release=lambda x: self._hw_save(idx, is_new, nf.text.strip(), uf.text.strip(), sf.text.strip())),
            ],
        )
        self.dialog.open()

    def _hw_save(self, idx, is_new, name, url, scale_str):
        if not name or not url:
            _toast("名称和 URL 不能为空")
            return
        try:
            scale = max(0.1, min(1.0, float(scale_str)))
        except ValueError:
            scale = 0.5
        entry = {"id": f"hw_{datetime.now().strftime('%Y%m%d%H%M%S')}", "name": name, "lessonName": name, "url": url, "scale": scale, "orientation": self._cur_ori}
        if is_new:
            HOMEWORK_DATA.append(entry)
        else:
            entry["id"] = HOMEWORK_DATA[idx]["id"]
            HOMEWORK_DATA[idx] = entry
        if self.dialog:
            self.dialog.dismiss()
        self.refresh_hw_list()
        _toast("已保存")

    def _hw_delete(self, idx):
        if 0 <= idx < len(HOMEWORK_DATA):
            name = HOMEWORK_DATA[idx]["name"]
            del HOMEWORK_DATA[idx]
            if self.dialog:
                self.dialog.dismiss()
            self.refresh_hw_list()
            _toast(f"已删除: {name}")

    # ---------- Tab 3: 设置 ----------

    def _build_settings_tab(self):
        box = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        card = MDCard(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, height=dp(160))
        card.add_widget(MDLabel(text="服务器状态", font_style="H6", bold=True))
        self.status_label = MDLabel(text="未启动", theme_text_color="Secondary", halign="center", font_style="H5")
        card.add_widget(self.status_label)
        box.add_widget(card)
        ic = MDCard(orientation="vertical", padding=dp(16), spacing=dp(4), size_hint_y=None, height=dp(100))
        ic.add_widget(MDLabel(text="IP 地址", font_style="H6"))
        self.ip_label = MDLabel(text="获取中...", font_style="H5", theme_text_color="Primary", halign="center")
        ic.add_widget(self.ip_label)
        box.add_widget(ic)
        br = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(16))
        self.start_btn = MDRaisedButton(text="启动服务器", icon="play", on_release=self.on_start_server)
        br.add_widget(self.start_btn)
        box.add_widget(br)
        hwr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        hwr.add_widget(MDLabel(text="关闭 HW 模式", size_hint_x=0.7))
        self.hw_switch = MDSwitch(active=ENABLE_CLOSE_HW, size_hint_x=0.3)
        self.hw_switch.bind(active=lambda i, v: globals().update(ENABLE_CLOSE_HW=v))
        hwr.add_widget(self.hw_switch)
        box.add_widget(hwr)
        lgr = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
        lgr.add_widget(MDLabel(text="日志记录", size_hint_x=0.7))
        self.log_switch = MDSwitch(active=ENABLE_LOGGING, size_hint_x=0.3)
        self.log_switch.bind(active=lambda i, v: globals().update(ENABLE_LOGGING=v))
        lgr.add_widget(self.log_switch)
        box.add_widget(lgr)
        box.add_widget(MDLabel(text="QRQLL Mobile v1.0\n基于 QRQLL V2.3 移植\n使用 KivyMD 构建", halign="center", theme_text_color="Secondary", size_hint_y=None, height=dp(80)))
        box.add_widget(MDBoxLayout())
        Clock.schedule_once(lambda dt: self.refresh_settings(), 0.5)
        return box

    def refresh_settings(self):
        running = is_server_running()
        ip = get_host_ip()
        if running:
            self.status_label.text = "运行中"
            self.status_label.theme_text_color = "Custom"
            self.status_label.text_color = (0, 0.6, 0, 1)
            self.start_btn.text = "重新启动"
        else:
            self.status_label.text = "已停止"
            self.status_label.theme_text_color = "Custom"
            self.status_label.text_color = (0.8, 0, 0, 1)
            self.start_btn.text = "启动服务器"
        self.ip_label.text = f"{ip}:2417"

    def on_start_server(self, instance):
        if start_server():
            self.server_started = True
            _toast("服务器已启动 → 0.0.0.0:2417")
        else:
            _toast("服务器已在运行")
        self.refresh_settings()

    def on_start(self):
        Clock.schedule_once(lambda dt: Thread(target=start_server, daemon=True).start(), 2.0)

    def on_stop(self):
        pass


if __name__ == "__main__":
    QRQLLMobileApp().run()
  
