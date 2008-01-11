"""Define the AFXForm class to handle views dialog box events.

Carl Osterwisch <carl.osterwisch@avlna.com> June 2006
$Id$
"""

from abaqusGui import *
import abaqusConstants
import viewsCommon
from xml.dom import minidom
from xml.utils import iso8601 # date/time support

###########################################################################
# Dialog box
###########################################################################
class viewManagerDB(AFXDataDialog):
    """The view manager dialog box class

    viewsForm will create an instance of this class when the user requests it.
    """
    
    [
        ID_TREE,
        ID_NAME,
        ID_NEWVIEW,
        ID_DELVIEW,
        ID_LAST
    ] = range(AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 5)

    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self,
                mode=form,
                title="Views Manager",
                opts=DIALOG_NORMAL|DECOR_RESIZE)

        mainframe = FXVerticalFrame(self, LAYOUT_FILL_X | LAYOUT_FILL_Y)

        self.tree = FXTreeList(
                p=mainframe,
                nvis=15,
                tgt=self,
                sel=self.ID_TREE,
                opts=TREELIST_SHOWS_BOXES|TREELIST_ROOT_BOXES|
                TREELIST_SINGLESELECT|LAYOUT_FILL_X|LAYOUT_FILL_Y)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_TREE, viewManagerDB.onTree)

        self.appendActionButton(self.DISMISS)

    def show(self):
        "Read view settings from registered list"
        parents = {}
        for userView in session.customData.userViews:
            print userView, dir(userView), minidom.Element.toxml(userView)
            od = userView.getElementsByTagName("userView")[0]
            odbName = od.getAttribute('name')
            if parents.has_key(odbName):
                parent = parents[odbName]
            else:
                # insert alpha
                parent = self.tree.getFirstItem()
                while parent and (parent.getText().lower() < odbName.lower()):
                    parent = parent.getNext()
                if not parent:
                    parent = self.tree.addItemLast(p=None, text=odbName)
                elif parent.getText().lower() > line.lower():
                    parent = self.tree.addItemBefore(
                            other=parent,
                            text=odbName)
                parents[odbName] = parent

            name = userView.getAttribute('name')
            self.tree.addItemLast(p=parent, text=name,
                ptr=userView)
        return AFXDataDialog.show(self)


    def onTree(self, sender, sel, ptr):
        "Tree selection changed - update the view"
        item=self.tree.getCurrentItem()
        if item.getData():
            self.getMode().issueCommands(item.getData())
        return 1


###########################################################################
# Form definition
###########################################################################
class viewManagerForm(AFXForm):
    "Class to launch the views GUI"
    def __init__(self, owner):

        AFXForm.__init__(self, owner) # Construct the base class.
                
        # Commands.
        cmd = AFXGuiCommand(self, 'setView', 'viewSave')

        self.parameters=''

    def issueCommands(self, parameters=None):
        "This function now accepts the parameter string to set"
        if parameters:
            self.parameters = parameters
        return AFXForm.issueCommands(self)

    def getCommandString(self):
        "Construct custom command string"
        cmdstr = AFXForm.getCommandString(self)
        cmdstr = cmdstr[:-1] + str(self.parameters) + ")"
        print cmdstr
        return cmdstr

    def getFirstDialog(self):
        return viewManagerDB(self)

###########################################################################
# Register abaqus plugin
###########################################################################
toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(
        buttonText='&Views|&Manager...', 
        object=viewManagerForm(toolset),
        kernelInitString='import viewSave; viewSave.init()',
        author='Carl Osterwisch',
        version=str(viewsCommon.__version__),
        applicableModules=abaqusConstants.ALL,
        description='Store and retrieve custom viewport views.')
