# $Id$

import viewsCommon
import abaqus
from abaqusConstants import *
import customKernel # for registered list of userViews
import os
from xml.dom import minidom
from xml.utils import iso8601 # date/time support

xmldoc = None

###############################################################################
# Utility functions
###############################################################################

def encode(value, chars="abcdefghijklmnopqrstuvwxyz"):
    "Return the int value encoded into arbitrary base defined by chars."
    if not value:
        return chars[0]
    base = len(chars)
    converted = []
    while(value):
        value, remainder = divmod(value, base)
        converted.append(chars[remainder])
    converted.reverse()
    return ''.join(converted)


def getUniqueId(xmlElement):
    "Return a unique id for this xmlElement, creating one if necessary."
    import random
    id = xmlElement.getAttribute('id')
    if not id:
        doc = xmlElement.ownerDocument
        maxid = 2*len(doc.documentElement.childNodes)
        intid = random.randint(0, maxid)
        id = encode(intid)
        while doc.getElementById(id):
            intid = random.randint(0, maxid)
            id = encode(intid)
        xmlElement.setAttribute('id', id)
    return id


def addLeaf(xmlElement, key, value=None, attrs={}):
    "Return a new child element of xmlElement with optional text value."
    leaf = xmlElement.ownerDocument.createElement(key)
    if value:
        leaf.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(value)))
    for k, v in attrs.items():
        leaf.setAttribute(k, v)
    return xmlElement.appendChild(leaf)


###############################################################################
# Functions to save a view in the database
###############################################################################

def saveViewCut(xmlElement, viewCut):
    "Add child elements to xmlElement which define the viewCut."
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
        saveXml(attrElement, getattr(viewCut, attr))
    for attr in members:
        attrElement = xmlElement.ownerDocument.createElement(attr)
        xmlElement.appendChild(attrElement)
        saveXml(attrElement, getattr(viewCut, attr))


def saveActiveViewCut(xmlElement, abaqusObject):
    "Add child elements to xmlElement to define the active view cut."
    viewCutNames=[]
    for viewCut in abaqusObject.viewCuts.values():
        if viewCut.active:
            vcElement = addLeaf(xmlElement, 'ViewCut')
            saveXml(vcElement, viewCut)
            viewCutNames.append(viewCut.name)
    vc = addLeaf(xmlElement, 'viewCut')
    if len(viewCutNames):
        addLeaf(xmlElement, 'viewCutNames', viewCutNames)
        vc.appendChild(
            xmlElement.ownerDocument.createTextNode('ON'))
    else:
        vc.appendChild(
            xmlElement.ownerDocument.createTextNode('OFF'))


def savePlotStateOptions(xmlElement, odbDisplay):
    "Add child elements to xmlElement depending on the current plotState."
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
        saveXml(addLeaf(xmlElement, 'contourOptions'), odbDisplay.contourOptions)
    if SYMBOLS_ON_UNDEF in plotState or \
            SYMBOLS_ON_DEF in plotState or \
            ORIENT_ON_UNDEF in plotState or \
            ORIENT_ON_DEF in plotState:
        saveXml(addLeaf(xmlElement, 'symbolOptions'), odbDisplay.symbolOptions)
    if len(plotState) > 1:
        saveXml(addLeaf(xmlElement, 'superimposeOptions'), odbDisplay.superimposeOptions)
            

def saveWindowState(xmlElement, viewport):
    "Store whether the viewport is normal or maximized"
    if MAXIMIZED == viewport.windowState:
        addLeaf(xmlElement, 'maximize')
    elif MINIMIZED == viewport.windowState:
        addLeaf(xmlElement, 'minimize')
    elif NORMAL == viewport.windowState:
        addLeaf(xmlElement, 'restore')


knownObjects = {
    'Viewport': [saveWindowState, 'origin', 'width', 'height', 
        'viewportAnnotationOptions', 'view', 'odbDisplay'],
    'View': ['width', 
        'cameraTarget', 'cameraPosition', 'cameraUpVector'],
    'OdbDisplay': ['display', savePlotStateOptions, 'commonOptions',
        saveActiveViewCut ],
    'ViewCut': [ saveViewCut ],
    }

skipMembers = ['autoDeformationScaleValue', 'autoMaxValue', 'autoMinValue']
 

