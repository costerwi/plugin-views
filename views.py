"""Functions called from Abaqus/CAE plugins to manipulate the point of view.

Carl Osterwisch, 2005 vim: set modeline foldmethod=indent fdn=1:
"""

from __future__ import print_function
from abaqus import session
from abaqusConstants import *

import numpy as np
from numpy.linalg import norm  # vector length

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
            np.dot(a, [np.cos(th), norm(vector)*np.sin(th)])
    return a/np.sum(vector*vector)

def getViewportDisplay(viewport=None):
    """Return current viewport and display"""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    display = viewport.odbDisplay
    o = viewport.displayedObject
    if hasattr(o, 'Instance'):
        display = viewport.assemblyDisplay
    elif hasattr(o, 'AutoRepair'):
        display = viewport.partDisplay
    return viewport, display

# {{{1 VIEWS

def alignToDatum(datum):
    print(datum)
    print(dir(datum))
    if hasattr(datum, "normal"):
        alignToPlanar(datum)

def planarFeatures(planar):
    """Extract target and normal from any planar feature"""
    if hasattr(planar, 'getCentroid'):
        target = np.squeeze(planar.getCentroid())
    elif hasattr(planar, 'pointOn'):
        target = np.asarray(planar.pointOn)
    else:
        raise TypeError('Unsupported planar normal', repr(planar))
    if hasattr(planar, 'getNormal'):
        normal = np.asarray(planar.getNormal())
    elif hasattr(planar, 'normal'):
        normal = np.asarray(planar.normal)
    else:
        raise TypeError('Unsupported planar normal', repr(planar))
    return target, normal

def alignToPlanar(planar):
    """Change view to face a planar feature"""
    try:
        target, normal = planarFeatures(planar)
    except TypeError as E:
            print(E)
            return
    viewport = session.viewports[session.currentViewportName]
    viewport.view.setValues(
            cameraTarget=target,
            cameraPosition=target + normal,
            )

def alignToUp(line):
    """Pick a line to align the vertical orientation"""
    viewport = session.viewports[session.currentViewportName]
    print('line', line)
    print(repr(line))
    print(dir(line))

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

def viewSnap(viewport=None):
    """Snap view to closest saved view and closest orthogonal up vector"""
    if not viewport:
        viewport = session.viewports[session.currentViewportName]
    view = viewport.view
    normal = np.asarray(view.cameraTarget) - view.cameraPosition

    # find saved view with normal closest to current view
    maxNormal = (-1000, )
    for savedView in session.views.values():
        savedNormal = np.asarray(savedView.cameraTarget) - savedView.cameraPosition
        dp = np.dot(savedNormal/norm(savedNormal), normal)
        maxNormal = max((dp, savedView, savedNormal), maxNormal)
    dp, newView, newNormal = maxNormal
    print('Snap to', newView.name, 'view')

    # find orthogonal cameraUpVector closest to current view
    upVector = np.asarray(newView.cameraUpVector)
    maxUp = (-1000, )
    for angle in 0, 90, 180, 270:
        dp = np.dot(upVector, view.cameraUpVector)
        maxUp = max((dp, angle, upVector), maxUp)
        upVector = rotateVector(upVector, newNormal, np.pi/2)

    view.setValues(
        cameraPosition = view.cameraTarget - newNormal,
        cameraUpVector = maxUp[2],
        )

def cutViewNormal(viewport=None, cutName="Viewnormal"):
    """Create a cut normal to the current view."""
    viewport, display = getViewportDisplay()
    viewVector = np.array(viewport.view.viewVector)
    if cutName in display.viewCuts:
        viewCut = display.viewCuts[cutName]
        viewCut.setValues(
            normal=-viewVector,
            axis2=np.cross(-viewVector,
                viewport.view.cameraUpVector))
    else:
        viewCut = display.ViewCut(
            name=cutName,
            shape=PLANE,
            origin=viewport.view.cameraTarget,
            normal=-viewVector,
            axis2=np.cross(-viewVector,
                viewport.view.cameraUpVector))
    viewCut.setValues(motion=TRANSLATE, position=0)
    if hasattr(display, 'viewCutNames'):
        display.setValues(viewCutNames=(cutName,), viewCut=ON)
    else:
        display.setValues(activeCutName=cutName, viewCut=ON)

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
            if opt.startswith('_'):
                continue
            optOther = getattr(othervp.odbDisplay, opt)
            try:
                optOther.setValues(getattr(basevp.odbDisplay, opt))
            except (TypeError, AttributeError):
                pass
        if othervp.odbDisplay.name == basevp.odbDisplay.name:
            # Use the same display group if the odbs are the same
            othervp.odbDisplay.setValues(visibleDisplayGroups=(dg, ))
        if othervp.odbDisplay.name != basevp.odbDisplay.name or \
           othervp.odbDisplay.fieldFrame != basevp.odbDisplay.fieldFrame:
            # Use the same field variables if the frames are different
            try:
                othervp.odbDisplay.setDeformedVariable(variableLabel=deformVar[0])
                othervp.odbDisplay.setPrimaryVariable(variableLabel=primVar[0],
                    outputPosition=varPos,
                    refinement=(refType, primVar[5]))
            except Exception as ex:
                print(ex)

        if len(viewCutAttrs):
            if viewCut.name in othervp.odbDisplay.viewCuts:
                del(othervp.odbDisplay.viewCuts[viewCut.name])
            othervc = othervp.odbDisplay.ViewCut(
                name=viewCut.name,
                shape=viewCut.shape,
                origin=viewCut.origin,
                normal=viewCut.normal,
                axis2=viewCut.axis2)
            othervc.setValues(**viewCutAttrs)

