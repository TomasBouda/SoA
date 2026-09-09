# Behavioural analysis of the game while it runs.
#
# Static analysis of the cracked exe found nothing, but it cannot prove the
# absence of malicious code - an encrypted payload unpacked only at run time
# would not show up in it. This script watches what the process actually does.
#
# Run it INSIDE the sandbox.
#
# Networking: the default state of SoA.wsb is Disable, so any data being sent
# would not get through and the script looks for traces visible without the
# network as well. To test the network behaviour, switch SoA.wsb to Enable
# temporarily and run the script with -UnblockHosts, which removes the GameSpy
# block from hosts - otherwise the real destinations would hide behind
# 127.0.0.1. Put both back afterwards.
#
# The result of the last run is in ../behavior.md.
#
# What it watches:
#   before/after  files in the system and user folders, the registry,
#                 scheduled tasks, services, the run keys
#   while running  child processes, libraries loaded from outside the game
#                  folder, network connections
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File monitor-run.ps1
#   powershell ... -File monitor-run.ps1 -Exe C:\Game\soa.exe -Minutes 5

param(
    [string]$Exe = 'C:\Game\soa.exe',
    [int]$Minutes = 10,
    [string]$OutDir = 'C:\SoA\_sandbox\logs',
    # Removes the GameSpy block prepare.cmd puts into hosts. Off by default so
    # that running the monitor does not change a security setting; it is turned
    # on only when the goal is to learn the real connection destinations.
    [switch]$UnblockHosts
)

$ErrorActionPreference = 'Continue'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$report = Join-Path $OutDir "behavior_$stamp.log"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Say([string]$m, [string]$lvl = 'INFO') {
    $line = '[{0}] {1,-5} {2}' -f (Get-Date -Format 'HH:mm:ss'), $lvl, $m
    $color = switch ($lvl) { 'OK' { 'Green' } 'WARN' { 'Yellow' } 'FIND' { 'Red' } default { 'Gray' } }
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $report -Value $line -ErrorAction SilentlyContinue
}

# --- the places malicious code usually reaches for ---
$watchDirs = @(
    "$env:APPDATA", "$env:LOCALAPPDATA", "$env:TEMP", "$env:PUBLIC",
    "$env:USERPROFILE\Documents", "$env:USERPROFILE\Desktop",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:WINDIR\System32\drivers\etc", "$env:WINDIR\Tasks"
)
$runKeys = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Windows',
    'HKLM:\System\CurrentControlSet\Control\Session Manager'
)


function Snapshot {
    $s = @{}
    $files = @{}
    foreach ($d in $watchDirs) {
        if (-not (Test-Path $d)) { continue }
        foreach ($f in Get-ChildItem $d -Recurse -File -Force -ErrorAction SilentlyContinue) {
            $files[$f.FullName] = '{0}|{1:o}' -f $f.Length, $f.LastWriteTimeUtc
        }
    }
    $s.Files = $files

    $reg = @{}
    foreach ($k in $runKeys) {
        if (-not (Test-Path $k)) { continue }
        $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
        foreach ($n in $p.PSObject.Properties.Name) {
            if ($n -like 'PS*') { continue }
            $reg["$k\$n"] = [string]$p.$n
        }
    }
    $s.Registry = $reg

    $s.Tasks = @{}
    foreach ($t in (Get-ScheduledTask -ErrorAction SilentlyContinue)) {
        $s.Tasks["$($t.TaskPath)$($t.TaskName)"] = $t.State.ToString()
    }
    $s.Services = @{}
    foreach ($sv in (Get-CimInstance Win32_Service -ErrorAction SilentlyContinue)) {
        $s.Services[$sv.Name] = $sv.PathName
    }
    return $s
}


# Changes Windows and the drivers make on their own. They are not hidden, only
# marked as noise so that the real findings do not drown in the report.
$noise = @(
    '*\NVIDIA\DXCache\*',                          # driver shader cache
    '*\UsrClass.dat',                              # the user class registry hive
    '*ModuleAnalysisCache*',                       # PowerShell cache
    '*ActivitiesCache.db*',                        # Windows activity history
    '*\INetCache\*',
    '*\WebCache\*',
    '*\CrashDumps\*',
    '*\AppID\PolicyConverter',
    '*\AppID\VerifiedPublisherCertStoreCheck'
)

# The comparison uses -like with wildcards, not -match. A regular expression
# would be a trap here: in the pattern '\NVIDIA\DXCache\' the \N and \D are
# escape sequences (\D means a non-digit), so it would match nothing.
function IsNoise([string]$s) {
    foreach ($n in $noise) { if ($s -like $n) { return $true } }
    return $false
}

function DiffMaps($before, $after, [string]$label) {
    $added = @($after.Keys | Where-Object { -not $before.ContainsKey($_) })
    $changed = @($after.Keys | Where-Object { $before.ContainsKey($_) -and $before[$_] -ne $after[$_] })
    $real = 0
    foreach ($a in $added) {
        if (IsNoise $a) { Say "$label added (noise): $a" }
        else { Say "$label ADDED: $a" 'FIND'; $real++ }
    }
    foreach ($c in $changed) {
        if (IsNoise $c) { Say "$label changed (noise): $c" }
        else { Say "$label CHANGED: $c" 'FIND'; $real++ }
    }
    if ($real -eq 0) { Say "$label - no suspicious change" 'OK' }
}


