Set WshShell = WScript.CreateObject("WScript.Shell")
strDesktop = "c:\Users\signa\OneDrive\Desktop"
strCentral = strDesktop & "\AQI_Central_Command\Active_Units"

Sub CreateShortcut(Name, TargetPath)
    Dim linkPath, shortcut
    linkPath = strCentral & "\" & Name & ".lnk"
    Set shortcut = WshShell.CreateShortcut(linkPath)
    shortcut.TargetPath = TargetPath
    shortcut.Save
End Sub

CreateShortcut "Agent X", strDesktop & "\Agent X"
CreateShortcut "Veronica", strDesktop & "\AQI North Connector"
CreateShortcut "RSE Agent", strDesktop & "\RSE Agent"
CreateShortcut "Master Index", strDesktop & "\Agent X\AQI_MASTER_INDEX.md"
