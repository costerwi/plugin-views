"""Define the AFXForm class to handle views dialog box events.

Carl Osterwisch <carl.osterwisch@avlna.com> June 2006
$Id$
"""

from abaqusGui import *
import abaqusConstants
import viewsCommon
import re

class myQuery:
    "Object used to register/unregister Queries"
    def __init__(self, object, subroutine):
        "register the query when this object is created"
        self.object = object
        self.subroutine = subroutine
        object.registerQuery(subroutine)
    def __del__(self):
        "unregister the query when this object is deleted"
        self.object.unregisterQuery(self.subroutine)


class myAFXTable(AFXTable):
    def deleteRows(self, startRow, numRows=1, notify=FALSE):
        " Notify the kernel that these views are no longer wanted. "
        if notify:
            ids = [ self.getItemValue(row, 0) 
                    for row in range(startRow, startRow + numRows) ]
            AFXTable.deleteRows(self, startRow, numRows, notify)
            sendCommand("viewSave.deleteViews(%r)"%ids)
        else:
            AFXTable.deleteRows(self, startRow, numRows, notify)


###########################################################################
# Dialog box
###########################################################################
class viewManagerDB(AFXDataDialog):
    """The view manager dialog box class

    viewsForm will create an instance of this class when the user requests it.
    """
    
    [
        ID_TABLE,
        ID_FILTER,
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

        mainframe = FXVerticalFrame(self, FRAME_SUNKEN | LAYOUT_FILL_X | LAYOUT_FILL_Y)

        self.table = myAFXTable(
                p=mainframe,
                numVisRows=15,
                numVisColumns=3,
                numRows=1,
                numColumns=4,
                tgt=self,
                sel=self.ID_TABLE,
                opts=AFXTABLE_NORMAL|AFXTABLE_ROW_MODE)
#                    AFXTABLE_BROWSE_SELECT|AFXTABLE_ROW_MODE)
        FXMAPFUNC(self, SEL_CLICKED, self.ID_TABLE, viewManagerDB.onTable)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_TABLE, viewManagerDB.onCommand)
        self.table.setLeadingRows(numRows=1)
        self.table.setLeadingRowLabels('Id\tName\tDate\tOdbName')
        self.table.setColumnWidth(0, 0) # Don't show id column
        self.table.setColumnEditable(1, 1) # Allow name edit
        self.table.setStretchableColumn(3) # Expand OdbName as necessary

        for col in range(self.table.getNumColumns()):
            self.table.setColumnSortable(col, TRUE) # All are sortable
        self.table.setCurrentSortColumn(2) # date

        self.table.setPopupOptions(
                AFXTable.POPUP_DELETE_ROW
                |AFXTable.POPUP_FILE)

        self.filter = ''  # Don't filter anything
        AFXTextField(p=mainframe,
                ncols=15,
                labelText='Regular expression filter:',
                tgt=self,
                sel=self.ID_FILTER,
                opts=LAYOUT_FILL_X)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_FILTER, viewManagerDB.onFilter)

        self.appendActionButton(self.APPLY)
        self.appendActionButton(self.DISMISS)
        

    def updateTable(self):
        "Read view settings from customData.userViews registered list"
        sortColumn = self.table.getCurrentSortColumn()

        # Collect filtered table data
        filtered = []
        filterre = re.compile(self.filter, re.IGNORECASE)
        for row in session.customData.userViews:
            if filterre.search(' '.join(row)):
                filtered.append( (row[sortColumn].lower(), row) )

        # Sort table data
        filtered.sort()
        if self.table.getColumnSortOrder(sortColumn) == AFXTable.SORT_DESCENDING:
            filtered.reverse()

        # Adjust table widget size
        diff = len(filtered) + 1 - self.table.getNumRows()
        if diff > 0:
            self.table.insertRows(
                    startRow=1,
                    numRows=diff,
                    notify=FALSE)
        elif diff < 0:
            self.table.deleteRows(
                    startRow=1,
                    numRows=-diff,
                    notify=FALSE)

        # Update table widget
        selected = self.getMode().viewId.getValue()
        for row, (key, rowtext) in enumerate(filtered):
            tableRow = row + 1
            if rowtext[0] == selected:
                selected = tableRow
            self.table.deselectRow(tableRow)
            for col, itemtext in enumerate(rowtext):
                self.table.setItemValue(
                        row=tableRow,
                        column=col,
                        valueText=itemtext)

        if isinstance(selected, int):
            self.table.selectRow(selected)
            self.table.makeRowVisible(selected)


    def onCommand(self, sender, sel, ptr):
        " Called for rename "
        row = self.table.getCurrentRow()
        if row > 0:
            id = sender.getItemValue(row, 0)
            name = sender.getItemValue(row, 1)
            sendCommand("viewSave.renameView(viewId=%r, name=%r)"%(id, name))
        return 0


    def onTable(self, sender, sel, ptr):
        "Table was clicked - update the keyword or sorting"
        row = sender.getCurrentRow()
        if row > 0:
            id = sender.getItemValue(row, 0)
            self.getMode().viewId.setValue(id)
        if row == 0:
            self.updateTable()  # sorting has changed
        return 0
 

    def onFilter(self, sender, sel, ptr):
        "Search field was changed"
        self.filter = sender.getText()
        self.updateTable()
        return 0


    def show(self):
        "Prepare to show the dialog box"
        # Register query and populate the table
        self.userViewsQuery = \
                myQuery(session.customData.userViews, self.updateTable)
        self.updateTable()
        return AFXDataDialog.show(self)


    def hide(self):
        "Called to remove the dialog box"
        del self.userViewsQuery
        sendCommand("viewSave.writeXmlFile()")
        return AFXDataDialog.hide(self)


###########################################################################
# Form definition
###########################################################################
class viewManagerForm(AFXForm):
    "Class to launch the views GUI"
    def __init__(self, owner):

        AFXForm.__init__(self, owner) # Construct the base class.
                
        # Commands.
        cmd = AFXGuiCommand(mode=self, method='setView', objectName='viewSave')

        self.viewId = AFXStringKeyword(command=cmd, 
                name='viewId',
                isRequired=TRUE,
                defaultValue='0')


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
