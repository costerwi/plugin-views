# $Id$

def xmlOut(object, attrs):
    line = ''
    for attr in attrs:
        line += "<%s>%s"%(attr, getattr(object, attr))
        line += "</%s>"%attr
    return line
        

def saveView(view):
    attrs = ['width', 'cameraTarget', 'cameraPosition', 'cameraUpVector']
    return '<view>' + xmlOut(view, attrs) + '</view>\n'


def saveViewCut(viewCuts):
    line = ''
    attrs = ['motion', 'showModelAboveCut', 
            'showModelOnCut', 'showModelBelowCut']
    for viewCut in viewCuts.values():
        if viewCut.active:
            if TRANSLATE == viewCut.motion:
                attrs.append('position')
            elif ROTATE == viewCut.motion:
                attrs += ['rotationAxis', 'angle']
            if CYLINDER == viewCut.shape or SPHERE == viewCut.shape:
                attrs.append('radius')
            elif ISOSURFACE == viewCut.shape:
                attrs.append('value')
            line = '<viewCut, name="%s">'%viewCut.name
            line += xmlOut(viewCut, attrs) + '</viewCut>/n'
            break   # Found active viewcut
    return line
    

def saveViewport(viewport):
        
