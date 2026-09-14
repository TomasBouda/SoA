<#
.SYNOPSIS
    Copies the part of this project that may be public into the GitHub
    repository, and pushes it.

.DESCRIPTION
    The two repositories are separate on purpose. This one holds the game -
    its archives, its executable, the upscaled textures, the saves - and none
    of that is ours to hand out. github.com/TomasBouda/SoA holds our own
    writing, our own code and the website, and nothing else.

    Nothing propagated between them until this script existed: the public
    repository was updated by hand, from a working copy in a temporary folder,
    which is a way of working that goes wrong quietly. A tool changes here and
    the public copy silently stays old; a new file appears and somebody has to
    remember whether it may go out.

    So the rule this enforces is an **allow list, not a deny list**, and the
    list is publish-manifest.json beside this script. A file goes out because
    a rule there names it, and a new file that no rule names stays here.
    Getting that the wrong way round is how the game's own data ends up
    published by accident, and it cannot be taken back once it is.

    It refuses to publish anything that looks like the game's data even when a
    rule would allow it - the manifest's "forbidden" part. That check exists
    because the allow list is written by hand and hands slip.

    The public repository also gets PUBLISHED.md, written here on every run:
    every file it holds and the rule that put it there, so what is published
    can be read on GitHub without reading this script.

    The pipeline (azure-pipelines.yml at the root of this repository) runs
    this on every push to main with -Token, so the public repository follows
    this one on its own; run by hand it does the same from this machine.

.EXAMPLE
    publish.ps1
    What would change, and nothing else. This is the default on purpose.

.EXAMPLE
    publish.ps1 -Push -Message "Read the mission scripts"
    Copy, commit and push.

.EXAMPLE
    publish.ps1 -Push -Public $env:TEMP\public -Token $env:GITHUB_TOKEN
    What the pipeline does: a fresh clone, the token for the push, the
    message of the commit being published.
#>
param(
    # Where the public repository is checked out - beside this one, as
    # SoA-Public. It is cloned if missing.
    [string]$Public = (Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))) 'SoA-Public'),
    [string]$Remote = 'https://github.com/TomasBouda/SoA.git',
    [string]$Message = '',
    # A GitHub token with write access to the repository, for the pipeline;
    # it is used for the clone and the push and is not written anywhere.
    [string]$Token = '',
    # Without this the script only says what it would do.
    [switch]$Push
)

$ErrorActionPreference = 'Stop'
$Source = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\Games\SoA
$Manifest = Join-Path $PSScriptRoot 'publish-manifest.json'

# The commits must carry this and nothing else. The e-mail is what GitHub pairs
# a commit with an account by, and the obvious-looking one on this machine
# belongs to a different account - which put two strangers in the contributor
# list and needed the history rewritten to get out again. No Co-Authored-By
# either: GitHub counts a co-author as a contributor.
$AuthorName = 'Tomáš Bouda'
$AuthorMail = 'email@tomasbouda.cz'
$Listing = 'PUBLISHED.md'

function Say([string]$m, [string]$lvl = 'INFO') {
    $color = switch ($lvl) { 'OK' { 'Green' } 'WARN' { 'Yellow' } 'BAD' { 'Red' } default { 'Gray' } }
    Write-Host ('  {0,-5} {1}' -f $lvl, $m) -ForegroundColor $color
}

# --- what may go out ------------------------------------------------------
$manifest = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$rules = @($manifest.rules)
$forbidden = @($manifest.forbidden.names)
$forbiddenSize = [long]$manifest.forbidden.maxBytes

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

function PublicPath([string]$to, [string]$name) {
    if ($to -eq '.') { return $name }
    return Join-Path $to $name
}

# The remote with the token in it, for the pipeline; the checkout never keeps it.
$authed = $Remote
if ($Token) { $authed = $Remote -replace '^https://', "https://x-access-token:$Token@" }

Write-Host ''
Write-Host '=== Publishing to GitHub ===' -ForegroundColor Cyan
if (-not $Push) { Say 'a dry run - nothing is copied, committed or pushed' 'WARN' }

