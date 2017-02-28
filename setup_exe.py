from distutils.core import setup
import py2exe


setup(windows=['pws_app.py'], options={'py2exe': {'includes': ['lxml.etree', 'lxml._elementpath', 'gzip']}})
