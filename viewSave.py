# $Id$ vim: set modeline foldmethod=marker:

from collections import namedtuple
from datetime import datetime
import os
import sys
import re
from tempfile import TemporaryFile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import viewsCommon
import abaqus
from abaqusConstants import *
import customKernel # for registered list of userViews

xmldoc = None
databaseName = None
Extra = namedtuple('Extra', ['odb', 'step', 'description'], defaults=['', '', ''])
debug = os.environ.get('DEBUG')

# {{{1 Utility functions ######################################################

if not hasattr(customKernel.RegisteredList, "clear"):
    def clear(self):
        while len(self) > 0:
            self.pop(0)
    customKernel.RegisteredList.clear = clear

def saferEval(string):  # {{{2
    """Check for trouble before eval"""
    assert re.search(r'\w\(', string) == None, "Detected possible method call {!r}".format(string)
    return eval(string)

def intRanges(intList):
    """Yield ranges of continuous sequences within list of integers

    >>> list(ranges([10,11,12,1,2,3,4,17,18,20]))
    [(1, 4), (10, 12), (17, 18), (20, 20)]
    """

    sortedInts = sorted(intList)
    lower = 0 # lower index
    while lower < len(sortedInts):
        upper = lower # begin binary search to find upper index
        boundary = len(sortedInts) # index of too high
        while boundary > upper + 1:
            mid = (upper + boundary)//2 # middle index
            while sortedInts[mid] - sortedInts[upper] > mid - upper:
                boundary = mid
                mid = (upper + boundary)//2
            upper = mid
        yield sortedInts[lower], sortedInts[upper]
        lower = upper + 1

def intListToString(intList):
    """Convert list of ints to compact string

    >>> intListToString([10,11,12,1,2,3,4,17,18,20])
    '1:4 10:12 17 18 20'
    """

    strList = []
    for lower, upper in intRanges(intList):
        if lower == upper:
            strList.append(str(lower))
        elif lower + 1 == upper:
            # adjacent ints listed separately
            strList.append('%d %d'%(lower, upper))
        else:
            # range of ints
            strList.append('%d:%d'%(lower, upper))
    return ' '.join(strList)

def stringToIntList(strList):
    """Convert string to list of ints

    >>> stringToIntList('1:4 10:12 17 18 20')
    [1, 2, 3, 4, 10, 11, 12, 17, 18, 20]
    """
    intList = []
    for i in strList.split():
        if not ':' in i:
            intList.append(int(i))
        else:
            # expand range
            lower, upper = i.split(':')
            intList.extend(range(int(lower), int(upper) + 1))
    return intList

class InstSet(dict):  # {{{2
    """Class for working with sets defined across multiple instances"""
    def __init__(self, other):
        super().__init__()
        for InstName, value in other.items():
            self[InstName] = set(value)

    def __len__(self):
        return sum(len(value) for value in self.values())

    def issubset(self, other):
        for instName, value in self.items():
            if not value.issubset(other.get(instName, set())):
                return False
        return True

    def __str__(self):
        s = []
        for instName, value in self.items():
            s.append("{} [{}]".format(instName, len(value)))
        return '\n'.join(s)

    def difference_update(self, other):
        empty = []
        for instName, value in self.items():
            value -= other.get(instName, set())
            if not(value):
                empty.append(instName)
        for instName in empty:
            del self[instName]

    def union_update(self, other):
        for instName, value in self.items():
            value += other.get(instName, set())
        for instName, value in other.items():
            if not instName in self:
                self[instName] = value

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


def saveDisplayGroup(xmlElement, viewport):  # {{{2
    """Try to determine named sets to define current element display group"""

    odbDisplayElement = xmlElement.find("odbDisplay")
    if odbDisplayElement is None: return  # must already exist
    xmlElement = ET.SubElement(odbDisplayElement, "displayGroup")

    rootAssembly = abaqus.session.odbs[viewport.odbDisplay.name].rootAssembly
    odbData = abaqus.session.odbData[viewport.odbDisplay.name]

    odbDisplay = viewport.odbDisplay
    viewCut = odbDisplay.viewCut
    odbDisplay.setValues(viewCut=OFF)  # turn off temporarily
    displaySet = InstSet(viewport.getActiveElementLabels())
    odbDisplay.setValues(viewCut=viewCut)

    # check for all
    elset = InstSet(odbData.elementSets[' ALL ELEMENTS'].elements)
    if elset.issubset(displaySet):
        dg = ET.SubElement(xmlElement, "all")
        return

    # check whole instances
    for instName, elements in displaySet.items():
        if len(elements) == len(rootAssembly.instances[instName].elements):
            dg = ET.SubElement(xmlElement, "instance")
            dg.set('name', instName)
            elements.clear()

    # check for adding sets, largest to smallest
    elsets = [(name, InstSet(elset.elements)) for name, elset in odbData.elementSets.items()]
    elsets.sort(key=lambda s: len(s[1]), reverse=True)  # largest to smallest
    for name, elset in elsets:
        if elset.issubset(displaySet):
            dg = ET.SubElement(xmlElement, "elset")
            dg.set('name', name)
            displaySet.difference_update(elset)

    # TODO check for removing sets, largest to smallest

    # record list of whatever individual element labels are remaining
    for instName, value in displaySet.items():
        if len(value) == 0:
            continue
        dg = ET.SubElement(xmlElement, "element")
        dg.set('instance', instName)
        dg.set('instanceElems', str(len(rootAssembly.instances[instName].elements)))
        dg.text = intListToString(value)