# --- 1. the checkout ------------------------------------------------------
if (-not (Test-Path (Join-Path $Public '.git'))) {
    Say "cloning $Remote into $Public"
    if ($Push) {
        git clone --quiet $authed $Public
        if ($LASTEXITCODE -ne 0) { throw 'the clone failed' }
        if ($Token) { git -C $Public remote set-url origin $Remote }
    } else {
        Say 'the dry run stops here: there is nothing to compare against yet' 'WARN'
        return
    }
} else {
    Say "bringing $Public up to date"
    if ($Push) {
        git -C $Public pull --quiet --ff-only $authed
        if ($LASTEXITCODE -ne 0) { throw 'the pull failed - the checkout and the remote have diverged' }
    }
}

# --- 2. what the rules select --------------------------------------------
$wanted = @{}      # relative path in the public repo -> the file it comes from
$ruleOf = @{}      # relative path -> the rule's index, for the listing
for ($i = 0; $i -lt $rules.Count; $i++) {
    $rule = $rules[$i]
    $from = Join-Path $Source ($rule.from -replace '/', '\')
    if (-not (Test-Path $from)) { Say "$($rule.from) is not there" 'WARN'; continue }
    foreach ($pattern in @($rule.files)) {
        foreach ($file in Get-ChildItem $from -File -Filter $pattern -Force -ErrorAction SilentlyContinue) {
            $why = Refuse $file.FullName
            if ($why) {
                Say "refusing $($rule.from)\$($file.Name) - $why" 'BAD'
                continue
            }
            $rel = PublicPath ($rule.to -replace '/', '\') $file.Name
            $wanted[$rel] = $file.FullName
            $ruleOf[$rel] = $i
        }
    }
}
Say "$($wanted.Count) files may be published"

# --- the listing ----------------------------------------------------------
# Written into the public repository on every run, so what is published can be
# read there. It is compared like any other file, so a run that changes nothing
# else and nothing here is still a no-op.
$lines = @('# What is published here', '',
           'Everything in this repository comes out of a private one that also holds the game itself,',
           'which is not ours to hand out. A file is here because a rule in',
           '[research/tools/publish-manifest.json](research/tools/publish-manifest.json) names it - an allow list,',
           'kept by [research/tools/publish.ps1](research/tools/publish.ps1), which the pipeline runs on every push',
           'and which also writes this file. Nothing shaped like the game''s data passes, whatever the rules say.', '')
for ($i = 0; $i -lt $rules.Count; $i++) {
    $rule = $rules[$i]
    $files = @($ruleOf.Keys | Where-Object { $ruleOf[$_] -eq $i } | Sort-Object)
    if ($files.Count -eq 0) { continue }
    $where = if ($rule.to -eq '.') { 'the root' } else { "``$($rule.to)/``" }
    $lines += "## $where - $($files.Count) file$(if ($files.Count -ne 1) { 's' })"
    $lines += ''
    if ($rule.note) { $lines += $rule.note; $lines += '' }
    $lines += ('From `{0}/`: {1}' -f $rule.from, (($rule.files | ForEach-Object { "``$_``" }) -join ', '))
    $lines += ''
    foreach ($f in $files) { $lines += ('- ' + ($f -replace '\\', '/')) }
    $lines += ''
}
$listingTmp = Join-Path ([IO.Path]::GetTempPath()) 'soa-published.md'
[IO.File]::WriteAllText($listingTmp, (($lines -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))
$wanted[$Listing] = $listingTmp

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
# else in the public repository is left alone.
$owned = $rules | ForEach-Object { $_.to -replace '/', '\' } | Sort-Object -Unique
foreach ($folder in $owned) {
    $here = if ($folder -eq '.') { $Public } else { Join-Path $Public $folder }
    if (-not (Test-Path $here)) { continue }
    foreach ($file in Get-ChildItem $here -File -Force) {
        $rel = PublicPath $folder $file.Name
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
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Copy-Item $wanted[$rel] $target -Force
}
foreach ($rel in $removed) { git -C $Public rm --quiet -- $rel }

if (-not $Message) {
    $Message = 'Bring the tools and the documents up to date'
}
git -C $Public add -A
git -C $Public -c "user.name=$AuthorName" -c "user.email=$AuthorMail" commit --quiet -m $Message
if ($LASTEXITCODE -ne 0) { throw 'the commit failed' }
git -C $Public push --quiet $authed HEAD:main
if ($LASTEXITCODE -ne 0) { throw 'the push failed' }

$head = (git -C $Public log -1 --format='%h %an <%ae>').Trim()
Say "pushed: $head" 'OK'
Write-Host ''
Write-Host "  https://github.com/TomasBouda/SoA" -ForegroundColor Green
