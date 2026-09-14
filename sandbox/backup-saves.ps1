# Versioned backup of the saved games.
#
# It does two things:
#   1) a snapshot - every end of a session puts a copy of the saves into its own
#      folder with a timestamp, the last $keep generations are kept
#   2) a mirror   - _saves matches exactly what is in the game, deletions included
#
# The mirroring is safe precisely because of the snapshots: when a save is
# damaged or deleted by mistake, the previous generation lies next to it.
# Without them /MIR would mean that a single bad session overwrites the single
# copy.

param(
    [int]$keep = 5
)

$src  = 'C:\Game\SaveGames'
$mir  = 'C:\SoA\_saves'
$hist = 'C:\SoA\_savehist'

if (-not (Test-Path $src)) {
    Write-Host '[saves] there are no saved games in the game, nothing to do.'
    return
}

# A safety net: an empty source would delete every backup while mirroring.
$savs = @(Get-ChildItem $src -Recurse -File -Filter *.sav -ErrorAction SilentlyContinue)
if ($savs.Count -eq 0) {
    Write-Host '[saves] the source holds no .sav at all - mirroring SKIPPED (safety net).' -ForegroundColor Yellow
    return
}

# --- 1) the snapshot ---
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$dest  = Join-Path $hist $stamp
robocopy $src $dest /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) {
    Write-Host ('[saves] the snapshot failed (robocopy {0})' -f $LASTEXITCODE) -ForegroundColor Red
}
else {
    $sz = (Get-ChildItem $dest -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ('[saves] snapshot {0} ({1} files, {2:N1} MB)' -f $stamp, $savs.Count, $sz)
}

# --- 2) pruning the old generations ---
$all = @(Get-ChildItem $hist -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
if ($all.Count -gt $keep) {
    foreach ($old in $all[$keep..($all.Count - 1)]) {
        Remove-Item $old.FullName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host ('[saves] old generation {0} removed' -f $old.Name)
    }
}
Write-Host ('[saves] generations available: {0} (keeping {1})' -f
            [math]::Min($all.Count, $keep), $keep)

# --- 3) the mirror ---
# /MIR propagates deletions too, so whatever is deleted in the game or on the
# host does not come back with the next export.
robocopy $src $mir /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) {
    Write-Host ('[saves] the mirroring failed (robocopy {0})' -f $LASTEXITCODE) -ForegroundColor Red
}
else {
    Write-Host ('[saves] mirrored into {0}' -f $mir)
    Write-Host '        (on the host: _saves of the repository, the history in _savehist)'
}
