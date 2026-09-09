# Behavioural analysis at run time

Static analysis of the cracked `soa.exe` found nothing — the same 15 libraries
as the original, fewer imported functions, no suspicious URL, no Defender hit.
It cannot prove the absence of malicious code though: an encrypted payload
unpacked only at run time would not show up in it. Hence the observation while
it runs.

The tool: [`tools/monitor-run.ps1`](tools/monitor-run.ps1). It is started inside
the sandbox, launches the game itself and watches it.

After the test the network in `SoA.wsb` is `Disable` again and the GameSpy block
in `hosts` is in force — removing it is the `-UnblockHosts` switch of the
monitor, so an ordinary run changes nothing about the safety measures.

## The result

A run on 31 August 2026, **4 minutes of actual play**, the game ended normally,
networking in the sandbox on and the GameSpy block removed from `hosts` so that
the real connection destinations would show.

| what was watched | result |
|---|---|
| child processes | **none** |
| libraries from outside the game folder and Windows | **none** |
| network connections | **none** |
| DNS queries | only the sandbox's own name |
| run keys (`Run`, `RunOnce`, Session Manager) | unchanged |
| scheduled tasks | unchanged |
| services | unchanged |
| files in `AppData`, `Temp`, `Documents`, Startup, `drivers\etc` | system noise only |

That noise was two items: the NVIDIA driver shader cache and
`ActivitiesCache.db` of the Windows activity history. Neither has anything to do
with the game.

What did **not** happen is interesting too: the game made no attempt to reach
GameSpy even though we deliberately let it. So the version check either runs
only under particular circumstances, or the 1.1.2.178 patch removed it.

## What that proves and what it does not

**It proves** that during startup and four minutes of play the game started no
process, loaded no foreign library, connected nowhere and set up no
persistence. That covers the typical behaviour of a dropper and of a trojan.

**It does not prove** absolute innocence. The code could activate later, only in
a particular mission, or detect the sandbox and behave itself on purpose. Which
is why the main measure stands — the game runs in the sandbox and nowhere else.

## Notes on the method

- **The working directory.** The game has to be started with `-WorkingDirectory`
  set to its own folder, otherwise it does not find the `.ubn` archives and ends
  with `0x80070002`. The first attempt fell over this and it looked like a crash.
- **The block in `hosts` distorts the picture.** `prepare.cmd` points GameSpy at
  `127.0.0.1`; for the analysis it has to be removed, otherwise the real
  destinations hide.
- **The DNS cache catches even the failed attempts**, which are not visible in
  the list of established connections.
- **Compare the noise filters with `-like`, not `-match`.** In the pattern
  `\NVIDIA\DXCache\` the `\N` and `\D` are regular expression escape sequences
  (`\D` means a non-digit), so it would match nothing and the noise would be
  reported as a finding. This mistake really did happen in the first run.
