# Builds a standalone package of the game that runs directly, without a sandbox.
#
# The result is a folder (optionally a ZIP too) with Play.exe to play. It holds
# the game with every change we made - dgVoodoo, fixed sounds, upscaled
# textures, WASD controls - and a launcher that imports the settings on first
# run.
#
# Deliberately NOT packed:
#   soa.exe.securom, soa.exe.1.1.0.71   spare copies of the exe, useless here
#   SaveGames                           saves belong to one particular install
#   tracefile.log, replay.log.gz        debug output
#   running.lock                        lock left after a crash, the game
#                                       refuses to start with it
#
# The DisplayMode* values are dropped from the settings, because they come from
# the sandbox window (2560x1360) and would not fit another machine. The game
# picks the resolution itself on every start from the desktop size - that is
# what the launcher takes care of.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File build-package.ps1
#   powershell ... -File build-package.ps1 -Out D:\SoA-ready -Zip
#
# To verify the package on clean Windows, use _research/tools/sandbox.

param(
    # Which of the packages to build. They come out of the same source and
    # differ in who may have what - see _research/packaging.md.
    #
    #   full     the game with every change we made, and the launcher
    #   vanilla  the game as it shipped, the settings and dgVoodoo, no launcher
    #   kit      the launcher and the wrapper, no game at all
    #   all      each of them, one after the other
    [ValidateSet('full', 'vanilla', 'kit', 'all')]
    [string]$Variant = 'full',
    [string]$Source = 'F:\Games\SoA\_patched',
    [string]$Settings = 'F:\Games\SoA\_sandbox\config\soa-settings.reg',
    [string]$dgVoodoo = 'F:\Games\SoA\_sandbox\tools\dgVoodoo',
    [string]$Out = '',
    [switch]$Zip,
    # Make the changes rather than expect them already made. Point -Source at a
    # plain retail installation and the tools that produce the sharper textures,
    # the repaired sounds and the interface run against it first. This is what
    # lets somebody build the full package from their own copy of the game,
    # since none of those files may be handed out - see _research/packaging.md.
    [switch]$Generate,
    # The upscale is the only step that wants a GPU and torch. It takes under a
    # minute on one and installing torch is 2.5 GB, so it can be left out and
    # everything else still runs.
    [switch]$NoUpscale
)

$ErrorActionPreference = 'Stop'

