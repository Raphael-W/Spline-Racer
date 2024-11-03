import os
from win32com.client import Dispatch

print("Welcome to the setup wizard!\n")
continueToSetup = input("Would you like to install the required modules?\nNOTE: This uses the 'pip install' command. If you want to use a venv instead, manually install the requirements found in requirements.txt\nContinue? (y/n) ")

#Installing Requirements
if continueToSetup.lower() == 'y':
    exitCode = os.system("pip install -r requirements.txt")
    if exitCode != 0:
        print("Unable to install requirements")


onWindows = os.name == 'nt'
if onWindows:
    continueToSetup = input("\nWould you like to create a shortcut to the program?\nNOTE: If you choose not to create a shortcut, you can run the program from the main.pyw located in src/\nContinue? (y/n) ")

    if continueToSetup.lower() == 'y':
        try:
            #Creating a shortcut to main.pyw
            executionDir = os.path.dirname(__file__)
            mainScriptPath = os.path.normpath(os.path.join(executionDir, "src/main.pyw"))
            shortcutPath = os.path.join(executionDir, "Spline Racer.lnk")
            iconPath = os.path.join(executionDir, "assets/icons/logo.ico")

            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcutPath)
            shortcut.Targetpath = mainScriptPath
            shortcut.IconLocation = iconPath
            shortcut.save()
        except:
            print("Unable to create shortcut")

input("Setup complete! Press enter to exit...")
