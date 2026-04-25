import os
import sys
import time
import json
import argparse
from threading import Thread
from datetime import datetime
from typing import Dict
from socket import socket, AF_INET, SOCK_DGRAM
from flask import Flask, jsonify, request, send_from_directory
from waitress import serve

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()
RESOURCES_DIR = os.path.join(APP_DIR, "resources")
DATA_FILE = os.path.join(APP_DIR, "qrqll_data.json")

if not os.path.exists(RESOURCES_DIR):
    os.makedirs(RESOURCES_DIR)

DEFAULT_DATA = {
    "enable_close_hw": False,
    "enable_logging": False,
    "enable_log_headers": False,
    "homework_data": [
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
}

def load_data():
    if not os.path.exists(DATA_FILE): return DEFAULT_DATA
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

LAST_SHUTDOWN_CLICK = 0
app = Flask(__name__)

@app.after_request
def log_request(response):
    cfg = load_data()
    if cfg.get("enable_logging"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {request.remote_addr} - \"{request.method} {request.path}\" {response.status_code}")
        if cfg.get("enable_log_headers"):
            print("-" * 20 + " HEADERS " + "-" * 20)
            for k, v in request.headers.items(): print(f"{k}: {v}")
            print("-" * 49)
    return response

def ok(result=None, message: str = ""):
    return jsonify({"status": 0, "message": message, "result": result if result is not None else {}})

def get_param(name: str, default: str = "") -> str:
    if request.args.get(name) is not None: return request.args.get(name, default)
    return request.form.get(name, default)

def build_homework_list_dynamic(page_index: int, page_size: int) -> Dict:
    cfg = load_data()
    data_list = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_data = list(cfg.get("homework_data", []))
    
    if cfg.get("enable_close_hw"):
        source_data.append({"id": "SYS_CLOSE_001", "name": "🔴 关闭服务端", "lessonName": "系统", "url": f"http://{request.host}/api/shutdown", "scale": 1.0, "orientation": "landscape"})
    
    start = (page_index - 1) * page_size
    end = start + page_size
    sliced_data = source_data[start:end]

    for hw in sliced_data:
        data_list.append({
            "publishTime": now, "homeworkId": hw["id"], "homeworkName": hw["name"],
            "lessonName": hw.get("lessonName", "通用"), "lessonId": "1001", "startTime": now,
            "endTime": None, "publishAnswerTime": "0", "submitStatus": 0, "redoQuestionNums": None
        })

    return {"pageIndex": page_index, "pageSize": page_size, "pageCount": (len(source_data) + page_size - 1) // page_size, "recordCount": len(source_data), "data": data_list}

def build_homework_detail_dynamic(homework_id: str) -> Dict:
    cfg = load_data()
    hw_list = cfg.get("homework_data", [])
    
    if homework_id == "SYS_CLOSE_001":
        target_hw = {"id": "SYS_CLOSE_001", "name": "🔴 关闭服务端", "url": f"http://{request.host}/api/shutdown", "scale": 1.0, "orientation": "landscape"}
    else:
        target_hw = next((item for item in hw_list if item["id"] == homework_id), None)
        if not target_hw:
            target_hw = hw_list[0] if hw_list else {}
            if not target_hw: return {}

    iframe_url = target_hw.get("url", "")
    hw_name = target_hw.get("name", "")
    scale = float(target_hw.get("scale", 0.5))
    if scale <= 0: scale = 0.5
    ori = target_hw.get("orientation", "landscape")

    if ori == "portrait":
        w, h = f"{100/scale:.2f}vh", f"{100/scale:.2f}vw"
        iframe_style = f"position:fixed;top:50%;left:50%;width:{w};height:{h};transform:translate(-50%, -50%) scale({scale}) rotate(-90deg);transform-origin:center center;border:none;"
    else:
        w, h = f"{100/scale:.2f}vw", f"{100/scale:.2f}vh"
        iframe_style = f"position:fixed;top:0;left:0;width:{w};height:{h};transform:scale({scale});transform-origin:0 0;border:none;"

    html_content = f'<div style="width:100vw;height:100vh;overflow:hidden;position:relative;background:#000;"><iframe src="{iframe_url}" allow="fullscreen *; clipboard-read *; clipboard-write *" sandbox="allow-same-origin allow-forms allow-scripts allow-popups allow-modals allow-top-navigation-by-user-activation allow-pointer-lock allow-downloads" style="{iframe_style}"></iframe></div>'

    return {
        "id": homework_id, "name": hw_name, "bizType": 21, "createType": None,
        "publishAnswerStatus": 1, "submitStatus": 1, "taskId": "TASK_" + homework_id,
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

@app.route("/api/shutdown", methods=["GET"])
def api_shutdown():
    global LAST_SHUTDOWN_CLICK
    now = time.time()
    if now - LAST_SHUTDOWN_CLICK < 3.0:
        Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
        return "<h2>退出中...</h2>"
    else:
        LAST_SHUTDOWN_CLICK = now
        return "<h2 style='text-align:center; margin-top:20%;'>[确认关闭]<br><br>请在 3 秒内再点一次本页面以确认关闭</h2><script>document.body.onclick = () => location.reload();</script>"

@app.route("/qlBox-manager/getBindedSchoolInfo", methods=["POST", "GET"])
def get_binded_school_info(): return ok({"schoolId": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校"})

@app.route("/classInApp/box/auth/tokenValid", methods=["POST", "GET"])
@app.route("/classInApp/serv-manager/j_spring_security_check", methods=["POST", "GET"])
def auth_mock():
    return ok({"userId": "student001", "schoolKey": "LOCAL_SCHOOL", "schoolName": "QRQLL 模拟学校", "classroomId": "C001", "classroomName": "模拟教室", "className": "模拟班级", "loginIp": request.host.split(":")[0], "classInSocketPort": "9000", "token": "mock-token", "isBoxClass": True, "isAirClass": False})

@app.route("/classInApp/serv-teachplatform/pub/alive", methods=["POST", "GET"])
def ping_alive(): return ok({"alive": True})

@app.route("/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
@app.route("/classInApp/serv-teachplatform/courseware/student/selectShareFileList", methods=["GET", "POST"])
def teacher_file_list():
    page_index, page_size = int(get_param("pageIndex", "1")), int(get_param("pageSize", "20"))
    files, items = [], []
    for root, _, filenames in os.walk(RESOURCES_DIR):
        for name in filenames: files.append(os.path.relpath(os.path.join(root, name), RESOURCES_DIR).replace("\\", "/"))
    for idx, rel_path in enumerate(sorted(files), start=1):
        abs_path = os.path.join(RESOURCES_DIR, rel_path)
        items.append({"fileId": f"file-{idx}", "fileName": os.path.basename(rel_path), "shareTime": "2024-01-01", "size": str(os.path.getsize(abs_path)) if os.path.exists(abs_path) else "0", "lessonName": "Mock Course", "suffix": os.path.splitext(rel_path)[1].lower().lstrip("."), "fileUrl": f"resources/{rel_path}", "teacherName": "Mock Teacher"})
    total, start = len(items), (page_index - 1) * page_size
    return ok({"data": items[start:start + page_size], "pageCount": (total + page_size - 1) // page_size, "pageIndex": page_index, "pageSize": page_size, "recordCount": total})

@app.route("/resources/<path:filename>")
def serve_resource(filename: str): return send_from_directory(RESOURCES_DIR, filename, as_attachment=False)

@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/selectPadHomeworkList", methods=["GET", "POST"])
def homework_list(): return ok(build_homework_list_dynamic(int(get_param("pageIndex", "1")), int(get_param("pageSize", "20"))))

@app.route("/classInApp/serv-teachplatform/hw/basicInfo/student/selectPadHomeworkDetail", methods=["GET", "POST"])
def homework_detail(): return ok(build_homework_detail_dynamic(get_param("homeworkId")))

@app.route("/classInApp/serv-teachplatform/appMenuInfo/list", methods=["GET"])
@app.route("/serv-teachplatform/appMenuInfo/list", methods=["GET"])
def app_menu_list(): return ok([{"id": "pkg_001", "appName": "应用卸载", "appKey": "local.app.uninstall"}])

def get_host_ip():
    try:
        s = socket(AF_INET, SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return '127.0.0.1'

def main():
    parser = argparse.ArgumentParser(description="QRQLL Mock Server CLI", prog="qrqll")
    subparsers = parser.add_subparsers(dest="command")

    p_start = subparsers.add_parser("start")
    p_start.add_argument("--port", type=int, default=2417)

    subparsers.add_parser("hw")

    p_add = subparsers.add_parser("add")
    p_add.add_argument("url")
    p_add.add_argument("-n", "--name", default="自定义网页")
    p_add.add_argument("-s", "--scale", type=float, default=0.5)
    p_add.add_argument("-p", "--portrait", action="store_true")

    p_rm = subparsers.add_parser("rm")
    p_rm.add_argument("id")

    p_set = subparsers.add_parser("set")
    p_set.add_argument("key", choices=["close", "log", "headers"])
    p_set.add_argument("value", choices=["on", "off"])

    p_import = subparsers.add_parser("import")
    p_import.add_argument("file")
    p_import.add_argument("-o", "--overwrite", action="store_true")

    p_export = subparsers.add_parser("export")
    p_export.add_argument("file")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    data = load_data()

    if args.command == "start":
        if not os.path.exists(DATA_FILE): save_data(DEFAULT_DATA)
        port = getattr(args, 'port', 2417)
        print(f"Server Running: http://{get_host_ip()}:{port}")
        serve(app, host="0.0.0.0", port=port)

    elif args.command == "hw":
        for hw in data.get("homework_data", []):
            print(f"[{hw['id']}] {hw['name']}\n    URL: {hw['url']} | Scale: {hw['scale']} | Ori: {hw['orientation']}\n")

    elif args.command == "add":
        new_id = str(int(time.time() * 1000))
        sc = max(0.1, min(args.scale, 5.0))
        ori = "portrait" if args.portrait else "landscape"
        data.setdefault("homework_data", []).append({"id": new_id, "name": args.name, "lessonName": "通用", "url": args.url, "scale": sc, "orientation": ori})
        save_data(data)
        print(f"Added ID: {new_id}")

    elif args.command == "rm":
        hw_list = data.get("homework_data", [])
        data["homework_data"] = [h for h in hw_list if h["id"] != args.id]
        save_data(data)
        print("Removed" if len(data["homework_data"]) < len(hw_list) else "Not Found")

    elif args.command == "set":
        k_map = {"close": "enable_close_hw", "log": "enable_logging", "headers": "enable_log_headers"}
        data[k_map[args.key]] = (args.value == "on")
        save_data(data)
        print(f"Set {k_map[args.key]} -> {data[k_map[args.key]]}")

    elif args.command == "import":
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                new_hw = json.load(f)
            if args.overwrite: data["homework_data"] = new_hw
            else: data.setdefault("homework_data", []).extend(new_hw)
            save_data(data)
            print("Imported successfully")
        except Exception as e: print(str(e))

    elif args.command == "export":
        try:
            with open(args.file, 'w', encoding='utf-8') as f:
                json.dump(data.get("homework_data", []), f, ensure_ascii=False, indent=2)
            print("Exported successfully")
        except Exception as e: print(str(e))

if __name__ == "__main__":
    main()