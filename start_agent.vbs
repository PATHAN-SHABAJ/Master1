Set shell = CreateObject("WScript.Shell")

project = "D:\fyndXO_DB\flipcart"
shell.CurrentDirectory = project


' ============================================================
' START WEBSITE
' ============================================================

shell.Run _
    "pythonw.exe """ & _
    project & "\website\test_website.py""", _
    0, _
    False


' ============================================================
' WAIT FOR WEBSITE
' ============================================================

WScript.Sleep 5000


' ============================================================
' START DISCOVERY + PRODUCT AGENT
' ============================================================

shell.Run _
    "pythonw.exe -m agents.discovery_agent", _
    0, _
    False


' ============================================================
' WAIT FOR DISCOVERY PIPELINE
' ============================================================

WScript.Sleep 5000


' ============================================================
' START CHANGE AGENT
' ============================================================

shell.Run _
    "pythonw.exe -m agents.change_agent", _
    0, _
    False


' ============================================================
' START UPDATE / SYNC AGENT
' ============================================================

WScript.Sleep 3000

shell.Run _
    "pythonw.exe -m agents.update_agent", _
    0, _
    False


' ============================================================
' OPEN ONLY CLONE WEBSITE
' ============================================================

WScript.Sleep 3000

shell.Run _
    "http://127.0.0.1:8000", _
    1, _
    False


Set shell = Nothing