def saveXml(xmlElement, abaqusObject):
    "Recursively read abaqus data and store in xml dom."
    if hasattr(abaqusObject, 'name'):
        xmlElement.setAttribute('name', abaqusObject.name)

    # Must convert type to string since Abaqus does not define all types
    typeName = str(type(abaqusObject))[7:-2]
    if knownObjects.has_key(typeName):
        members = knownObjects[typeName]
    else:
        # Try to figure out which members to save for this object type
        members = knownObjects.setdefault(typeName, [])
        for a in dir(abaqusObject):
            if not a.startswith('__') \
                    and not a in skipMembers \
                    and not callable(getattr(abaqusObject, a)):
                members.append(a)

    if len(members):
        # Complex type with data members
        for attr in members:
            if callable(attr):
                attr(xmlElement, abaqusObject)
            else:
                saveXml(addLeaf(xmlElement, attr),
                        getattr(abaqusObject, attr))
    else:
        # No data members - insert the string value of this object
        xmlElement.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(abaqusObject)))


def addUserView(xmlView):
    "Add a view to the session.customData"
    id = str(getUniqueId(xmlView))
    name = str(xmlView.getAttribute('name'))
    datestr = xmlView.getAttribute('dateTime')
    if datestr:
        dateTime = iso8601.parse(datestr)
        localtime = iso8601.time.localtime(dateTime)
        datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
    for od in xmlView.getElementsByTagName("odbDisplay"):
        odbName = str(od.getAttribute('name'))
        abaqus.session.customData.userViews.append(
                (id, name, datestr, odbName) )


###############################################################################
# Functions to restore a view from the database
###############################################################################

def restoreXml(xmlElement, abaqusObject):
    "Recursively extract xml data and set abaqus values"
    if callable(abaqusObject):
        arguments=dict([ (str(key), str(value))
            for key, value in xmlElement.attributes.items() ])
        for xmlChild in xmlElement.childNodes:
            if xmlChild.ELEMENT_NODE == xmlChild.nodeType and \
                    xmlChild.getAttribute('type') == u'argument':
                        arguments[str(xmlChild.tagName)] = \
                                eval(restoreXml(xmlChild, None))
        try:
            abaqusObject = abaqusObject(**arguments)
        except:
            if arguments.has_key('name'):
                abaqusObject = abaqusObject(name=arguments['name'])

    setValues = {}
    text = ''
    for xmlChild in xmlElement.childNodes:
        if xmlChild.ELEMENT_NODE == xmlChild.nodeType and \
            not len(xmlChild.getAttribute('type')):
                abaqusChild = getattr(abaqusObject, xmlChild.tagName, None)
                value = restoreXml(xmlChild, abaqusChild)
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

def readXmlFile(fileName):
    "Read fileName into xmldoc or create a new xmldoc if necessary"
    if os.path.exists(fileName):
        doc = minidom.parse(fileName)
    else:
        # Create a new document
        doc = minidom.parseString('<?xml version="1.0" ?>\n'
            '<!DOCTYPE userViews [<!ATTLIST userView id ID #IMPLIED>]>\n'
            '<userViews />')
#        impl = minidom.getDOMImplementation()
#        doctype = impl.createDocumentType(
#                qualifiedName="userViews",
#                publicId=None,
#                systemId=None)
#        doctype.internalSubset=u'<!ATTLIST userView id ID #IMPLIED>'
#        doc = impl.createDocument(
#                namespaceURI=None,
#                qualifiedName="userViews",
#                doctype=doctype)
    assert doc.documentElement.tagName == "userViews"
    return doc


def writeXmlFile(fileName=viewsCommon.xmlFileName):
    "Save the xml document to fileName"
    if os.path.exists(fileName):
        bkupName = fileName + '~'
        if os.path.exists(bkupName):
            os.remove(bkupName)
        os.rename(fileName, bkupName)
    open(fileName, 'w').write(xmldoc.toxml())
    #os.remove(bkupName)


