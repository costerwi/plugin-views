# $Id$

import viewsCommon
import abaqus
from abaqusConstants import *
import customKernel # for registered list of userViews
import os
from xml.dom import minidom
from xml.utils import iso8601 # date/time support

xmldoc = None
odbDisplay = abaqus.session.viewports.values()[0].odbDisplay

###############################################################################
# Functions to save a view in the database
###############################################################################

def addLeaf(xmlElement, key, value=None, attrs={}):
    leaf = xmlElement.ownerDocument.createElement(key)
    if value:
        leaf.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(value)))
    for k, v in attrs.items():
        leaf.setAttribute(k, v)
    return xmlElement.appendChild(leaf)


def saveViewCut(xmlElement, viewCut):
    arguments = ['shape']
    members = ['showModelAboveCut', 'showModelOnCut', 'showModelBelowCut']
    if PLANE == viewCut.shape:
        arguments += ['normal', 'axis2']
        members.append('motion')
        if TRANSLATE == viewCut.motion:
            members.append('position')
        elif ROTATE == viewCut.motion:
            members += ['rotationAxis', 'angle']
    elif CYLINDER == viewCut.shape:
        arguments.append('cylinderAxis')
        members.append('radius')
    elif SPHERE == viewCut.shape:
        members.append('radius')
    if ISOSURFACE == viewCut.shape:
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
    "Store whether the viewport is normal or maximized"
    if MAXIMIZED == viewport.windowState:
        xmlElement.appendChild(xmlElement.ownerDocument.createElement('maximize'))
    elif MINIMIZED == viewport.windowState:
        xmlElement.appendChild(xmlElement.ownerDocument.createElement('minimize'))
    elif NORMAL == viewport.windowState:
        xmlElement.appendChild(xmlElement.ownerDocument.createElement('restore'))


attrs = {
    abaqus.ViewportType: [saveWindowState, 'origin', 'width', 'height', 
        'viewportAnnotationOptions', 'view', 'odbDisplay'],
    abaqus.ViewType: ['width', 'cameraTarget', 'cameraPosition', 'cameraUpVector'],
    type(odbDisplay): ['display', savePlotStateOptions, 'commonOptions',
        saveActiveViewCut ],
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


def addUserView(name=None):
    "Create a new userView xmlElement with the given name."
    userView = addLeaf(xmldoc.documentElement, 'userView')
    if (name):
        userView.setAttribute('name', name)
    userView.setAttribute('abaqusViewer',
            '%s.%s-%s'%(abaqus.majorVersion, abaqus.minorVersion,
                abaqus.updateVersion))
    now = iso8601.time.time()
    userView.setAttribute('dateTime', iso8601.tostring(now))
    userView.setAttribute('version', str(viewsCommon.__version__))
    return userView

###############################################################################
# Functions to extract a view from the database
###############################################################################

def getLeaf(xmlElement, abaqusObject):
    "Recursively extract xml data and set abaqus values"
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

###############################################################################
# File access functions
###############################################################################

def readXml(fileName=viewsCommon.xmlFileName):
    "Read fileName into xmldoc or create a new xmldoc if necessary"
    global xmldoc
    if os.path.exists(fileName):
        xmldoc = minidom.parse(fileName)
    else:
        # Create a new document
        impl = minidom.getDOMImplementation()
        xmldoc = impl.createDocument(None, "userViews", None)
    assert xmldoc.documentElement.tagName == "userViews"


def saveXml(fileName=viewsCommon.xmlFileName):
    "Save the xml document to fileName"
    if os.path.exists(fileName):
        bkupName = fileName + '~'
        if os.path.exists(bkupName):
            os.remove(bkupName)
        os.rename(fileName, bkupName)
    open(fileName, 'w').write(xmldoc.toxml())
    #os.remove(bkupName)


def upgradeViews():
    "Upgrade from text file format"
    import re
    attrre = re.compile('(\w+)=(\(.*?\)|.*?),')
    for fn in (viewsCommon.userFileName, viewsCommon.printFileName):
        if os.path.exists(fn):
            odbname=None
            for line in open(fn):
                line = line.strip()
                sp = line.split(';')
                if 1 == len(sp):
                    odbname = sp[0]
                else:
                    userview = addUserView(name=sp[0])
                    vpElement = addLeaf(userview, 'Viewport')
                    vpElement.setAttribute('name', 'Viewport: 1')
                    viewElement = addLeaf(vpElement, 'view')
                    for key, value in attrre.findall(sp[1] + ','):
                        addLeaf(viewElement, key, value)

                    odElement = addLeaf(vpElement, 'odbDisplay')
                    odElement.setAttribute('name', odbname)
            os.rename(fn, fn + '~')  # prevent parsing next time
            saveXml()



###############################################################################
# Abaqus/Viewer plugin functions
###############################################################################

def printToFileCallback(callingObject, args, kws, user):
    "Add a new userView to the xml document"

    userView = addUserView(name=kws['fileName'])
    for object in kws['canvasObjects']:
        if isinstance(object, ViewportType):
            vpElement = addLeaf(userView, 'Viewport')
            savexml(vpElement, object)
    session.customData.userViews.append(userView) # pass to gui
    saveXml()


def setView(xmlUserView):
    if isinstance(xmlUserView, int):
        xmlUserView = xmldoc.getElementsByTagName("userView")[xmlUserView]
    vps = xmluserView.getElementsByTagName('Viewport')
    if len(vps) > 1:
        for vpElement in vps:
            getLeaf(vpElement, session) # will create and edit viewports
    else:
        vpElement = vps[0]
        vpObject = session.viewports.values()[0]  # current viewport
        getLeaf(vpElement, vpObject)
   

def init():
    import methodCallback
    print __name__, 'addCallback printToFile'
    methodCallback.addCallback(type(abaqus.session), 'printToFile', 
            printToFileCallback)
    readXml()
    upgradeViews()

    # Add to session.customData
    if not hasattr(abaqus.session.customData, "userViews"):
        abaqus.session.customData.userViews = customKernel.RegisteredList()
    for view in xmldoc.getElementsByTagName("userView"):
        name = view.getAttribute('name')
        date = view.getAttribute('date')
        od = userView.getElementsByTagName("odbDisplay")[0]
        odbName = od.getAttribute('name')
        abaqus.session.customData.userViews.append( (name, date, odbName) )

