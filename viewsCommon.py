"""This defines variables and methods used by views.py and views_plugin.py

"""

from collections import namedtuple

__version__ = '1.0.0'
helpUrl='https://github.com/costerwi/plugin-views'

databaseName = 'savedViews.zip'
ViewRow = namedtuple('ViewRow', ['name', 'date', 'odb', 'step', 'description'])
