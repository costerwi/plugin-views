"""Define a dialog box to allow manual editing of viewport parameters.

Carl Osterwisch <costerwi@gmail.com> November 2012
$Id$
"""

from abaqusGui import *
import abaqusConstants

__version__ = 0.1

###########################################################################
# Dialog Box
###########################################################################
class viewportEditDB(AFXDataDialog):
    """The view edit dialog box class

    viewportEditForm will create an instance of this class when the user requests it.
    """
    
    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self,
                mode=form,
                title="Viewport Edit",
                actionButtonIds=self.OK | self.APPLY | self.DISMISS,
                opts=DIALOG_NORMAL|DECOR_RESIZE)

        va = AFXVerticalAligner(self, opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='origin',
                tgt=form.originKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='width',
                tgt=form.widthKw,
                opts=LAYOUT_FILL_X)

        AFXTextField(
                p=va,
                ncols=10,
                labelText='height',
                tgt=form.heightKw,
                opts=LAYOUT_FILL_X)

###########################################################################
# Form
###########################################################################
class viewportEditForm(AFXForm):
    "Class to launch the viewportEdit dialog box and handle its messages"

    def __init__(self, owner):
        AFXForm.__init__(self, owner) # Construct the base class.
                
        # Commands.
        optionsCmd = AFXGuiCommand(mode=self,
                method='setValues',
                objectName='session.viewports[%s]',
                registerQuery=TRUE)

        self.originKw = AFXTupleKeyword(
                command=optionsCmd,
                name='origin',
                isRequired=FALSE,
                minLength=2,
                maxLength=2)

        self.widthKw = AFXFloatKeyword(
                command=optionsCmd,
                name='width',
                isRequired=FALSE)

        self.heightKw = AFXFloatKeyword(
                command=optionsCmd,
                name='height',
                isRequired=FALSE)

    def getFirstDialog(self):
        return viewportEditDB(self)

###########################################################################
# Register the plugin
###########################################################################
toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(
    buttonText='&Views|Edit Viewport...', 
    object=viewportEditForm(toolset),
    author='Carl Osterwisch',
    version=str(__version__),
    applicableModules=abaqusConstants.ALL,
    description='Edit parameters for the current viewport.',
    )
