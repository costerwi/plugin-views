"""Register the Abaqus kernel methods from plotfonts.py"""

import abaqusGui
import viewsCommon

toolset = abaqusGui.getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerKernelMenuButton(
        buttonText='&Views|&Plot fonts', 
        moduleName='plotfonts',
        functionName='setFonts()',
        author='Carl Osterwisch',
        version=viewsCommon.__version__,
        helpUrl=viewsCommon.helpUrl,
        applicableModules=['Visualization'],
        description='Increase font size in current session charts.')
