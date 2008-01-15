"""Define the AFXForm class to handle views dialog box events.

Carl Osterwisch <carl.osterwisch@avlna.com> June 2006
$Id$
"""

from abaqusGui import *
import abaqusConstants
import viewsCommon

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

###########################################################################
# Dialog box
###########################################################################
class viewManagerDB(AFXDataDialog):
    """The view manager dialog box class

    viewsForm will create an instance of this class when the user requests it.
    """
    
    [
        ID_TABLE,
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

        mainframe = FXVerticalFrame(self, FRAME_SUNKEN | LAYOUT_FILL_X | LAYOUT_FILL_Y)

        self.table = AFXTable(
                p=mainframe,
                numVisRows=15,
                numVisColumns=3,
                numRows=1,
                numColumns=4,
                tgt=self,
                sel=self.ID_TABLE,
                opts=AFXTABLE_NORMAL|
                    AFXTABLE_SINGLE_SELECT|AFXTABLE_ROW_MODE)
        FXMAPFUNC(self, SEL_CLICKED, self.ID_TABLE, viewManagerDB.onTable)
        self.table.setLeadingRows(numRows=1)
        self.table.setLeadingRowLabels('Id\tName\tDate\tOdbName')
        self.table.setColumnWidth(0, 0) # Don't show id column
        self.table.setStretchableColumn(3) # Expand OdbName as necessary

        for col in range(self.table.getNumColumns()):
            self.table.setColumnSortable(col, TRUE) # All are sortable
        self.table.setCurrentSortColumn(2) # date

        self.appendActionButton(self.APPLY)
        self.appendActionButton(self.DISMISS)


    def sortTable(self):
        "Sort the table data according to the current sortColumn"
        t = self.table
        sortColumn = t.getCurrentSortColumn()
        sortOrder = (sortColumn, t.getColumnSortOrder(sortColumn))

        if self.sortOrder != sortOrder:
            self.sortOrder = sortOrder
            nrows = t.getNumRows()
            ncols = t.getNumColumns()

            values = []
            for row in range(1, nrows):
                d = [ t.getItemValue(row, c) for c in range(ncols) ]
                values.append( (d[sortColumn].lower(), d) )
 
            values.sort()
            if sortOrder[1] == AFXTable.SORT_ASCENDING:
                values.reverse()

            for row in range(1, nrows):
                for col, text in enumerate(values[row - 1][1]):
                    t.setItemValue(row=row, column=col, valueText=text)

            t.selectRow(1)
            t.makeRowVisible(1)
            return 1
        return 0


    def updateTable(self):
        "Read view settings from customData.userViews registered list"
        trows = self.table.getNumRows() - 1
        uv=session.customData.userViews
        uvrows = len(uv)
        self.table.insertRows(startRow=trows + 1, numRows=uvrows - trows)
        for row in range(trows, uvrows):
            for col, text in enumerate(uv[row]):
                self.table.setItemValue(
                        row=row+1,
                        column=col,
                        valueText=text)
        self.sortOrder = None # table needs to be re-sorted
        self.sortTable()


    def onTable(self, sender, sel, ptr):
        "Table was clicked - update the keyword or sorting"
        if not self.sortTable():    # sort if necessary
            row = self.table.getCurrentRow()
            id = self.table.getItemValue(row, 0)
            self.getMode().viewId.setValue(id)
        return 1
      

    def show(self):
        "Prepare to show the dialog box"
        # Register query and populate the table
        self.userViewsQuery = \
                myQuery(session.customData.userViews, self.updateTable)
        return AFXDataDialog.show(self)


    def hide(self):
        "Called to remove the dialog box"
        del self.userViewsQuery
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
