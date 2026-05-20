# $Id$ vim: set modeline foldmethod=marker:

from __future__ import print_function
import viewsCommon
import abaqus
from abaqus import session
from abaqusConstants import *
import customKernel # for registered list of userViews
import os
import sys
import xml.etree.ElementTree as ET
try:
    from xml.utils import iso8601 # date/time support
except ImportError:
    import isoDateTime as iso8601

xmldoc = None
xmlFileName = None
debug = os.environ.get('DEBUG')

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
    return ''.join(reversed(converted))


class myElementTree(ET.ElementTree):  # {{{2
    def __init__(self, *args, **kwargs):
        ET.ElementTree.__init__(self, *args, **kwargs)
        self.ids = {}

    def assignUniqueId(self, xmlElement):
        """Return a unique id for this xmlElement, creating one if necessary."""
        import random
        xmlid = xmlElement.get('id')
        existing = self.ids.get(xmlid)
        if existing is not None:
            if existing == xmlElement:
                return xmlid
            # element has an id but it's already in use by another element
            xmlid = None
        maxid = 2*len(self.ids)
        while xmlid is None or xmlid in self.ids:
            intid = random.randint(0, maxid)
            xmlid = encode(intid)
        xmlElement.set('id', xmlid)
        self.ids[xmlid] = xmlElement
        return xmlid

    def getElementById(self, id):
        """Quickly find element by id"""
        element = self.ids.get(id)
        if element is None:
            # initialize the lookup
            for element in self.findall(".//*[@id]"):
                self.ids[element.get("id")] = element
            element = self.ids.get(id)
        return element


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
        attrElement = ET.SubElement(xmlElement, attr)
        attrElement.set('type', 'argument')
        saveXml(attrElement, getattr(viewCut, attr))
    for attr in members:
        attrElement = ET.SubElement(xmlElement, attr)
        saveXml(attrElement, getattr(viewCut, attr))


def saveActiveViewCut(xmlElement, abaqusObject): # {{{2
    "Add child elements to xmlElement to define the active view cut."
    viewCutNames=[]
    for viewCut in abaqusObject.viewCuts.values():
        if viewCut.active:
            vcElement = ET.SubElement(xmlElement, 'ViewCut')
            saveXml(vcElement, viewCut)
            viewCutNames.append(viewCut.name)
    vc = ET.SubElement(xmlElement, 'viewCut')
    if len(viewCutNames):
        e = ET.SubElement(xmlElement, 'viewCutNames')
        e.text = str(viewCutNames)
        vc.text = 'ON'
    else:
        vc.text = 'OFF'


def savePlotStateOptions(xmlElement, odbDisplay):   # {{{2
    "Add child elements to xmlElement depending on the current plotState."
    plotState = odbDisplay.display.plotState
    if DEFORMED in plotState or \
            CONTOURS_ON_DEF in plotState or \
            SYMBOLS_ON_DEF in plotState or \
            ORIENT_ON_DEF in plotState:
        deformedVariable = odbDisplay.deformedVariable[0]
        if len(deformedVariable):
            cmdElement = ET.SubElement(xmlElement, 'setDeformedVariable')
            label = ET.SubElement(cmdElement, 'variableLabel')
            label.set('type', 'argument')
            label.text = repr(deformedVariable)

    if CONTOURS_ON_UNDEF in plotState or \
            CONTOURS_ON_DEF in plotState:
        primVar = odbDisplay.primaryVariable
        if len(primVar[0]):
            varPos = [ UNDEFINED_POSITION, NODAL, INTEGRATION_POINT, ELEMENT_FACE,
                ELEMENT_NODAL, WHOLE_ELEMENT, ELEMENT_CENTROID, WHOLE_REGION,
                WHOLE_PART_INSTANCE, WHOLE_MODEL, GENERAL_PARTICLE ][primVar[1]]
            cmdElement = ET.SubElement(xmlElement, 'setPrimaryVariable')
            label = ET.SubElement(cmdElement, 'variableLabel')
            label.set('type', 'argument')
            label.text = repr(primVar[0])
            pos = ET.SubElement(cmdElement, 'outputPosition')
            pos.set('type', 'argument')
            pos.text = str(varPos)
            if primVar[4]:
                refType = [ NO_REFINEMENT, INVARIANT, COMPONENT ][primVar[4]]
                ref = ET.SubElement(cmdElement, 'refinement')
                ref.set('type', 'argument')
                ref.text = "({}, {!r})".format(refType, primVar[5])
        saveXml(ET.SubElement(xmlElement, 'contourOptions'), odbDisplay.contourOptions)
    if SYMBOLS_ON_UNDEF in plotState or \
            SYMBOLS_ON_DEF in plotState or \
            ORIENT_ON_UNDEF in plotState or \
            ORIENT_ON_DEF in plotState:
        saveXml(ET.SubElement(xmlElement, 'symbolOptions'), odbDisplay.symbolOptions)
    if len(plotState) > 1:
        saveXml(ET.SubElement(xmlElement, 'superimposeOptions'), odbDisplay.superimposeOptions)

