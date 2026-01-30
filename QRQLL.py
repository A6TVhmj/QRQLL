import os
import shutil
import sys
import threading
from datetime import datetime
from typing import Dict, List, Tuple
from tkinter import filedialog, messagebox, StringVar
import ttkbootstrap as ttk
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image
from PIL.ImageTk import PhotoImage
from ttkbootstrap.constants import *

# Flask应用部分
app = Flask(__name__)
def get_app_dir():
    """获取应用真实目录（兼容开发/打包环境）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()  # 直接获取路径
RESOURCES_DIR = os.path.join(APP_DIR, "resources")
# 确保资源目录存在
if not os.path.exists(RESOURCES_DIR):
    os.makedirs(RESOURCES_DIR)
def ok(result=None, message: str = ""):
    return jsonify({"status": 0, "message": message, "result": result if result is not None else {}})

def list_resources() -> List[str]:
    files = []
    for root, _, filenames in os.walk(RESOURCES_DIR):
        for name in filenames:
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, RESOURCES_DIR).replace("\\", "/")
            files.append(rel)
    return sorted(files)

def get_param(name: str, default: str = "") -> str:
    if request.args.get(name) is not None:
        return request.args.get(name, default)
    return request.form.get(name, default)

def paginate(items: List[Dict], page_index: int, page_size: int) -> Tuple[List[Dict], int, int, int]:
    if page_index <= 0:
        page_index = 1
    if page_size <= 0:
        page_size = 20
    total = len(items)
    page_count = max((total + page_size - 1) // page_size, 1)
    start = (page_index - 1) * page_size
    end = start + page_size
    return items[start:end], total, page_count, page_size

def build_teacher_file_list(page_index: int, page_size: int, search_key: str = "", file_type: str = "") -> Dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items: List[Dict] = []
    for idx, rel_path in enumerate(list_resources(), start=1):
        name = os.path.basename(rel_path)
        ext = os.path.splitext(rel_path)[1].lower().lstrip(".")
        if search_key and search_key not in name:
            continue
        if file_type:
            if file_type.isdigit():
                pass
            else:
                if ext != file_type.lower().lstrip("."):
                    continue
        abs_path = os.path.join(RESOURCES_DIR, rel_path)
        size = str(os.path.getsize(abs_path)) if os.path.exists(abs_path) else "0"
        items.append(
            {
                "fileId": f"file-{idx}",
                "fileName": name,
                "shareTime": now,
                "size": size,
                "lessonName": "QRQLL 模拟课程",
                "suffix": ext,
                "fileUrl": f"resources/{rel_path}",
                "teacherName": "QRQLL 模拟教师",
            }
        )

    page_items, total, page_count, page_size = paginate(items, page_index, page_size)
    return {
        "data": page_items,
        "pageCount": page_count,
        "pageIndex": page_index,
        "pageSize": page_size,
        "recordCount": total,
    }

def build_account(host_ip: str) -> Dict:
    return {
        "userId": "student001",
        "schoolKey": "LOCAL_SCHOOL",
        "schoolName": "QRQLL 模拟学校",
        "classroomId": "CLASSROOM001",
        "classroomName": "QRQLL 模拟教室",
        "className": "QRQLL 模拟班级",
        "loginIp": host_ip,
        "classInSocketPort": "9000",
        "token": "mock-token",
        "isBoxClass": True,
        "isAirClass": False,
    }

# Flask路由
@app.route("/qlBox-manager/getBindedSchoolInfo", methods=["POST", "GET"])
def get_binded_school_info():
    return ok({"schoolId": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校"})

@app.route("/classInApp/box/auth/tokenValid", methods=["POST", "GET"])
def token_valid():
    host_ip = request.host.split(":")[0]
    return ok(build_account(host_ip))

@app.route("/classInApp/serv-manager/j_spring_security_check", methods=["POST", "GET"])
def login_box():
    host_ip = request.host.split(":")[0]
    return ok(build_account(host_ip))

@app.route("/classInApp/serv-teachplatform/pub/alive", methods=["POST", "GET"])
def ping_alive():
    return ok({"alive": True})

@app.route("/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
@app.route("/classInApp/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
def teacher_file_list():
    page_index = int(get_param("pageIndex", "1"))
    page_size = int(get_param("pageSize", "20"))
    search_key = get_param("fuzzyName", "")
    file_type = get_param("fileType", "")
    return ok(build_teacher_file_list(page_index, page_size, search_key, file_type))

@app.route("/resources/<path:filename>")
def serve_resource(filename: str):
    return send_from_directory(RESOURCES_DIR, filename, as_attachment=False)

# GUI部分
class MockResourceManager:
    def __init__(self, root):
        self.root = root
        self.root.title("QRQLL Mock 资源管理器")
        self.root.geometry("900x600")
        self.set_app_icon()
        # 设置目标文件夹路径
        self.target_dir = RESOURCES_DIR
        self.create_widgets()
        self.refresh_file_list()
        self.check_server_status()
    def get_resource_path(self, relative_path):
        """获取资源的绝对路径，支持开发环境和打包后的环境"""
        try:
            base_path = sys._MEIPASS # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    def set_app_icon(self):
        """设置应用图标，支持开发和打包环境"""
        try:
            icon_path = self.get_resource_path("icon.png")
            if os.path.exists(icon_path):
                self.root.iconphoto(False, PhotoImage(Image.open(icon_path)))
        except Exception as e:
            print(f"设置图标失败: {e}")
    
    def check_server_status(self):
        """检查服务器状态"""
        try:
            self.status_var.set("服务器运行中 | 就绪")
        except Exception as e:
            self.status_var.set(f"服务器状态检查失败: {e}")
        self.root.after(5000, self.check_server_status)
    
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 10))
        title_label = ttk.Label(
            header_frame, 
            text="QRQLL Mock 资源管理器", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=LEFT)
        path_label = ttk.Label(
            header_frame, 
            text=f"目标路径: {self.target_dir}",
            font=("Arial", 10),
            bootstyle=SECONDARY
        )
        path_label.pack(side=RIGHT)
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=X, pady=(0, 10))
        self.add_btn = ttk.Button(
            toolbar_frame,
            text="📁 添加文件",
            command=self.add_files,
            bootstyle=SUCCESS,
            width=15
        )
        self.add_btn.pack(side=LEFT, padx=5)
        self.refresh_btn = ttk.Button(
            toolbar_frame,
            text="🔄 刷新",
            command=self.refresh_file_list,
            bootstyle=PRIMARY,
            width=10
        )
        self.refresh_btn.pack(side=LEFT, padx=5)
        self.delete_btn = ttk.Button(
            toolbar_frame,
            text="🗑️ 删除",
            command=self.delete_selected,
            bootstyle=DANGER,
            width=10
        )
        self.delete_btn.pack(side=LEFT, padx=5)
        self.open_btn = ttk.Button(
            toolbar_frame,
            text="📂 打开文件夹",
            command=self.open_folder,
            bootstyle=SECONDARY,
            width=12
        )
        self.open_btn.pack(side=RIGHT, padx=5)
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=BOTH, expand=True)
        columns = ("name", "size", "type", "modified")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="tree headings",
            bootstyle=PRIMARY
        )
        self.tree.heading("#0", text="📁")
        self.tree.heading("name", text="文件名")
        self.tree.heading("size", text="大小")
        self.tree.heading("type", text="类型")
        self.tree.heading("modified", text="修改时间")
        self.tree.column("#0", width=40)
        self.tree.column("name", width=300)
        self.tree.column("size", width=100)
        self.tree.column("type", width=100)
        self.tree.column("modified", width=150)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.bind("<Double-1>", self.on_double_click)
        
        # 状态栏
        self.status_var = StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=SUNKEN,
            anchor=W,
            padding=(5, 2)
        )
        status_bar.pack(fill=X, pady=(10, 0))
    
    def refresh_file_list(self):
        """刷新文件列表"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取文件列表
        try:
            items = []
            for root, dirs, files in os.walk(self.target_dir):
                # 添加目录
                for d in sorted(dirs):
                    path = os.path.join(root, d)
                    items.append((d, "folder", path))
                # 添加文件
                for f in sorted(files):
                    path = os.path.join(root, f)
                    items.append((f, "file", path))
            # 排序：文件夹在前，文件在后
            items.sort(key=lambda x: (0 if x[1] == "folder" else 1, x[0].lower()))
            
            # 添加到树形视图
            for name, item_type, path in items:
                try:
                    stat = os.stat(path)
                    size = self.format_size(stat.st_size) if item_type == "file" else "<文件夹>"
                    modified = self.format_time(stat.st_mtime)
                    ext = os.path.splitext(name)[1].upper() if item_type == "file" else "FOLDER"
                    
                    icon = "📁" if item_type == "folder" else "📄"
                    
                    self.tree.insert(
                        "",
                        "end",
                        text=icon,
                        values=(name, size, ext, modified),
                        tags=(path,)
                    )
                except Exception as e:
                    print(f"无法获取 {path} 的信息: {e}")
            
            file_count = len([i for i in items if i[1] == "file"])
            folder_count = len([i for i in items if i[1] == "folder"])
            self.status_var.set(f"已加载 {file_count} 个文件，{folder_count} 个文件夹")
            
        except Exception as e:
            messagebox.showerror("错误", f"无法读取目录: {e}")
            self.status_var.set("错误：无法读取目录")
    
    def add_files(self):
        """添加文件到目标目录"""
        files = filedialog.askopenfilenames(
            title="选择要添加的文件",
            filetypes=[("所有文件", "*.*")]
        )
        
        if files:
            success_count = 0
            for file_path in files:
                try:
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(self.target_dir, filename)
                    
                    # 如果文件已存在，询问是否覆盖
                    if os.path.exists(dest_path):
                        if not messagebox.askyesno(
                            "文件已存在",
                            f"文件 '{filename}' 已存在，是否覆盖？"
                        ):
                            continue
                    
                    shutil.copy2(file_path, dest_path)
                    success_count += 1
                    
                except Exception as e:
                    messagebox.showerror("错误", f"复制文件 {file_path} 失败: {e}")
            
            if success_count > 0:
                self.refresh_file_list()
                messagebox.showinfo("成功", f"成功添加 {success_count} 个文件")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return messagebox.showwarning("警告", "请先选择文件")
        to_delete = []
        for item_id in selected:
            path = self.tree.item(item_id)['tags'][0]
            name = self.tree.item(item_id)['values'][0]
            to_delete.append((path, name))

        msg = f"确定删除 {len(to_delete)} 个项目？" if len(to_delete)>1 else f"确定删除 '{to_delete[0][1]}'？"
        if not messagebox.askyesno("确认删除", msg + "\n此操作不可恢复！"):
            return
        
        # 批量删除
        errors = []
        for path, name in to_delete:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
        
        self.refresh_file_list()
        if errors:
            messagebox.showerror("部分失败", "\n".join(errors))
        else:
            self.status_var.set(f"成功删除 {len(to_delete)} 个项目")
    def on_double_click(self, event):
        """双击打开文件或文件夹"""
        selected = self.tree.selection()
        
        if selected:
            file_path = self.tree.item(selected[0])['tags'][0]
            
            if os.path.isdir(file_path):
                # 打开文件夹
                self.open_directory(file_path)
            else:
                # 打开文件
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
    def format_time(self, timestamp):
        """格式化时间"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=80, debug=False, use_reloader=False), daemon=True)
    flask_thread.start()
    root = ttk.Window(themename="litera")
    app = MockResourceManager(root)
    root.mainloop()
