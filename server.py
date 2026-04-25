"""
QRQLL Mobile — Flask 服务端模块
从 QRQLL V2.3 移植，API 完全保留
"""

import os
import sys
import time
import json
from threading import Thread, Lock
from datetime import datetime
from typing import Dict, Optional
from socket import socket, AF_INET, SOCK_DGRAM

from flask import Flask, jsonify, request, send_from_directory
from waitress import serve

# ====================================================================
# 全局配置
# ====================================================================

HOMEWORK_DATA = [
    {
        "id": "1867975578577879042",
        "name": "百度搜索（横屏版）",
        "lessonName": "搜索",
        "url": "https://baidu.com",
        "scale": 0.5,
        "orientation": "landscape"
    },
    {
        "id": "1867975578577879043",
        "name": "百度搜索（竖屏版）",
        "lessonName": "搜索",
        "url": "https://baidu.com",
        "scale": 0.5,
        "orientation": "portrait"
    }
]
ENABLE_CLOSE_HW = False
ENABLE_LOGGING = False
ENABLE_LOG_HEADERS = False
LAST_SHUTDOWN_CLICK = 0

# 服务器生命周期控制
_server_thread: Optional[Thread] = None
_server_running = False
_server_lock = Lock()

# ====================================================================
# 路径管理
# ====================================================================

def get_resources_dir() -> str:
    """获取 resources 目录路径，不存在则自动创建"""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    res_dir = os.path.join(app_dir, "resources")
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)
    return res_dir

RESOURCES_DIR = get_resources_dir()

# ====================================================================
# Flask 应用
# ====================================================================

app = Flask(__name__)


@app.after_request
def log_request(response):
    if ENABLE_LOGGING:
        now = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
        proto = request.environ.get("SERVER_PROTOCOL", "HTTP/1.1")
        print(f'{request.remote_addr} - - [{now}] '
              f'"{request.method} {request.full_path} {proto}" '
              f'{response.status_code} -')
        if ENABLE_LOG_HEADERS:
            print("-" * 40)
            for k, v in request.headers.items():
                print(f"{k}: {v}")
            print("-" * 40)
    return response


# ====================================================================
# 辅助函数
# ====================================================================

def ok(result=None, message: str = ""):
    return jsonify({
        "status": 0,
        "message": message,
        "result": result if result is not None else {}
    })


def get_param(name: str, default: str = "") -> str:
    if request.args.get(name) is not None:
        return request.args.get(name, default)
    return request.form.get(name, default)


def build_homework_list_dynamic(page_index: int, page_size: int) -> Dict:
    """构建作业列表（模拟 ClassIn 分页）"""
    data_list = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_data = list(HOMEWORK_DATA)
    if ENABLE_CLOSE_HW:
        source_data.append({
            "id": "SYS_CLOSE_001",
            "name": "🔴 关闭服务端",
            "lessonName": "系统",
            "url": f"http://{request.host}/api/shutdown",
            "scale": 1.0,
            "orientation": "landscape"
        })

    start = (page_index - 1) * page_size
    end = start + page_size
    sliced_data = source_data[start:end]

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
        "pageCount": (len(source_data) + page_size - 1) // page_size,
        "recordCount": len(source_data),
        "data": data_list
    }


