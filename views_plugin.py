"""Register the Abaqus kernel methods from views.py"""

import abaqusGui

toolset = abaqusGui.getAFXApp().getAFXMainWindow().getPluginToolset()

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
        applicableModules=['Visualization'],
        description='Flip the view 180 degrees (look behind)')

toolset.registerKernelMenuButton(
        buttonText='&Views|View &steps', 
        moduleName='views',
        functionName='viewSteps()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization'],
        description='Create a new viewport for each analysis step.')

toolset.registerKernelMenuButton(
        buttonText='&Views|Reset &layer transforms', 
        moduleName='views',
        functionName='resetLayerTransform()',
        author='Carl Osterwisch',
        version='0.21',
        applicableModules=['Visualization'],
        description='Set layer transforms to 1')

