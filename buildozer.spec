[app]

title = QRQLL Mobile
package.name = qrqllmobile
package.domain = org.qrqll.mobile
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,txt,json
version = 1.0.1
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

# GPU 兼容 — OPPO/ColorOS
android.gradle_gl_mode = 2
android.gradle_android_gl_mode = 2
android.enable_androidx = True
android.numeric_version = 34