Say "report: $report"
Say "watched program: $Exe"
Say ('networking in the sandbox: {0}' -f $(if (Get-NetAdapter -ErrorAction SilentlyContinue) { 'ON' } else { 'off' }))
# --- unblocking GameSpy only on request ---
# prepare.cmd points motd.gamespy.com and master.gamespy.com at 127.0.0.1.
# During the analysis that hides where the game really tries to connect, but it
# is also a safety measure - which is why it is only lifted with -UnblockHosts.
$hosts = "$env:WINDIR\System32\drivers\etc\hosts"
if ($UnblockHosts) {
    try {
        $lines = Get-Content $hosts -ErrorAction Stop
        $clean = $lines | Where-Object { $_ -notmatch 'gamespy' }
        if ($clean.Count -ne $lines.Count) {
            Set-Content -Path $hosts -Value $clean -ErrorAction Stop
            Say ('{0} gamespy lines removed from hosts so the real destinations show' -f ($lines.Count - $clean.Count)) 'WARN'
            Say 'this only lasts until the sandbox closes, prepare.cmd puts them back on the next start' 'WARN'
        }
    }
    catch { Say "hosts could not be edited: $($_.Exception.Message)" 'WARN' }
}
else {
    Say 'the GameSpy block in hosts stays (run with -UnblockHosts to see the real destinations)'
}

# --- the DNS queries the game leaves behind in the cache ---
$dnsBefore = @()
try { $dnsBefore = (Get-DnsClientCache -ErrorAction Stop).Entry } catch { }

Say 'taking the snapshot before the start...'
$before = Snapshot
Say ('  files: {0}, keys: {1}, tasks: {2}, services: {3}' -f
    $before.Files.Count, $before.Registry.Count, $before.Tasks.Count, $before.Services.Count)

Say 'starting the game'
# The working directory has to be the game folder, otherwise it does not find
# its .ubn archives and ends with 0x80070002 (ERROR_FILE_NOT_FOUND).
$proc = Start-Process $Exe -WorkingDirectory (Split-Path $Exe) -PassThru
Start-Sleep -Seconds 3

# --- watching while it runs ---
$seenChild = @{}
$seenModule = @{}
$seenConn = @{}
$deadline = (Get-Date).AddMinutes($Minutes)
$gameDir = Split-Path $Exe

while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
    # child processes
    foreach ($p in (Get-CimInstance Win32_Process -Filter "ParentProcessId=$($proc.Id)" -ErrorAction SilentlyContinue)) {
        $key = "$($p.ProcessId):$($p.Name)"
        if (-not $seenChild.ContainsKey($key)) {
            $seenChild[$key] = $true
            Say "CHILD PROCESS: $($p.Name) - $($p.CommandLine)" 'FIND'
        }
    }
    # libraries loaded from outside the game folder and System32
    try {
        foreach ($m in (Get-Process -Id $proc.Id -ErrorAction Stop).Modules) {
            $path = $m.FileName
            if ($seenModule.ContainsKey($path)) { continue }
            $seenModule[$path] = $true
            if ($path -notlike "$gameDir*" -and $path -notlike "$env:WINDIR*") {
                Say "LIBRARY FROM AN UNEXPECTED PATH: $path" 'FIND'
            }
        }
    }
    catch { }
    # network connections
    foreach ($c in (Get-NetTCPConnection -OwningProcess $proc.Id -ErrorAction SilentlyContinue)) {
        $key = '{0}:{1}' -f $c.RemoteAddress, $c.RemotePort
        if ($c.RemoteAddress -in '0.0.0.0', '::') { continue }
        if (-not $seenConn.ContainsKey($key)) {
            $seenConn[$key] = $true
            Say "CONNECTION: $key ($($c.State))" 'FIND'
        }
    }
    Start-Sleep -Milliseconds 1500
}

if (-not $proc.HasExited) {
    Say 'time is up, waiting for the game to end...' 'WARN'
    $proc.WaitForExit()
}
$code = $proc.ExitCode
if ($code -eq 0) { Say "the game ended normally" 'OK' }
else {
    Say ("the game ended with code {0} (0x{1:X8})" -f $code, ($code -band 0xFFFFFFFF)) 'WARN'
    if (($code -band 0xFFFFFFFF) -eq 0x80070002) {
        Say 'that is ERROR_FILE_NOT_FOUND - the game did not find its files, check the working directory' 'WARN'
    }
}
Say ('while running: children {0}, libraries from unexpected paths {1}, connections {2}' -f
    $seenChild.Count, ($seenModule.Keys | Where-Object { $_ -notlike "$gameDir*" -and $_ -notlike "$env:WINDIR*" }).Count, $seenConn.Count)

Say 'taking the snapshot after the end...'
Start-Sleep -Seconds 2
$after = Snapshot

# new entries in the DNS cache = the names the game asked about
try {
    $dnsAfter = (Get-DnsClientCache -ErrorAction Stop).Entry
    $newDns = @($dnsAfter | Where-Object { $_ -and $dnsBefore -notcontains $_ } | Sort-Object -Unique)
    if ($newDns) {
        foreach ($n in $newDns) { Say "DNS QUERY: $n" 'FIND' }
    }
    else { Say 'DNS - no new queries' 'OK' }
}
catch { Say 'the DNS cache is not available' 'WARN' }

Say ''
Say '=== differences ==='
DiffMaps $before.Files $after.Files 'FILE'
DiffMaps $before.Registry $after.Registry 'REGISTRY'
DiffMaps $before.Tasks $after.Tasks 'TASK'
DiffMaps $before.Services $after.Services 'SERVICE'

Say ''
Say "done, the report is in $report" 'OK'
Say '(on the host: F:\Games\SoA\_sandbox\logs)'
