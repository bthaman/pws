from distutils.core import setup
import py2exe


option = 'console'

if option == 'windows':
    # in windows option, command window is not displayed
    setup(windows=['pws_app.py'], options={'py2exe': {'includes': ['lxml.etree', 'lxml._elementpath', 'gzip']}})
else:
    # in console option, command window is displayed
    setup(console=['pws_app.py'], options={'py2exe': {'includes': ['lxml.etree', 'lxml._elementpath', 'gzip']}})

