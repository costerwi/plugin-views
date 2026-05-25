# $Id$ vim: set modeline foldmethod=marker:

from collections import namedtuple
from datetime import datetime
import os
import sys
from tempfile import TemporaryFile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import viewsCommon
import abaqus
from abaqusConstants import *
import customKernel # for registered list of userViews

xmldoc = None
databaseName = None
Extra = namedtuple('Extra', ['odb', 'step', 'comment'], defaults=['', '', ''])
debug = os.environ.get('DEBUG')

# {{{1 Utility functions ######################################################

if not hasattr(customKernel.RegisteredList, "clear"):
    def clear(self):
        while len(self) > 0:
            self.pop(0)
    customKernel.RegisteredList.clear = clear


def encode(value=0, chars="abcdefghijklmnopqrstuvwxyz"):  # {{{2
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
        maxid = max(26, 2*len(self.ids))
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
        saveObject(attrElement, getattr(viewCut, attr))
    for attr in members:
        attrElement = ET.SubElement(xmlElement, attr)
        saveObject(attrElement, getattr(viewCut, attr))


def saveActiveViewCut(xmlElement, abaqusObject): # {{{2
    "Add child elements to xmlElement to define the active view cut."
    viewCutNames=[]
    for viewCut in abaqusObject.viewCuts.values():
        if viewCut.active:
            vcElement = ET.SubElement(xmlElement, 'ViewCut')
            saveObject(vcElement, viewCut)
            viewCutNames.append(viewCut.name)
    vc = ET.SubElement(xmlElement, 'viewCut')
    if len(viewCutNames):
        e = ET.SubElement(xmlElement, 'viewCutNames')
        e.text = str(viewCutNames)
        vc.text = 'ON'
    else:
        vc.text = 'OFF'


def saveOdbMeta(xmlElement, odbDisplay):   # {{{2
    """Add metadata attributes to odbDisplay element"""
    xmlElement.set('name', os.path.basename(odbDisplay.name))
    stepName = odbDisplay.fieldFrame[0]
    if isinstance(stepName, int):
        odb = abaqus.session.odbs[odbDisplay.name]
        stepName = odb.steps.keys()[stepName]
    xmlElement.set('step', stepName)


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
        saveObject(ET.SubElement(xmlElement, 'contourOptions'), odbDisplay.contourOptions)
    if SYMBOLS_ON_UNDEF in plotState or \
            SYMBOLS_ON_DEF in plotState or \
            ORIENT_ON_UNDEF in plotState or \
            ORIENT_ON_DEF in plotState:
        saveObject(ET.SubElement(xmlElement, 'symbolOptions'), odbDisplay.symbolOptions)
    if len(plotState) > 1:
        saveObject(ET.SubElement(xmlElement, 'superimposeOptions'), odbDisplay.superimposeOptions)

def saveUserSpectrum(xmlElement, sessionObject):  # {{{2
    """Store any custom color spectrum"""
    for spectrum in sessionObject.spectrums.values():
        if spectrum.type == USER_DEFINED:
            xmlSpectrum = ET.SubElement(xmlElement, 'Spectrum')
            xmlSpectrum.set('name', spectrum.name)
            xmlColors = ET.SubElement(xmlSpectrum, 'colors')
            xmlColors.set('type', 'argument')
            xmlColors.text = str(spectrum.colors)

def saveAnnotations(xmlElement, userData):  # {{{2
    "Store current annotations"
    for ann in userData.annotations.values():
        if isinstance(ann, abaqus.ArrowType):
            anElement = ET.SubElement(xmlElement, 'Arrow')
        else:
            anElement = ET.SubElement(xmlElement, 'Text')
        saveObject(anElement, ann)


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
    'Session' : [ saveUserSpectrum ],
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
    'OdbDisplay': [saveOdbMeta, 'display', savePlotStateOptions, 'basicOptions', 'commonOptions',
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

def saveObject(xmlElement, abaqusObject):  # {{{2
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
            saveObject(ET.SubElement(xmlElement, attr),
                    getattr(abaqusObject, attr))


def saveCurrentState(userView, abaqusObjects):  # {{{2
    """Main method called to record everything to an xml userView"""
    saveObject(userView, abaqus.session)  # save some session data
    for abaqusObject in abaqusObjects:
        if isinstance(abaqusObject, abaqus.ViewportType):
            if hasattr(abaqusObject.odbDisplay, 'name'):
                odb = abaqus.session.odbs[abaqusObject.odbDisplay.name]
                if len(odb.userData.annotations):
                    odbElement = ET.SubElement(userView, 'Odb')
                    saveObject(odbElement, odb)
            vpElement = ET.SubElement(userView, 'Viewport')
            saveObject(vpElement, abaqusObject)
    return userView


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
                (name, datestr, odbName, ud) )


# {{{1 Functions to restore a view from the database ##########################

