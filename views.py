"""Various kernel functions called from Abaqus/Viewer plugins to manipulate
the point of view.

Carl Osterwisch, 2005 vim: set modeline foldmethod=indent fdn=1:
$Id$
"""
from abaqus import session
from abaqusConstants import *

try:
    import numpy as np
except ImportError:
    # Abaqus versions < 6.10-ef use the older Numeric module.
    import Numeric as np

    def cross(a, b):
        " Vector cross product as in Matlab "
        return np.array([ a[1]*b[2] - a[2]*b[1],
                          a[2]*b[0] - a[0]*b[2],
                          a[0]*b[1] - a[1]*b[0] ])
    np.cross = cross

def norm(v):
    " Vector length as in Matlab "
    return np.sqrt(np.sum(v*v, axis=-1))

def rotateVector(point, vector, th):
    """Calculate rotation of "point" around arbitrary "vector" by radian angle "th".

    http://www.mines.edu/~gmurray/ArbitraryAxisRotation/ArbitraryAxisRotation.html
    """
    x, y, z = point
    u, v, w = vector
    a = np.array([ [x*(v*v + w*w) - u*(v*y + w*z), -w*y + v*z],
                   [y*(u*u + w*w) - v*(u*x + w*z),  w*x - u*z],
                   [z*(u*u + v*v) - w*(u*x + v*y), -v*x + u*y] ])
    a = point*np.sum(point*vector) + \
            np.dot(a, [cos(th), norm(vector)*sin(th)])
    return a/np.sum(vector*vector)

def behind(viewport=None):
    """Flip the view 180 degrees (look behind)"""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    target = np.array(viewport.view.cameraTarget)
    pos = np.array(viewport.view.cameraPosition)
    viewport.view.setValues(cameraPosition=2*target - pos)

def modelPan(vector, viewport=None):
    """Shift viewing target using model coordinates"""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    target = np.array(viewport.view.cameraTarget)
    pos = np.array(viewport.view.cameraPosition)
    viewport.view.setValues(
            cameraPosition=pos + vector,
            cameraTarget=target + vector)

def cutViewNormal(viewport=None, cutName="Viewnormal"):
    """Create a cut normal to the current view."""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    odbDisplay = viewport.odbDisplay
    viewVector = np.array(viewport.view.viewVector)
    if odbDisplay.viewCuts.has_key(cutName):
        viewCut = odbDisplay.viewCuts[cutName]
        viewCut.setValues(
            normal=-viewVector,
            axis2=np.cross(-viewVector,
                viewport.view.cameraUpVector))
    else:
        viewCut = odbDisplay.ViewCut(
            name=cutName,
            shape=PLANE,
            origin=viewport.view.cameraTarget,
            normal=-viewVector,
            axis2=np.cross(-viewVector,
                viewport.view.cameraUpVector))

