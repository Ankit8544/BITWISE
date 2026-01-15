Attribute VB_Name = "Module3"
Public NextRun_Agg As Date
Public AggGuard_Running As Boolean

Sub XlOil_FastGuard_aggTrade()

    If AggGuard_Running Then Exit Sub
    AggGuard_Running = True

    Dim targets As Variant
    Dim i As Long
    Dim ws As Worksheet
    Dim c As Range
    Dim txt As String
    Dim f As String

    targets = Array( _
        "AT_1m!F3", _
        "AT_5m!F3", _
        "AT_15m!F3" _
    )

    On Error GoTo ExitSafe

    ' ? DO NOT TOUCH CALCULATION FOR STREAMS
    Application.EnableEvents = False
    Application.ScreenUpdating = False

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
            c.Formula2 = f   ' ? no "=" rebuild

        End If

NextCell:
    Next i

ExitSafe:
    Application.ScreenUpdating = True
    Application.EnableEvents = True

    AggGuard_Running = False

    ' ?? LOWER FREQUENCY – aggTrade already streams
    NextRun_Agg = Now + TimeValue("00:00:10")
    Application.OnTime NextRun_Agg, "XlOil_FastGuard_aggTrade"

End Sub


