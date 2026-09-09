# A screenshot out of the sandbox.
#
# The sandbox has the clipboard disabled, so a screenshot cannot simply be
# copied to the host. A mapped folder works both ways though: whatever is saved
# into it shows up outside straight away.
#
# Usage (inside the sandbox):
#   snap.cmd        grabs the screen after five seconds
#   snap.cmd 10     after ten - time to switch into the game
#   snap.cmd 5 3    three shots five seconds apart

param(
    [int]$Delay = 5,
    [int]$Count = 1,
    [string]$To
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# Where it can write depends on which sandbox is running: the development one
# maps the whole repository as C:\SoA, the verification one maps the tool folder
# as C:\Test. They are told apart by their contents, not by the drive letter -
# that always exists.
if (-not $To) {
    if (Test-Path 'C:\SoA\_gameout') { $To = 'C:\SoA\_gameout\screens' }
    elseif (Test-Path 'C:\Test\prepare.cmd') { $To = 'C:\Test\screens' }
    else { $To = Join-Path ([Environment]::GetFolderPath('Desktop')) 'screens' }
}
New-Item -ItemType Directory -Force -Path $To | Out-Null

Write-Host ''
Write-Host "  The shots go to $To" -ForegroundColor Green
if ($To -like 'C:\SoA\*' -or $To -like 'C:\Test\*') {
    Write-Host '  That folder is mapped, so they show up on the host straight away.' -ForegroundColor Green
}
Write-Host ''

for ($i = 1; $i -le $Count; $i++) {
    Write-Host ("  {0}/{1}: switch into the game, grabbing in {2} s" -f $i, $Count, $Delay)
    Start-Sleep -Seconds $Delay

    $r = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp = New-Object System.Drawing.Bitmap $r.Width, $r.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($r.X, $r.Y, 0, 0, $bmp.Size)
    $g.Dispose()

    $file = Join-Path $To ('snap-{0}.png' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host ("      saved: {0} ({1:N0} kB)" -f (Split-Path $file -Leaf), ((Get-Item $file).Length / 1KB)) -ForegroundColor Green
}