def synchVps(basevp=None):
    """ Synchronize all other viewports to the given or current viewport """
    # Updated Aug 2006 for CAE version 6.6
    if not basevp:
        basevp = session.viewports[session.currentViewportName]
    dg = basevp.odbDisplay.displayGroup
    primVar = basevp.odbDisplay.primaryVariable
    varPos = [ UNDEFINED_POSITION, NODAL, INTEGRATION_POINT, ELEMENT_FACE, 
        ELEMENT_NODAL, WHOLE_ELEMENT, ELEMENT_CENTROID, WHOLE_REGION, 
        WHOLE_PART_INSTANCE, WHOLE_MODEL, GENERAL_PARTICLE ][primVar[1]]
    refType = [ NO_REFINEMENT, INVARIANT, COMPONENT ][primVar[4]]
    deformVar = basevp.odbDisplay.deformedVariable
    viewCutAttrs = {}
    for viewCut in basevp.odbDisplay.viewCuts.values():
        if viewCut.active:
            attrs = ['motion', 'showModelAboveCut', 
                    'showModelOnCut', 'showModelBelowCut']
            if TRANSLATE == viewCut.motion:
                attrs.append('position')
            elif ROTATE == viewCut.motion:
                attrs += ['rotationAxis', 'angle']
            if CYLINDER == viewCut.shape or SPHERE == viewCut.shape:
                attrs.append('radius')
            elif ISOSURFACE == viewCut.shape:
                attrs.append('value')
            for attr in attrs:
                viewCutAttrs[attr] = getattr(viewCut, attr)
            break   # Found active viewcut
    for othervp in session.viewports.values():
        if othervp.name == basevp.name:
            # Skip this viewport if it is the base viewport
            continue
        if othervp.windowState == MINIMIZED:
            # Ignore minimized viewports
            continue
        if hasattr(basevp.odbDisplay, 'display'):
            # CAE version >=6.6
            othervp.odbDisplay.display.setValues(
                    plotState=basevp.odbDisplay.display.plotState)
        else:
            # CAE version <6.6
            othervp.odbDisplay.setPlotMode(basevp.odbDisplay.plotMode)

        for opt in ['view', 'viewportAnnotationOptions']:
            optOther = getattr(othervp, opt)
            optOther.setValues(getattr(basevp, opt))
        for opt in [option for option in dir(basevp.odbDisplay) if option.endswith('Options')]:
            optOther = getattr(othervp.odbDisplay, opt)
            try:
                optOther.setValues(getattr(basevp.odbDisplay, opt))
            except TypeError:
                pass
        if othervp.odbDisplay.name == basevp.odbDisplay.name:
            # Use the same display group if the odbs are the same
            othervp.odbDisplay.setValues(visibleDisplayGroups=(dg, ))
        if othervp.odbDisplay.name != basevp.odbDisplay.name or \
           othervp.odbDisplay.fieldFrame != basevp.odbDisplay.fieldFrame:
            # Use the same field variables if the frames are different
            #try:
            othervp.odbDisplay.setPrimaryVariable(variableLabel=primVar[0],
                    outputPosition=varPos,
                    refinement=(refType, primVar[5]))
            othervp.odbDisplay.setDeformedVariable(variableLabel=deformVar[0])
            #except VisError:
            #    pass

        if len(viewCutAttrs):
            if othervp.odbDisplay.viewCuts.has_key(viewCut.name):
                del(othervp.odbDisplay.viewCuts[viewCut.name])
            othervc = othervp.odbDisplay.ViewCut(
                name=viewCut.name,
                shape=viewCut.shape,
                origin=viewCut.origin,
                normal=viewCut.normal,
                axis2=viewCut.axis2)
            othervc.setValues(**viewCutAttrs)

def viewCutNormal(viewport=None):
    """Orient the view to be perpendicular to the active cutting plane."""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    odbDisplay = viewport.odbDisplay
    for viewCut in odbDisplay.viewCuts.values():
        if viewCut.active:
            if viewCut.shape != PLANE:
                continue # throw an error here?
            if viewCut.csysName:
                # Find the csys which defines this cut
                scratchOdb = session.scratchOdbs[odbDisplay.name]
                csys = scratchOdb.rootAssembly.datumCsyses[viewCut.csysName]
                if csys.type != CARTESIAN:
                    continue # throw an error here?
                origin = csys.origin
                if AXIS_1 == viewCut.normal:
                    normal = csys.xAxis
                    axis2 = csys.yAxis
                elif AXIS_2 == viewCut.normal:
                    normal = csys.yAxis
                    axis2 = csys.zAxis
                else:
                    normal = csys.zAxis
                    axis2 = csys.xAxis
            else:
                # cut is defined by points
                origin = np.array(viewCut.origin)
                normal = np.array(viewCut.normal)
                axis2 = np.array(viewCut.axis2)

            if viewCut.motion == ROTATE:
                # cut is rotated by some angle
                if viewCut.rotationAxis == AXIS_2:
                    normal = rotateVector(normal, axis2, viewCut.angle*pi/180)
                else:
                    axis3 = np.cross(normal, axis2)
                    normal = rotateVector(normal, axis3, viewCut.angle*pi/180)
                    axis2 = np.cross(axis3, normal)

            if viewCut.showModelAboveCut and not viewCut.showModelBelowCut:
                # look at the back of the cut
                normal = -1*normal
                axis2 = -1*axis2

            target = viewport.view.cameraTarget
            dist = norm(np.array(viewport.view.cameraPosition) - target)

            viewport.view.setValues(
                    #cameraTarget=origin,
                    cameraPosition=target + dist*normal/norm(normal),
                    cameraUpVector=np.cross(normal, axis2))

            break   # stop searching for the active view cut