def saveAnnotations(xmlElement, userData):  # {{{2
    "Store current annotations"
    for ann in userData.annotations.values():
        if isinstance(ann, abaqus.ArrowType):
            anElement = ET.SubElement(xmlElement, 'Arrow')
        else:
            anElement = ET.SubElement(xmlElement, 'Text')
        saveXml(anElement, ann)


def saveWindowState(xmlElement, viewport):  # {{{2
    "Store whether the viewport is normal or maximized"
    if MAXIMIZED == viewport.windowState:
        ET.SubElement(xmlElement, 'maximize')
    elif MINIMIZED == viewport.windowState:
        ET.SubElement(xmlElement, 'minimize')
    elif NORMAL == viewport.windowState:
        ET.SubElement(xmlElement, 'restore')


def saveColorMode(xmlElement, viewport):  # {{{2
    "Store the viewport colorMode"
    if DEFAULT_COLORS == viewport.colorMode:
        ET.SubElement(xmlElement, 'disableMultipleColors')
        return
    for name, cmap in viewport.colorMappings.items():
        if str(viewport.colorMode).startswith(str(cmap.type)):
            break
    else:
        if debug:
            print('unknown colorMode', viewport.colorMode)
        return
    # TODO
    #ET.SubElement(xmlElement, 'enableMultipleColors')
    if debug:
        print('colorMode', name)


knownObjects = {    # {{{2 What to save from each element type
    'Odb' : [ 'userData' ],
    'UserData': [ saveAnnotations ],
    'Text' : [ 'name', 'box', 'justification', 'referencePoint', 'color', 'text', 'backgroundStyle',
        'rotationAngle', 'backgroundColor', 'offset', 'font', 'anchor' ],
    'Viewport': ['name', saveWindowState, saveColorMode,
        'origin', 'width', 'height',
        'viewportAnnotationOptions', 'view', 'odbDisplay'],
    'View': ['projection',
        'cameraTarget', 'cameraPosition', 'cameraUpVector',
        'width', 'viewOffsetX', 'viewOffsetY'],
    'OdbDisplay': ['name', 'display', savePlotStateOptions, 'basicOptions', 'commonOptions',
        'viewCutOptions', saveActiveViewCut ],
    'ViewCut': [ 'name', saveViewCut ],
    'float' : [],
    'int': [],
    'bool': [],
    'symbolicConstants.AbaqusBoolean': [],
    'symbolicConstants.SymbolicConstant': [],
    }

skipMembers = {
        'autoDeformationScaleValue',
        'autoMaxValue',
        'autoMinValue',
        'fieldOfViewAngle',
        }

def saveXml(xmlElement, abaqusObject):  # {{{2
    "Recursively read abaqus data and store in xmldoc."

    import re

    # Must convert type to string since Abaqus does not define all types
    m = re.search(r"'(?:abaqus\.)?(.+)'", str(type(abaqusObject)))
    typeName = m.group(1)
    if typeName in knownObjects:
        members = knownObjects[typeName]
        if debug:
            print("knownObject %r has members %r"%(typeName, members))
    else:
        # Try to figure out which members to save for this object type
        members = knownObjects.setdefault(typeName, [])
        for a in dir(abaqusObject):
            if not a.startswith('_') \
                    and not a in skipMembers \
                    and not callable(getattr(abaqusObject, a)):
                members.append(a)
        if debug:
            print("unknownObject %r has members %r"%(typeName, members))

    if len(members) == 0:
        # No data members - insert the string value of this object
        xmlElement.text = repr(abaqusObject)
        return
    # Complex type with data members
    for attr in members:
        if debug:
            print("saving member %r"%attr)
        if 'name' == attr:
            xmlElement.set('name', abaqusObject.name)
        elif callable(attr):
            attr(xmlElement, abaqusObject)
        elif hasattr(abaqusObject, attr):
            saveXml(ET.SubElement(xmlElement, attr),
                    getattr(abaqusObject, attr))


