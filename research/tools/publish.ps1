<#
.SYNOPSIS
    Copies the part of this project that may be public into the GitHub
    repository, and pushes it.

.DESCRIPTION
    The two repositories are separate on purpose. This one holds the game -
    its archives, its executable, the upscaled textures, the saves - and none
    of that is ours to hand out. github.com/TomasBouda/SoA holds our own
    writing and our own code, and nothing else.

    Nothing propagated between them until this script existed: the public
    repository was updated by hand, from a working copy in a temporary folder,
    which is a way of working that goes wrong quietly. A tool changes here and
    the public copy silently stays old; a new file appears and somebody has to
    remember whether it may go out.

    So the rule this enforces is an **allow list, not a deny list**. A file
    goes out because a rule below names it, and a new file that no rule names
    stays here. Getting that the wrong way round is how the game's own data
    ends up published by accident, and it cannot be taken back once it is.

    It refuses to publish anything that looks like the game's data even when a
    rule would allow it - see the guard further down. That check exists because
    the allow list is written by hand and hands slip.

.EXAMPLE
    publish.ps1
    What would change, and nothing else. This is the default on purpose.

.EXAMPLE
    publish.ps1 -Push -Message "Read the mission scripts"
    Copy, commit and push.
#>
param(
    # Where the public repository is checked out. It is cloned if missing.
    [string]$Public = 'F:\Games\SoA-Public',
    [string]$Remote = 'https://github.com/TomasBouda/SoA.git',
    [string]$Message = '',
    # Without this the script only says what it would do.
    [switch]$Push
)

$ErrorActionPreference = 'Stop'
$Source = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\Games\SoA

# The commits must carry this and nothing else. The e-mail is what GitHub pairs
# a commit with an account by, and the obvious-looking one on this machine
# belongs to a different account - which put two strangers in the contributor
# list and needed the history rewritten to get out again. No Co-Authored-By
# either: GitHub counts a co-author as a contributor.
$AuthorName = 'Tomáš Bouda'
$AuthorMail = 'email@tomasbouda.cz'

function Say([string]$m, [string]$lvl = 'INFO') {
    $color = switch ($lvl) { 'OK' { 'Green' } 'WARN' { 'Yellow' } 'BAD' { 'Red' } default { 'Gray' } }
    Write-Host ('  {0,-5} {1}' -f $lvl, $m) -ForegroundColor $color
}

# --- what may go out ------------------------------------------------------
# From, to, and which files. Everything else stays in this repository.
$rules = @(
    @{ from = '_research';                  to = 'research';                 files = '*.md' }
    @{ from = '_research\tools';            to = 'research\tools';           files = @('*.py', '*.ps1', 'addresses.json') }
    @{ from = '_research\tools\launcher';   to = 'research\tools\launcher';  files = @('*.cs', 'catalog.txt', 'soa.ico') }
    # The catalog is built out of the game's own data and is here by the
    # owner's decision, the same one that put it in the public kit: the
    # launcher is no use without it. It is the single exception to the rule
    # that only our own work is published, and it is deliberate.
    @{ from = '_research\tools\launcher\catalog'; to = 'research\tools\launcher\catalog'; files = '*.png' }
    @{ from = '_research\tools\sandbox';    to = 'research\tools\sandbox';   files = @('*.ps1', '*.cmd', '*.md', 'sandbox.template') }
    # Our own pictures: frames of the game with the patches at work and the
    # launcher's windows, what the Arsenal page and the docs show.
    @{ from = '_research\pictures';         to = 'research\pictures';        files = @('*.png', '*.jpg') }
    @{ from = '_research\translation';      to = 'research\translation';     files = @('cs.tsv', 'glossary.md') }
    @{ from = 'analysis';                   to = 'analysis';                 files = '*.py' }
    @{ from = '_sandbox';                   to = 'sandbox';                  files = @('*.ps1', '*.cmd', '*.wsb') }
)

# Files that live only in the public repository and are edited there. The
# script owns the folders above and would otherwise delete anything in them it
# cannot account for; these are none of its business.
$notOurs = @('README.md', '.gitignore', 'LICENSE', 'docs')

# --- the guard ------------------------------------------------------------
# The allow list is written by hand and hands slip, so nothing gets published
# without passing this as well. These are the shapes the game's own data takes.
$forbidden = @('*.ubn', '*.diff3D', '*.sav', '*.mis', '*.trs', '*.lay', '*.olb',
               '*.bik', '*.mp3', '*.wav', '*.tga', '*.exe', '*.dll', '*.pth')
$forbiddenSize = 8MB

function Refuse([string]$path) {
    $name = Split-Path -Leaf $path
    foreach ($pattern in $forbidden) {
        if ($name -like $pattern) { return "it is a $pattern" }
    }
    if ((Get-Item $path).Length -gt $forbiddenSize) {
        return ('it is {0:N1} MB, and nothing of ours is' -f ((Get-Item $path).Length / 1MB))
    }
    return $null
}