def build_homework_detail_dynamic(homework_id: str) -> Dict:
    """构建作业详情（含 iframe 注入）"""
    if homework_id == "SYS_CLOSE_001":
        target_hw = {
            "id": "SYS_CLOSE_001",
            "name": "🔴 关闭服务端",
            "url": f"http://{request.host}/api/shutdown",
            "scale": 1.0,
            "orientation": "landscape"
        }
    else:
        target_hw = next(
            (item for item in HOMEWORK_DATA if item["id"] == homework_id),
            None
        )
        if not target_hw:
            target_hw = HOMEWORK_DATA[0] if HOMEWORK_DATA else {}
            if not target_hw:
                return {}

    iframe_url = target_hw.get("url", "")
    hw_name = target_hw.get("name", "")
    scale = float(target_hw.get("scale", 0.5))
    if scale <= 0:
        scale = 0.5
    ori = target_hw.get("orientation", "landscape")

    if ori == "portrait":
        w = f"{100/scale:.2f}vh"
        h = f"{100/scale:.2f}vw"
        iframe_style = (
            f"position:fixed;top:50%;left:50%;"
            f"width:{w};height:{h};"
            f"transform:translate(-50%, -50%) scale({scale}) rotate(-90deg);"
            f"transform-origin:center center;border:none;"
        )
    else:
        w = f"{100/scale:.2f}vw"
        h = f"{100/scale:.2f}vh"
        iframe_style = (
            f"position:fixed;top:0;left:0;"
            f"width:{w};height:{h};"
            f"transform:scale({scale});transform-origin:0 0;border:none;"
        )

    html_content = (
        f'<div style="width:100vw;height:100vh;overflow:hidden;'
        f'position:relative;">'
        f'<iframe src="{iframe_url}" '
        f'allow="fullscreen *; clipboard-read *; clipboard-write *" '
        f'sandbox="allow-same-origin allow-forms allow-scripts '
        f'allow-popups allow-modals allow-top-navigation-by-user-activation '
        f'allow-pointer-lock allow-downloads" '
        f'style="{iframe_style}"></iframe></div>'
    )

    return {
        "id": homework_id,
        "name": hw_name,
        "bizType": 21,
        "createType": None,
        "publishAnswerStatus": 1,
        "submitStatus": 1,
        "taskId": "TASK_" + homework_id,
        "hwPageInfoDTOs": [{
            "id": "PAGE_" + homework_id,
            "homeworkId": homework_id,
            "pageType": 3,
            "pageSeqNum": 1,
            "needAnswerStatus": 0,
            "pageStatus": 1,
            "del": 0,
            "createTime": "2024-12-15 00:50:57",
            "updateTime": "2024-12-15 00:50:57",
            "hwQuestionInfos": [{
                "id": "Q_" + homework_id,
                "homeworkId": homework_id,
                "typeId": 4,
                "seqNum": 1,
                "seqNumName": "1",
                "content": html_content,
                "answer": "",
                "del": 0,
                "studentAnswerDetails": []
            }]
        }],
        "trajectoryPageDTOs": None
    }