def addSessionUserView(xmlView):    # {{{2 Update customData.userViews for the GUI
    "Add a view to the session.customData"
    id = xmldoc.assignUniqueId(xmlView)
    name = xmlView.get('name', 'unknown')
    datestr = xmlView.get('dateTime')
    userData = xmlView.find('./Odb/userData')
    if datestr is not None:
        dateTime = iso8601.parse(datestr)
        localtime = iso8601.time.localtime(dateTime)
        datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
    if userData is not None:
        ud = '*'
    else:
        ud = ''
    for od in xmlView.findall("./Viewport/odbDisplay"):
        odbName = str(od.get('name'))
        abaqus.session.customData.userViews.append(
                (id, name, datestr, odbName, ud) )


# {{{1 Functions to restore a view from the database ##########################

def restoreXml(xmlElement, abaqusObject):
    "Recursively extract xml data and set abaqus values"
    if callable(abaqusObject):
        arguments=xmlElement.attrib.copy()
        for xmlChild in xmlElement:
            if xmlChild.get('type') == 'argument':
                arguments[xmlChild.tag] = eval(restoreXml(xmlChild, None))
        if debug:
            print(xmlElement.tag, "( %r )"%arguments)
        try:
            abaqusObject = abaqusObject(**arguments)
        except Exception as e: # TODO better error checking!
            if debug: print("Exception in restoreXml:", e)
            if 'name' in arguments:
                abaqusObject = abaqusObject(name=arguments['name'])

    setValues = {}
    for xmlChild in xmlElement:
        if xmlChild.get('type') is None:
                abaqusChild = getattr(abaqusObject, xmlChild.tag, None)
                value = restoreXml(xmlChild, abaqusChild)
                if len(value):
                    try:
                        setValues[xmlChild.tag] = eval(value)
                    except AttributeError as e:
                        print(e, repr(value))

    if hasattr(abaqusObject, 'setValues'):
        removed = {}
        while len(setValues):
            if debug:
                print(xmlElement.tag, ".setValues %r"%setValues)
            try:
                abaqusObject.setValues(**setValues)
                if debug and removed:
                    print('removed invalid keywords', removed)
                break  # success!
            except TypeError:
                msg = str(sys.exc_info()[1])
                last = msg.split()[-1]
                if 'keyword error on' in msg and last in setValues:
                    # remove this setting and try again
                    removed[last] = setValues[last]
                    del setValues[last]
                else:
                    print(repr(abaqusObject), xmlElement.tag, msg)
                    break # failed for other reason

    return (xmlElement.text or '').strip()

# {{{1 File access functions ##################################################

def readXmlFile(fileName):  # {{{2
    "Read fileName into xmldoc or create a new xmldoc if necessary"
    global xmldoc, xmlFileName
    if os.path.exists(fileName):
        with open(fileName) as file:
            doc = myElementTree(file=file)
    else:
        # Create a new document
        doc = myElementTree(ET.Element("userViews"))
        doc.changed = 1
    fileType = doc.getroot().tag
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
    for view in xmldoc.getroot().findall("userView"):
        if debug:
            print('view', view.get('name'))
        addSessionUserView(view)


def writeXmlFile(fileName=None): # {{{2
    "Save the xml document to fileName"
    if not hasattr(xmldoc, 'changed'):
        return
    if not fileName:
        fileName=xmlFileName
    bkupName = fileName + '~'
    xmldoc.write(bkupName)
    if os.path.exists(fileName):
        os.remove(fileName)
    os.rename(bkupName, fileName)
    delattr(xmldoc, 'changed')


# {{{1 Abaqus/Viewer plugin functions #########################################

