# $Id$ vim: set modeline foldmethod=marker:

import viewsCommon
import abaqus
from abaqusConstants import *
import customKernel # for registered list of userViews
import os
import sys
from xml.dom import minidom
try:
    from xml.utils import iso8601 # date/time support
except ImportError:
    import isoDateTime as iso8601

xmldoc = None
xmlFileName = None
debug = os.environ.get('DEBUG')
if debug:
    print "viewSave Debug mode is on"

# {{{1 Utility functions ######################################################

def encode(value, chars="abcdefghijklmnopqrstuvwxyz"):  # {{{2
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


def getUniqueId(xmlElement):    # {{{2
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


def addLeaf(xmlElement, key, value=None, attrs={}): # {{{2
    "Return a new child element of xmlElement with optional text value."
    leaf = xmlElement.ownerDocument.createElement(key)
    if value:
        leaf.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(value)))
    for k, v in attrs.items():
        leaf.setAttribute(k, v)
    return xmlElement.appendChild(leaf)


###############################################################################
# {{{1 Functions to save a view in the database ###############################

def saveViewCut(xmlElement, viewCut):   # {{{2
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


def saveActiveViewCut(xmlElement, abaqusObject): # {{{2
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


def savePlotStateOptions(xmlElement, odbDisplay):   # {{{2
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
            

def saveAnnotations(xmlElement, userData):  # {{{2
    "Store current annotations"
    for ann in userData.annotations.values():
        if isinstance(ann, abaqus.ArrowType):
            anElement = addLeaf(xmlElement, 'Arrow')
        else:
            anElement = addLeaf(xmlElement, 'Text')
        saveXml(anElement, ann)


def saveWindowState(xmlElement, viewport):  # {{{2
    "Store whether the viewport is normal or maximized"
    if MAXIMIZED == viewport.windowState:
        addLeaf(xmlElement, 'maximize')
    elif MINIMIZED == viewport.windowState:
        addLeaf(xmlElement, 'minimize')
    elif NORMAL == viewport.windowState:
        addLeaf(xmlElement, 'restore')


knownObjects = {    # {{{2 What to save from each element type
    'Odb' : [ 'userData' ],
    'UserData': [ saveAnnotations ],
    'Text' : [ 'box', 'justification', 'referencePoint', 'color', 'text', 'backgroundStyle',
        'rotationAngle', 'backgroundColor', 'offset', 'font', 'anchor' ],
    'Viewport': [saveWindowState, 'origin', 'width', 'height', 
        'viewportAnnotationOptions', 'view', 'odbDisplay'],
    'View': ['projection',
        'cameraTarget', 'cameraPosition', 'cameraUpVector',
        'width', 'viewOffsetX', 'viewOffsetY'],
    'OdbDisplay': ['display', savePlotStateOptions, 'commonOptions',
        'viewCutOptions', saveActiveViewCut ],
    'ViewCut': [ saveViewCut ],
    'float' : [],
    'int': [],
    }

skipMembers = ['autoDeformationScaleValue', 'autoMaxValue', 'autoMinValue', 'name']
 

def saveXml(xmlElement, abaqusObject):  # {{{2
    "Recursively read abaqus data and store in xml dom."
    if hasattr(abaqusObject, 'name'):
        xmlElement.setAttribute('name', abaqusObject.name)

    # Must convert type to string since Abaqus does not define all types
    typeName = str(type(abaqusObject))[7:-2]
    if knownObjects.has_key(typeName):
        members = knownObjects[typeName]
        if debug:
            print "knownObject %r has members %r"%(typeName, members)
    else:
        # Try to figure out which members to save for this object type
        members = knownObjects.setdefault(typeName, [])
        for a in dir(abaqusObject):
            if not a.startswith('__') \
                    and not a in skipMembers \
                    and not callable(getattr(abaqusObject, a)):
                members.append(a)
        if debug:
            print "unknownObject %r has members %r"%(typeName, members)

    if len(members):
        # Complex type with data members
        for attr in members:
            if callable(attr):
                attr(xmlElement, abaqusObject)
            elif hasattr(abaqusObject, attr):
                saveXml(addLeaf(xmlElement, attr),
                        getattr(abaqusObject, attr))
    else:
        # No data members - insert the string value of this object
        xmlElement.appendChild(
            xmlElement.ownerDocument.createTextNode(repr(abaqusObject)))


def addSessionUserView(xmlView):    # {{{2 Update customData.userViews for the GUI
    "Add a view to the session.customData"
    id = str(getUniqueId(xmlView))
    name = str(xmlView.getAttribute('name'))
    datestr = xmlView.getAttribute('dateTime')
    userData = xmlView.getElementsByTagName('userData')
    if datestr:
        dateTime = iso8601.parse(datestr)
        localtime = iso8601.time.localtime(dateTime)
        datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
    if userData:
        ud = '*'
    else:
        ud = ''
    for od in xmlView.getElementsByTagName("odbDisplay"):
        odbName = str(od.getAttribute('name'))
        abaqus.session.customData.userViews.append(
                (id, name, datestr, odbName, ud) )


# {{{1 Functions to restore a view from the database ##########################

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
        if debug:
            print xmlElement.tagName, "( %r )"%arguments
        try:
            abaqusObject = abaqusObject(**arguments)
        except: # TODO better error checking!
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
        if debug:
            print xmlElement.tagName, ".setValues %r"%setValues
        try:
            abaqusObject.setValues(**setValues)
        except TypeError:
            print xmlElement.tagName, sys.exc_info()[1]

    return text.strip()

# {{{1 File access functions ##################################################

