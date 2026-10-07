KHALA JOYBUG
============

What is in this folder
  main.py            the game (Kivy)
  ladybug.png        Khala Joybug
  ladybug_gold.png   Khala while invincible
  spider.png  leaf.png  clover.png  bee.png  thorns.png
  crunch.wav         bite sound
  icon.png           app icon
  buildozer.spec     settings that turn the folder into an Android app
  .github/workflows/build-apk.yml   builds the Android app on GitHub
  art_source/        the editable SVG drawings the PNGs were made from
  character_sheet.png   all the art on one page (not used by the game)

Not included: metal_music.mp3. Drop your own track in this folder with that
exact name and the game plays it on a loop. Without it the game runs silent.

Try it on a computer
  pip install kivy
  python main.py          (arrow keys move Khala)

Make the Android app
  Option A, no computer setup: put this folder in a GitHub repository. The
  workflow builds the .apk (about 30 minutes the first time) and attaches
  it to the repository's "Releases" page.
  Option B, on Linux or WSL:  pip install buildozer  then
  buildozer android debug     (the .apk lands in bin/)

  Then on the phone: open the .apk, allow "install unknown apps" when asked.

Tuning
  Every speed, size, score and spawn rate is in the TUNING NUMBERS block at
  the top of main.py.
