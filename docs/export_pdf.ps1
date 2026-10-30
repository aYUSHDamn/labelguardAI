# Exports a .docx to PDF using Microsoft Word.  Usage: powershell -File docs\export_pdf.ps1 <in.docx> <out.pdf>
param([string]$In, [string]$Out)
$w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0
try { $d = $w.Documents.Open((Resolve-Path $In).Path, $false, $true); $d.ExportAsFixedFormat($Out, 17); $d.Close($false) } finally { $w.Quit() }