if ($Variant -eq 'all') {
    foreach ($one in 'full', 'vanilla', 'kit') {
        & $PSCommandPath -Variant $one -Source $Source -Settings $Settings `
                         -dgVoodoo $dgVoodoo -Zip:$Zip
    }
    return
}

# Each variant has a folder of its own unless one was named.
if (-not $Out) {
    $Out = switch ($Variant) {
        'vanilla' { 'F:\Games\SoA-Vanilla' }
        'kit'     { 'F:\Games\SoA-Kit' }
        default   { 'F:\Games\SoA-Package' }
    }
}

# What goes in. The vanilla package is the game as it shipped, so everything we
# added is left out: the upscaled textures and terrain, the repaired sounds and
# the interface with more contrast - all of them loose folders that override
# the archives - and the patched exe, which is swapped for the original further
# down. It keeps dgVoodoo and the settings, because without a wrapper there is
# no game on Windows 11, and without the settings the controls are not on WASD.
# The kit carries no game, and by rule nothing derived from one either - no
# catalog, no upscaled textures, no repaired sounds, no interface of ours. It
# is meant to be handed to someone who owns their own copy, and it works out
# the rest from that copy. See _research/packaging.md.
$wantGame = $Variant -ne 'kit'
$wantOurChanges = $Variant -eq 'full'
$wantLauncher = $Variant -ne 'vanilla'
# The catalog goes into the kit as well. It is derived from the game's data -
# the names and descriptions out of the TRES resources, the 156 icons cut from
# the sheets in gui.ubn - so by the rule the kit was built on it would stay
# out; the owner of the project decided otherwise and that is the decision
# that stands. It does not generalise: the upscaled textures and the repaired
# sounds are a separate question and have not been asked.
$wantCatalog = $Variant -ne 'vanilla'
# SelfTest.exe is ours to run when something needs checking against a real
# game, not something to hand anybody. It stays out of the kit.
$wantSelfTest = $Variant -eq 'full'

function Say([string]$m, [string]$lvl = 'INFO') {
    $color = switch ($lvl) { 'OK' { 'Green' } 'WARN' { 'Yellow' } default { 'Gray' } }
    Write-Host ('  {0,-5} {1}' -f $lvl, $m) -ForegroundColor $color
}

$skipFiles = @('soa.exe.securom', 'soa.exe.1.1.0.71', 'soa.exe.orig', 'tracefile.log',
    'replay.log.gz', 'running.lock', 'Restart.sav', 'Send System Config.lnk')
$skipDirs = @('SaveGames', 'DirectX8')
# Everything we added to the game sits in a loose folder that overrides an
# archive, so the vanilla package is made by not copying four folders.
$ourLooseFolders = @('textures', 'terrain', 'Sounds', 'gui')

# --- version -------------------------------------------------------------
# The package changes under our hands, so it needs a number that says what a
# person has installed. The versions go up on their own according to what
# changed:
#
#   MINOR  game data (_patched) - different textures, sounds, exe, config
#   PATCH  launcher and catalog - code, images, item list
#
# The state lives in version.json next to the script. A fingerprint is a
# listing of paths, sizes and modification times; hashing a gigabyte of data on
# every build would be needlessly expensive and this reliably notices that we
# overwrote something.
function Fingerprint([string[]]$paths) {
    $lines = foreach ($c in $paths) {
        if (Test-Path $c -PathType Container) {
            Get-ChildItem $c -Recurse -File | ForEach-Object {
                '{0}|{1}|{2}' -f $_.FullName.Substring($c.Length), $_.Length, $_.LastWriteTimeUtc.Ticks
            }
        }
        elseif (Test-Path $c) {
            $f = Get-Item $c
            '{0}|{1}|{2}' -f $f.Name, $f.Length, $f.LastWriteTimeUtc.Ticks
        }
    }
    # The order has to be sorted ordinally, not by Sort-Object: that one sorts
    # by culture and Windows PowerShell orders paths differently than
    # PowerShell 7. The same folder then came out with two different
    # fingerprints and the version went up although nothing had changed.
    $lines = [string[]]$lines
    [Array]::Sort($lines, [StringComparer]::Ordinal)
    $text = ($lines -join "`n")
    $sha = [Security.Cryptography.SHA256]::Create()
    $bytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text))
    ($bytes | ForEach-Object { '{0:x2}' -f $_ }) -join ''
}

$stateFile = Join-Path $PSScriptRoot 'version.json'
$state = if (Test-Path $stateFile) { Get-Content $stateFile -Raw | ConvertFrom-Json }
         else { [pscustomobject]@{ version = '1.0.0'; dataFingerprint = ''; launcherFingerprint = '' } }

$dataFingerprint = Fingerprint @($Source)
$launcherFingerprint = Fingerprint @((Join-Path $PSScriptRoot 'launcher'))

$numbers = $state.version.Split('.') | ForEach-Object { [int]$_ }
$reason = 'no change'
if ($dataFingerprint -ne $state.dataFingerprint) {
    $numbers[1]++; $numbers[2] = 0
    $reason = 'the game data changed'
}
elseif ($launcherFingerprint -ne $state.launcherFingerprint) {
    $numbers[2]++
    $reason = 'the launcher or the catalog changed'
}
$version = '{0}.{1}.{2}' -f $numbers[0], $numbers[1], $numbers[2]

Write-Host ''
Write-Host ("=== Building the $Variant package ===") -ForegroundColor Cyan

# --- 0. is anything from the package running? ---
# The build deletes the target folder first. A running Play.exe or soa.exe holds
# its own file, so the deletion dies halfway through and what is left behind is
# a package with the game data already gone. Better to refuse before touching
# anything.
if (-not $wantOurChanges) { $skipDirs += $ourLooseFolders }

$busy = @(Get-Process -Name 'Play', 'soa' -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($Out, [StringComparison]::OrdinalIgnoreCase) })
if ($busy) {
    $what = ($busy | ForEach-Object { '{0} (pid {1})' -f $_.ProcessName, $_.Id }) -join ', '
    throw "$what is running from $Out - close it and run the build again."
}

