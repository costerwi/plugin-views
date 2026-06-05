"""Define the AFXForm class to handle views dialog box events.

Carl Osterwisch, June 2006
"""

import re
from abaqusGui import *
from viewsCommon import ViewRow, databaseName

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
    def __repr__(self):
        return 'myQuery {}'.format(self.subroutine.__doc__)


class myAFXTable(AFXTable):
    def deleteRows(self, startRow, numRows=1, notify=FALSE):
        " Notify the kernel that these views are no longer wanted. "
        if notify:
            names = [ self.getItemValue(row, ViewRow._fields.index('name'))
                    for row in range(startRow, startRow + numRows) ]
            AFXTable.deleteRows(self, startRow, numRows, notify)
            sendCommand("viewSave.deleteViews(%r)"%names)
        else:
            AFXTable.deleteRows(self, startRow, numRows, notify)


###########################################################################
# Dialog box
###########################################################################
class ViewManagerDB(AFXDataDialog):
    """The view manager dialog box class

    viewsForm will create an instance of this class when the user requests it.
    """
    
    (
        ID_TABLE,
        ID_FILTER,
        ID_BUTTON_ANNOTATION,
        ID_SELECT_FILE,
        ID_FILE_CHANGED,
        ID_LAST
    ) = range(AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 6)


    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self,
                mode=form,
                title="Views Manager",
                opts=DIALOG_NORMAL|DECOR_RESIZE)
        self.fileDialog = None
        self.form = form
        self.filter = ''  # Don't filter anything
        self.viewNames = []


    def create(self):
        """Make the widgets"""
        self.mainframe = FXVerticalFrame(self, FRAME_SUNKEN | LAYOUT_FILL_X | LAYOUT_FILL_Y)
        frame = FXHorizontalFrame(p=self.mainframe, opts=LAYOUT_FILL_X)
        AFXTextField(
                p=frame,
                ncols=12,
                labelText='Database:\tSaved views database file',
                tgt=self.form.databaseKw,
                opts=AFXTEXTFIELD_STRING|AFXTEXTFIELD_READONLY|LAYOUT_CENTER_Y|LAYOUT_FILL_X)
        icon = afxGetIcon('fileOpen')
        FXButton(p=frame, text='\tSelect view database file...', ic=icon,
                tgt=self, sel=self.ID_SELECT_FILE,
                opts=BUTTON_TOOLBAR | FRAME_RAISED | LAYOUT_RIGHT)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_SELECT_FILE, ViewManagerDB.selectDatabaseFile)
        self.form.databaseKw.setTarget(self)
        self.form.databaseKw.setSelector(self.ID_FILE_CHANGED)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_FILE_CHANGED, ViewManagerDB.onFileChanged)

        self.table = myAFXTable(
                p=self.mainframe,
                numVisRows=4,
                numVisColumns=3,
                numRows=1,
                numColumns=len(ViewRow._fields),
                tgt=self,
                sel=self.ID_TABLE,
                opts=AFXTABLE_NORMAL|AFXTABLE_ROW_MODE)
