"""This defines variables and methods used by views.py and views_plugin.py

"""

userFileName = 'userViews.txt'
printFileName = 'printViews.txt'

viewAttrs = ['width', 'cameraTarget', 'cameraPosition', 'cameraUpVector']

def viewData(view, attrs=viewAttrs):
    "Return a string which describes the specfied view"
    return ", ".join(["%s=%s"%(attr, getattr(view, attr)) 
        for attr in viewAttrs])

