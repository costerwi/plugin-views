"""Register the Abaqus kernel methods from views.py"""

from abaqusGui import *
import viewsCommon

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerKernelMenuButton(
        buttonText='&Views|&Synchronize',
        moduleName='views',
        functionName='synchVps()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Copy current viewport options to the others.')

toolset.registerKernelMenuButton(
        buttonText='&Views|S&wap viewport positions',
        moduleName='views',
        functionName='swapVps()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Shift the positions of multiple viewports.')

toolset.registerKernelMenuButton(
        buttonText='&Views|&Snap to saved view',
        moduleName='views',
        functionName='viewSnap()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Snap view to closest saved view and closest up vector.')

toolset.registerKernelMenuButton(
        buttonText='&Views|&Cut plane normal to view',
        moduleName='views',
        functionName='cutViewNormal()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Cut normal to the current view.')

toolset.registerKernelMenuButton(
        buttonText='&Views|&View normal to cut plane',
        moduleName='views',
        functionName='viewCutNormal()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Orient view normal to current ' +
                    'cutting plane.')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &behind',
        moduleName='views',
        functionName='behind()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Flip the view 180 degrees (look behind)')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &steps',
        moduleName='views',
        functionName='viewSteps()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Create a new viewport for each analysis step.')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &odbs',
        moduleName='views',
        functionName='viewOdbs()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Create a new viewport for each analysis step.')

toolset.registerKernelMenuButton(
        buttonText='&Views|Tile &vertical',
        moduleName='views',
        functionName='tileVertical()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        description='Arrange visible viewports side-by-side.')

toolset.registerKernelMenuButton(
        buttonText='&Views|Reset &layer transforms',
        moduleName='views',
        functionName='resetLayerTransform()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Reset layer transforms to 1 (identity)')


class viewCutDatumProcedure(AFXProcedure):
    def __init__(self, owner):
        # Construct the base class
        AFXProcedure.__init__(self, owner)

        # Command
        viewCutCommand = AFXGuiCommand(mode=self,
                method='viewCutDatum',
                objectName='views',
                registerQuery=FALSE)

        # Keywords
        self.datumKw = AFXObjectKeyword(
                command=viewCutCommand,
                name='datum',
                isRequired=TRUE)

        viewCutCommand.setKeywordValuesToDefaults()


    def getFirstStep(self):
        return AFXPickStep(
                owner=self,
                keyword=self.datumKw,
                prompt="Select datum plane",
                entitiesToPick=DATUM_PLANES,
                numberToPick=ONE,
                sequenceStyle=ARRAY)    # TUPLE or ARRAY

toolset.registerGuiMenuButton(
        buttonText='&Views|Cut from &datum plane...',
        object=viewCutDatumProcedure(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Assembly', 'Load', 'Mesh', 'Part', 'Property'],
        description='Create view cut from selected datum plane.'
        )


class viewCutPointProcedure(AFXProcedure):
    def __init__(self, owner):
        # Construct the base class
        AFXProcedure.__init__(self, owner)

        # Command
        viewCutCommand = AFXGuiCommand(mode=self,
                method='viewCutPoint',
                objectName='views',
                registerQuery=FALSE)

        # Keywords
        self.pointKw = AFXObjectKeyword(
                command=viewCutCommand,
                name='point',
                isRequired=TRUE)

        viewCutCommand.setKeywordValuesToDefaults()

    def getFirstStep(self):
        return AFXPickStep(
                owner=self,
                keyword=self.pointKw,
                prompt="Select point",
                entitiesToPick=POINTS,
                numberToPick=ONE,
                sequenceStyle=ARRAY)    # TUPLE or ARRAY


toolset.registerGuiMenuButton(
        buttonText='&Views|Cut through point...',
        object=viewCutPointProcedure(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Assembly', 'Part', 'Visualization'],
        description='Adjust cut position to pass through given point.'
        )

