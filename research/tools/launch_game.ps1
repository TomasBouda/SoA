# Starts the game through the launcher the way a person would - Play.exe, the
# mode box set to Windowed, the PLAY button - and waits for soa.exe. For the
# research bots (menu_bot.py, play_bot.py), which are calibrated on the
# window and must not take the desktop over.
#
#   .\launch_game.ps1                the package in F:\Games\SoA-Package
#   .\launch_game.ps1 -Package D:\x  another one
#   .\launch_game.ps1 -FullScreen    the mode box left alone
param(
    [string]$Package = 'F:\Games\SoA-Package',
    [switch]$FullScreen
)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$auto = 'System.Windows.Automation'

if (Get-Process soa -ErrorAction SilentlyContinue) {
    Write-Output "soa.exe is already running"
    exit 0
}
if (-not (Get-Process Play -ErrorAction SilentlyContinue)) {
    Start-Process (Join-Path $Package 'Play.exe') -WorkingDirectory $Package
}

$root = [System.Windows.Automation.AutomationElement]::RootElement
$win = $null
for ($i = 0; $i -lt 40 -and -not $win; $i++) {
    Start-Sleep -Milliseconds 500
    $win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children,
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, 'Soldiers of Anarchy')))
}
if (-not $win) { Write-Error 'the launcher window did not come up'; exit 1 }

if (-not $FullScreen) {
    $combos = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants,
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::ComboBox)))
    foreach ($c in $combos) {
        $sel = $c.GetCurrentPattern([System.Windows.Automation.SelectionPattern]::Pattern).Current.GetSelection() |
            ForEach-Object { $_.Current.Name }
        if ($sel -in @('Full screen', 'Full screen (exclusive)', 'Borderless full screen', 'Windowed')) {
            if ($sel -ne 'Windowed') {
                $c.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
                Start-Sleep -Milliseconds 300
                $item = $c.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
                    (New-Object System.Windows.Automation.PropertyCondition(
                        [System.Windows.Automation.AutomationElement]::NameProperty, 'Windowed')))
                $item.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
                $c.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse()
                Start-Sleep -Milliseconds 300
            }
        }
    }
}

$play = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, 'PLAY')))
$play.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()

for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep 1
    $game = Get-Process soa -ErrorAction SilentlyContinue
    if ($game -and $game.MainWindowHandle -ne 0) {
        Start-Sleep 6
        Write-Output "soa.exe $($game.Id) is up"
        exit 0
    }
}
Write-Error 'soa.exe did not come up'
exit 1
