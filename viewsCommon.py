"""This defines variables and methods used by views.py and views_plugin.py

"""

from collections import namedtuple

__version__ = '1.0.0'
helpUrl='https://github.com/costerwi/plugin-views'

databaseName = 'userViews.zip'
ViewRow = namedtuple('ViewRow', ['id', 'name', 'date', 'odb', 'step', 'comment'], defaults=['', ''])
