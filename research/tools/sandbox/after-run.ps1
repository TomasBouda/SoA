# Check after starting the game: shows what the launcher really set and leaves
# the game log on the host. Started by hand through after-run.cmd.
$ErrorActionPreference = 'Continue'
$pkg = 'C:\SoA'
$game = Join-Path $pkg 'Game'
$key = 'HKCU:\Software\Silver Style Entertainment\Soldiers of Anarchy\Settings'
$lines = New-Object System.Collections.Generic.List[string]

function Line([string]$text, [string]$color = 'Gray') {
    Write-Host "  $text" -ForegroundColor $color
    $lines.Add("  $text")
}

Line 'What is in the registry after the run' 'Cyan'
if (Test-Path $key) {
    $s = Get-ItemProperty $key
    Line ('resolution: {0}x{1}, {2} bits' -f $s.DisplayModeWidth, $s.DisplayModeHeight, $s.DisplayModeBPP)
    # The shortcuts are named AK<hex action>_<slot number>.
    $shortcuts = ($s.PSObject.Properties.Name | Where-Object { $_ -like 'AK*' }).Count
    Line "keys:       $shortcuts entries (the WASD controls were imported)"
}
else { Line 'the game key is not in the registry - the launcher has not run yet' 'Yellow' }

$inst = (Get-ItemProperty 'HKCU:\Software\Silver Style Entertainment\Soldiers of Anarchy' -Name INSTALLDIR -ErrorAction SilentlyContinue).INSTALLDIR
if ($inst) { Line "INSTALLDIR: $inst" }

$layers = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
$exe = Join-Path $game 'soa.exe'
$layer = (Get-ItemProperty $layers -Name $exe -ErrorAction SilentlyContinue).$exe
if ($layer) { Line "compatibility flag: $layer" }

Write-Host ''
Line 'What the game left behind' 'Cyan'
$sav = Join-Path $game 'SaveGames'
if (Test-Path $sav) {
    $n = (Get-ChildItem $sav -File -ErrorAction SilentlyContinue).Count
    Line "SaveGames:  $n files (saving works)"
}
else { Line 'SaveGames has not appeared yet - no position was saved' 'Yellow' }

# tracefile.log is written by the game itself and usually says outright what
# went wrong.
$trace = Join-Path $game 'tracefile.log'
if (Test-Path $trace) {
    $found = @(Select-String -Path $trace -Pattern 'error|failed|warning' -ErrorAction SilentlyContinue)
    Line ('tracefile.log: {0:N0} B, {1} lines with an error or a warning' -f (Get-Item $trace).Length, $found.Count)
    foreach ($c in ($found | Select-Object -First 10)) { Line ('   ' + $c.Line.Trim()) 'Yellow' }
    New-Item -ItemType Directory -Force -Path 'C:\Test\logs' | Out-Null
    Copy-Item $trace ('C:\Test\logs\tracefile-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss')) -Force
    Line 'a copy of the game log was saved to the host'
}
else { Line 'tracefile.log does not exist - the game has not started yet' 'Yellow' }

New-Item -ItemType Directory -Force -Path 'C:\Test\logs' | Out-Null
[IO.File]::WriteAllLines(('C:\Test\logs\after-run-{0}.txt' -f (Get-Date -Format 'yyyyMMdd-HHmmss')), $lines)
Write-Host ''
Write-Host '  Done. The logs are on the host in the sandbox folder, subfolder logs.' -ForegroundColor Green
