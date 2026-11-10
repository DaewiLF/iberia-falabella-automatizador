param([Parameter(Mandatory=$true)][string]$Archivo)
$ErrorActionPreference = 'Stop'
$excel = $null
$book = $null
try {
    $path = (Resolve-Path -LiteralPath $Archivo).Path
    if ([IO.Path]::GetExtension($path).ToLowerInvariant() -ne '.xlsx') {
        throw 'Se necesita un archivo .xlsx.'
    }
    $base = [IO.Path]::Combine([IO.Path]::GetDirectoryName($path), [IO.Path]::GetFileNameWithoutExtension($path))
    $destination = $base + '_RECALCULADO.xlsx'
    if (Test-Path -LiteralPath $destination) {
        $destination = $base + '_RECALCULADO_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.xlsx'
    }
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AskToUpdateLinks = $false
    # Desactiva macros cuando sea compatible con la instalación local de Excel.
    try { $excel.AutomationSecurity = 3 } catch { }
    # Apertura read-only, sin actualizar vínculos externos.
    $book = $excel.Workbooks.Open($path, 0, $true)
    $excel.CalculateFullRebuild()
    $book.SaveAs($destination, 51)
    Write-Host 'Excel recalculado guardado en:' -ForegroundColor Green
    Write-Host $destination
    Write-Host 'Ahora carga este archivo en la casilla de Precios de Falabella.'
}
catch {
    Write-Host ('Error: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
finally {
    if ($book -ne $null) {
        try { $book.Close($false) } catch { }
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book) } catch { }
    }
    if ($excel -ne $null) {
        try { $excel.Quit() } catch { }
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel) } catch { }
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
