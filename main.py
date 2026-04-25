"""
QRQLL Mobile — KivyMD 主应用入口
Material Design 3 底部导航栏，3 个 Tab
"""

import os
import sys
import json
from threading import Thread
from datetime import datetime

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.utils import platform
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
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.gridlayout import MDGridLayout

from server import (
    app as flask_app,
    HOMEWORK_DATA,
    RESOURCES_DIR,
    ENABLE_CLOSE_HW,
    ENABLE_LOGGING,
    start_server,
    is_server_running,
    get_host_ip,
    get_resources_dir,
)


class QRQLLMobileApp(MDApp):
    """QRQLL Mobile 主应用"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_started = False
        self.resources_list = []
        self.hw_list = []
        self.dialog = None

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.material_style = "M3"

        kv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "kv", "qrqll.kv"
        )
        if os.path.exists(kv_path):
            Builder.load_file(kv_path)

        return self._build_main_layout()

    def _build_main_layout(self):
        """构建主界面"""
        bg = self.theme_cls.bg_normal
        layout = MDBoxLayout(orientation="vertical", md_bg_color=bg)

        # 顶部工具栏
        toolbar = MDTopAppBar(
            title="QRQLL Mobile",
            md_bg_color=self.theme_cls.primary_color,
            specific_text_color="#FFFFFF",
            left_action_items=[["menu", lambda x: None]],
        )
        layout.add_widget(toolbar)

        # 底部导航
        nav = MDBottomNavigation(panel_color=bg)

        # ---- Tab 1: 资源文件 ----
        tab_res = MDBottomNavigationItem(
            name="resources",
            text="资源文件",
            icon="folder-outline",
        )
        self.resources_content = self._build_resources_tab()
        tab_res.add_widget(self.resources_content)
        nav.add_widget(tab_res)

        # ---- Tab 2: 上网配置 ----
        tab_hw = MDBottomNavigationItem(
            name="homework",
            text="上网配置",
            icon="link-variant",
        )
        self.hw_content = self._build_homework_tab()
        tab_hw.add_widget(self.hw_content)
        nav.add_widget(tab_hw)

        # ---- Tab 3: 设置 ----
        tab_set = MDBottomNavigationItem(
            name="settings",
            text="设置",
            icon="cog-outline",
        )
        self.settings_content = self._build_settings_tab()
        tab_set.add_widget(self.settings_content)
        nav.add_widget(tab_set)

        layout.add_widget(nav)
        return layout

    # ================================================================
    # Tab 1: 资源文件
    # ================================================================

    def _build_resources_tab(self):
        """构建资源文件 Tab 布局"""
        box = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        btn_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )
        btn_row.add_widget(MDRaisedButton(
            text="添加文件",
            icon="file-plus",
            on_release=self.on_add_resource,
        ))
        btn_row.add_widget(MDRaisedButton(
            text="刷新列表",
            icon="refresh",
            on_release=self.on_refresh_resources,
        ))
        box.add_widget(btn_row)

        scroll = MDScrollView()
        self.resources_list_widget = MDList()
        scroll.add_widget(self.resources_list_widget)
        box.add_widget(scroll)

        Clock.schedule_once(lambda dt: self.refresh_resources_list(), 0.5)

        return box

    def on_add_resource(self, instance):
        """添加资源文件"""
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            fpath = filedialog.askopenfilename(
                title="选择资源文件"
            )
            root.destroy()
            if fpath:
                import shutil
                dest = os.path.join(get_resources_dir(), os.path.basename(fpath))
                shutil.copy2(fpath, dest)
                self.refresh_resources_list()
                Snackbar(text=f"已添加: {os.path.basename(fpath)}", duration=2).open()
        except Exception as e:
            Snackbar(text=f"添加失败: {e}", duration=3).open()

    def on_refresh_resources(self, instance):
        """刷新资源列表"""
        self.refresh_resources_list()
        Snackbar(text="已刷新", duration=1).open()

    def refresh_resources_list(self):
        """刷新资源文件列表显示"""
        self.resources_list_widget.clear_widgets()
        res_dir = get_resources_dir()

        try:
            files = sorted(os.listdir(res_dir))
        except Exception:
            files = []

        if not files:
            self.resources_list_widget.add_widget(MDLabel(
                text="没有资源文件\n点击「添加文件」上传",
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(80),
            ))
            return

        for fname in files:
            fpath = os.path.join(res_dir, fname)
            size = os.path.getsize(fpath) if os.path.isfile(fpath) else 0
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            item = TwoLineIconListItem(
                text=fname,
                secondary_text=size_str,
                on_release=lambda x, fn=fname: self.on_delete_resource(fn),
            )
            item.add_widget(IconLeftWidget(icon="file-outline"))
            self.resources_list_widget.add_widget(item)

    def on_delete_resource(self, fname):
        """删除资源文件"""
        fpath = os.path.join(get_resources_dir(), fname)
        try:
            os.remove(fpath)
            self.refresh_resources_list()
            Snackbar(text=f"已删除: {fname}", duration=2).open()
        except Exception as e:
            Snackbar(text=f"删除失败: {e}", duration=3).open()

    # ================================================================
    # Tab 2: 上网配置
    # ================================================================

    def _build_homework_tab(self):
        """构建上网配置 Tab 布局"""
        box = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        btn_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )
        btn_row.add_widget(MDRaisedButton(
            text="添加上网",
            icon="plus",
            on_release=self.on_add_homework,
        ))
        btn_row.add_widget(MDRaisedButton(
            text="导出 JSON",
            icon="file-export",
            on_release=self.on_export_homework,
        ))
        btn_row.add_widget(MDRaisedButton(
            text="导入 JSON",
            icon="file-import",
            on_release=self.on_import_homework,
        ))
        box.add_widget(btn_row)

        scroll = MDScrollView()
        self.hw_list_widget = MDList()
        scroll.add_widget(self.hw_list_widget)
        box.add_widget(scroll)

        Clock.schedule_once(lambda dt: self.refresh_hw_list(), 0.5)

        return box

    def on_add_homework(self, instance):
        """添加上网配置"""
        self.show_hw_editor(None)

    def on_export_homework(self, instance):
        """导出作业配置为 JSON"""
        try:
            from kivy.utils import platform
            if platform == "win":
                import tkinter.filedialog as fd
                from tkinter import Tk
                root = Tk()
                root.withdraw()
                fpath = fd.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")],
                    initialfile="homework_config.json"
                )
                root.destroy()
                if fpath:
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(HOMEWORK_DATA, f, ensure_ascii=False, indent=2)
                    Snackbar(text=f"已导出: {os.path.basename(fpath)}", duration=3).open()
            else:
                Snackbar(text="导出功能仅在桌面端可用", duration=2).open()
        except Exception as e:
            Snackbar(text=f"导出失败: {e}", duration=3).open()

    def on_import_homework(self, instance):
        """导入作业配置 JSON"""
        try:
            if platform == "win":
                import tkinter.filedialog as fd
                from tkinter import Tk
                root = Tk()
                root.withdraw()
                fpath = fd.askopenfilename(
                    filetypes=[("JSON files", "*.json")]
                )
                root.destroy()
                if fpath:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    HOMEWORK_DATA.clear()
                    HOMEWORK_DATA.extend(data)
                    self.refresh_hw_list()
                    Snackbar(text=f"已导入 {len(data)} 项", duration=3).open()
            else:
                Snackbar(text="导入功能仅在桌面端可用", duration=2).open()
        except Exception as e:
            Snackbar(text=f"导入失败: {e}", duration=3).open()

    def refresh_hw_list(self):
        """刷新上网配置列表"""
        self.hw_list_widget.clear_widgets()
        if not HOMEWORK_DATA:
            self.hw_list_widget.add_widget(MDLabel(
                text="没有上网配置\n点击「添加上网」新建",
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(80),
            ))
            return

        for idx, hw in enumerate(HOMEWORK_DATA):
            ori_icon = "rotate-3d" if hw.get("orientation") == "landscape" else "cellphone"
            ori_text = "横屏" if hw.get("orientation") == "landscape" else "竖屏"
            item = TwoLineIconListItem(
                text=hw.get("name", "未命名"),
                secondary_text=f"{hw.get('url', '')} | {ori_text} ×{hw.get('scale', 1.0)}",
                on_release=lambda x, i=idx: self.on_edit_homework(i),
            )
            item.add_widget(IconLeftWidget(icon=ori_icon))
            self.hw_list_widget.add_widget(item)

    def on_edit_homework(self, idx: int):
        """编辑上网配置"""
        hw = HOMEWORK_DATA[idx]
        self.show_hw_editor(idx, hw)

    # ================================================================
    # 上网配置编辑弹窗
    # ================================================================

    def show_hw_editor(self, idx, hw=None):
        """显示编辑/添加上网配置的弹窗"""
        is_new = idx is None
        hw = hw or {"name": "", "url": "", "scale": 0.5, "orientation": "landscape"}

        if self.dialog:
            self.dialog.dismiss()

        name_field = MDTextField(
            text=hw["name"],
            hint_text="名称",
            helper_text="例: 百度搜索（横屏版）",
            helper_text_mode="on_focus",
        )
        url_field = MDTextField(
            text=hw["url"],
            hint_text="URL",
            helper_text="例: https://baidu.com",
            helper_text_mode="on_focus",
        )
        scale_field = MDTextField(
            text=str(hw.get("scale", 0.5)),
            hint_text="缩放 (0.1~1.0)",
            helper_text="例: 0.5",
            helper_text_mode="on_focus",
        )

        ori_layout = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(48),
        )
        ori_land_btn = MDRaisedButton(
            text="横屏",
            on_release=lambda x: self._set_orientation("landscape"),
        )
        ori_port_btn = MDRaisedButton(
            text="竖屏",
            on_release=lambda x: self._set_orientation("portrait"),
        )
        if hw.get("orientation") == "portrait":
            ori_port_btn.md_bg_color = self.theme_cls.primary_color
        else:
            ori_land_btn.md_bg_color = self.theme_cls.primary_color
        ori_layout.add_widget(ori_land_btn)
        ori_layout.add_widget(ori_port_btn)

        self._current_orientation = hw.get("orientation", "landscape")

        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(320),
        )
        content.add_widget(name_field)
        content.add_widget(url_field)
        content.add_widget(scale_field)
        content.add_widget(ori_layout)

        self.dialog = MDDialog(
            title="编辑上网配置" if not is_new else "添加上网配置",
            type="custom",
            content=content,
            buttons=[
                MDFlatButton(
                    text="删除" if not is_new else "取消",
                    on_release=lambda x: self._hw_delete(idx) if not is_new else self.dialog.dismiss(),
                ),
                MDFlatButton(
                    text="保存",
                    on_release=lambda x: self._hw_save(
                        idx, is_new,
                        name_field.text.strip(),
                        url_field.text.strip(),
                        scale_field.text.strip(),
                    ),
                ),
            ],
        )
        self.dialog.open()

    def _set_orientation(self, ori):
        self._current_orientation = ori

    def _hw_save(self, idx, is_new, name, url, scale_str):
        """保存上网配置"""
        if not name or not url:
            Snackbar(text="名称和 URL 不能为空", duration=2).open()
            return
        try:
            scale = float(scale_str)
            if scale <= 0:
                scale = 0.5
        except ValueError:
            scale = 0.5

        hw_entry = {
            "id": f"hw_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "lessonName": name,
            "url": url,
            "scale": scale,
            "orientation": self._current_orientation,
        }

        if is_new:
            HOMEWORK_DATA.append(hw_entry)
        else:
            hw_entry["id"] = HOMEWORK_DATA[idx]["id"]
            HOMEWORK_DATA[idx] = hw_entry

        if self.dialog:
            self.dialog.dismiss()
        self.refresh_hw_list()
        Snackbar(text="已保存", duration=1).open()

    def _hw_delete(self, idx):
        """删除上网配置"""
        if 0 <= idx < len(HOMEWORK_DATA):
            name = HOMEWORK_DATA[idx]["name"]
            del HOMEWORK_DATA[idx]
            if self.dialog:
                self.dialog.dismiss()
            self.refresh_hw_list()
            Snackbar(text=f"已删除: {name}", duration=2).open()

    # ================================================================
    # Tab 3: 设置
    # ================================================================

    def _build_settings_tab(self):
        """构建设置 Tab"""
        box = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
        )

        card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(160),
        )
        card.add_widget(MDLabel(
            text="服务器状态",
            font_style="H6",
            bold=True,
        ))

        self.status_label = MDLabel(
            text="未启动",
            theme_text_color="Secondary",
            halign="center",
            font_style="H5",
        )
        card.add_widget(self.status_label)
        box.add_widget(card)

        self.ip_card = MDCard(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(100),
        )
        self.ip_card.add_widget(MDLabel(text="IP 地址", font_style="H6"))
        self.ip_label = MDLabel(
            text="获取中...",
            font_style="H5",
            theme_text_color="Primary",
            halign="center",
        )
        self.ip_card.add_widget(self.ip_label)
        box.add_widget(self.ip_card)

        btn_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(16),
        )
        self.start_btn = MDRaisedButton(
            text="启动服务器",
            icon="play",
            on_release=self.on_start_server,
        )
        btn_row.add_widget(self.start_btn)
        box.add_widget(btn_row)

        # --- 开关设置 ---
        hw_switch_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )
        hw_switch_row.add_widget(MDLabel(
            text="关闭 HW 模式",
            size_hint_x=0.7,
        ))
        self.hw_switch = MDSwitch(
            active=ENABLE_CLOSE_HW,
            size_hint_x=0.3,
        )
        self.hw_switch.bind(active=self._on_hw_switch)
        hw_switch_row.add_widget(self.hw_switch)
        box.add_widget(hw_switch_row)

        log_switch_row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )
        log_switch_row.add_widget(MDLabel(
            text="日志记录",
            size_hint_x=0.7,
        ))
        self.log_switch = MDSwitch(
            active=ENABLE_LOGGING,
            size_hint_x=0.3,
        )
        self.log_switch.bind(active=self._on_log_switch)
        log_switch_row.add_widget(self.log_switch)
        box.add_widget(log_switch_row)

        about_label = MDLabel(
            text="QRQLL Mobile v1.0\n基于 QRQLL V2.3 移植\n使用 KivyMD 构建",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(80),
        )
        box.add_widget(about_label)
        box.add_widget(MDBoxLayout())
        Clock.schedule_once(lambda dt: self.refresh_settings(), 0.5)
        return box

    def refresh_settings(self):
        """刷新设置页面的状态"""
        running = is_server_running()
        ip = get_host_ip()

        if running:
            self.status_label.text = "▶ 运行中"
            self.status_label.theme_text_color = "Custom"
            self.status_label.text_color = (0.0, 0.6, 0.0, 1.0)
            self.start_btn.text = "重新启动"
        else:
            self.status_label.text = "⏹ 已停止"
            self.status_label.theme_text_color = "Custom"
            self.status_label.text_color = (0.8, 0.0, 0.0, 1.0)
            self.start_btn.text = "启动服务器"

        self.ip_label.text = f"{ip}:2417"

    def on_start_server(self, instance):
        ok = start_server()
        if ok:
            self.server_started = True
            Snackbar(text="服务器已启动 → 0.0.0.0:2417", duration=3).open()
        else:
            Snackbar(text="服务器已在运行", duration=2).open()
        self.refresh_settings()

    def _on_hw_switch(self, instance, value):
        global ENABLE_CLOSE_HW
        ENABLE_CLOSE_HW = value

    def _on_log_switch(self, instance, value):
        global ENABLE_LOGGING
        ENABLE_LOGGING = value

    # ================================================================
    # 应用生命周期
    # ================================================================

    def on_start(self):
        Thread(target=lambda: start_server(), daemon=True).start()
        Snackbar(text="正在启动服务器...", duration=2).open()
        Clock.schedule_interval(lambda dt: self.refresh_settings(), 3.0)

    def on_stop(self):
        pass


if __name__ == "__main__":
    QRQLLMobileApp().run()
