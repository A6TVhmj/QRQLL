import os
import shutil
import sys
import threading
import socket
import time
from datetime import datetime
from typing import Dict
from tkinter import filedialog, messagebox, StringVar
import ttkbootstrap as ttk
from flask import Flask, jsonify, request, send_from_directory
from ttkbootstrap.constants import *
from ttkbootstrap.utility import *
from PIL import Image
from PIL.ImageTk import PhotoImage

HOMEWORK_DATA = [
    {
        "id": "1867975578577879042",
        "name": "百度搜索",
        "lessonName": "数学",
        "url": "https://baidu.com" 
    }
]

# Flask应用部分
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
    start = (page_index - 1) * page_size
    end = start + page_size
    sliced_data = HOMEWORK_DATA[start:end]
    
    for hw in sliced_data:
        data_list.append({
            "publishTime": now,
            "homeworkId": hw["id"],
            "homeworkName": hw["name"],
            "lessonName": hw["lessonName"],
            "lessonId": "1001",
            "startTime": now,
            "endTime": None,
            "publishAnswerTime": "0",
            "submitStatus": 0,
            "redoQuestionNums": None
        })

    return {
        "pageIndex": page_index,
        "pageSize": page_size,
        "pageCount": (len(HOMEWORK_DATA) + page_size - 1) // page_size,
        "recordCount": len(HOMEWORK_DATA),
        "data": data_list
    }

def build_homework_detail_dynamic(homework_id: str) -> Dict:
    target_hw = next((item for item in HOMEWORK_DATA if item["id"] == homework_id), None)
    
    # 兜底逻辑：找不到ID就用第一个，保证测试时不报错
    if not target_hw:
        if HOMEWORK_DATA:
            target_hw = HOMEWORK_DATA[0]
        else:
            return {}

    iframe_url = target_hw["url"]
    hw_name = target_hw["name"]
    
    html_content = (
        f'<div style="width:70%">'
        f'<iframe src="{iframe_url}" allow="fullscreen"'
        f'sandbox="allow-same-origin allow-forms allow-scripts allow-popups allow-modals allow-top-navigation-by-user-activation allow-pointer-lock allow-downloads"'
        f'style="width:144vw;height:81vw;transform:scale(0.5);transform-origin:0 0;border:none">'
        f'</iframe></div><div style="width:70%">'
    )

    return {
        "id": homework_id,
        "name": hw_name,
        "bizType": 21,
        "createType": None,
        "publishAnswerStatus": 0,
        "submitStatus": 0,
        "taskId": "TASK_" + homework_id,
        "hwPageInfoDTOs": [
            {
                "id": "PAGE_" + homework_id,
                "homeworkId": homework_id,
                "pageType": 3,
                "pageSeqNum": 1,
                "needAnswerStatus": 0,
                "pageStatus": 1,
                "del": 0,
                "createTime": "2024-12-15 00:50:57",
                "updateTime": "2024-12-15 00:50:57",
                "hwQuestionInfos": [
                    {
                        "id": "Q_" + homework_id,
                        "homeworkId": homework_id,
                        "typeId": 4,
                        "seqNum": 1,
                        "seqNumName": "1",
                        "content": html_content, # 注入带样式的 HTML
                        "answer": "",
                        "del": 0,
                        "studentAnswerDetails": []
                    }
                ]
            }
        ],
        "trajectoryPageDTOs": None
    }

