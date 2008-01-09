# $Id$

import abaqusConstants
from xml.dom import minidom

def saveRepository(xmlElement, repository):
    xmlElement.setAttribute('type', 'Repository')
    if len(repository):
        itemType = str(type(repository.values()[0]))[7:-2]
    for name, item in repository.items():
        itemElement = xmlElement.ownerDocument.createElement(itemType)
        xmlElement.appendChild(itemElement)
        savexml(itemElement, item)

def saveViewCut(xmlElement, viewCut):
    arguments = ['shape']
    members = ['showModelAboveCut', 'showModelOnCut', 'showModelBelowCut']
    if abaqusConstants.PLANE == viewCut.shape:
        arguments += ['normal', 'axis2']
        members.append('motion')
        if abaqusConstants.TRANSLATE == viewCut.motion:
            members.append('position')
        elif abaqusConstants.ROTATE == viewCut.motion:
            members += ['rotationAxis', 'angle']
    elif abaqusConstants.CYLINDER == viewCut.shape:
        arguments.append('cylinderAxis')
        members.append('radius')
    elif abaqusConstants.SPHERE == viewCut.shape:
        members.append('radius')
    if abaqusConstants.ISOSURFACE == viewCut.shape:
        members.append('value')
    else:
        if len(viewCut.csysName):
            arguments.append('csysName') #TODO: make sure this exists
        else:
            arguments.append('origin')
    for attr in arguments:
        attrElement = xmlElement.ownerDocument.createElement(attr)
        attrElement.setAttribute('type', 'argument')
        xmlElement.appendChild(attrElement)
        savexml(attrElement, getattr(viewCut, attr))
    for attr in members:
        attrElement = xmlElement.ownerDocument.createElement(attr)
        xmlElement.appendChild(attrElement)
        savexml(attrElement, getattr(viewCut, attr))


def saveActiveViewCut(xmlElement, abaqusObject):
    viewCutNames=[]
    for viewCut in abaqusObject.viewCuts.values():
        if viewCut.active:
            vcElement = xmlElement.ownerDocument.createElement('ViewCut')
            xmlElement.appendChild(vcElement)
            savexml(vcElement, viewCut)
            viewCutNames.append(viewCut.name)
    vc = xmlElement.ownerDocument.createElement('viewCut')
    if len(viewCutNames):
        e = xmlElement.ownerDocument.createElement('viewCutNames')
        xmlElement.appendChild(e)
        e.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(viewCutNames)))
        vc.appendChild(
            xmlElement.ownerDocument.createTextNode('ON'))
    else:
        vc.appendChild(
            xmlElement.ownerDocument.createTextNode('OFF'))
    xmlElement.appendChild(vc)


    

odbDisplay = session.viewports.values()[0].odbDisplay

attrs = {
    ViewportType: ['origin', 'width', 'height', 
        'viewportAnnotationOptions', 'view', 'odbDisplay'],
    ViewType: ['width', 'cameraTarget', 'cameraPosition', 'cameraUpVector'],
    type(odbDisplay): ['commonOptions', 'contourOptions', 'display',
        saveActiveViewCut ],
    type(session.viewports): [ saveRepository ],   # Repository type
    type(odbDisplay.viewCuts.values()[0]): [ saveViewCut ],
    }

skip = ['autoDeformationScaleValue', 'autoMaxValue', 'autoMinValue']

def savexml(xmlElement, abaqusObject):
    if hasattr(abaqusObject, 'name'):
        xmlElement.setAttribute('name', abaqusObject.name)

    if not attrs.has_key(type(abaqusObject)):
        # Try to figure out which members to save
        members = attrs.setdefault(type(abaqusObject), [])
        for a in dir(abaqusObject):
            if not a.startswith('__') \
                    and not a in skip \
                    and not callable(getattr(abaqusObject, a)):
                members.append(a)

    members = attrs[type(abaqusObject)]
    if len(members):
        # Complex type with data members
        for attr in members:
            if callable(attr):
                attr(xmlElement, abaqusObject)
            else:
                attrObject = getattr(abaqusObject, attr)
                attrElement = xmlElement.ownerDocument.createElement(attr)
                xmlElement.appendChild(attrElement)
                savexml(attrElement, attrObject)
    else:
        # No data members
        xmlElement.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(abaqusObject)))
        
impl = minidom.getDOMImplementation()
xmldoc = impl.createDocument(None, "printviews", None)
top_element = xmldoc.documentElement

printElement = xmldoc.createElement('print')
printElement.setAttribute('name', 'xyzsdfdf.png')
xmldoc.documentElement.appendChild(printElement)

vpElement = xmldoc.createElement('Viewport')
printElement.appendChild(vpElement)

savexml(vpElement, session.viewports.values()[0])

f = open('test.xml', 'w')
f.write(xmldoc.toprettyxml())
f.close()

xmldoc.unlink()