# --- 0b. make the changes, when asked ---
# Each tool writes loose files beside the game's archives, which the engine
# reads in preference to them - so this adds to an installation and takes
# nothing away, and each tool can undo its own work. SOA_SOURCE is how they are
# all pointed at the same place.
if ($Generate) {
    if (-not $wantOurChanges) {
        throw "-Generate only means anything for the full package - the $Variant one carries none of our changes."
    }
    Say "generating our changes into $Source"
    $env:SOA_SOURCE = $Source
    $steps = @(
        @{ what = 'the sounds the game asks for and never shipped'; run = @('fix_missing_sounds.py', '--install') },
        @{ what = 'the interface, with its dark and light pulled apart'; run = @('hud_contrast.py', '--apply') },
        @{ what = 'the portraits'; run = @('upscale_faces.py', '--apply') }
    )
    if (-not $NoUpscale) {
        $steps += @{ what = 'the object textures'; run = @('upscale_textures.py', 'ALL', '--install') }
        $steps += @{ what = 'the terrain textures'; run = @('upscale_terrain.py', '--install') }
        # The details - roads, tracks, grass - are cut out of shared sheets
        # rather than standalone, so they are a step of their own.
        $steps += @{ what = 'the detail textures of the ground'; run = @('upscale_details.py', '--install') }
    }
    foreach ($step in $steps) {
        $tool = Join-Path $PSScriptRoot $step.run[0]
        Say ('  ' + $step.what)
        & py -3 $tool @($step.run[1..($step.run.Count - 1)]) 2>&1 | ForEach-Object {
            Write-Host ('        ' + $_) -ForegroundColor DarkGray
        }
        if ($LASTEXITCODE -ne 0) { throw ('{0} failed with {1}' -f $step.run[0], $LASTEXITCODE) }
    }
    if ($NoUpscale) { Say 'the textures were left alone (-NoUpscale)' 'WARN' }
    Say 'our changes are in place' 'OK'
}

$game = Join-Path $Out 'Game'
if (-not $wantGame) {
    # No game step to clear the folder, so the kit clears it itself.
    if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
}

# The kit has no game in it - it is pointed at one the player already
# owns - so the copy, the exe and the saves are all somebody else's.
if ($wantGame) {
# --- 1. the game ---
Say "copying the game from $Source"
if (-not (Test-Path "$Source\soa.exe")) { throw "there is no soa.exe in $Source" }

# Saves survive a rebuild. The package is built from scratch, but once it has
# been played from, it holds saves that exist nowhere else - deleting them for
# the sake of a rebuild is data loss.
$saves = Join-Path $game 'SaveGames'
$parkedSaves = $null
if (Test-Path $saves) {
    $parkedSaves = Join-Path ([IO.Path]::GetTempPath()) ('soa-saves-' + [Guid]::NewGuid().ToString('N'))
    Move-Item $saves $parkedSaves
    $howMany = @(Get-ChildItem $parkedSaves -Recurse -File -Filter *.sav).Count
    Say "parking the saves ($howMany), they go back after the rebuild" 'WARN'
}

# From here to putting the saves back everything runs in try/finally. If the
# rebuild dies halfway through - because the game is running and holding files,
# say - the saves would otherwise stay in TEMP and disappear from the package.
try {
    if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $game | Out-Null

    $xf = $skipFiles | ForEach-Object { '/XF'; $_ }
    $xd = $skipDirs | ForEach-Object { '/XD'; $_ }
    robocopy $Source $game /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP @xf @xd | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "copying failed (robocopy $LASTEXITCODE)" }
}
finally {
    if ($parkedSaves -and (Test-Path $parkedSaves)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $saves -Parent) | Out-Null
        Move-Item $parkedSaves $saves
        Say 'saves restored' 'OK'
    }
}

