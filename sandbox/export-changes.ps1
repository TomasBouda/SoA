# Pulls everything the game created or changed out of the sandbox.
#
# The game runs from the local disk C:\Game, which is thrown away when the
# sandbox closes. play.cmd deals with the saves separately, but the game and
# above all the MISSION EDITOR write elsewhere as well - new missions, maps,
# exported heights. Instead of guessing where exactly, the whole tree is
# compared against the original copy in _patched and the difference is carried
# out.

$game = 'C:\Game'
$base = 'C:\SoA\_patched'
$out  = 'C:\SoA\_gameout'

# The files the sandbox preparation puts there, or ordinary rubbish - there is
# no point dragging those to the host.
$skipNames = @('ddraw.dll', 'D3DImm.dll', 'dgVoodooCpl.exe', 'dgVoodoo.conf',
               'play.cmd', 'running.lock', 'replay.log.gz', 'dgVoodoo.log',
               'tracefile.log')
# SaveGames is handled separately by play.cmd / watch-saves.ps1
$skipDirs  = @('SaveGames')

if (-not (Test-Path $game)) {
    Write-Host '[export] C:\Game does not exist, nothing to export.'
    return
}

$found = @()
foreach ($f in Get-ChildItem $game -Recurse -File -ErrorAction SilentlyContinue) {
    $rel = $f.FullName.Substring($game.Length).TrimStart('\')
    $top = $rel.Split('\')[0]
    if ($skipDirs -contains $top) { continue }
    if ($skipNames -contains $f.Name) { continue }

    $ref = Join-Path $base $rel
    if (Test-Path $ref) {
        $r = Get-Item $ref
        # the same size and time = unchanged
        if ($r.Length -eq $f.Length -and
            [math]::Abs(($r.LastWriteTime - $f.LastWriteTime).TotalSeconds) -lt 2) { continue }
        $why = 'changed'
    }
    else { $why = 'new' }

    $dest = Join-Path $out $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item $f.FullName $dest -Force -ErrorAction SilentlyContinue
    $found += [pscustomobject]@{ Rel = $rel; Why = $why; KB = [math]::Round($f.Length / 1KB, 1) }
}

if ($found) {
    Write-Host ('[export] {0} files carried into {1}:' -f $found.Count, $out)
    foreach ($x in $found) {
        Write-Host ('           {0,-9} {1,8} kB  {2}' -f $x.Why, $x.KB, $x.Rel)
    }
    Write-Host '           (on the host: _gameout of the repository)'
}
else {
    Write-Host '[export] the game created nothing new.'
}
