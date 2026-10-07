[app]
title = Khala Joybug
package.name = khalajoybug
package.domain = org.joybug
source.dir = .
source.include_exts = py,png,wav,mp3
source.exclude_dirs = art_source,.github,bin,.buildozer
source.exclude_patterns = character_sheet.png
version = 1.0
requirements = python3,kivy
icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 1
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