Write-Host ''
Write-Host '=== Publishing to GitHub ===' -ForegroundColor Cyan
if (-not $Push) { Say 'a dry run - nothing is copied, committed or pushed' 'WARN' }

# --- 1. the checkout ------------------------------------------------------
if (-not (Test-Path (Join-Path $Public '.git'))) {
    Say "cloning $Remote into $Public"
    if ($Push) {
        git clone --quiet $Remote $Public
        if ($LASTEXITCODE -ne 0) { throw 'the clone failed' }
    } else {
        Say 'the dry run stops here: there is nothing to compare against yet' 'WARN'
        return
    }
} else {
    Say "bringing $Public up to date"
    if ($Push) {
        git -C $Public pull --quiet --ff-only
        if ($LASTEXITCODE -ne 0) { throw 'the pull failed - the checkout and the remote have diverged' }
    }
}

# --- 2. what the rules select --------------------------------------------
$wanted = @{}      # relative path in the public repo -> the file it comes from
foreach ($rule in $rules) {
    $from = Join-Path $Source $rule.from
    if (-not (Test-Path $from)) { Say "$($rule.from) is not there" 'WARN'; continue }
    foreach ($pattern in @($rule.files)) {
        foreach ($file in Get-ChildItem $from -File -Filter $pattern -ErrorAction SilentlyContinue) {
            $why = Refuse $file.FullName
            if ($why) {
                Say "refusing $($rule.from)\$($file.Name) - $why" 'BAD'
                continue
            }
            $wanted[(Join-Path $rule.to $file.Name)] = $file.FullName
        }
    }
}
Say "$($wanted.Count) files may be published"

# --- 3. what that changes ------------------------------------------------
# Compared with the line endings normalised, not byte for byte. Git checks the
# public repository out with CRLF and this one keeps LF, so a raw comparison
# calls every text file changed and each publish would be seventy-odd files of
# noise with the real change buried in it.
$binary = @('.png', '.jpg', '.ico', '.zip', '.pth')
function Same([string]$a, [string]$b) {
    if ([IO.Path]::GetExtension($a).ToLower() -in $binary) {
        return (Get-FileHash $a -Algorithm SHA256).Hash -eq (Get-FileHash $b -Algorithm SHA256).Hash
    }
    $x = [IO.File]::ReadAllText($a).Replace("`r`n", "`n")
    $y = [IO.File]::ReadAllText($b).Replace("`r`n", "`n")
    return $x -eq $y
}

$new = @(); $changed = @(); $removed = @()
foreach ($rel in $wanted.Keys) {
    $target = Join-Path $Public $rel
    if (-not (Test-Path $target)) { $new += $rel; continue }
    if (-not (Same $wanted[$rel] $target)) { $changed += $rel }
}
# Removals propagate too, but only inside the folders the rules own - anything
# else in the public repository is somebody else's and is left alone.
$owned = $rules | ForEach-Object { $_.to } | Sort-Object -Unique
foreach ($folder in $owned) {
    $here = Join-Path $Public $folder
    if (-not (Test-Path $here)) { continue }
    foreach ($file in Get-ChildItem $here -File) {
        $rel = Join-Path $folder $file.Name
        if ($notOurs -contains $file.Name) { continue }
        if (-not $wanted.ContainsKey($rel)) { $removed += $rel }
    }
}

foreach ($set in @(@{n='new'; v=$new}, @{n='changed'; v=$changed}, @{n='gone'; v=$removed})) {
    if ($set.v.Count -eq 0) { continue }
    Say "$($set.v.Count) $($set.n):"
    foreach ($r in ($set.v | Sort-Object)) { Write-Host "        $r" -ForegroundColor DarkGray }
}
if ($new.Count + $changed.Count + $removed.Count -eq 0) {
    Say 'the public repository already matches' 'OK'
    return
}

if (-not $Push) {
    Say 'run it again with -Push to copy, commit and push' 'WARN'
    return
}

# --- 4. copy, commit, push -----------------------------------------------
foreach ($rel in ($new + $changed)) {
    $target = Join-Path $Public $rel
    $dir = Split-Path -Parent $target
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Copy-Item $wanted[$rel] $target -Force
}
foreach ($rel in $removed) { git -C $Public rm --quiet -- $rel }

if (-not $Message) {
    $Message = 'Bring the tools and the documents up to date'
}
git -C $Public add -A
git -C $Public -c "user.name=$AuthorName" -c "user.email=$AuthorMail" commit --quiet -m $Message
if ($LASTEXITCODE -ne 0) { throw 'the commit failed' }
git -C $Public push --quiet
if ($LASTEXITCODE -ne 0) { throw 'the push failed' }

$head = (git -C $Public log -1 --format='%h %an <%ae>').Trim()
Say "pushed: $head" 'OK'
Write-Host ''
Write-Host "  https://github.com/TomasBouda/SoA" -ForegroundColor Green
