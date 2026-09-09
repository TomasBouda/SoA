# A safety net in case the game crashes or the sandbox is closed while it runs:
# it watches the saves folder and copies them to the host after every change.
#
# prepare.cmd starts it in the background. It runs until the sandbox is closed.
# play.cmd does the same when the game ends normally - this is the backup of the
# backup.
#
# WATCH OUT for files being written: the last write time of an open file is not
# updated continuously, so "wait N seconds after a change" is not enough - the
# game may still be writing. That is why every file is opened exclusively before
# the copy; when that fails, the round is skipped.

$src      = 'C:\Game\SaveGames'
$dst      = 'C:\SoA\_saves'
$log      = 'C:\SoA\_sandbox\logs\watch-saves.log'
$interval = 15

New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

function Note([string]$m) {
    Add-Content -Path $log -Value ('[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m) -ErrorAction SilentlyContinue
}

function Test-FileClosed([string]$path) {
    try {
        $fs = [IO.File]::Open($path, 'Open', 'Read', 'None')   # None = no sharing
        $fs.Close()
        return $true
    }
    catch { return $false }
}

Note '--- watcher started ---'
$lastSync = [DateTime]::MinValue

while ($true) {
    Start-Sleep -Seconds $interval
    if (-not (Test-Path $src)) { continue }

    $files = Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue
    if (-not $files) { continue }

    $newest = ($files | Measure-Object -Property LastWriteTime -Maximum).Maximum
    if ($newest -le $lastSync) { continue }

    # every file has to be closed, otherwise the game is still writing
    $open = $files | Where-Object { -not (Test-FileClosed $_.FullName) }
    if ($open) {
        Note ('skipping, {0} files are open ({1})' -f $open.Count, ($open.Name -join ', '))
        continue
    }

    robocopy $src $dst /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Note ('robocopy failed, code {0}' -f $LASTEXITCODE)
    }
    else {
        $lastSync = $newest
        Note ('synchronised ({0} files, newest {1:HH:mm:ss})' -f $files.Count, $newest)
    }
}