# Which soa.exe ends up in the package.
#
# For vanilla it is the original: soa.exe.orig is the shipped 1.1.2.178 with
# the copy protection taken off and none of our patches - nine bytes separate
# it from ours.
#
# For full it is ours, but it has to be put into a known state first. The
# launcher rewrites soa.exe on every Play according to the window mode chosen,
# so without this the package would carry whatever the last run happened to
# leave behind. The state written here is what a person sees the first time
# they open the launcher.
$exe = Join-Path $game 'soa.exe'
if (-not $wantOurChanges) {
    $original = Join-Path $Source 'soa.exe.orig'
    if (-not (Test-Path $original)) { throw "vanilla needs $original and it is not there" }
    Copy-Item $original $exe -Force
    Say 'soa.exe is the original, without our patches' 'OK'
}
else {
    $patcher = Join-Path $PSScriptRoot 'patch_exe.py'
    if (Test-Path $patcher) {
        & py -3 $patcher --exe $exe --fullscreen --no-intro --keep-focus --share-log --camera --fast-camera --active-pause --mailbox --airstrike-menu | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'putting soa.exe into a known state failed' }
        Say 'soa.exe set to full screen, no intro, keeps focus, shared log, free and fast camera, active pause, mailbox, air strike in the menu' 'OK'
    }
    else { Say 'patch_exe.py not found, soa.exe goes in as it was found' 'WARN' }

    # The radio calls the air strike button plays go into sounds.ubn: the
    # game finds a sound by its bare name in the archive's directory, and a
    # new loose file is not found at all. add_sounds.py appends by hand and
    # skips what is already there. The source's own archive stays as it was
    # shipped - the clips are the package's, put in here every build.
    $adder = Join-Path $PSScriptRoot 'add_sounds.py'
    $clips = Get-ChildItem (Join-Path $PSScriptRoot 'launcher') -Filter 'radio_airstrike_*.wav' | ForEach-Object { $_.FullName }
    if ((Test-Path $adder) -and $clips) {
        & py -3 $adder (Join-Path $game 'sounds.ubn') 'sounds/InGame/misc' @clips | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'putting the radio calls into sounds.ubn failed' }
        Say "radio calls in sounds.ubn ($($clips.Count) clips, sounds/InGame/misc)" 'OK'
    }
}

$n = (Get-ChildItem $game -Recurse -File).Count
$mb = [math]::Round((Get-ChildItem $game -Recurse -File | Measure-Object Length -Sum).Sum / 1MB)
Say "$n files, $mb MB" 'OK'

}

# --- 2. dgVoodoo ---
Say 'checking dgVoodoo'
# The kit has no game folder to put the wrapper in, so it carries it beside the
# launcher and the readme says where it goes. Without it there is no game on
# Windows 11 at all, which is why it travels with the kit rather than being
# left to the player to find.
$wrapperTo = if ($wantGame) { $game } else { Join-Path $Out 'dgVoodoo' }
New-Item -ItemType Directory -Force -Path $wrapperTo | Out-Null
# dgVoodoo.conf is always overwritten, not only when missing: _patched holds an
# old untuned copy (app-driven filtering, watermark on), while the tuned one
# lives in _sandbox/tools/dgVoodoo and is only copied into the sandbox at run
# time.
foreach ($f in @('ddraw.dll', 'D3DImm.dll', 'dgVoodoo.conf')) {
    if ($f -ne 'dgVoodoo.conf' -and (Test-Path (Join-Path $wrapperTo $f))) { continue }
    $src = switch ($f) {
        'ddraw.dll' { Join-Path $dgVoodoo 'MS\x86\DDraw.dll' }
        'D3DImm.dll' { Join-Path $dgVoodoo 'MS\x86\D3DImm.dll' }
        default { Join-Path $dgVoodoo $f }
    }
    if (Test-Path $src) { Copy-Item $src (Join-Path $wrapperTo $f) -Force; Say "deployed: $f" }
    else { Say "MISSING and not found: $f" 'WARN' }
}
Say 'wrapper in place' 'OK'

# --- 3. settings without the resolution ---
Say 'preparing the settings'
if (Test-Path $Settings) {
    $raw = [IO.File]::ReadAllBytes($Settings)
    $enc = if ($raw[0] -eq 0xFF -and $raw[1] -eq 0xFE) { [Text.Encoding]::Unicode } else { [Text.Encoding]::Default }
    # GetString leaves the byte order mark in the string as a character;
    # WriteAllText then adds its own and the file starts with two BOMs in a row.
    # reg.exe refuses such a file with "The specified file is not a registry
    # file" - and because the import was done silently, it only showed up as the
    # game having the default keys.
    $lines = $enc.GetString($raw).TrimStart([char]0xFEFF) -split "`r?`n"
    $keep = $lines | Where-Object { $_ -notmatch '^"DisplayMode' -and $_ -notmatch '^"DDDevice' -and $_ -notmatch '^"D3DDevice' }
    $dropped = $lines.Count - $keep.Count
    [IO.File]::WriteAllText((Join-Path $Out 'settings.reg'), ($keep -join "`r`n"), $enc)
    Say "dropped $dropped display values (they come from another machine)" 'OK'
}
else { Say 'the settings file was not found, the package will go without it' 'WARN' }

