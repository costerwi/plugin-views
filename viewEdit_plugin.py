"""Define a dialog box to allow manual editing of view direction.

Carl Osterwisch <carl.osterwisch@avlna.com> July 2007
"""

from abaqusGui import *
import abaqusConstants

###########################################################################
# Dialog Box
###########################################################################
class viewEditDB(AFXDataDialog):
    """The view edit dialog box class

    viewEditForm will create an instance of this class when the user requests it.
    """
    
    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self,
                mode=form,
                title="View Edit",
                actionButtonIds=self.OK | self.APPLY | self.DISMISS,
                opts=DIALOG_NORMAL|DECOR_RESIZE)

        va = AFXVerticalAligner(self, opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='fieldOfViewAngle',
                tgt=form.fieldOfViewAngleKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='nearPlane',
                tgt=form.nearPlaneKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='cameraTarget',
                tgt=form.cameraTargetKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='cameraPosition',
                tgt=form.cameraPositionKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='cameraUpVector',
                tgt=form.cameraUpVectorKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='viewOffsetX',
                tgt=form.viewOffsetXKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='viewOffsetY',
                tgt=form.viewOffsetYKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='width',
                tgt=form.widthKw,
                opts=AFXTEXTFIELD_FLOAT|LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='height',
                tgt=form.heightKw,
                opts=AFXTEXTFIELD_FLOAT|LAYOUT_FILL_X)

###########################################################################
# Form
###########################################################################
class viewEditForm(AFXForm):
    "Class to launch the viewEdit dialog box and handle its messages"

    def __init__(self, owner):
        AFXForm.__init__(self, owner) # Construct the base class.
                
        # Commands.
        optionsCmd = AFXGuiCommand(mode=self,
                method='setValues',
                objectName='session.viewports[%s].view',
                registerQuery=TRUE)

        self.fieldOfViewAngleKw = AFXFloatKeyword(
                command=optionsCmd,
                name='fieldOfViewAngle',
                isRequired=FALSE)

        self.nearPlaneKw = AFXFloatKeyword(
                command=optionsCmd,
                name='nearPlane',
                isRequired=FALSE)

        self.cameraTargetKw = AFXTupleKeyword(
                command=optionsCmd,
                name='cameraTarget',
                isRequired=FALSE,
                minLength=3,
                maxLength=3)

        self.cameraPositionKw = AFXTupleKeyword(
                command=optionsCmd,
                name='cameraPosition',
                isRequired=FALSE,
                minLength=3,
                maxLength=3)

        self.cameraUpVectorKw = AFXTupleKeyword(
                command=optionsCmd,
                name='cameraUpVector',
                isRequired=FALSE,
                minLength=3,
                maxLength=3)

        self.viewOffsetXKw = AFXFloatKeyword(
                command=optionsCmd,
                name='viewOffsetX',
                isRequired=FALSE)

        self.viewOffsetYKw = AFXFloatKeyword(
                command=optionsCmd,
                name='viewOffsetY',
                isRequired=FALSE)

        self.widthKw = AFXFloatKeyword(
                command=optionsCmd,
                name='width',
                isRequired=FALSE)

        self.heightKw = AFXFloatKeyword(
                command=optionsCmd,
                name='height',
                isRequired=FALSE)

    def getFirstDialog(self):
        return viewEditDB(self)

###########################################################################
# Register the plugin
###########################################################################
toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(
    buttonText='&Views|&Edit...', 
    object=viewEditForm(toolset),
    author='Carl Osterwisch',
    version=str(0.3),
    applicableModules=abaqusConstants.ALL,
    description='Edit parameters for the current viewport view.',
    )
