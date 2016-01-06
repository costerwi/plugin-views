"""Register the Abaqus kernel methods from views.py"""

from abaqusGui import *

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerKernelMenuButton(
        buttonText='&Views|&Synchronize', 
        moduleName='views',
        functionName='synchVps()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization'],
        description='Copy current viewport options to the others.')

toolset.registerKernelMenuButton(
        buttonText='&Views|&Cut plane normal to view', 
        moduleName='views',
        functionName='cutViewNormal()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization'],
        description='Cut normal to the current view.')

toolset.registerKernelMenuButton(
        buttonText='&Views|&View normal to cut plane', 
        moduleName='views',
        functionName='viewCutNormal()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization'],
        description='Orient view normal to current ' +
                    'cutting plane.')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &behind', 
        moduleName='views',
        functionName='behind()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization', 'Assembly', 'Part'],
        description='Flip the view 180 degrees (look behind)')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &steps', 
        moduleName='views',
        functionName='viewSteps()',
        author='Carl Osterwisch',
        version='0.22',
        applicableModules=['Visualization'],
        description='Create a new viewport for each analysis step.')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &odbs', 
        moduleName='views',
        functionName='viewOdbs()',
        author='Carl Osterwisch',
        version='0.1',
        applicableModules=['Visualization'],
        description='Create a new viewport for each analysis step.')

toolset.registerKernelMenuButton(
        buttonText='&Views|Tile &vertical', 
        moduleName='views',
        functionName='tileVertical()',
        author='Carl Osterwisch',
        version='0.2',
        applicableModules=['Visualization'],
        description='Arrange visible viewports side-by-side.')

toolset.registerKernelMenuButton(
        buttonText='&Views|Reset &layer transforms', 
        moduleName='views',
        functionName='resetLayerTransform()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization'],
        description='Set layer transforms to 1')


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
        version='0.1',
        applicableModules=['Assembly'],
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
                entitiesToPick=VERTICES, # TODO extend to other types
                numberToPick=ONE,
                sequenceStyle=ARRAY)    # TUPLE or ARRAY


toolset.registerGuiMenuButton(
        buttonText='&Views|Cut through point...',
        object=viewCutPointProcedure(toolset),
        kernelInitString='import views',
        author='Carl Osterwisch',
        version='0.1',
        applicableModules=['Assembly'],
        description='Adjust cut position to pass through given point.'
        )

