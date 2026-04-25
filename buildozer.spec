[app]

title = QRQLL Mobile
package.name = qrqllmobile
package.domain = org.qrqll.mobile
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
version = 1.0.0
requirements = python3,kivy,kivymd,flask==2.3.3,waitress,werkzeug==2.3.7,pyjnius,android
orientation = portrait
fullscreen = 0
author = A6
icon.filename = %(source.dir)s/icon.png

#
# Android specific
#
android.api = 34
android.minapi = 26
android.ndk_path = /mnt/c/Android/sdk/ndk/25.2.9519653
android.accept_sdk_license = True
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, FOREGROUND_SERVICE
android.archs = arm64-v8a

# 修复 hwuiTask GPU 渲染崩溃 — 使用软件渲染/兼容 OpenGL
android.gradle_kivy_use_opengl = False
android.enable_androidx = True