@app.route("/qlBox-manager/getBindedSchoolInfo", methods=["POST", "GET"])
def get_binded_school_info(): return ok({"schoolId": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校"})

@app.route("/classInApp/box/auth/tokenValid", methods=["POST", "GET"])
@app.route("/classInApp/serv-manager/j_spring_security_check", methods=["POST", "GET"])
def auth_mock():
    host_ip = request.host.split(":")[0]
    return ok({
        "userId": "student001", "schoolKey": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校",
        "classroomId": "C001", "classroomName": "模拟教室", "className": "模拟班级",
        "loginIp": host_ip, "classInSocketPort": "9000", "token": "mock-token",
        "isBoxClass": True, "isAirClass": False,
    })

@app.route("/classInApp/serv-teachplatform/pub/alive", methods=["POST", "GET"])
def ping_alive(): return ok({"alive": True})

# 资源列表接口
@app.route("/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
@app.route("/classInApp/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
def teacher_file_list():
    page_index = int(get_param("pageIndex", "1"))
    page_size = int(get_param("pageSize", "20"))
    
    files = []
    for root, _, filenames in os.walk(RESOURCES_DIR):
        for name in filenames:
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, RESOURCES_DIR).replace("\\", "/")
            files.append(rel)
    
    items = []
    for idx, rel_path in enumerate(sorted(files), start=1):
        name = os.path.basename(rel_path)
        ext = os.path.splitext(rel_path)[1].lower().lstrip(".")
        abs_path = os.path.join(RESOURCES_DIR, rel_path)
        size = str(os.path.getsize(abs_path)) if os.path.exists(abs_path) else "0"
        
        items.append({
            "fileId": f"file-{idx}", "fileName": name, "shareTime": "2024-01-01",
            "size": size, "lessonName": "Mock Course", "suffix": ext,
            "fileUrl": f"resources/{rel_path}", "teacherName": "Mock Teacher"
        })
    
    total = len(items)
    start = (page_index - 1) * page_size
    return ok({
        "data": items[start:start+page_size], "pageCount": (total+page_size-1)//page_size,
        "pageIndex": page_index, "pageSize": page_size, "recordCount": total
    })

@app.route("/resources/<path:filename>")
def serve_resource(filename: str):
    return send_from_directory(RESOURCES_DIR, filename, as_attachment=False)

# 作业接口
@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/selectPadHomeworkList", methods=["GET", "POST"])
def homework_list():
    page_index = int(get_param("pageIndex", "1"))
    page_size = int(get_param("pageSize", "20"))
    return ok(build_homework_list_dynamic(page_index, page_size))

@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/selectPadHomeworkDetail", methods=["GET", "POST"])
def homework_detail():
    homework_id = get_param("homeworkId")
    return ok(build_homework_detail_dynamic(homework_id))

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
        
        self.status_var = StringVar()
        self.status_var.set("服务器运行中...")
        ttk.Label(self.root, textvariable=self.status_var, relief=SUNKEN, padding=5).pack(fill=X)

    def get_host_ip(self):
        """获取本机IP地址"""
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))  # 改为80端口
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return '127.0.0.1'
    def get_resource_path(self, relative_path):
        """获取资源的绝对路径，支持开发环境和打包后的环境"""
        try:
            base_path = sys._MEIPASS # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    def set_app_icon(self):
        try:
            icon_path = self.get_resource_path("icon.png")
            if os.path.exists(icon_path):
                self.icon_image = PhotoImage(Image.open(icon_path))
                self.root.iconphoto(False, self.icon_image)
        except Exception as e:
            print(f"设置图标失败: {e}") 

    def create_header(self):
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=X)
        ttk.Label(header, text="QRQLL Mock 控制台", font=("Arial", 16, "bold")).pack(side=LEFT)
        ip = self.get_host_ip()
        ttk.Label(header, text=f"Local IP: {ip}:2417", font=("Consolas", 12, "bold"), 
                 bootstyle="inverse-primary", padding=5).pack(side=LEFT, padx=20)


    def init_resource_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📂 资源文件管理")
        
        # 工具栏
        tool_frame = ttk.Frame(tab, padding=5)
        tool_frame.pack(fill=X)
        
        ttk.Button(tool_frame, text="📁 添加文件", command=self.add_files, bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        ttk.Button(tool_frame, text="🔄 刷新", command=self.refresh_files, bootstyle=INFO).pack(side=LEFT, padx=2)
        ttk.Button(tool_frame, text="🗑️ 删除选中", command=self.delete_selected_files, bootstyle=DANGER).pack(side=LEFT, padx=2)
        
        ttk.Button(tool_frame, text="📂 打开文件夹", command=self.open_folder, 
                  bootstyle=SECONDARY).pack(side=RIGHT, padx=2)
        
        # 列表
        columns = ("name", "size", "path") # 增加path列用于隐藏存储完整路径
        self.file_tree = ttk.Treeview(tab, columns=columns, show="headings", bootstyle=PRIMARY)
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("size", text="大小")
        
        self.file_tree.column("name", width=400)
        self.file_tree.column("size", width=100)
        self.file_tree.column("path", width=0, stretch=False) 
        
        self.file_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        self.refresh_files()

    def refresh_files(self):
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        if not os.path.exists(self.target_dir): return
        
        for root, _, files in os.walk(self.target_dir):
            for f in files:
                path = os.path.join(root, f)
                stat = os.stat(path)
                size = self.format_size(stat.st_size)
                # 将完整路径存在第三列
                self.file_tree.insert("", "end", values=(f, size, path))
    
    def add_files(self):
        files = filedialog.askopenfilenames(title="选择要添加的文件", filetypes=[("所有文件", "*.*")])
        if files:
            count = 0
            for file_path in files:
                try:
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(self.target_dir, filename)
                    if os.path.exists(dest_path):
                        if not messagebox.askyesno("覆盖", f"文件 '{filename}' 已存在，覆盖吗？"): continue
                    shutil.copy2(file_path, dest_path)
                    count += 1
                except Exception as e:
                    print(e)
            self.refresh_files()
            self.status_var.set(f"已添加 {count} 个文件")

    def delete_selected_files(self):
        selected = self.file_tree.selection()
        if not selected:
            return messagebox.showwarning("提示", "请先选择文件")
        
        if not messagebox.askyesno("确认", f"确定删除选中的 {len(selected)} 个文件吗？"):
            return
            
        for item in selected:
            # 获取之前存储在隐藏列中的完整路径
            values = self.file_tree.item(item)["values"]
            if len(values) >= 3:
                full_path = values[2]
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Delete failed: {e}")
        
        self.refresh_files()
        self.status_var.set("删除完成")
    def on_double_click(self, event):
        """双击打开文件"""
        selected = self.file_tree.selection()
        if not selected:
            return
        
        values = self.file_tree.item(selected[0])["values"]
        if len(values) >= 3:
            file_path = values[2]
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS and Linux
                    if sys.platform == 'darwin':  # macOS
                        os.system(f'open "{file_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{file_path}"')
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {e}")
    def open_folder(self):
        """打开目标文件夹"""
        self.open_directory(self.target_dir)
    def open_directory(self, path):
        """打开指定目录"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS and Linux
                if sys.platform == 'darwin':  # macOS
                    os.system(f'open "{path}"')
                else:  # Linux
                    os.system(f'xdg-open "{path}"')
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    def init_homework_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📝 上网配置")
        
        paned = ttk.Panedwindow(tab, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 左侧列表
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        ttk.Label(left_frame, text="作业列表", font=("Arial", 10, "bold")).pack(anchor=W, pady=5)
        
        cols = ("id", "name")
        self.hw_tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.hw_tree.heading("id", text="ID")
        self.hw_tree.heading("name", text="作业名称")
        self.hw_tree.column("id", width=100)
        self.hw_tree.column("name", width=200)
        self.hw_tree.pack(fill=BOTH, expand=True)
        self.hw_tree.bind("<<TreeviewSelect>>", self.on_hw_select)
        
        btn_frame = ttk.Frame(left_frame, padding=5)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="+ 新增", command=self.add_homework, bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        ttk.Button(btn_frame, text="- 删除", command=self.delete_homework, bootstyle=DANGER).pack(side=LEFT, padx=2)

        # 右侧编辑
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=2)
        ttk.Label(right_frame, text="编辑详情", font=("Arial", 10, "bold")).pack(anchor=W, pady=10)
        
        self.var_hw_id = StringVar()
        self.var_hw_name = StringVar()
        self.var_hw_url = StringVar()
        
        self.create_form_entry(right_frame, "ID:", self.var_hw_id, readonly=True)
        self.create_form_entry(right_frame, "名称:", self.var_hw_name)
        self.create_form_entry(right_frame, "URL:", self.var_hw_url)
        
        ttk.Button(right_frame, text="💾 保存修改", command=self.save_current_hw, bootstyle=PRIMARY).pack(pady=20, fill=X)
        self.refresh_hw_list()

    def create_form_entry(self, parent, label, variable, readonly=False):
        f = ttk.Frame(parent)
        f.pack(fill=X, pady=5)
        ttk.Label(f, text=label, width=8).pack(side=LEFT)
        ttk.Entry(f, textvariable=variable, state="readonly" if readonly else "normal").pack(side=LEFT, fill=X, expand=True)

    def refresh_hw_list(self):
        selected_id = None
        sel = self.hw_tree.selection()
        if sel: selected_id = self.hw_tree.item(sel[0])["values"][0]

        for item in self.hw_tree.get_children(): self.hw_tree.delete(item)
        for hw in HOMEWORK_DATA: self.hw_tree.insert("", "end", values=(hw["id"], hw["name"]))
            
        if selected_id:
            for item in self.hw_tree.get_children():
                if str(self.hw_tree.item(item)["values"][0]) == str(selected_id):
                    self.hw_tree.selection_set(item)
                    break

    def on_hw_select(self, event):
        sel = self.hw_tree.selection()
        if not sel: return
        hw_id = str(self.hw_tree.item(sel[0])["values"][0])
        target = next((h for h in HOMEWORK_DATA if h["id"] == hw_id), None)
        if target:
            self.var_hw_id.set(target["id"])
            self.var_hw_name.set(target["name"])
            self.var_hw_url.set(target["url"])

    def add_homework(self):
        new_id = str(int(time.time() * 1000))
        HOMEWORK_DATA.append({"id": new_id, "name": f"作业 {new_id[-4:]}", "lessonName": "通用", "url": "https://www.baidu.com"})
        self.refresh_hw_list()

    def delete_homework(self):
        sel = self.hw_tree.selection()
        if not sel: return
        hw_id = str(self.hw_tree.item(sel[0])["values"][0])
        if messagebox.askyesno("确认", "确定删除该作业吗？"):
            global HOMEWORK_DATA
            HOMEWORK_DATA = [h for h in HOMEWORK_DATA if h["id"] != hw_id]
            self.var_hw_id.set(""); self.var_hw_name.set(""); self.var_hw_url.set("")
            self.refresh_hw_list()

    def save_current_hw(self):
        hw_id = self.var_hw_id.get()
        if not hw_id: return
        for hw in HOMEWORK_DATA:
            if hw["id"] == hw_id:
                hw["name"] = self.var_hw_name.get()
                hw["url"] = self.var_hw_url.get()
                break
        self.refresh_hw_list()
        messagebox.showinfo("成功", "保存成功")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=2417, debug=False, use_reloader=False), daemon=True).start()
    enable_high_dpi_awareness()
    root = ttk.Window(themename="litera")
    gui = MockServerApp(root)
    root.mainloop()
