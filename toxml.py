# $Id$

import os
import re
from xml.dom import minidom
from xml.utils import iso8601 # date/time support

def addLeaf(xmlElement, key, value=None, attrs={}):
    leaf = xmlElement.ownerDocument.createElement(key)
    if value:
        leaf.appendChild(
            xmlElement.ownerDocument.createTextNode(value))
    for k, v in attrs.items():
        leaf.setAttribute(k, v)
    return xmlElement.appendChild(leaf)

xmlfn = 'userViews.xml'
if os.path.exists(xmlfn):
    xmldoc = minidom.parse(xmlfn)
else:
    impl = minidom.getDOMImplementation()
    xmldoc = impl.createDocument(None, "userViews", None)

attrre = re.compile('(\w+)=(\(.*?\)|.*?),')
for fn in ('userViews.txt', 'printViews.txt'):
    if os.path.exists(fn):
        odbname=None
        for line in open(fn):
            line = line.strip()
            sp = line.split(';')
            if 1 == len(sp):
                odbname = sp[0]
            else:
                userview = addLeaf(xmldoc.documentElement, 'userView')
                userview.setAttribute('name', sp[0])
                userview.setAttribute('abaqusViewer', '6.6-2')
                now = iso8601.time.time()
                userview.setAttribute('dateTime', iso8601.tostring(now))

                vpElement = addLeaf(userview, 'Viewport')
                vpElement.setAttribute('name', 'Viewport: 1')
                viewElement = addLeaf(vpElement, 'view')
                for key, value in attrre.findall(sp[1] + ','):
                    addLeaf(viewElement, key, value)

                odElement = addLeaf(vpElement, 'odbDisplay')
                odElement.setAttribute('name', odbname)

f = open(xmlfn, 'w')
f.write(xmldoc.toxml())
f.close()
xmldoc.unlink()
