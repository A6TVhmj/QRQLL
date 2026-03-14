import os
import sys
import time
from shutil import copy2
from threading import Thread
from datetime import datetime
from typing import Dict
from tkinter import filedialog, messagebox, StringVar
from socket import socket, AF_INET, SOCK_DGRAM
import ttkbootstrap as ttk
from flask import Flask, jsonify, request, send_from_directory
from ttkbootstrap.constants import *
from ttkbootstrap.utility import *
from PIL import Image
from PIL.ImageTk import PhotoImage
from waitress import serve

HOMEWORK_DATA = [
    {
        "id": "1867975578577879042",
        "name": "百度搜索",
        "lessonName": "数学",
        "url": "https://baidu.com",
        "scale": 0.5
    }
]
ENABLE_CLOSE_HW = False

app = Flask(__name__)

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()
RESOURCES_DIR = os.path.join(APP_DIR, "resources")
if not os.path.exists(RESOURCES_DIR):
    os.makedirs(RESOURCES_DIR)

def ok(result=None, message: str = ""):
    return jsonify({"status": 0, "message": message, "result": result if result is not None else {}})

def get_param(name: str, default: str = "") -> str:
    if request.args.get(name) is not None:
        return request.args.get(name, default)
    return request.form.get(name, default)

def build_homework_list_dynamic(page_index: int, page_size: int) -> Dict:
    data_list = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_data = list(HOMEWORK_DATA)
    if ENABLE_CLOSE_HW:
        source_data.insert(0, {"id": "SYS_CLOSE_001", "name": "🔴 关闭服务端", "lessonName": "系统", "url": f"http://{request.host}/api/shutdown", "scale": 1.0})
    
    start = (page_index - 1) * page_size
    end = start + page_size
    sliced_data = source_data[start:end]

    for hw in sliced_data:
        data_list.append({
            "publishTime": now, "homeworkId": hw["id"], "homeworkName": hw["name"],
            "lessonName": hw["lessonName"], "lessonId": "1001", "startTime": now,
            "endTime": None, "publishAnswerTime": "0", "submitStatus": 0, "redoQuestionNums": None
        })

    return {
        "pageIndex": page_index, "pageSize": page_size,
        "pageCount": (len(source_data) + page_size - 1) // page_size,
        "recordCount": len(source_data), "data": data_list
    }

def build_homework_detail_dynamic(homework_id: str) -> Dict:
    if homework_id == "SYS_CLOSE_001":
        target_hw = {"id": "SYS_CLOSE_001", "name": "🔴 关闭服务端", "url": f"http://{request.host}/api/shutdown", "scale": 1.0}
    else:
        target_hw = next((item for item in HOMEWORK_DATA if item["id"] == homework_id), None)
        if not target_hw:
            target_hw = HOMEWORK_DATA[0] if HOMEWORK_DATA else {}
            if not target_hw: return {}

    iframe_url = target_hw.get("url", "")
    hw_name = target_hw.get("name", "")
    scale = float(target_hw.get("scale", 0.5))
    if scale <= 0: scale = 0.5

    html_content = (
        f'<div style="width:100vw;height:100vh;overflow:hidden;position:relative;">'
        f'<iframe src="{iframe_url}" allow="fullscreen *; clipboard-read *; clipboard-write *" '
        f'sandbox="allow-same-origin allow-forms allow-scripts allow-popups allow-modals allow-top-navigation-by-user-activation allow-pointer-lock allow-downloads" '
        f'style="position:fixed;top:0;left:0;width:{100/scale:.2f}vw;height:{100/scale:.2f}vh;'
        f'transform:scale({scale});transform-origin:0 0;border:none;"></iframe></div>'
    )

    return {
        "id": homework_id, "name": hw_name, "bizType": 21, "createType": None,
        "publishAnswerStatus": 0, "submitStatus": 0, "taskId": "TASK_" + homework_id,
        "hwPageInfoDTOs": [{
            "id": "PAGE_" + homework_id, "homeworkId": homework_id, "pageType": 3,
            "pageSeqNum": 1, "needAnswerStatus": 0, "pageStatus": 1, "del": 0,
            "createTime": "2024-12-15 00:50:57", "updateTime": "2024-12-15 00:50:57",
            "hwQuestionInfos": [{
                "id": "Q_" + homework_id, "homeworkId": homework_id, "typeId": 4,
                "seqNum": 1, "seqNumName": "1", "content": html_content, "answer": "",
                "del": 0, "studentAnswerDetails": []
            }]
        }], "trajectoryPageDTOs": None
    }

