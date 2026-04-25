[app]

title = QRQLL Mobile
package.name = qrqllmobile
package.domain = org.qrqll.mobile
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json,DroidSansFallback.ttf
version = 1.0.0
requirements = python3,kivy,kivymd,flask,waitress,pyjnius,android
orientation = portrait
fullscreen = 0
author = A6
icon.filename = %(source.dir)s/icon.png

#
# Android specific
#
android.api = 34
android.minapi = 26
android.accept_sdk_license = True
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, FOREGROUND_SERVICE
android.archs = arm64-v8a

# 修复 hwuiTask SIGABRT 渲染崩溃 — OPPO/ColorOS GPU 兼容修复
# gl_mode=2 强制 GLES 2.0（避免手机不支持 GLES 3.0 导致崩溃）
# post_delay=0 禁用 SDL2 的延迟渲染，减少 hwuiTask mutex 竞争
android.gradle_gl_mode = 2
android.gradle_android_gl_mode = 2
android.enable_androidx = True

# SDL2 渲染优化：修复 hwuiTask mutex 崩溃（OPPO/ColorOS 特有）
android.numeric_version = 34