def swapVps(basevp=None):
    """ Swap the positions of multiple viewports """
    viewports = [vp for vp in session.viewports.values()
            if MINIMIZED != vp.windowState]
    viewports.sort(key=lambda vp: vp.origin)    # sort by current position
    state = [(vp.origin, vp.width, vp.height) for vp in viewports]
    state.append(state.pop(0)) # shift the values
    for vp, (origin, width, height) in zip(viewports, state):
        vp.setValues(
                origin=origin,
                width=width,
                height=height,
                )

def viewCutNormal(viewport=None):
    """Orient the view to be perpendicular to the active cutting plane."""
    viewport, display = getViewportDisplay(viewport)
    for viewCut in display.viewCuts.values():
        if not viewCut.active:
            continue
        if viewCut.shape != PLANE:
            continue # throw an error here?
        if hasattr(viewCut, 'csysName') and viewCut.csysName:
            # Find the csys which defines this cut
            scratchOdb = session.scratchOdbs[display.name]
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
                normal = rotateVector(normal, axis2, viewCut.angle*np.pi/180)
            else:
                axis3 = np.cross(normal, axis2)
                normal = rotateVector(normal, axis3, viewCut.angle*np.pi/180)
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

def viewCutPlanar(planar, cutName="PlanarCut"):
    """Create a view cut from a planar feature"""
    viewport, display = getViewportDisplay()
    try:
        origin, normal = planarFeatures(planar)
    except TypeError as E:
            print(E)
            return
    for v in (0,1,0), (0,0,1), (1,0,0):
        if abs(np.dot(v, normal)) < 0.5: # Dissimilar directions
            break
    if cutName in display.viewCuts:
        viewCut = display.viewCuts[cutName]
        viewCut.setValues(
            origin = origin,
            normal = normal,
            axis2 = np.cross(v, normal) )
    else:
        viewCut = display.ViewCut(
            name = cutName,
            shape = PLANE,
            origin = origin,
            normal = normal,
            axis2 = np.cross(v, normal) )
    viewCut.setValues(motion=TRANSLATE, position=0)
    display.setValues(activeCutName=cutName, viewCut=ON)

def viewCutPoint(point):
    """Adjust viewCuts to pass through given point"""
    viewport, display = getViewportDisplay()
    if hasattr(point, 'coordinates'):
        xyz = point.coordinates
    else:
        xyz = viewport.displayedObject.getCoordinates(point)
    viewDirection = np.asarray(viewport.view.cameraTarget) - viewport.view.cameraPosition
    bestCut = (-1,)
    for viewCut in display.viewCuts.values():
        if viewCut.shape != PLANE:
            print(viewCut.name, "unsupported shape", viewCut.shape)
            continue
        if viewCut.motion == TRANSLATE:
            pos = np.dot(np.asarray(xyz) - viewCut.origin,
                    viewCut.normal)
            viewCut.setValues(position=float(pos))
        else:
            # TODO ROTATE
            print(viewCut.name, "unsupported motion", viewCut.motion)
        dot = np.dot(viewCut.normal, viewDirection)
        bestCut = max( bestCut, (abs(dot), viewCut) )
        if dot <= 0:
            viewCut.setValues(showModelBelowCut=True, showModelAboveCut=False)
        else:
            viewCut.setValues(showModelBelowCut=False, showModelAboveCut=True)
    if not display.viewCut:
        # Activate the best aligned cut
        display.setValues(viewCutNames=(bestCut[1].name,), viewCut=ON)

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
        # Create enough Viewports to hold all steps
        while 'Viewport: %d'%viewid in session.viewports:
            # Find a unique Viewport name
            viewid += 1
        session.Viewport(name='Viewport: %d'%viewid)
    for (step, vpname) in zip(steps, session.viewports.keys()):
        viewport=session.viewports[vpname]
        viewport.setValues(displayedObject=currentOdb)
        viewport.odbDisplay.setFrame(step.frames[-1])
        print(viewport.name, step.name, step.description, sep='\t')

def viewOdbs():
    """ Create and assign a separate viewport for each open odb. """
    viewid = 1
    while len(session.viewports) < len(session.odbs):
        # Create enough Viewports to hold all odbs
        while 'Viewport: %d'%viewid in session.viewports:
            # Find a unique Viewport name
            viewid += 1
        session.Viewport(name='Viewport: %d'%viewid)
    for (odb, viewport) in zip(
            list(session.odbs.values()), list(session.viewports.values())):
        viewport.setValues(displayedObject=odb)
        print(viewport.name, odb.name, sep='\t')

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

