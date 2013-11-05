"""Register the Abaqus kernel methods from plotfonts.py"""

import abaqusGui

toolset = abaqusGui.getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerKernelMenuButton(
        buttonText='&Views|&Plot fonts', 
        moduleName='plotfonts',
        functionName='setFonts()',
        author='Carl Osterwisch',
        version='0.1',
        applicableModules=['Visualization'],
        description='Increase font size in current session charts.')