# The vanilla package has no launcher: the game is started directly and
# the settings are imported by double-clicking settings.reg.
if ($wantLauncher) {
# --- 4. launcher ---
# We compile a WPF desktop application. Against a batch file it can do the
# things that matter: read the current desktop resolution, offer the display
# mode and antialiasing, and write everything where it belongs - the resolution
# into the registry, the rest into dgVoodoo.conf. The .NET Framework 4.8 that
# ships with Windows is enough, so the package needs no extra SDK or runtime.
# Everything the launcher reaches into the game for is tied to one build of
# soa.exe and fails quietly when it moves. check.py compares those addresses
# against what is pinned in addresses.json, checks the patch signatures are
# unique and reverse byte for byte, and that the catalog still agrees with
# Data.set. A second, and it saves finding out by playing.
if ($wantGame) {
    Say 'checking the addresses and the patches'
    $check = & py -3 (Join-Path $PSScriptRoot 'check.py') 2>&1
    if ($LASTEXITCODE -ne 0) {
        $check | ForEach-Object { Write-Host "    $_" }
        throw 'check.py failed - the package would not work; see the lines above'
    }
    Say 'the exe still holds what the launcher expects' 'OK'
}
else {
    Say 'no exe here to check - the kit checks the one it is pointed at, when it runs'
}

Say 'compiling the launcher'
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" }
# The version is packed in as a generated source file so the launcher can show
# it and so that Play.exe itself carries it too.
$versionCs = Join-Path $env:TEMP 'SoA-BuildInfo.cs'
@"
// Generated by build-package.ps1, editing it by hand makes no sense.
using System.Reflection;

[assembly: AssemblyVersion("$version.0")]
[assembly: AssemblyFileVersion("$version.0")]
[assembly: AssemblyTitle("Soldiers of Anarchy - launcher")]

internal static class BuildInfo
{
    public const string Package = "$version";
    public const string Built = "$(Get-Date -Format 'yyyy-MM-dd')";
}
"@ | Set-Content $versionCs -Encoding UTF8

$src = @((Join-Path $PSScriptRoot 'launcher\App.cs'),
         (Join-Path $PSScriptRoot 'launcher\Catalog.cs'),
         (Join-Path $PSScriptRoot 'launcher\Console.cs'),
         (Join-Path $PSScriptRoot 'launcher\GameLink.cs'),
         (Join-Path $PSScriptRoot 'launcher\CatalogData.cs'),
         (Join-Path $PSScriptRoot 'launcher\GamePath.cs'),
         (Join-Path $PSScriptRoot 'launcher\Inspect.cs'),
         (Join-Path $PSScriptRoot 'launcher\Inventory.cs'),
         (Join-Path $PSScriptRoot 'launcher\Models.cs'),
         (Join-Path $PSScriptRoot 'launcher\ModelsWindow.cs'),
         (Join-Path $PSScriptRoot 'launcher\Map.cs'),
         (Join-Path $PSScriptRoot 'launcher\Patches.cs'),
         (Join-Path $PSScriptRoot 'launcher\Keys.cs'),
         (Join-Path $PSScriptRoot 'launcher\KeysData.cs'),
         (Join-Path $PSScriptRoot 'launcher\Remote.cs'),
         (Join-Path $PSScriptRoot 'launcher\Saves.cs'),
         (Join-Path $PSScriptRoot 'launcher\SelfTest.cs'),
         $versionCs)
# The WPF reference assemblies. System.dll and System.Core.dll are not listed -
# csc adds them itself and a manual reference would end in a double import
# error.
$refDir = "${env:ProgramFiles(x86)}\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8"
if (-not (Test-Path $csc)) { throw 'csc.exe not found' }
foreach ($f in $src) { if (-not (Test-Path $f)) { throw "$f not found" } }
if (-not (Test-Path $refDir)) { throw "the .NET Framework 4.8 reference assemblies were not found in $refDir" }

# The catalog goes inside the exe. It used to sit beside it as catalog.txt and
# a folder of 156 pictures - 2.6 MB of loose files in a package where nothing
# else is loose - and the launcher reads it out of its own resources now.
#
# In both packages that have a launcher. Vanilla has none, so it has no
# catalog either.
$catalogSource = Join-Path $PSScriptRoot 'launcher\catalog.txt'
$catalogImages = Join-Path $PSScriptRoot 'launcher\catalog'
$catalogZip = $null
if ($wantCatalog -and (Test-Path $catalogSource)) {
    $staging = Join-Path ([IO.Path]::GetTempPath()) ('soa-catalog-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    Copy-Item $catalogSource (Join-Path $staging 'catalog.txt') -Force
    if (Test-Path $catalogImages) {
        $into = Join-Path $staging 'catalog'
        New-Item -ItemType Directory -Force -Path $into | Out-Null
        Copy-Item (Join-Path $catalogImages '*.png') $into -Force
    }
    $catalogZip = Join-Path ([IO.Path]::GetTempPath()) ('soa-catalog-' + [Guid]::NewGuid().ToString('N') + '.zip')
    Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $catalogZip -CompressionLevel Optimal
    Remove-Item $staging -Recurse -Force
    Say ('catalog packed into the exe ({0:N0} kB)' -f ((Get-Item $catalogZip).Length / 1KB)) 'OK'
}

$exeOut = Join-Path $Out 'Play.exe'
$cscArgs = @('/nologo', '/target:winexe', '/platform:anycpu', '/optimize+',
             '/main:Program', "/out:$exeOut")
foreach ($r in 'PresentationFramework.dll', 'PresentationCore.dll', 'WindowsBase.dll', 'System.Xaml.dll',
              'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll') {
    $cscArgs += "/reference:$refDir\$r"
}
# The game icon, pulled out of soa.exe by extract_icon.py. WPF uses it for the
# window and the taskbar as well, because the launcher sets no Icon of its own.
$icon = Join-Path $PSScriptRoot 'launcher\soa.ico'
if ($catalogZip) { $cscArgs += "/resource:$catalogZip,SoA.Catalog" }
# The radio calls the air strike plays, made by radio_clip.py - one resource
# per variant, SoA.Radio.a, SoA.Radio.b and so on, and the launcher picks one
# at random. Without any the strike is silent, which is not an error.
foreach ($radio in Get-ChildItem (Join-Path $PSScriptRoot 'launcher') -Filter 'radio_airstrike_*.wav') {
    $radioName = $radio.BaseName.Substring('radio_airstrike_'.Length)
    $cscArgs += "/resource:$($radio.FullName),SoA.Radio.$radioName"
}
if (Test-Path $icon) { $cscArgs += "/win32icon:$icon" }
else { Say 'launcher\soa.ico is missing, Play.exe will have no icon' 'WARN' }
$cscArgs += $src
& $csc $cscArgs | Out-Null
if (-not (Test-Path $exeOut)) { throw 'compiling the launcher failed' }
Say ('Play.exe compiled ({0:N0} B)' -f (Get-Item $exeOut).Length) 'OK'

# The same sources again, as a console program. A window program cannot be
# waited for from a command line and has nowhere to print, so the checks that
# need the game get an executable of their own; /main picks which entry point
# each build uses.
#
# Only in the full package: it is a tool for working on this, and it starts the
# game and drives it about, which is not a thing to leave lying in a package
# somebody else opens.
if ($wantSelfTest) {
$testOut = Join-Path $Out 'SelfTest.exe'
$testArgs = @('/nologo', '/target:exe', '/platform:anycpu', '/optimize+',
              '/main:SelfTest', "/out:$testOut")
foreach ($r in 'PresentationFramework.dll', 'PresentationCore.dll', 'WindowsBase.dll', 'System.Xaml.dll',
              'System.IO.Compression.dll', 'System.IO.Compression.FileSystem.dll') {
    $testArgs += "/reference:$refDir\$r"
}
$testArgs += $src
& $csc $testArgs | Out-Null
if (-not (Test-Path $testOut)) { throw 'compiling SelfTest.exe failed' }
Say ('SelfTest.exe compiled ({0:N0} B)' -f (Get-Item $testOut).Length) 'OK'
}

# The catalog is inside Play.exe now - see where it is packed, above. Nothing
# is copied beside it any more.
if ($catalogZip) {
    Remove-Item $catalogZip -Force -ErrorAction SilentlyContinue
    $rows = (Get-Content $catalogSource | Where-Object { $_ -and $_[0] -ne '#' }).Count
    $shots = if (Test-Path $catalogImages) { (Get-ChildItem $catalogImages -Filter *.png).Count } else { 0 }
    Say "catalog: $rows items and $shots pictures, inside the exe" 'OK'
}
elseif (-not $wantCatalog) {
    Say 'no catalog: this package has no launcher to show one in'
}
else { Say 'catalog.txt is missing, run tools/gen_catalog.py' 'WARN' }

# Config.cmd is no longer produced. It was a shortcut for "Play.exe -o" from the
# days when the launcher had no window; today the Game settings button does the
# same. The launcher still accepts the -o argument, so anyone can make the
# shortcut themselves.

}

# --- 4b. is vanilla really vanilla? ---
# By construction it should be, but the whole point of the variant is that it
# carries nothing of ours, and a mistake there would be invisible - the game
# would simply look better than it should.
if ($Variant -eq 'vanilla') {
    $leaked = $ourLooseFolders | Where-Object { Test-Path (Join-Path $game $_) }
    if ($leaked) { throw ("the vanilla package carries our changes: " + ($leaked -join ', ')) }
    $ours = Get-FileHash (Join-Path $Source 'soa.exe.orig') -Algorithm SHA256
    $packed = Get-FileHash (Join-Path $game 'soa.exe') -Algorithm SHA256
    if ($ours.Hash -ne $packed.Hash) { throw 'the packed soa.exe is not the original' }
    if (Test-Path (Join-Path $Out 'Play.exe')) { throw 'the vanilla package has a launcher in it' }
    Say 'checked: the original exe, and none of our changes' 'OK'
}

# --- 5. readme ---
Say 'writing readme.txt'
if ($Variant -eq 'kit') {
$readme = @'
Soldiers of Anarchy - the kit
=============================

To start:  Play.exe

This is the launcher and the tools that go with it. There is no game in it -
it is meant for someone who already owns a copy of the game, which this cannot
replace and does not try to.

The first time it runs it looks for the game in three places - a Game folder
beside the launcher, wherever it was pointed at before, and the install path in
the registry. If none of them has a soa.exe it says so, and the button "Find
the game..." asks for one. The answer is remembered.

The launcher expects soa.exe version 1.1.2.178, the last official patch.
Another build will still start, but the catalog, the console and the map read
addresses that only hold for that one, and the launcher says so rather than
pretending.

The wrapper
-----------

The dgVoodoo folder holds ddraw.dll, D3DImm.dll and dgVoodoo.conf. Copy all
three next to soa.exe. They stand in for the DirectDraw that Windows no longer
has; without them the game gets as far as a black screen.

The settings
------------

settings.reg carries the controls on WASD and the detail levels. Double-click
it once. The launcher writes the resolution itself.
'@
}
elseif ($Variant -eq 'vanilla') {
$readme = @'
Soldiers of Anarchy - as it shipped
===================================

To start:  Game\soa.exe

Import settings.reg once first, by double-clicking it. It carries the controls
on WASD and the detail levels; without it the game starts on its own defaults
and the camera will not move with the keys most people expect.

This package is the game as it was released, patched to 1.1.2.178, which was
the last official patch. It is not the one with our changes in it - there are
no upscaled textures, the body hit sounds are as silent as they were in 2002,
and the interface is at its original contrast.

Two things are not original, and both of them are the reason it runs at all:

* soa.exe has the copy protection removed. The protected one does not start on
  Windows 11 at all, so there was no version of this package with it in.
* dgVoodoo is in the folder - ddraw.dll, D3DImm.dll and dgVoodoo.conf. It
  stands in for the DirectDraw that Windows no longer has. Without it the game
  gets as far as a black screen.

There is no launcher here, so the game keeps whatever resolution is in the
registry and does not follow the monitor. Changing it is Game\soa.exe -o, the
game's own settings dialog.

Saves go in Game\SaveGames.
'@
}
else {
$readme = @'
Soldiers of Anarchy - ready to play
===================================

To start:  Play.exe

The launcher starts the game. When Game\soa.exe is started directly instead,
the default controls stay in place - the keys and detail levels live in the
registry and it is the launcher that puts them there from settings.reg. Anyone
who wants to start the game directly can double-click settings.reg once;
Windows imports it on its own.

The launcher preselects the resolution from the desktop size and writes it into
the registry for the game; the game does not adapt on its own and remembers the
last one used. Display mode, antialiasing and texture mipmaps are both read and
written in dgVoodoo.conf, so the window always shows the real state, not the
defaults.

Mipmapping deserves a word: the engine builds a pyramid of smaller copies of
every texture and at a normal camera height it draws a lower level. The textures
in this package are upscaled, so most of the gain is lost that way - which is
why the default is "off". The price is shimmering on distant surfaces; whoever
minds it can switch to "game controlled".

The "Game settings" button opens the configuration dialog of the game itself -
texture and shadow detail, filtering, volumes. It has its own list of
resolutions and overwrites the setting its own way. "Play.exe -o" from the
command line does the same.

The "Catalog" button opens the list of gear and vehicles that can be added to
the base - 156 items, searchable by name. The window stays above the game, so
there is no need to switch anywhere. It only works on the base screen, not
during a mission. It can also be started on its own: Play.exe -catalog.

SelfTest.exe starts the game, walks it through everything the launcher can do
to it - a cheat, loading a mission, reading the map, quick save and quick load
- closes it again and writes selftest.txt. Run it from a command line and it
prints as it goes and waits to be finished; "Play.exe -selftest" does the same
in a window for anyone who would rather double-click. It is for checking that a
change did not quietly break something; playing does not need it.

The "Map" button opens the map of the running mission - what the engine walks
on, read out of the game several times a second and drawn here. It is the only
way to see it while the game is full screen. Nothing is written back to the
game.

The "Console" button opens a window with the game's log as it is written - what
it loaded, what it did not find, why it stopped - and a line to type commands
into. The base cheats (soldierspawn, allvehicles, equipment(number) and so on)
are taken on the base screen, the mission ones (immortalone, endlessmunition,
winmission, speedhack) inside a running mission. Type "help" there for the whole
list. Both windows stay above the game.

What is different from the original
-----------------------------------
* version 1.1.2.178, that is the last official patch
* dgVoodoo2 translates DirectDraw7 and Direct3D7 to Direct3D11; without it the
  game either does not start on Windows 10 and 11, or it flickers
* fixed body hit sounds - in the original they never played because of a 2002
  bug in the archive (the file name written in two different encodings)
* upscaled object and terrain textures (Real-ESRGAN, twice the size)
* camera on WASD, turning with Q/E, orders moved off the colliding keys:
  attack T, stop Z, kneel K, AI behaviour N/L/U

Saved games
-----------
They are created in the Game\SaveGames folder. To back them up, copy it.

When something does not work
----------------------------
* The game writes its own log into Game\tracefile.log - it usually says
  outright what went wrong.
* Graphics are tuned by dgVoodooCpl.exe in the Game folder. With antialiasing
  trouble (dark frames around trees) lower Antialiasing to 4x or off.
* Fullscreen is switched in dgVoodooCpl.exe through FullScreenMode. The default
  is windowed, because mouse capture works reliably there.
'@
}
[IO.File]::WriteAllText((Join-Path $Out 'readme.txt'), $readme, [Text.Encoding]::Default)
Say 'readme done' 'OK'

# --- 6. optional ZIP ---
if ($Zip) {
    $zipPath = "$Out.zip"
    Say "packing into $zipPath (this takes a while)"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path (Join-Path $Out '*') -DestinationPath $zipPath -CompressionLevel Optimal
    Say ('done, {0:N0} MB' -f ((Get-Item $zipPath).Length / 1MB)) 'OK'
}

# The version number inside the package, so it is possible to tell what a person
# has installed.
$versionText = @"
Soldiers of Anarchy - $Variant package $version
Built: $(Get-Date -Format 'yyyy-MM-dd HH:mm')
Reason for the bump: $reason

MINOR goes up when the game data changes, PATCH when the launcher or the
catalog does. The fingerprints below are there for comparison, they are not
checksums of the content.

Game data fingerprint: $dataFingerprint
Launcher fingerprint:  $launcherFingerprint
"@
[IO.File]::WriteAllText((Join-Path $Out 'version.txt'), $versionText, [Text.Encoding]::Default)

[pscustomobject]@{
    version = $version
    dataFingerprint = $dataFingerprint
    launcherFingerprint = $launcherFingerprint
    built = (Get-Date -Format 'yyyy-MM-dd HH:mm')
} | ConvertTo-Json | Set-Content $stateFile -Encoding UTF8
Say "package version $version ($reason)" 'OK'

$total = [math]::Round((Get-ChildItem $Out -Recurse -File | Measure-Object Length -Sum).Sum / 1MB)
Write-Host ''
$howToStart = if ($wantLauncher) { 'Play.exe' } else { 'Game\soa.exe, after importing settings.reg' }
Write-Host ("The $Variant package $version is in $Out ($total MB). Start it with $howToStart.") -ForegroundColor Green

# robocopy returns 1 on a successful copy; without this the script would report
# an error
exit 0
