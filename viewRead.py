
from abaqusConstants import *
from xml.dom import minidom



def setView(xmlElement, abaqusObject):
    if callable(abaqusObject):
        arguments=dict([ (str(key), str(value))
            for key, value in xmlElement.attributes.items() ])
        for xmlChild in xmlElement.childNodes:
            if xmlChild.ELEMENT_NODE == xmlChild.nodeType and \
                    xmlChild.getAttribute('type') == u'argument':
                        arguments[str(xmlChild.tagName)] = eval(setView(xmlChild, None))
        try:
            abaqusObject = abaqusObject(**arguments)
        except TypeError:
            abaqusObject = abaqusObject(name=arguments['name'])

    setValues = {}
    text = ''
    for xmlChild in xmlElement.childNodes:
        if xmlChild.ELEMENT_NODE == xmlChild.nodeType and \
                xmlChild.getAttribute('type') != u'argument':
                    abaqusChild = None
                    if hasattr(abaqusObject, xmlChild.tagName):
                        abaqusChild = getattr(abaqusObject, xmlChild.tagName)
                    value = setView(xmlChild, abaqusChild)
                    if len(value):
                        setValues[str(xmlChild.tagName)] = eval(value)
        elif xmlChild.TEXT_NODE == xmlChild.nodeType:
            text += xmlChild.data

    if len(setValues):
        abaqusObject.setValues(**setValues)

    return text.strip()


dom = minidom.parse('test.xml')
assert dom.documentElement.tagName == 'printviews'

p = dom.getElementsByTagName('print')[-1]
vps = p.getElementsByTagName('Viewport')
if len(vps) > 1:
    for vpElement in vps:
        vpObject = session.Viewport(name=str(vpElement.getAttribute('name')))
        setView(vpElement, vpObject)
else:
    vpElement = vps[0]
    vpObject = session.viewports.values()[0]
    setView(vpElement, vpObject)
