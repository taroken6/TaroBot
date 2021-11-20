#!C:\Users\audie\PycharmProjects\TaroBot\venv\Scripts\python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'youtube-dl2==2.0','console_scripts','youtube-dl'
__requires__ = 'youtube-dl2==2.0'
import re
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit(
        load_entry_point('youtube-dl2==2.0', 'console_scripts', 'youtube-dl')()
    )
