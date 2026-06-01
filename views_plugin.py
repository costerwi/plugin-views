"""Register the Abaqus kernel methods from views.py"""

from abaqusGui import *
from viewEditDB import viewEditForm
from viewportEditDB import viewportEditForm
from viewManagerDB import ViewManagerForm
import viewsCommon

# {{{1 Procedure definition
class PickSomethingProcedure(AFXProcedure):
    """Base class to allow user to select things and run a views command"""

    entitiesToPick = PLANES # may be redefined by child class
    prompt = 'objects to operate upon' # must be redefined by child class
    method = 'thing_to_do' # must be redefined by child class

    def __init__(self, owner):
        AFXProcedure.__init__(self, owner) # Construct the base class.

        self.command = AFXGuiCommand(mode=self,
                method=self.method,
                objectName='views',
                registerQuery=FALSE)

        objectToPick = self.prompt.split()[0]
        if objectToPick.endswith('s'): # plural
            self.numberToPick = MANY
        else:
            self.numberToPick = ONE
        self.pickedKw = AFXObjectKeyword(
                command=self.command,
                name=objectToPick.lower(),
                isRequired=TRUE)

    def getFirstStep(self):
        self.step1 = AFXPickStep(
                owner=self,
                keyword=self.pickedKw,
                prompt='Select ' + self.prompt,
                entitiesToPick=self.entitiesToPick,
                numberToPick=self.numberToPick,
                #sequenceStyle=TUPLE,    # TUPLE or ARRAY
                )
        return self.step1

    def getLoopStep(self):
        if MANY == self.numberToPick:
            return self.step1  # loop until canceled

# {{{1 VIEWS

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

menu = ['&Views']

class PlanarPicked(PickSomethingProcedure):
        entitiesToPick = PLANES
        prompt = 'Planar surface to align view'
        method = 'alignToPlanar'

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|&Align normal to plane...',
        object=PlanarPicked(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Pick a planar feature to align the view'
        )

class DatumPicked(PickSomethingProcedure):
        entitiesToPick = DATUM_CSYS | DATUM_AXES | DATUM_PLANES
        prompt = 'Datum feature to align view'
        method = 'alignToDatum'

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|&Align to datum...',
        object=DatumPicked(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Pick a datum csys, plane, or axis to align the view'
        )

class UpPicked(PickSomethingProcedure):
        entitiesToPick = LINES
        prompt = 'line to define vertical orientation'
        method = 'alignToUp'

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|Align vertical with picked line...',
        object=UpPicked(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Pick a line to align the vertical orientation'
        )

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|&Behind',
        moduleName='views',
        functionName='behind()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Flip the view 180 degrees (look behind)')

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|&Edit parameters...',
        object=viewEditForm(toolset),
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Directly edit parameters for the current view.',
        )

kernelInitString='import viewSave; viewSave.init()'
if not isinstance(u'unicode', str):
    kernelInitString='print "*** View Manager requires Abaqus CAE version >= 2024"'
toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|View &Manager...',
        object=ViewManagerForm(toolset),
        kernelInitString=kernelInitString,
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Retrieve the view settings which were saved when a view was printed.')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|Reset overlay &layer transforms',
        moduleName='views',
        functionName='resetLayerTransform()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Reset all overlay layer view transforms to 1 (identity)')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|&Snap to nearest saved view',
        moduleName='views',
        functionName='viewSnap()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Snap view to closest saved view and closest up vector.')

# {{{1 VIEW CUT PLUGINS

menu.append('View &cut')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|Cut plane &normal to view',
        moduleName='views',
        functionName='cutViewNormal()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Cut normal to the current view.')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|&View normal to cut plane',
        moduleName='views',
        functionName='viewCutNormal()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Orient view normal to current ' +
                    'cutting plane.')

class CutPlanarPicked(PickSomethingProcedure):
        entitiesToPick = PLANES
        prompt = 'Planar feature to define cut'
        method = 'viewCutPlanar'

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|Cut from planar feature...',
        object=CutPlanarPicked(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Pick a planar feature to define the cut'
        )

class viewCutPointProcedure(PickSomethingProcedure):
        entitiesToPick = POINTS
        prompt = 'Point to cut through'
        method = 'viewCutPoint'

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|Cut through &point...',
        object=viewCutPointProcedure(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Adjust cut position to pass through picked point.'
        )

menu.pop()

# {{{1 VIEWPORT PLUGINS

menu.append('&Viewports')

toolset.registerGuiMenuButton(
        buttonText='|'.join(menu) + '|&Edit parameters...',
        object=viewportEditForm(toolset),
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Edit parameters for the current viewport.',
        )

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|For each &step of current odb',
        moduleName='views',
        functionName='viewSteps()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Create a new viewport for each analysis step.')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|For each open &odb',
        moduleName='views',
        functionName='viewOdbs()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Create a new viewport for each open odb.')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|&Synchronize',
        moduleName='views',
        functionName='synchVps()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Copy current viewport options to the others.')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|S&wap viewport positions',
        moduleName='views',
        functionName='swapVps()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Shift the positions of multiple viewports.')

toolset.registerKernelMenuButton(
        buttonText='|'.join(menu) + '|Tile &vertical',
        moduleName='views',
        functionName='tileVertical()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Arrange visible viewports side-by-side.')

