' run-hidden.vbs
' Launches any command completely hidden (SW_HIDE = 0) without triggering Windows 11 Terminal
Set WshShell = CreateObject("WScript.Shell")
If WScript.Arguments.Count > 0 Then
    Dim cmd, i
    cmd = ""
    For i = 0 To WScript.Arguments.Count - 1
        If InStr(WScript.Arguments(i), " ") > 0 Then
            cmd = cmd & """" & WScript.Arguments(i) & """ "
        Else
            cmd = cmd & WScript.Arguments(i) & " "
        End If
    Next
    WshShell.Run Trim(cmd), 0, False
End If