#                    AFXTABLE_BROWSE_SELECT|AFXTABLE_ROW_MODE)
        FXMAPFUNC(self, SEL_CLICKED, self.ID_TABLE, ViewManagerDB.onTable)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_TABLE, ViewManagerDB.onCommand)
        self.table.setLeadingRows(numRows=1)
        self.table.setLeadingRowLabels('\t'.join([f.title() for f in ViewRow._fields]))
        self.table.setColumnEditable(ViewRow._fields.index('name'), True)
        self.table.setColumnEditable(ViewRow._fields.index('description'), True)
        self.table.setStretchableColumn(ViewRow._fields.index('description')) # Expand Description as necessary

        for col in range(self.table.getNumColumns()):
            self.table.setColumnSortable(col, TRUE)
        self.table.setCurrentSortColumn(ViewRow._fields.index('date'))

        self.table.setPopupOptions(
                AFXTable.POPUP_DELETE_ROW) # | AFXTable.POPUP_FILE)
        self.table.appendClientPopupItem('Reprint selected view(s)', icon=afxGetIcon('filePrint'))

        AFXTextField(p=self.mainframe,
                ncols=15,
                labelText='Regular expression filter:',
                tgt=self,
                sel=self.ID_FILTER,
                opts=LAYOUT_FILL_X)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_FILTER, ViewManagerDB.onFilter)

        btn = self.appendActionButton(self.APPLY)
        btn.setText("Restore View")
        self.appendActionButton(text="Restore Annotations", tgt=self, sel=self.ID_BUTTON_ANNOTATION)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_BUTTON_ANNOTATION, ViewManagerDB.onAnnotation)
        self.appendActionButton(self.DISMISS)
        AFXDataDialog.create(self)


    def updateTable(self):
        "Read view settings from customData.userViews registered list"
        sortColumn = self.table.getCurrentSortColumn()
        
        # Collect filtered table data
        filtered = []
        filterre = re.compile(self.filter, re.IGNORECASE)
        try:
            for row in session.customData.userViews:
                row = ViewRow(*row)  # interpret as ViewRow
                if filterre.search('\t'.join(row)):
                    filtered.append( (row[sortColumn].lower(), row) )
        except AttributeError:
            return

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
        selected = self.form.viewNameKw.getValue()
        for i, (_, row) in enumerate(filtered):
            tableRow = i + 1
            if row.name == selected:
                selected = tableRow
            self.table.deselectRow(tableRow)
            for col, itemtext in enumerate(row):
                self.table.setItemValue(
                        row=tableRow,
                        column=col,
                        valueText=str(itemtext))
        self.viewNames = [row.name for _, row in filtered]

        if isinstance(selected, int):
            self.table.selectRow(selected)
            self.table.makeRowVisible(selected)


    def onCommand(self, sender, sel, ptr):
        " Called for rename "
        tableRow = self.table.getCurrentRow()
        if tableRow > 0:
            viewName = self.viewNames[tableRow - 1]
            col = self.table.getCurrentColumn()
            field = ViewRow._fields[col]
            value = sender.getItemValue(tableRow, col)
            if field == 'name':
                self.getMode().viewNameKw.setValue(value)
                sendCommand("viewSave.renameView(viewName=%r, newName=%r)"%(viewName, value))
            elif field == 'description':
                sendCommand("viewSave.setDescription(viewName=%r, description=%r)"%(viewName, value))


    def onTable(self, sender, sel, ptr):
        "Table was clicked - update the keyword or sorting"
        tableRow = sender.getCurrentRow()
        if tableRow > 0:
            viewName = self.viewNames[tableRow - 1]
            self.getMode().viewNameKw.setValue(viewName)
        if tableRow == 0:
            self.updateTable()  # sorting has changed
 

    def onFilter(self, sender, sel, ptr):
        "Search field was changed"
        self.filter = sender.getText()
        self.updateTable()


    def onAnnotation(self, sender, sel, ptr):
        "Annotation button was pushed"
        selected = self.getMode().viewNameKw.getValue()
        if selected:
            sendCommand("viewSave.restoreAnnotations(viewName=%r)"%selected)


    def selectDatabaseFile(self, sender, sel, ptr):
        """Construct database file selection dialog"""
        if not self.fileDialog:
            self.fileDialog = AFXFileSelectorDialog(self.mainframe,
                    'Select userView database file', # title
                    self.form.databaseKw, # pathNameKw
                    None, # readOnlyKw
                    AFXSELECTFILE_EXISTING, # mode
                    'View database (*.zip)', # pattern
                    )
            self.fileDialog.create()
        self.fileDialog.showModal()


    def onFileChanged(self, sender, sel, ptr):
        """A new database file was selected"""
        if not hasattr(self, 'userViewsQuery'):
            return
        filename = self.form.databaseKw.getValue()
        sendCommand('viewSave.scanDatabase({!r})'.format(filename))


    def show(self):
        "Prepare to show the dialog box"
        # Register query and populate the table
        try:
            self.userViewsQuery = \
                myQuery(session.customData.userViews, self.updateTable)
        except AttributeError:
            pass
        return AFXDataDialog.show(self)


    def hide(self):
        "Called to remove the dialog box"
        if hasattr(self, 'userViewsQuery'):
            del self.userViewsQuery
        return AFXDataDialog.hide(self)


###########################################################################
# Form definition
###########################################################################
class ViewManagerForm(AFXForm):
    "Class to launch the views GUI"

    def __init__(self, owner):

        AFXForm.__init__(self, owner) # Construct the base class.
                
        # Commands.
        #scanDatabase = AFXGuiCommand(mode=self, method='scanDatabase', objectName='viewSave')
        restoreView = AFXGuiCommand(mode=self, method='restoreView', objectName='viewSave')

        self.viewNameKw = AFXStringKeyword(command=restoreView,
                name='viewName',
                isRequired=TRUE,
                defaultValue='')

        self.databaseKw = AFXStringKeyword(command=restoreView,
                name='fileName',
                isRequired=FALSE,
                defaultValue=databaseName)


    def getFirstDialog(self):
        return ViewManagerDB(self)


