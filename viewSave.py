# $Id$

import abaqusConstants
from xml.dom import minidom
from xml.utils import iso8601 # date/time support

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



def addLeaf(xmlElement, key, value=None, attrs={}):
    leaf = xmlElement.ownerDocument.createElement(key)
    if value:
        leaf.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(value)))
    for k, v in attrs.items():
        leaf.setAttribute(k, v)
    return xmlElement.appendChild(leaf)


def savePlotStateOptions(xmlElement, odbDisplay):
    plotState = odbDisplay.display.plotState
    if DEFORMED in plotState or \
            CONTOURS_ON_DEF in plotState or \
            SYMBOLS_ON_DEF in plotState or \
            ORIENT_ON_DEF in plotState:
        deformedVariable = odbDisplay.deformedVariable[0]
        if len(deformedVariable):
            cmdElement = addLeaf(xmlElement, 'setDeformedVariable')
            addLeaf(cmdElement, 'variableLabel', deformedVariable, {'type': 'argument'})
    if CONTOURS_ON_UNDEF in plotState or \
            CONTOURS_ON_DEF in plotState:
        primVar = odbDisplay.primaryVariable
        if len(primVar[0]):
            varPos = [ UNDEFINED_POSITION, NODAL, INTEGRATION_POINT, ELEMENT_FACE, 
                ELEMENT_NODAL, WHOLE_ELEMENT, ELEMENT_CENTROID, WHOLE_REGION, 
                WHOLE_PART_INSTANCE, WHOLE_MODEL, GENERAL_PARTICLE ][primVar[1]]
            cmdElement = addLeaf(xmlElement, 'setPrimaryVariable')
            addLeaf(cmdElement, 'variableLabel', primVar[0], {'type': 'argument'})
            addLeaf(cmdElement, 'outputPosition', varPos, {'type': 'argument'})
            if primVar[4]:
                refType = [ NO_REFINEMENT, INVARIANT, COMPONENT ][primVar[4]]
                addLeaf(cmdElement, 'refinement',
                        (refType, primVar[5]), {'type': 'argument'})
        savexml(addLeaf(xmlElement, 'contourOptions'), odbDisplay.contourOptions)
    if SYMBOLS_ON_UNDEF in plotState or \
            SYMBOLS_ON_DEF in plotState or \
            ORIENT_ON_UNDEF in plotState or \
            ORIENT_ON_DEF in plotState:
        savexml(addLeaf(xmlElement, 'symbolOptions'), odbDisplay.symbolOptions)
    if len(plotState) > 1:
        savexml(addLeaf(xmlElement, 'superimposeOptions'), odbDisplay.superimposeOptions)
            

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

def saveWindowState(xmlElement, viewport):
    if MAXIMIZED == viewport.windowState:
        xmlElement.appendChild(xmlElement.ownerDocument.createElement('maximize'))
    elif MINIMIZED == viewport.windowState:
        xmlElement.appendChild(xmlElement.ownerDocument.createElement('minimize'))
    elif NORMAL == viewport.windowState:
        xmlElement.appendChild(xmlElement.ownerDocument.createElement('restore'))
    

odbDisplay = session.viewports.values()[0].odbDisplay

attrs = {
    ViewportType: [saveWindowState, 'origin', 'width', 'height', 
        'viewportAnnotationOptions', 'view', 'odbDisplay'],
    ViewType: ['width', 'cameraTarget', 'cameraPosition', 'cameraUpVector'],
    type(odbDisplay): ['display', savePlotStateOptions, 'commonOptions',
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
xmldoc = impl.createDocument(None, "userViews", None)

userview = addLeaf(xmldoc.documentElement, 'userView')
userview.setAttribute('name', 'xyzsdfdf.png')
userview.setAttribute('abaqusViewer',
        '%s.%s-%s'%(majorVersion, minorVersion, updateVersion))
now = iso8601.time.time()
userview.setAttribute('dateTime', iso8601.tostring(now))

vpElement = addLeaf(userview, 'Viewport')

savexml(vpElement, session.viewports.values()[0])

f = open('userViews.xml', 'w')
f.write(xmldoc.toprettyxml())
f.close()

xmldoc.unlink()