def get_host_ip() -> str:
    """获取本机局域网 IP"""
    try:
        s = socket(AF_INET, SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# ====================================================================
# API 路由
# ====================================================================

@app.route("/api/shutdown", methods=["GET"])
def api_shutdown():
    """两段式关闭确认（需 3 秒内点两次）"""
    global LAST_SHUTDOWN_CLICK
    now = time.time()
    if now - LAST_SHUTDOWN_CLICK < 3.0:
        Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
        return ("<h2 style='text-align:center;margin-top:20%;"
                "font-family:sans-serif;'>服务端已断开，程序退出中...</h2>")
    else:
        LAST_SHUTDOWN_CLICK = now
        return """
        <h2 style='text-align:center; margin-top:20%;'>
            [确认关闭]<br><br>请在 3 秒内再点一次本页面以确认关闭
        </h2>
        <script>
            document.body.onclick = () => location.reload();
        </script>
        """


@app.route("/qlBox-manager/getBindedSchoolInfo", methods=["POST", "GET"])
def get_binded_school_info():
    return ok({
        "schoolId": "LOCAL_SCHOOL",
        "schoolName": "QRQLL 模拟学校"
    })


@app.route("/classInApp/box/auth/tokenValid", methods=["POST", "GET"])
@app.route("/classInApp/serv-manager/j_spring_security_check",
           methods=["POST", "GET"])
def auth_mock():
    return ok({
        "userId": "student001",
        "schoolKey": "LOCAL_SCHOOL",
        "schoolName": "QRQLL 模拟学校",
        "classroomId": "C001",
        "classroomName": "模拟教室",
        "className": "模拟班级",
        "loginIp": request.host.split(":")[0],
        "classInSocketPort": "9000",
        "token": "mock-token",
        "isBoxClass": True,
        "isAirClass": False
    })


@app.route("/classInApp/serv-teachplatform/pub/alive",
           methods=["POST", "GET"])
def ping_alive():
    return ok({"alive": True})


@app.route("/serv-teachplatform/courseware/student/selectShareFileList",
           methods=["GET", "POST"])
@app.route("/classInApp/serv-teachplatform/courseware/student/"
           "selectShareFileList", methods=["GET", "POST"])
def teacher_file_list():
    page_index = int(get_param("pageIndex", "1"))
    page_size = int(get_param("pageSize", "20"))

    files = []
    for root, _, filenames in os.walk(RESOURCES_DIR):
        for name in filenames:
            rel = os.path.relpath(os.path.join(root, name),
                                  RESOURCES_DIR).replace("\\", "/")
            files.append(rel)

    items = []
    for idx, rel_path in enumerate(sorted(files), start=1):
        abs_path = os.path.join(RESOURCES_DIR, rel_path)
        size = (str(os.path.getsize(abs_path))
                if os.path.exists(abs_path) else "0")
        items.append({
            "fileId": f"file-{idx}",
            "fileName": os.path.basename(rel_path),
            "shareTime": "2024-01-01",
            "size": size,
            "lessonName": "Mock Course",
            "suffix": os.path.splitext(rel_path)[1].lower().lstrip("."),
            "fileUrl": f"resources/{rel_path}",
            "teacherName": "Mock Teacher"
        })

    total = len(items)
    start = (page_index - 1) * page_size

    return ok({
        "data": items[start:start + page_size],
        "pageCount": (total + page_size - 1) // page_size,
        "pageIndex": page_index,
        "pageSize": page_size,
        "recordCount": total
    })


@app.route("/resources/<path:filename>")
def serve_resource(filename: str):
    return send_from_directory(RESOURCES_DIR, filename, as_attachment=False)


@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/"
           "selectPadHomeworkList", methods=["GET", "POST"])
def homework_list():
    return ok(build_homework_list_dynamic(
        int(get_param("pageIndex", "1")),
        int(get_param("pageSize", "20"))
    ))


@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/"
           "selectPadHomeworkDetail", methods=["GET", "POST"])
def homework_detail():
    return ok(build_homework_detail_dynamic(get_param("homeworkId")))


@app.route("/classInApp/serv-teachplatform/appMenuInfo/list",
           methods=["GET"])
@app.route("/serv-teachplatform/appMenuInfo/list",
           methods=["GET"])
def app_menu_list():
    return ok([
        {"id": "pkg_001", "appName": "应用卸载", "appKey": "local.app.uninstall"}
    ])


# ====================================================================
# 服务器生命周期管理
# ====================================================================

def start_server(host: str = "0.0.0.0", port: int = 2417) -> bool:
    """在后台线程启动 Flask + Waitress 服务器"""
    global _server_thread, _server_running
    with _server_lock:
        if _server_running:
            return False
        _server_running = True

    def _run():
        global _server_running
        try:
            serve(app, host=host, port=port)
        except Exception as e:
            print(f"[server] 服务异常退出: {e}")
        finally:
            with _server_lock:
                _server_running = False

    _server_thread = Thread(target=_run, daemon=True, name="QRQLL-Server")
    _server_thread.start()
    return True


def stop_server():
    """停止服务器（通过强制退出来实现）"""
    global _server_running
    with _server_lock:
        _server_running = False
    os._exit(0)


def is_server_running() -> bool:
    with _server_lock:
        return _server_running


# ====================================================================
# 直接运行（调试用）
# ====================================================================

if __name__ == "__main__":
    print(f"[server] QRQLL Mobile 服务器启动中...")
    print(f"[server] 资源目录: {RESOURCES_DIR}")
    print(f"[server] 监听地址: 0.0.0.0:2417")
    start_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[server] 服务停止")