def printToFileCallback(callingObject, args, kws, user):    # {{{2
    "Add a new userView to the xml document"

    userView = ET.SubElement(xmldoc.getroot(), 'userView')
    userView.set('name', kws['fileName'])
    userView.set('abaqusViewer',
            '%s.%s-%s'%(abaqus.majorVersion, abaqus.minorVersion,
                abaqus.updateVersion))
    now = iso8601.time.time()
    userView.set('dateTime', iso8601.tostring(now))
    userView.set('version', str(viewsCommon.__version__))
    xmldoc.assignUniqueId(userView)

    for canvasObject in kws['canvasObjects']:
        if isinstance(canvasObject, abaqus.ViewportType):
            if hasattr(canvasObject.odbDisplay, 'name'):
                odb = abaqus.session.odbs[canvasObject.odbDisplay.name]
                if len(odb.userData.annotations):
                    odbElement = ET.SubElement(userView, 'Odb')
                    saveXml(odbElement, odb)
            vpElement = ET.SubElement(userView, 'Viewport')
            saveXml(vpElement, canvasObject)
    addSessionUserView(userView) # pass to gui
    xmldoc.changed = 1
    writeXmlFile()


def setView(viewId):    # {{{2 Restore the specified xml userview Id
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerForm when executing the form command.
    """
    xmlView = xmldoc.getElementById(viewId)
    if xmlView is None:
        print("View %r not in userViews database."%viewId)
        return
    datestr = xmlView.get('dateTime')
    if datestr:
        dateTime = iso8601.parse(datestr)
        localtime = iso8601.time.localtime(dateTime)
        datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
    print(xmlView.get('name'), datestr)
    vps = xmlView.findall('Viewport')
    vpObject = list(abaqus.session.viewports.values())[0]  # current viewport
    if len(vps) > 1:
        for vpElement in vps:
            vpname = str(vpElement.get('name'))
            if vpname in abaqus.session.viewports:
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
        print("No viewports defined.")

def setAnnotation(viewId):    # {{{2 Restore annotations from the specified xml userview Id
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerDB to restore saved annotations.
    """
    xmlView = xmldoc.getElementById(viewId)
    if not xmlView:
        print("View %r not in userViews database."%viewId)
        return
    datestr = xmlView.get('dateTime')
    if datestr:
        dateTime = iso8601.parse(datestr)
        localtime = iso8601.time.localtime(dateTime)
        datestr = iso8601.time.strftime('%Y-%m-%d %H:%M', localtime)
    print(xmlView.get('name'), datestr)
    xmlUserData = xmlView.find('./Odb/userData')
    if xmlUserData is None:
        print("View does not contain annotations.")
        return

    vpObject = abaqus.session.viewports.values()[0]  # current viewport
    userData = abaqus.session.odbs[vpObject.odbDisplay.name].userData
    restoreXml(xmlUserData, userData)    # XXX only reads first value
    for ann in userData.annotations.values():    # TODO only plot new annotations
        vpObject.plotAnnotation(ann)

def deleteViews(viewIds):   # {{{2 Delete a userview from the database
    "Remove the specified views from the database."
    userViews = xmldoc.getroot()
    for viewId in viewIds:
        userView = xmldoc.getElementById(viewId)
        userViews.remove(userView)
        del xmldoc.ids[viewId]
        xmldoc.changed = 1
    for view in reversed(abaqus.session.customData.userViews):
        if view[0] in viewIds:
            abaqus.session.customData.userViews.remove(view)
    writeXmlFile()

def renameView(viewId, name):   # {{{2 Rename a userview
    "Modify the view name in the database."
    xmlView = xmldoc.getElementById(viewId)
    if xmlView is None:
        print("View %r not in userViews database."%viewId)
    else:
        xmlView.set('name', name)
        views = abaqus.session.customData.userViews
        for rownum, row in enumerate(views):
            if row[0] == viewId:
                copy = list(row)
                copy[1] = name
                views[rownum] = tuple(copy)
        xmldoc.changed = 1
    writeXmlFile()


def init(): # {{{2
    """Retrieve the xml document and initialize customData.userViews.

    Called by kernelInitString in toolset registration.
    """
    import methodCallback

    # Add to session.customData
    if not hasattr(abaqus.session.customData, "userViews"):
        abaqus.session.customData.userViews = customKernel.RegisteredList()
        print(__name__, 'addCallback printToFile')
        methodCallback.addCallback(type(abaqus.session), 'printToFile',
                printToFileCallback)
    readXmlFile(viewsCommon.xmlFileName)


