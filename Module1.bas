Attribute VB_Name = "Module1"
Public NextRun_Core As Date

Sub XlOil_FastGuard_core()

    Dim targets As Variant
    Dim i As Long
    Dim ws As Worksheet
    Dim c As Range
    Dim txt As String
    Dim f As String

    targets = Array( _
        "All Coins!F3", _
        "Assets!F3" _
    )

    On Error GoTo ExitSafe

    Application.EnableEvents = False
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    For i = LBound(targets) To UBound(targets)

        Set ws = ThisWorkbook.Worksheets(Split(targets(i), "!")(0))
        Set c = ws.Range(Split(targets(i), "!")(1))

        If Not c.HasFormula Then GoTo NextCell

        txt = CStr(c.Value)

        If IsError(c.Value) _
        Or InStr(txt, "#NAME?") > 0 _
        Or InStr(txt, "Traceback") > 0 _
        Or InStr(txt, "connection") > 0 _
        Or InStr(txt, "closed") > 0 _
        Or InStr(txt, "Exception") > 0 Then

            f = c.Formula
            c.ClearContents
            c.Formula2 = "=" & Mid$(f, 2)

        End If

NextCell:
    Next i

ExitSafe:
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
    Application.EnableEvents = True

    NextRun_Core = Now + TimeValue("00:00:02")
    Application.OnTime NextRun_Core, "XlOil_FastGuard_core"

End Sub


