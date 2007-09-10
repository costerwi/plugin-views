"""Define the AFXForm class to handle views dialog box events.

Carl Osterwisch <carl.osterwisch@avlna.com> June 2006
"""

from abaqusGui import *
import abaqusConstants
import viewsCommon

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

        FXCheckButton(p=mainframe, text='Autofit', tgt=form.autoFit)

        self.tree = FXTreeList(
                p=mainframe,
                nvis=15,
                tgt=self,
                sel=self.ID_TREE,
                opts=TREELIST_SHOWS_BOXES|TREELIST_ROOT_BOXES|
                TREELIST_SINGLESELECT|LAYOUT_FILL_X|LAYOUT_FILL_Y)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_TREE, viewManagerDB.onTree)

        self.name = AFXTextField(mainframe, 10, '', self, self.ID_NAME,
                LAYOUT_FILL_X)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_NAME, viewManagerDB.onName)

        self.appendActionButton("New", self, self.ID_NEWVIEW)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_NEWVIEW, viewManagerDB.onNewView)
        self.appendActionButton("Delete", self, self.ID_DELVIEW)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_DELVIEW, viewManagerDB.onDelView)
        self.appendActionButton(self.DISMISS)

    def show(self):
        "Read view settings from a file"
        for fn in (viewsCommon.userFileName, viewsCommon.printFileName):
            if os.path.exists(fn):
                parent=None
                for line in open(fn):
                    line = line.strip()
                    i = line.rfind(';')
                    if i > 0:
                        self.tree.addItemLast(p=parent, text=line[:i],
                            ptr=line[i + 1:])
                    else:
                        parent = self.tree.getFirstItem()
                        while parent and (parent.getText().lower() < line.lower()):
                            parent = parent.getNext()
                        if not parent:
                            parent = self.tree.addItemLast(p=None, text=line)
                        elif parent.getText().lower() > line.lower():
                            parent = self.tree.addItemBefore(
                                    other=parent,
                                    text=line)

        if os.path.exists(viewsCommon.printFileName):
            os.remove(viewsCommon.printFileName)

        if 0 == self.tree.getNumItems():
            # Insert standard views
            parent = self.tree.addItemLast(None, "Standard")
            for view in session.views.values():
                self.tree.addItemLast(p=parent, text=view.name,
                        ptr=viewsCommon.viewData(view))
        return AFXDataDialog.show(self)

    def printleaf(self, output, item):
        while item:
            if item.getData():
                print >>output, "%s;%s"%(item.getText(), item.getData())
            else:
                print >>output, item.getText()
            self.printleaf(output, item.getFirst())
            item = item.getNext()

    def hide(self):
        "Save view settings to a file before closing the window"
        o = open(viewsCommon.userFileName, 'w')
        self.printleaf(o, self.tree.getFirstItem())
        return AFXDataDialog.hide(self)

    def onTree(self, sender, sel, ptr):
        "Tree selection changed - update the view"
        item=self.tree.getCurrentItem()
        self.name.setText(item.getText())
        self.name.setFocusAndSelection()
        if item.getData():
            self.getMode().issueCommands(item.getData())
        return 1

    def onName(self, sender, sel, ptr):
        "User changed the view name - rename the item text"
        item=self.tree.getCurrentItem()
        if item:
            item.setText(self.name.getText())
            self.tree.updateItem(item)
        return 1

    def onNewView(self, sender, sel, ptr):
        "Add the current view to the list"
        view=session.viewports[session.currentViewportName].view
        item=self.tree.getCurrentItem()
        if item and item.getParent():
            item = item.getParent()
        else:
            item = self.tree.getFirstItem()
        self.tree.addItemLast(p=item, text="Untitled",
                ptr=viewsCommon.viewData(view))
        return 1

    def onDelView(self, sender, sel, ptr):
        "Remove the current view from the list"
        item=self.tree.getCurrentItem()
        if item and not item.getNumChildren():
            self.tree.removeItem(item)
        return 1

###########################################################################
# Form definition
###########################################################################
class viewManagerForm(AFXForm):
    "Class to launch the views GUI"
    def __init__(self, owner):

        AFXForm.__init__(self, owner) # Construct the base class.
                
        # Commands.
        cmd = AFXGuiCommand(self, 'setValues', 'session.viewports[%s].view')

        self.autoFit = AFXIntTarget(0)
        self.parameters=''

    def printToFileCallback(self, callingObject, args, kws, user):
        # Will eventually add the current view to the list of saved views
        print("printing..." + str(kws))

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
        kernelInitString='import views; views.registerCallback()',
        author='Carl Osterwisch',
        version='0.1',
        applicableModules=abaqusConstants.ALL,
        description='Store and retrieve custom ' +
                    'viewport views.')
