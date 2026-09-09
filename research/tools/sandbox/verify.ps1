# Runs the verification of the game package on clean Windows.
#
# On the machine where the package was built dgVoodoo, the registry settings
# and everything else installed along the way are already there - the package
# "works" there even if something is missing from it. Windows Sandbox
# disappears when it is closed, so it shows exactly the state the package
# arrives in elsewhere.
#
# A .wsb configuration only understands absolute paths, which is why it is not
# carried around ready-made but built from a template right here - the package
# and this folder can then be moved freely.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File verify.ps1 [-Package D:\SoA-Package]

param(
    [string]$Package = 'F:\Games\SoA-Package'
)

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot

if (-not (Test-Path (Join-Path $Package 'Play.exe'))) {
    Write-Host "There is no Play.exe in $Package - that does not look like the game package." -ForegroundColor Red
    exit 1
}
$Package = (Resolve-Path $Package).Path
New-Item -ItemType Directory -Force -Path (Join-Path $here 'logs') | Out-Null

# Fingerprints of the key files and the overall size. The check inside the
# sandbox uses them to tell whether the package arrived whole and undamaged.
$manifest = New-Object System.Collections.Generic.List[string]
foreach ($rel in 'Play.exe', 'Game\soa.exe', 'Game\ddraw.dll', 'Game\D3DImm.dll', 'Game\dgVoodoo.conf') {
    $f = Join-Path $Package $rel
    if (Test-Path $f) { $manifest.Add(('{0}  {1}' -f (Get-FileHash $f -Algorithm SHA256).Hash, $rel)) }
}
$all = Get-ChildItem $Package -Recurse -File
$manifest.Add('FILES {0}' -f $all.Count)
$manifest.Add('BYTES {0}' -f ($all | Measure-Object Length -Sum).Sum)
[IO.File]::WriteAllLines((Join-Path $here 'package.sha256'), $manifest)

$wsb = Join-Path $env:TEMP 'SoA-verification.wsb'
$template = (Get-Content (Join-Path $here 'sandbox.template') -Raw).Replace('__PACKAGE__', $Package).Replace('__TEST__', $here)
[IO.File]::WriteAllText($wsb, $template, [Text.Encoding]::ASCII)

Write-Host ''
Write-Host "  Package: $Package"
Write-Host "  Logs:    $(Join-Path $here 'logs')"
Write-Host ''
Write-Host '  The sandbox is starting. Copying the package into it takes a while.' -ForegroundColor Green
Write-Host '  The logs of the check stay here even after it is closed.' -ForegroundColor Green
Write-Host ''
Start-Process $wsb