def viewSteps():
    """ Create and assign a separate viewport for each analysis step. """
    currentvp = session.viewports[session.currentViewportName]
    currentvp.restore()
    odbname = currentvp.odbDisplay.name
    currentOdb = session.odbs[odbname]
    steps = [step for step in currentOdb.steps.values()
            if len(step.frames) > 0]
    viewid = 1
    while len(session.viewports) < len(steps):
        while session.viewports.has_key('Viewport: %d'%viewid):
            viewid += 1
        session.Viewport(name='Viewport: %d'%viewid)
    sortednames = session.viewports.keys()
    sortednames.sort()
    for (step, vpname) in zip(steps, sortednames):
        viewport=session.viewports[vpname]
        viewport.setValues(displayedObject=currentOdb)
        viewport.odbDisplay.setFrame(step.frames[-1])

def viewOdbs():
    """ Create and assign a separate viewport for each open odb. """
    viewid = 1
    while len(session.viewports) < len(session.odbs):
        while session.viewports.has_key('Viewport: %d'%viewid):
            viewid += 1
        session.Viewport(name='Viewport: %d'%viewid)
    for (odb, viewport) in zip(
            session.odbs.values(), session.viewports.values()):
        viewport.setValues(displayedObject=odb)

def tileVertical():
    """ Arrange visible viewports side-by-side """
    viewports = [vp for vp in session.viewports.values() 
            if MINIMIZED != vp.windowState]
    viewports.sort(key=lambda vp: vp.origin)    # sort by current position
    da = session.drawingArea
    width = da.width/len(viewports)
    previousvp = None
    for i, vp in enumerate(viewports):
        vp.restore()    # ensure windowState is NORMAL (not MAXIMIZED)
        vp.setValues(height = da.height, width = width,
                origin=(i*width + da.origin[0], da.origin[1]))
        # default annotation options
        triad = OFF
        compass = OFF
        legend = ON
        title = ON
        state = ON
        if previousvp and hasattr(previousvp.odbDisplay, 'fieldFrame') and hasattr(vp.odbDisplay, 'fieldFrame'):
            if previousvp.displayedObject == vp.displayedObject:
                title = OFF
                if previousvp.odbDisplay.fieldFrame == vp.odbDisplay.fieldFrame:
                    state = OFF
            legend = previousvp.odbDisplay.primaryVariable != vp.odbDisplay.primaryVariable
            co0 = previousvp.odbDisplay.contourOptions
            co1 = vp.odbDisplay.contourOptions
            for attr in ('maxAutoCompute', 'minAutoCompute', 'contourType',
                    'numIntervals', 'intervalType', 'maxValue', 'minValue'):
                legend |= getattr(co0, attr) != getattr(co1, attr)
            legend |= co0.minAutoCompute | co0.maxAutoCompute

        vp.viewportAnnotationOptions.setValues(
                triad=triad,
                compass=compass,
                legend=legend,
                title=title,
                state=state)
        previousvp = vp
    # special treatment for rightmost viewport
    previousvp.viewportAnnotationOptions.setValues(
            triad=ON, compass=ON)

def resetLayerTransform(viewport=None):
    """Set layer view transforms to something sane (no transform)"""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    for layer in viewport.layers.values():
        layer.view.setLayerTransform(layerTransform=(1, 0, 0, 0,
                                                     0, 1, 0, 0,
                                                     0, 0, 1, 0,
                                                     0, 0, 0, 1))