def restoreObject(xmlElement, abaqusObject):
    "Recursively extract xml data and set abaqus values"
    if callable(abaqusObject):
        arguments=xmlElement.attrib.copy()
        for xmlChild in xmlElement:
            if xmlChild.get('type') == 'argument':
                arguments[xmlChild.tag] = eval(restoreObject(xmlChild, None))
        if debug:
            print(xmlElement.tag, "( %r )"%arguments)
        try:
            abaqusObject = abaqusObject(**arguments)
        except Exception as e: # TODO better error checking!
            if debug: print("Exception in restoreObject:", e)
            if 'name' in arguments:
                abaqusObject = abaqusObject(name=arguments['name'])

    setValues = {}
    for xmlChild in xmlElement:
        if xmlChild.get('type') is None:
                abaqusChild = getattr(abaqusObject, xmlChild.tag, None)
                value = restoreObject(xmlChild, abaqusChild)
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

def formatViewRow(zipinfo):  # {{{2
    """Create a ViewRow to be added to customData.userViews"""
    name, ext = os.path.splitext(zipinfo.filename)
    if ext != '.xml':
        return None
    extra = Extra(*((zipinfo.comment or b';;').decode().split(';', 2)))
    return viewsCommon.ViewRow(
        name,
        "{}-{:02}-{:02} {:02}:{:02}:{:02}".format(*zipinfo.date_time),
        extra.odb,
        extra.step,
        extra.comment,
        )

# {{{1 Database functions #########################################

def newView(viewName, viewports):    # {{{2
    "Add a new userView to the xml document"

    userView = ET.Element('userView')
    userView.set('abaqusViewer',
            '%s.%s-%s'%(abaqus.majorVersion, abaqus.minorVersion,
                abaqus.updateVersion))
    userView.set('version', str(viewsCommon.__version__))
    saveCurrentState(userView, viewports)

    extra = Extra()
    odbDisplay = userView.find('Viewport/odbDisplay')
    if odbDisplay is not None:
        extra = extra._replace(odb=os.path.basename(odbDisplay.get('name', '')))
        extra = extra._replace(step=odbDisplay.get('step', ''))
        primary = odbDisplay.find('setPrimaryVariable/variableLabel')
        if primary is not None:
            extra = extra._replace(comment=primary.text)

    now = datetime.now()
    info = ZipInfo(viewName + '.xml', now.timetuple()[:6])
    info.compress_type = ZIP_DEFLATED

    info.comment = ';'.join(extra).encode()  # must be bytes

    if any([viewName == row.name for row in abaqus.session.customData.userViews]):
        deleteViews([viewName])

    with ZipFile(databaseName, mode='a') as database:
        if not database.comment:
            database.comment = 'This is a database of stored view data ' \
                'for the Abaqus CAE view manager plugin.'.encode()
        database.writestr(info, ET.tostring(userView, encoding='unicode'))
    abaqus.session.customData.userViews.append(formatViewRow(info))

def restoreView(viewName, fileName=None):    # {{{2 Restore the specified xml userview Id
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerForm when executing the form command.
    """
    with ZipFile(fileName or databaseName) as database:
        with database.open(viewName + '.xml') as entry:
            userView = ET.fromstring(entry.read().decode())
    assert userView.tag == 'userView'
    for spectrum in userView.findall('Spectrum'):
        restoreObject(spectrum, abaqus.session.Spectrum)
    vps = userView.findall('Viewport')
    vpObject = list(abaqus.session.viewports.values())[0]  # current viewport
    if len(vps) > 1:
        for vpElement in vps:
            vpname = vpElement.get('name')
            if vpname in abaqus.session.viewports:
                vpObject = abaqus.session.viewports[vpname]
            else:
                # Create viewports as necessary for the userView
                odb = abaqus.session.odbs[vpObject.odbDisplay.name]
                vpObject = abaqus.session.Viewport(name=vpname)
                vpObject.setValues(displayedObject=odb)
            restoreObject(vpElement, vpObject)
    elif len(vps) == 1:
        vpElement = vps[0]
        # restoreObject settings to the current viewport
        restoreObject(vpElement, vpObject)
    else:
        print("No viewports defined.")

def restoreAnnotations(viewName):    # {{{2 Restore annotations from the specified xml userview Id
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerDB to restore saved annotations.
    """
    with ZipFile(databaseName) as database:
        with database.open(viewName + '.xml') as entry:
            userView = ET.fromstring(entry.read().decode())
    assert userView.tag == 'userView'
    xmlUserData = userView.find('./Odb/userData')
    if xmlUserData is None:
        print("View does not contain annotations.")
        return

    vpObject = abaqus.session.viewports.values()[0]  # current viewport
    userData = abaqus.session.odbs[vpObject.odbDisplay.name].userData
    restoreObject(xmlUserData, userData)    # XXX only reads first value
    for ann in userData.annotations.values():    # TODO only plot new annotations
        vpObject.plotAnnotation(ann)