###############################################################################
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
        'viewportAnnotationOptions', 'view', 'odbDisplay', saveDisplayGroup],
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


def saveCurrentState(userView, viewports):  # {{{2
    """Main method called to record everything to an xml userView"""
    saveObject(userView, abaqus.session)  # save some session data
    for abaqusObject in viewports:
        if isinstance(abaqusObject, abaqus.ViewportType):
            if hasattr(abaqusObject.odbDisplay, 'name'):
                odb = abaqus.session.odbs[abaqusObject.odbDisplay.name]
                if len(odb.userData.annotations):
                    odbElement = ET.SubElement(userView, 'Odb')
                    saveObject(odbElement, odb)
            vpElement = ET.SubElement(userView, 'Viewport')
            saveObject(vpElement, abaqusObject)
    return userView


# {{{1 Functions to restore a view from the database ##########################
def restoreDisplayGroup(xmlElement, displayGroup):  # {{{2
    import displayGroupOdbToolset as dgo
    first = True
    for leafElement in xmlElement:
        try:
            if leafElement.tag == 'all':
                leaf = dgo.Leaf(leafType=DEFAULT_MODEL)
            elif leafElement.tag == 'element':
                # TODO if str(len(inst.elements)) != leafElement.get('instanceElems'):
                leaf = dgo.LeafFromModelElemLabels(elementLabels=(
                    (leafElement.get('instance'), stringToIntList(leafElement.text)), ))
            elif leafElement.tag == 'elset':
                leaf = dgo.LeafFromElementSets(elementSets=(leafElement.get('name'),))
            elif leafElement.tag == 'instance':
                leaf = dgo.LeafFromPartInstance(partInstanceName=(leafElement.get('name'),))
            elif leafElement.tag == 'material':
                leaf = dgo.LeafFromElementMaterials(elementMaterials=(leafElement.get('name'),))
            elif leafElement.tag == 'section':
                leaf = dgo.LeafFromElementSections(elementSections=(leafElement.get('name'),))
            else:
                print(leafElement.tag, 'unsupported')
                continue  # unsupported type
        except ValueError:
            raise
        method = leafElement.get('method', 'add')
        if method == 'add' and first:
            displayGroup.replace(leaf=leaf)
            first = False
        elif method == 'add':
            displayGroup.add(leaf=leaf)
        elif method == 'remove':
            displayGroup.remove(leaf=leaf)
        elif method == 'replace':
            displayGroup.replace(leaf=leaf)
    return ''

