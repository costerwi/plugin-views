# $Id$

from abaqusConstants import *
from xml.dom import minidom

def getLeaf(xmlElement, abaqusObject):
    if callable(abaqusObject):
        arguments=dict([ (str(key), str(value))
            for key, value in xmlElement.attributes.items() ])
        for xmlChild in xmlElement.childNodes:
            if xmlChild.ELEMENT_NODE == xmlChild.nodeType and \
                    xmlChild.getAttribute('type') == u'argument':
                        arguments[str(xmlChild.tagName)] = eval(getLeaf(xmlChild, None))
        try:
            abaqusObject = abaqusObject(**arguments)
        except TypeError, msg:
            print repr(abaqusObject), msg
            if arguments.has_key('name'):
                abaqusObject = abaqusObject(name=arguments['name'])
        except VisError, msg:
            print repr(abaqusObject), msg

    setValues = {}
    text = ''
    for xmlChild in xmlElement.childNodes:
        if xmlChild.ELEMENT_NODE == xmlChild.nodeType and \
            not len(xmlChild.getAttribute('type')):
                abaqusChild = getattr(abaqusObject, xmlChild.tagName, None)
                value = getLeaf(xmlChild, abaqusChild)
                if len(value):
                    setValues[str(xmlChild.tagName)] = eval(value)
        elif xmlChild.TEXT_NODE == xmlChild.nodeType:
            text += xmlChild.data

    if len(setValues) and hasattr(abaqusObject, 'setValues'):
        abaqusObject.setValues(**setValues)

    return text.strip()


def setView(xmlUserView):
    vps = xmluserView.getElementsByTagName('Viewport')
    if len(vps) > 1:
        for vpElement in vps:
            getLeaf(vpElement, session) # will create and edit viewports
    else:
        vpElement = vps[0]
        vpObject = session.viewports.values()[0]  # current viewport
        getLeaf(vpElement, vpObject)


dom = minidom.parse('userViews.xml')
assert dom.documentElement.tagName == 'userViews'
setView(dom.getElementsByTagName('userView')[-1]) # find the last userView

