# Verifying the package in a sandbox

On the machine where the package was built, dgVoodoo, the registry settings and
everything else installed along the way are already there — the package "works"
there even if something is missing from it. Windows Sandbox is clean Windows
that disappears when closed, so it shows exactly the state the package arrives
in elsewhere.

These files do not belong in the package and `build-package.ps1` does not
generate them there: the package holds the game, not the tools for testing it.

## Usage

```
Verify.cmd                          tests F:\Games\SoA-Package
Verify.cmd D:\somewhere\SoA-Package tests a package elsewhere
```

1. `Verify.cmd` computes the package fingerprints, builds the configuration and
   starts the sandbox.
2. The sandbox copies the package to `C:\SoA` on its own and prints the check.
3. Run `C:\SoA\Play.exe` and play for a while — try saving a position.
4. Run `C:\Test\after-run.cmd`. It shows what the launcher set, whether saves
   appeared and what the game log says.
5. Close the sandbox. The logs stay in the `logs` folder.

The package is mapped into the sandbox **read-only**, so the test cannot change
it. Networking is off.

## What the individual files do

| file | what it does |
|---|---|
| `Verify.cmd` | this is what gets started, just a wrapper around `verify.ps1` |
| `verify.ps1` | package fingerprints, configuration from the template, sandbox start |
| `sandbox.template` | the `.wsb` template, the paths are filled in at run time |
| `prepare.cmd` | runs automatically after logon: copies the package and checks it |
| `check.ps1` | package contents, file fingerprints, assumptions about the system |
| `after-run.cmd` | the check after playing |
| `snap.cmd` | a screenshot out of the sandbox through the mapped folder |
| `logs/` | the results of the checks and a copy of `tracefile.log` |

## Why the `.wsb` is generated

The Windows Sandbox configuration only understands absolute paths. A finished
one would stop being valid the moment the package or this folder is moved, so
the repository carries only the template and the paths are filled into it on
every run.

## What the check watches for

* the required files and, the other way round, what must not stay in the
  package — the spare exe files (`soa.exe.securom`, `soa.exe.1.1.0.71`),
  `SaveGames`, `tracefile.log`, `running.lock`
* SHA-256 fingerprints of the key files plus the file count and total size —
  this catches a damaged or incomplete transfer
* the values in `dgVoodoo.conf` including their section; `Antialiasing` exists
  separately in `[Glide]` and in `[DirectX]`, and the game runs through DirectX
* that `settings.reg` carries no resolution from another machine
* that the system has the .NET Framework 4.8 the launcher needs
* that there is nothing from the game in the registry yet — proof that the test
  really starts clean
