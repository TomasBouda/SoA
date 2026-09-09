# Check of the package on a clean machine. It runs inside the sandbox; the
# result is stored in C:\Test\logs, which is a folder mapped from the host, so
# the log survives closing the sandbox.
$ErrorActionPreference = 'Stop'
$pkg = 'C:\SoA'
$game = Join-Path $pkg 'Game'
$lines = New-Object System.Collections.Generic.List[string]
$errors = 0

function Result([bool]$ok, [string]$text) {
    if (-not $ok) { $script:errors++ }
    $r = '  {0} {1}' -f $(if ($ok) { 'OK   ' } else { 'ERROR' }), $text
    Write-Host $r -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
    $lines.Add($r)
}
function Info([string]$text) {
    $r = '        {0}' -f $text
    Write-Host $r -ForegroundColor Gray
    $lines.Add($r)
}

# --- what has to be in the package ---
foreach ($rel in 'Play.exe', 'readme.txt', 'settings.reg', 'version.txt', 'catalog.txt',
    'Game\soa.exe', 'Game\ddraw.dll', 'Game\D3DImm.dll',
    'Game\dgVoodoo.conf', 'Game\dgVoodooCpl.exe') {
    Result (Test-Path (Join-Path $pkg $rel)) "present in the package: $rel"
}

# --- what must not be in it ---
# Spare exe files and debug output from someone else's machine; SaveGames
# belongs to one particular install and running.lock would stop the game from
# starting outright.
foreach ($rel in 'Game\soa.exe.securom', 'Game\soa.exe.1.1.0.71', 'Game\SaveGames',
    'Game\tracefile.log', 'Game\running.lock', 'Game\replay.log.gz') {
    Result (-not (Test-Path (Join-Path $pkg $rel))) "not left in the package: $rel"
}

# --- fingerprints and size ---
$manifest = 'C:\Test\package.sha256'
if (Test-Path $manifest) {
    foreach ($line in Get-Content $manifest) {
        if ($line -match '^([0-9A-Fa-f]{64})\s\s(.+)$') {
            $expected = $Matches[1]; $rel = $Matches[2]
            $path = Join-Path $pkg $rel
            if (Test-Path $path) {
                Result ((Get-FileHash $path -Algorithm SHA256).Hash -eq $expected) "fingerprint matches: $rel"
            }
            else { Result $false "the fingerprint cannot be checked, $rel is missing" }
        }
        elseif ($line -match '^FILES (\d+)$') {
            $expected = [int]$Matches[1]
            $has = (Get-ChildItem $pkg -Recurse -File).Count
            Result ($has -eq $expected) "the file count matches ($has)"
        }
        elseif ($line -match '^BYTES (\d+)$') {
            $expected = [long]$Matches[1]
            $has = (Get-ChildItem $pkg -Recurse -File | Measure-Object Length -Sum).Sum
            Result ($has -eq $expected) ('the size matches ({0:N0} MB)' -f ($has / 1MB))
        }
    }
}
else { Info 'package.sha256 is missing, the fingerprints are not checked' }

# --- dgVoodoo settings ---
$confPath = Join-Path $game 'dgVoodoo.conf'
if (Test-Path $confPath) {
    $conf = Get-Content $confPath -Raw
    # The keys repeat in several sections of dgVoodoo.conf - Antialiasing exists
    # separately for [Glide] and for [DirectX]. The game runs through DirectX,
    # so we print the section with every value, otherwise the number would say
    # nothing.
    $section = ''
    foreach ($line in Get-Content $confPath) {
        if ($line -match '^\s*\[(.+?)\]\s*$') { $section = $Matches[1]; continue }
        if ($section -notin @('General', 'DirectX')) { continue }
        if ($line -match '^\s*(FullScreenMode|Antialiasing|Filtering|VRAM|Resampling)\s*=\s*(.+?)\s*$') {
            Info ('[{0}] {1} = {2}' -f $section, $Matches[1], $Matches[2])
        }
    }
    # The watermark would draw the dgVoodoo logo across the corner of the image.
    Result ($conf -match '(?m)^\s*dgVoodooWatermark\s*=\s*false') 'the dgVoodoo watermark is off'
}

# --- settings without another machine's resolution ---
$regPath = Join-Path $pkg 'settings.reg'
if (Test-Path $regPath) {
    $reg = Get-Content $regPath -Raw
    Result ($reg -notmatch '"DisplayMode' -and $reg -notmatch '"DDDevice' -and $reg -notmatch '"D3DDevice') `
        'settings.reg carries no resolution from another machine'
}

# --- what the package expects from the system ---
$rel48 = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -Name Release -ErrorAction SilentlyContinue).Release
Result ($rel48 -ge 528040) "the system has .NET Framework 4.8 (Release $rel48), the launcher needs no other runtime"

# --- a genuinely clean state ---
Result (-not (Test-Path 'HKCU:\Software\Silver Style Entertainment')) `
    'there is nothing from the game in the registry yet - the test really starts clean'

$verdict = if ($errors -eq 0) { 'The package is fine, you can run C:\SoA\Play.exe' } else { "$errors things do not match - see above" }
Write-Host ''
Write-Host "  $verdict" -ForegroundColor $(if ($errors -eq 0) { 'Green' } else { 'Yellow' })
$lines.Add('')
$lines.Add($verdict)

New-Item -ItemType Directory -Force -Path 'C:\Test\logs' | Out-Null
[IO.File]::WriteAllLines(('C:\Test\logs\check-{0}.txt' -f (Get-Date -Format 'yyyyMMdd-HHmmss')), $lines)