def restoreObject(xmlElement, abaqusObject):  # {{{2
    """Recursively extract xml data and set abaqus values"""

    if xmlElement.tag == 'displayGroup':
        return restoreDisplayGroup(xmlElement, abaqusObject)

    if callable(abaqusObject):
        arguments=xmlElement.attrib.copy()
        for xmlChild in xmlElement:
            if xmlChild.get('type') == 'argument':
                arguments[xmlChild.tag] = saferEval(restoreObject(xmlChild, None))
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
                        setValues[xmlChild.tag] = saferEval(value)
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
    extra = Extra(*((zipinfo.comment or b'\t\t').decode().split('\t', 2)))
    return viewsCommon.ViewRow(
        name,
        "{}-{:02}-{:02} {:02}:{:02}:{:02}".format(*zipinfo.date_time),
        extra.odb,
        extra.step,
        extra.description,
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
        description = []
        primary = odbDisplay.find('setPrimaryVariable/variableLabel')
        if primary is not None:
            description.append(saferEval(primary.text))
        refinement = odbDisplay.find('setPrimaryVariable/refinement')
        if refinement is not None:
            description.append(saferEval(refinement.text)[1])
        extra = extra._replace(description=' '.join(description))

    now = datetime.now()
    info = ZipInfo(viewName + '.xml', now.timetuple()[:6])
    info.compress_type = ZIP_DEFLATED

    info.comment = '\t'.join(extra).encode()  # must be bytes

    if any([viewName == row.name for row in abaqus.session.customData.userViews]):
        deleteViews([viewName])

    with ZipFile(databaseName, mode='a') as database:
        if not database.comment:
            database.comment = 'This is a database of stored view data ' \
                'for the Abaqus CAE View Manager plugin.'.encode()
        database.writestr(info, ET.tostring(userView, encoding='unicode'))
    abaqus.session.customData.userViews.append(formatViewRow(info))

def restoreView(viewName, fileName=None, reprint=False):    # {{{2 Restore the specified viewName
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerForm when executing the form command.
    """
    with ZipFile(fileName or databaseName) as database:
        with database.open(viewName + '.xml') as entry:
            userView = ET.fromstring(entry.read().decode())
    assert userView.tag == 'userView', "Not a saved userView"
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

def restoreAnnotations(viewName):    # {{{2 Restore annotations from the specified viewName
    """Retrieve the xmlElement for the identified userView.

    Called by viewManagerDB to restore saved annotations.
    """
    with ZipFile(databaseName) as database:
        with database.open(viewName + '.xml') as entry:
            userView = ET.fromstring(entry.read().decode())
    assert userView.tag == 'userView', "Not a saved userView"
    xmlUserData = userView.find('./Odb/userData')
    if xmlUserData is None:
        print("View does not contain annotations.")
        return

    vpObject = abaqus.session.viewports.values()[0]  # current viewport
    userData = abaqus.session.odbs[vpObject.odbDisplay.name].userData
    restoreObject(xmlUserData, userData)    # XXX only reads first value
    for ann in userData.annotations.values():    # TODO only plot new annotations
        vpObject.plotAnnotation(ann)

def deleteViews(viewNames):   # {{{2 Delete a list of viewNames from the database
    """Remove the specified view names from the database."""
    removeRowNumbers = []
    for i, row in enumerate(abaqus.session.customData.userViews):
        if row.name in viewNames:
            removeRowNumbers.append(i)
    for i in reversed(removeRowNumbers):
        abaqus.session.customData.userViews.pop(i)
    modified = False
    with TemporaryFile() as temp:
        with ZipFile(temp, 'w') as dest_zip, ZipFile(databaseName) as source_zip:
            for info in source_zip.infolist(): # Iterate over each file in zip
                base, ext = os.path.splitext(info.filename)
                if base in viewNames and ext == '.xml':
                    modified = True
                    continue  # do not add to dest_zip
                dest_zip.writestr(info, source_zip.read(info))
            dest_zip.comment = source_zip.comment # Copy the comment if available
        if modified:
            temp.seek(0)
            with open(databaseName, 'wb') as out:
                out.write(temp.read())
        else:
            scanDatabase()
            raise KeyError("viewNames {!r} not found in database".format(viewNames))

def setDescription(viewName, description):  # {{{2
    """Set the description for a view"""
    for i, row in enumerate(abaqus.session.customData.userViews):
        if row.name == viewName:
            oldRow = abaqus.session.customData.userViews.pop(i)
            abaqus.session.customData.userViews.insert(i, oldRow._replace(description=description))
            break
    else:
        scanDatabase()
        raise KeyError("viewName {!r} not found in userViews".format(viewName))
    with TemporaryFile() as temp:
        with ZipFile(temp, 'w') as dest_zip, ZipFile(databaseName) as source_zip:
            for info in source_zip.infolist(): # Iterate over each file in zip
                base, ext = os.path.splitext(info.filename)
                if base == viewName and ext == '.xml':  # must match base
                    extra = '\t'.join([row.odb, row.step, description])
                    info.comment = extra.encode()
                    rowNumber = i
                dest_zip.writestr(info, source_zip.read(info))
            dest_zip.comment = source_zip.comment # Copy the ZipFile.comment if available
        temp.seek(0)
        with open(databaseName, 'wb') as out:
            out.write(temp.read())

def renameView(viewName, newName):   # {{{2 Rename a userview
    """Modify the view name in the database."""
    if viewName == newName:
        return
    for i, row in enumerate(abaqus.session.customData.userViews):
        if row.name == viewName:
            oldRow = abaqus.session.customData.userViews.pop(i)
            abaqus.session.customData.userViews.insert(i, oldRow._replace(name=newName))
            break
    else:
        scanDatabase()
        raise KeyError("viewName {!r} not found in userViews".format(viewName))
    with TemporaryFile() as temp:
        with ZipFile(temp, 'w') as dest_zip, ZipFile(databaseName) as source_zip:
            for info in source_zip.infolist(): # Iterate over each file in zip
                base, ext = os.path.splitext(info.filename)
                if ext == '.xml':
                    if base == viewName:  # must match base
                        info.filename = info.filename.replace(viewName, newName)
                    elif base == newName:
                        continue  # remove existing view with this name
                dest_zip.writestr(info, source_zip.read(info))
            dest_zip.comment = source_zip.comment # Copy the comment if available
        temp.seek(0)
        with open(databaseName, 'wb') as out:
            out.write(temp.read())

# {{{1 Initialization functions #########################################

def scanDatabase(fileName=None):  # {{{2
    "Read existing database entries into userViews"
    global databaseName
    databaseName = fileName or databaseName
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
        print("Views will be added for each Print to File")
        methodCallback.addCallback(type(abaqus.session), 'printToFile',
                printToFileCallback)
    scanDatabase(viewsCommon.databaseName)