def readXmlFile(fileName):  # {{{2
    "Read fileName into xmldoc or create a new xmldoc if necessary"
    global xmldoc, xmlFileName
    if os.path.exists(fileName):
        doc = minidom.parse(fileName)
    else:
        # Create a new document
        doc = minidom.parseString('<?xml version="1.0" ?>\n'
            '<!DOCTYPE userViews [<!ATTLIST userView id ID #IMPLIED>]>\n'
            '<!-- Saved settings for the View Manager Abaqus plugin -->\n'
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
        doc.changed = 1
    fileType = doc.documentElement.tagName
    if not "userViews" == fileType:
        return abaqus.getWarningReply(
                '%r is not userViews file format'%fileType,
                (abaqus.CANCEL, ))
    writeXmlFile()  # save any updates to the old document
    xmldoc = doc
    xmlFileName = fileName
    # Clear the old list items (if any)
    while len(abaqus.session.customData.userViews) > 0:
        del abaqus.session.customData.userViews[0]
    # Add new views
    for view in xmldoc.getElementsByTagName("userView"):
        addSessionUserView(view)


def writeXmlFile(fileName=None): # {{{2
    "Save the xml document to fileName"
    if not hasattr(xmldoc, 'changed'):
        return
    if not fileName:
        fileName=xmlFileName
    if os.path.exists(fileName):
        bkupName = fileName + '~'
        if os.path.exists(bkupName):
            os.remove(bkupName)
        os.rename(fileName, bkupName)
    open(fileName, 'w').write(xmldoc.toxml())
    delattr(xmldoc, 'changed')


# {{{1 Abaqus/Viewer plugin functions #########################################

def printToFileCallback(callingObject, args, kws, user):    # {{{2
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
            if hasattr(object.odbDisplay, 'name'):
                odb = abaqus.session.odbs[object.odbDisplay.name]
                if len(odb.userData.annotations):
                    odbElement = addLeaf(userView, 'Odb')
                    saveXml(odbElement, odb)
            vpElement = addLeaf(userView, 'Viewport')
            saveXml(vpElement, object)
    addSessionUserView(userView) # pass to gui
    xmldoc.changed = 1
    writeXmlFile()


def setView(viewId):    # {{{2 Restore the specified xml userview Id
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
        vpObject = abaqus.session.viewports.values()[0]  # current viewport
        if len(vps) > 1:
            for vpElement in vps:
                vpname = str(vpElement.getAttribute('name'))
                if abaqus.session.viewports.has_key(vpname):
                    vpObject = abaqus.session.viewports[vpname]
                else:
                    # Create viewports as necessary for the userView
                    odb = abaqus.session.odbs[vpObject.odbDisplay.name]
                    vpObject = abaqus.session.Viewport(name=vpname)
                    vpObject.setValues(displayedObject=odb)
                restoreXml(vpElement, vpObject)
        elif len(vps) == 1:
            vpElement = vps[0]
            # restoreXml settings to the current viewport
            restoreXml(vpElement, vpObject)
        else:
            print "No viewports defined."

def setAnnotation(viewId):    # {{{2 Restore annotations from the specified xml userview Id
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerDB to restore saved annotations.
    """
    xmlView = xmldoc.getElementById(viewId)
    if not xmlView:
        print "View %r not in userViews database."%viewId
        return
    datestr = xmlView.getAttribute('dateTime')
    if datestr:
        dateTime = iso8601.parse(datestr)
        localtime = iso8601.time.localtime(dateTime)
        datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
    print xmlView.getAttribute('name'), datestr
    xmlUserData = xmlView.getElementsByTagName('userData')
    if not xmlUserData:
        print "View does not contain annotations."
        return

    vpObject = abaqus.session.viewports.values()[0]  # current viewport
    userData = abaqus.session.odbs[vpObject.odbDisplay.name].userData
    restoreXml(xmlUserData[0], userData)    # XXX only reads first value
    for ann in userData.annotations.values():    # TODO only plot new annotations
        vpObject.plotAnnotation(ann)

def deleteViews(viewIds):   # {{{2 Delete a userview from the database
    "Remove the specified views from the database."
    for viewId in viewIds:
        xmlView = xmldoc.getElementById(viewId)
        if xmlView:
            xmlView.parentNode.removeChild(xmlView)
            xmlView.unlink()
            xmldoc.changed = 1
        else:
            print "View %r not in userViews database."%viewId
    for view in reversed(abaqus.session.customData.userViews):
        if view[0] in viewIds:
            abaqus.session.customData.userViews.remove(view)

   
def renameView(viewId, name):   # {{{2 Rename a userview
    "Modify the view name in the database."
    xmlView = xmldoc.getElementById(viewId)
    if xmlView:
        xmlView.setAttribute('name', name)
        views = abaqus.session.customData.userViews
        for rownum, row in enumerate(views):
            if row[0] == viewId:
                copy = list(row)
                copy[1] = name
                views[rownum] = tuple(copy)
        xmldoc.changed = 1
    else:
        print "View %r not in userViews database."%viewId


def init(): # {{{2
    """Retrieve the xml document and initialize customData.userViews.

    Called by kernelInitString in toolset registration.
    """
    import methodCallback

    # Add to session.customData
    if not hasattr(abaqus.session.customData, "userViews"):
        abaqus.session.customData.userViews = customKernel.RegisteredList()
    readXmlFile(viewsCommon.xmlFileName)

    print __name__, 'addCallback printToFile'
    methodCallback.addCallback(type(abaqus.session), 'printToFile', 
            printToFileCallback)

