[app]

title = QRQLL Mobile
package.name = qrqllmobile
package.domain = org.qrqll.mobile
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json
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
# 1. gradle_gl_mode=2 强制 GLES 2.0（避免手机不支持 GLES 3.0 导致崩溃）
# 2. enable_androidx 启用 AndroidX 兼容库
# 3. use_surface_view 使用 SurfaceView 替代 TextureView
android.gradle_gl_mode = 2
android.gradle_android_gl_mode = 2
android.use_surface_view = True
android.enable_androidx = True