@app.route("/api/shutdown", methods=["GET", "POST"])
def api_shutdown():
    Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
    return "<h2 style='text-align:center;margin-top:20%;font-family:sans-serif;'>服务端已断开，程序退出中...</h2>"

@app.route("/qlBox-manager/getBindedSchoolInfo", methods=["POST", "GET"])
def get_binded_school_info():
    return ok({"schoolId": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校"})

@app.route("/classInApp/box/auth/tokenValid", methods=["POST", "GET"])
@app.route("/classInApp/serv-manager/j_spring_security_check", methods=["POST", "GET"])
def auth_mock():
    return ok({
        "userId": "student001", "schoolKey": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校",
        "classroomId": "C001", "classroomName": "模拟教室", "className": "模拟班级",
        "loginIp": request.host.split(":")[0], "classInSocketPort": "9000", "token": "mock-token",
        "isBoxClass": True, "isAirClass": False,
    })

@app.route("/classInApp/serv-teachplatform/pub/alive", methods=["POST", "GET"])
def ping_alive():
    return ok({"alive": True})

@app.route("/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
@app.route("/classInApp/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
def teacher_file_list():
    page_index, page_size = int(get_param("pageIndex", "1")), int(get_param("pageSize", "20"))
    files, items = [], []
    for root, _, filenames in os.walk(RESOURCES_DIR):
        for name in filenames:
            files.append(os.path.relpath(os.path.join(root, name), RESOURCES_DIR).replace("\\", "/"))
    for idx, rel_path in enumerate(sorted(files), start=1):
        abs_path = os.path.join(RESOURCES_DIR, rel_path)
        items.append({
            "fileId": f"file-{idx}", "fileName": os.path.basename(rel_path), "shareTime": "2024-01-01",
            "size": str(os.path.getsize(abs_path)) if os.path.exists(abs_path) else "0",
            "lessonName": "Mock Course", "suffix": os.path.splitext(rel_path)[1].lower().lstrip("."),
            "fileUrl": f"resources/{rel_path}", "teacherName": "Mock Teacher"
        })
    total, start = len(items), (page_index - 1) * page_size
    return ok({
        "data": items[start:start + page_size], "pageCount": (total + page_size - 1) // page_size,
        "pageIndex": page_index, "pageSize": page_size, "recordCount": total
    })

@app.route("/resources/<path:filename>")
def serve_resource(filename: str):
    return send_from_directory(RESOURCES_DIR, filename, as_attachment=False)

@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/selectPadHomeworkList", methods=["GET", "POST"])
def homework_list():
    return ok(build_homework_list_dynamic(int(get_param("pageIndex", "1")), int(get_param("pageSize", "20"))))

@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/selectPadHomeworkDetail", methods=["GET", "POST"])
def homework_detail():
    return ok(build_homework_detail_dynamic(get_param("homeworkId")))
@app.route("/classInApp/serv-teachplatform/appMenuInfo/list", methods=["GET"])
@app.route("/serv-teachplatform/appMenuInfo/list", methods=["GET"])
def app_menu_list():
    return ok([
        {
            "id": "pkg_001",
            "appName": "应用卸载",
            "appKey": "local.app.uninstall"
        }
    ])
class MockServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QRQLL Mock 服务端")
        self.root.geometry("950x650")
        self.target_dir = RESOURCES_DIR
        self.set_app_icon()
        self.create_header()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=5)
        self.init_resource_tab()
        self.init_homework_tab()
        self.init_settings_tab()

        self.status_var = StringVar()
        self.status_var.set("服务器运行中...")
        ttk.Label(self.root, textvariable=self.status_var, relief=SUNKEN, padding=5).pack(fill=X)

    def get_host_ip(self):
        try:
            s = socket(AF_INET, SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'

    def set_app_icon(self):
        try:
            base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_path, "icon.png")
            if os.path.exists(icon_path):
                self.root.iconphoto(False, PhotoImage(Image.open(icon_path)))
        except: pass

    def create_header(self):
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=X)
        ttk.Label(header, text="QRQLL Mock 控制台", font=("Arial", 16, "bold")).pack(side=LEFT)
        ttk.Label(header, text=f"Local IP: {self.get_host_ip()}:2417", font=("Consolas", 12, "bold"),
                  bootstyle="inverse-primary", padding=5).pack(side=LEFT, padx=20)

    def init_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙️ 系统设置")
        f = ttk.Frame(tab, padding=20)
        f.pack(fill=BOTH, expand=True)
        self.var_close_hw = ttk.BooleanVar(value=ENABLE_CLOSE_HW)
        ttk.Checkbutton(f, text="启用「关闭程序」特殊作业", variable=self.var_close_hw, 
                        bootstyle="round-toggle", command=self.toggle_setting).pack(anchor=W)

    def toggle_setting(self):
        global ENABLE_CLOSE_HW
        ENABLE_CLOSE_HW = self.var_close_hw.get()

    def init_resource_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📂 资源文件管理")
        tool_frame = ttk.Frame(tab, padding=5)
        tool_frame.pack(fill=X)
        ttk.Button(tool_frame, text="📁 添加文件", command=self.add_files, bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        ttk.Button(tool_frame, text="🔄 刷新", command=self.refresh_files, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(tool_frame, text="🗑️ 删除选中", command=self.del_files, bootstyle=DANGER).pack(side=LEFT, padx=2)
        ttk.Button(tool_frame, text="📂 打开文件夹", command=lambda: self.open_dir(self.target_dir), bootstyle=SECONDARY).pack(side=RIGHT, padx=2)
        
        self.file_tree = ttk.Treeview(tab, columns=("name", "size", "path"), show="headings", bootstyle=PRIMARY)
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("size", text="大小")
        self.file_tree.column("name", width=400)
        self.file_tree.column("size", width=100)
        self.file_tree.column("path", width=0, stretch=False)
        self.file_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        self.refresh_files()

    def refresh_files(self):
        self.file_tree.delete(*self.file_tree.get_children())
        if not os.path.exists(self.target_dir): return
        for root, _, files in os.walk(self.target_dir):
            for f in files:
                p = os.path.join(root, f)
                size = os.stat(p).st_size
                for u in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0: break
                    size /= 1024.0
                self.file_tree.insert("", "end", values=(f, f"{size:.1f} {u}", p))

    def add_files(self):
        files = filedialog.askopenfilenames(title="选择文件", filetypes=[("所有文件", "*.*")])
        count = 0
        for f in files:
            dest = os.path.join(self.target_dir, os.path.basename(f))
            if os.path.exists(dest) and not messagebox.askyesno("覆盖", f"文件已存在，覆盖吗？"): continue
            copy2(f, dest)
            count += 1
        if count:
            self.refresh_files()
            self.status_var.set(f"已添加 {count} 个文件")

    def del_files(self):
        sel = self.file_tree.selection()
        if not sel: return messagebox.showwarning("提示", "请选择文件")
        if not messagebox.askyesno("确认", "确定删除？"): return
        for item in sel:
            try: os.remove(self.file_tree.item(item)["values"][2])
            except: pass
        self.refresh_files()

    def on_double_click(self, event):
        sel = self.file_tree.selection()
        if sel: self.open_dir(self.file_tree.item(sel[0])["values"][2])

    def open_dir(self, path):
        try:
            if os.name == 'nt': os.startfile(path)
            elif sys.platform == 'darwin': os.system(f'open "{path}"')
            else: os.system(f'xdg-open "{path}"')
        except Exception as e: messagebox.showerror("错误", str(e))

    def init_homework_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📝 上网配置")
        paned = ttk.Panedwindow(tab, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        ttk.Label(left_frame, text="作业列表", font=("Arial", 10, "bold")).pack(anchor=W, pady=5)
        self.hw_tree = ttk.Treeview(left_frame, columns=("id", "name"), show="headings", selectmode="browse")
        self.hw_tree.heading("id", text="ID")
        self.hw_tree.heading("name", text="作业名称")
        self.hw_tree.column("id", width=100)
        self.hw_tree.column("name", width=200)
        self.hw_tree.pack(fill=BOTH, expand=True)
        self.hw_tree.bind("<<TreeviewSelect>>", self.on_hw_select)

        btn_frame = ttk.Frame(left_frame, padding=5)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="+ 新增", command=self.add_hw, bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="- 删除", command=self.del_hw, bootstyle=DANGER).pack(side=LEFT, padx=2)

        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=2)
        ttk.Label(right_frame, text="编辑详情", font=("Arial", 10, "bold")).pack(anchor=W, pady=10)

        self.var_id, self.var_name, self.var_url, self.var_scale = StringVar(), StringVar(), StringVar(), StringVar()
        for l, v, r in [("ID:", self.var_id, True), ("名称:", self.var_name, False), ("URL:", self.var_url, False)]:
            f = ttk.Frame(right_frame)
            f.pack(fill=X, pady=5)
            ttk.Label(f, text=l, width=8).pack(side=LEFT)
            ttk.Entry(f, textvariable=v, state="readonly" if r else "normal").pack(side=LEFT, fill=X, expand=True)

        sf = ttk.Frame(right_frame)
        sf.pack(fill=X, pady=5)
        ttk.Label(sf, text="缩放:", width=8).pack(side=LEFT)
        ttk.Combobox(sf, textvariable=self.var_scale, values=["25%", "50%", "75%", "100%", "150%"], bootstyle="primary").pack(side=LEFT, fill=X, expand=True)
        ttk.Label(right_frame, text="💡 可输入数字，如 60 代表 60%。", font=("Arial", 8), bootstyle="secondary").pack(anchor=W, padx=60)
        ttk.Button(right_frame, text="💾 保存修改", command=self.save_hw, bootstyle=PRIMARY).pack(pady=20, fill=X)
        self.refresh_hw()

    def refresh_hw(self):
        sel_id = self.hw_tree.item(self.hw_tree.selection()[0])["values"][0] if self.hw_tree.selection() else None
        self.hw_tree.delete(*self.hw_tree.get_children())
        for hw in HOMEWORK_DATA: self.hw_tree.insert("", "end", values=(hw["id"], hw["name"]))
        if sel_id:
            for item in self.hw_tree.get_children():
                if str(self.hw_tree.item(item)["values"][0]) == str(sel_id):
                    self.hw_tree.selection_set(item)
                    break

    def on_hw_select(self, event):
        sel = self.hw_tree.selection()
        if not sel: return
        hw = next((h for h in HOMEWORK_DATA if h["id"] == str(self.hw_tree.item(sel[0])["values"][0])), None)
        if hw:
            self.var_id.set(hw["id"]); self.var_name.set(hw["name"]); self.var_url.set(hw["url"])
            self.var_scale.set(f"{int(hw.get('scale', 0.5) * 100)}%")

    def add_hw(self):
        new_id = str(int(time.time() * 1000))
        HOMEWORK_DATA.append({"id": new_id, "name": f"作业 {new_id[-4:]}", "lessonName": "通用", "url": "https://baidu.com", "scale": 0.5})
        self.refresh_hw()

    def del_hw(self):
        sel = self.hw_tree.selection()
        if sel and messagebox.askyesno("确认", "确定删除？"):
            global HOMEWORK_DATA
            HOMEWORK_DATA = [h for h in HOMEWORK_DATA if h["id"] != str(self.hw_tree.item(sel[0])["values"][0])]
            self.var_id.set(""); self.var_name.set(""); self.var_url.set(""); self.var_scale.set("")
            self.refresh_hw()

    def save_hw(self):
        if not self.var_id.get(): return
        try:
            val = float(self.var_scale.get().replace("%", "").strip())
            fs = val / 100.0 if val > 1.0 else val
            fs = max(0.1, min(fs, 5.0))
        except: return messagebox.showwarning("错误", "缩放比例需为数字")

        for hw in HOMEWORK_DATA:
            if hw["id"] == self.var_id.get():
                hw["name"] = self.var_name.get()
                hw["url"] = self.var_url.get()
                hw["scale"] = round(fs, 2)
                break
        self.refresh_hw()
        self.var_scale.set(f"{int(fs * 100)}%")
        messagebox.showinfo("成功", "保存成功")

if __name__ == "__main__":
    Thread(target=lambda: serve(app, host="0.0.0.0", port=2417), daemon=True).start()
    enable_high_dpi_awareness()
    root = ttk.Window(themename="litera")
    gui = MockServerApp(root)
    root.mainloop()