def upgradeViews():
    "Upgrade from old text file format"
    import re
    attrre = re.compile('(\w+)=(\(.*?\)|.*?),')
    for fn in (viewsCommon.userFileName, viewsCommon.printFileName):
        if os.path.exists(fn):
            abaqus.milestone('Importing views from %r'%fn)
            dateTime = iso8601.tostring(os.stat(fn).st_mtime)
            odbname=None
            for line in open(fn):
                line = line.strip()
                sp = line.split(';')
                if 1 == len(sp):
                    odbname = sp[0]
                else:
                    userView = addLeaf(xmldoc.documentElement, 'userView')
                    userView.setAttribute('name', sp[0])
                    userView.setAttribute('version', 
                            str(viewsCommon.__version__))
                    userView.setAttribute('dateTime', dateTime)
                    getUniqueId(userView)
                    vpElement = addLeaf(userView, 'Viewport')
                    vpElement.setAttribute('name', 'Viewport: 1')
                    viewElement = addLeaf(vpElement, 'view')
                    for key, value in attrre.findall(sp[1] + ','):
                        leaf = addLeaf(viewElement, key)
                        leaf.appendChild(
                            leaf.ownerDocument.createTextNode(value))

                    odElement = addLeaf(vpElement, 'odbDisplay')
                    odElement.setAttribute('name', odbname)
            os.rename(fn, fn + '~')  # prevent parsing next time
            writeXmlFile()

###############################################################################
# Abaqus/Viewer plugin functions
###############################################################################

def printToFileCallback(callingObject, args, kws, user):
    "Add a new userView to the xml document"

    userView = addLeaf(xmldoc.documentElement, 'userView')
    userView.setAttribute('name', kws['fileName'])
    userView.setAttribute('abaqusViewer',
            '%s.%s-%s'%(abaqus.majorVersion, abaqus.minorVersion,
                abaqus.updateVersion))
    now = iso8601.time.time()
    userView.setAttribute('dateTime', iso8601.tostring(now))
    userView.setAttribute('version', str(viewsCommon.__version__))

    for object in kws['canvasObjects']:
        if isinstance(object, abaqus.ViewportType):
            vpElement = addLeaf(userView, 'Viewport')
            saveXml(vpElement, object)
    addUserView(userView) # pass to gui
    writeXmlFile()


def setView(viewId):
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerForm when executing the form command.
    """
    xmlView = xmldoc.getElementById(viewId)
    if not xmlView:
        print "View %r not in userViews database."%viewId
    else:
        datestr = xmlView.getAttribute('dateTime')
        if datestr:
            dateTime = iso8601.parse(datestr)
            localtime = iso8601.time.localtime(dateTime)
            datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
        print xmlView.getAttribute('name'), datestr
        vps = xmlView.getElementsByTagName('Viewport')
        if len(vps) > 1:
            for vpElement in vps:
                # Create viewports as necessary for the userView
                restoreXml(vpElement, abaqus.session)
        elif len(vps) == 1:
            vpElement = vps[0]
            # restoreXml settings to the current viewport
            vpObject = abaqus.session.viewports.values()[0]  # current viewport
            restoreXml(vpElement, vpObject)
        else:
            print "No viewports defined."

   
def deleteViews(viewIds):
    "Remove the specified views from the database."
    for viewId in viewIds:
        xmlView = xmldoc.getElementById(viewId)
        if xmlView:
            xmlView.parentNode.removeChild(xmlView)
            xmlView.unlink()
        else:
            print "View %r not in userViews database."%viewId
    for view in abaqus.session.customData.userViews:
        if view[0] in viewIds:
            abaqus.session.customData.userViews.remove(view)
    writeXmlFile()

   
def renameView(viewId, name):
    "Modify the view name in the database."
    xmlView = xmldoc.getElementById(viewId)
    if xmlView:
        xmlView.setAttribute('name', name)
        for view in abaqus.session.customData.userViews:
            if view[0] == viewId:
                view[1] = name
    else:
        print "View %r not in userViews database."%viewId
    writeXmlFile()


def init():
    """Retrieve the xml document and initialize customData.userViews.

    Called by kernelInitString in toolset registration.
    """
    import methodCallback
    global xmldoc
    xmldoc = readXmlFile(viewsCommon.xmlFileName)
    upgradeViews()

    # Add to session.customData
    if not hasattr(abaqus.session.customData, "userViews"):
        abaqus.session.customData.userViews = customKernel.RegisteredList()
    for view in xmldoc.getElementsByTagName("userView"):
        addUserView(view)

    print __name__, 'addCallback printToFile'
    methodCallback.addCallback(type(abaqus.session), 'printToFile', 
            printToFileCallback)