def deleteViews(viewNames):   # {{{2 Delete a userview from the database
    """Remove the specified view names from the database."""
    removedRowNumbers = []
    with TemporaryFile() as temp:
        with ZipFile(temp, 'w') as dest_zip, ZipFile(databaseName) as source_zip:
            for i, info in enumerate(source_zip.infolist()): # Iterate over each file in zip
                base, _ = os.path.splitext(info.filename)
                if base in viewNames:
                    removedRowNumbers.append(i)
                    continue  # do not add to dest_zip
                dest_zip.writestr(info, source_zip.read(info))
            dest_zip.comment = source_zip.comment # Copy the comment if available
        if removedRowNumbers:
            temp.seek(0)
            with open(databaseName, 'wb') as out:
                out.write(temp.read())
            for i in sorted(removedRowNumbers, reverse=True):
                abaqus.session.customData.userViews.pop(i)

def setComment(viewName, comment):  # {{{2
    """Set the comment for a view"""
    rowNumber = None
    with TemporaryFile() as temp:
        with ZipFile(temp, 'w') as dest_zip, ZipFile(databaseName) as source_zip:
            for i, (row, info) in enumerate(zip(abaqus.session.customData.userViews, source_zip.infolist())): # Iterate over each file in zip
                base, _ = os.path.splitext(info.filename)
                assert row.name == base, "Database of sync {} != {}".format(row.name, base)
                if base == viewName:  # must match base
                    extra = ';'.join([row.odb, row.step, comment])
                    info.comment = extra.encode()
                    rowNumber = i
                dest_zip.writestr(info, source_zip.read(info))
            dest_zip.comment = source_zip.comment # Copy the ZipFile.comment if available
        if rowNumber is not None:
            temp.seek(0)
            with open(databaseName, 'wb') as out:
                out.write(temp.read())
            oldRow = abaqus.session.customData.userViews.pop(rowNumber)
            abaqus.session.customData.userViews.insert(rowNumber, oldRow._replace(comment=comment))
        else:
            raise KeyError("viewName=" + repr(viewName) + " not found")

def renameView(viewName, newName):   # {{{2 Rename a userview
    """Modify the view name in the database."""
    if viewName == newName:
        return
    rowNumber = None
    removedRowNumbers = []
    with TemporaryFile() as temp:
        with ZipFile(temp, 'w') as dest_zip, ZipFile(databaseName) as source_zip:
            for i, info in enumerate(source_zip.infolist()): # Iterate over each file in zip
                base, _ = os.path.splitext(info.filename)
                if base == viewName:  # must match base
                    info.filename = info.filename.replace(viewName, newName)
                    rowNumber = i
                elif base == newName:
                    removedRowNumbers.append(i)
                    continue  # remove existing view with this name
                dest_zip.writestr(info, source_zip.read(info))
            dest_zip.comment = source_zip.comment # Copy the comment if available
        if rowNumber is not None:
            temp.seek(0)
            with open(databaseName, 'wb') as out:
                out.write(temp.read())
            oldRow = abaqus.session.customData.userViews.pop(rowNumber)
            assert oldRow.name == viewName, "Out of sync {} != {}".format(oldRow.name, viewName)
            abaqus.session.customData.userViews.insert(rowNumber, oldRow._replace(name=newName))
            for i in sorted(removedRowNumbers, reverse=True):
                oldRow = abaqus.session.customData.userViews.pop(i)
                assert oldRow.name == newName, "Out of sync {} != {}".format(oldRow.name, newName)
        else:
            raise KeyError("viewName={:r} not found".format(viewName))

# {{{1 Initialization functions #########################################

def scanDatabase(fileName):  # {{{2
    "Read existing database entries into userViews"
    global databaseName
    databaseName = fileName
    abaqus.session.customData.userViews.clear()
    newRows = []
    try:
        with ZipFile(fileName) as database:
            for info in database.infolist():
                name, ext = os.path.splitext(info.filename)
                if ext != '.xml':
                    continue
                newRows.append(formatViewRow(info))
    except FileNotFoundError:
        pass
    abaqus.session.customData.userViews.extend(newRows)

def init(): # {{{2
    """Create customData.userViews and populate with existing database entries.

    Called by kernelInitString in toolset registration.
    """
    import methodCallback

    def printToFileCallback(callingObject, args, kws, user):
        """Add current view to the database before printing"""
        newView(viewName=kws['fileName'], viewports=kws['canvasObjects'])

    # Add to session.customData
    if not hasattr(abaqus.session.customData, "userViews"):
        abaqus.session.customData.userViews = customKernel.RegisteredList()
        print("Add views each time you Print to File")
        methodCallback.addCallback(type(abaqus.session), 'printToFile',
                printToFileCallback)
    scanDatabase(viewsCommon.databaseName)


