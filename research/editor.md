# The editor is still in the game

Soldiers of Anarchy was built with a mission editor, and the editor never left
the retail build. Not the code, not the artwork, not the menu button. This is
what is in the copy on this machine.

## The code

`soa.exe` carries 138 source files under `quellui_editor` and a state class of
its own in `Y2KEditor.cpp`. `CY2KEditor::Tick` is at `0x53B880`. The file names
alone describe the whole tool - a terrain brush, a texture painter, a tree and
object placer, a region editor, a player and diplomacy setup, a camera track
editor, a statistics panel, a file dialog that saves `.mis`, and a mission
design half with a panel for every trigger and event the scripting language
has: `EditorMissionDesignPatrolParamsPanel.cpp`,
`EditorMissionDesignSetDiplomacyParamsPanel.cpp`,
`EditorMissionDesignEnemySpottedParamsPanel.cpp` and forty more like them.

## The data

Everything the editor needs to draw itself ships too:

| where | what |
|---|---|
| `data.ubn` | 180 members with EDITOR in the name, including `Editor.gui` and 170-odd `LAY_EDITOR_*.lay` layouts |
| `gui.ubn` | 404 members under `gui/GUI_Editor` - controls, icons, mouse cursors, and preview thumbnails for buildings, characters and clothes |
| `TRES_EDITOR.TRS`, `TRES_EDITOR_MISSIONGOALS.TRS` | its text, in the same form as the rest of the game's |
| `1.1.0.71-1.1.1.118.ubn` | 29 more editor members - the 1.1.1 patch **updated** the editor, so it was still being maintained at release |

`LAY_EDITOR_MAIN.lay` alone lists 72 panels. `LAY_EDITOR_MAINMENUE_DATEI.lay`
has the buttons New, Load, Save, Import height map, Export height map, Objects,
Quit.

## The button

The main menu layout, `LAY_START_WELCOMEBUTTONS.lay`, has five buttons, and one
of them is the editor:

| widget | image | rectangle in the 640x480 menu |
|---|---|---|
| `LAY_START_WELCOMEBUTTON_MULTIPLAYER1` | 4002 | 271, 149 - 415, 229 |
| `LAY_START_WELCOMEBUTTON_EDITOR1` | 4002 | **512, 201 - 570, 283** |
| `LAY_START_WELCOMEBUTTON_CREDITS1` | 4002 | 448, 386 - 529, 447 |
| `LAY_START_WELCOMEBUTTON_OPTIONEN1` | 4002 | 295, 390 - 370, 449 |
| `LAY_START_WELCOMEBUTTON_EXIT1` | 4002 | 234, 418 - 281, 463 |

Each has a second widget at the same rectangle carrying its label picture -
4043 for the editor, 4044 to 4047 for the others. Image 4002 is shared by all
five and is the hit area.

The exe wires the editor button up like any other, unconditionally, at
`0x50C5F4` and `0x50C70C`, and it is registered with the panel at `0x50C8A4` as
widget 6. The hit test at `0x50CDC2` raises **command 3**.

## What happens on the click

Command 3 lands in `Y2KStart.cpp`. The branch is at `0x60A484`:

    0060A484  lea  ecx, [ebp-8]
    0060A487  call 0x60A060
    0060A499  push 0x85E9C8            ; "AppState Start : Editor\n"
    0060A4B6  mov  eax, [ebp+0x2C]
    0060A4BF  call 0x6A01C0
    0060A4C4  push 0 / push 0 / push 7 ; the state to go to
    0060A4CA  jmp  0x60A7DB            ; the shared fade and switch

`0x60A7DB` calls `0x6A2A80(0x3E8, 7, 0, 0)` and then fades over 2000 ms. The
sibling branches use the same call with 5 for Exit and 9 for Credits, and the
switch in `Y2KApp.cpp` at `0x6D3533` takes exactly that range, 5 to 9. The
factory it reaches, `0x6D3630`, builds the state objects:

| id | size | constructor | what it is |
|---|---|---|---|
| 2 | `0x28` | `0x6C2A40` | global effects |
| 3 | `0x5F0` | `0x538BE0` | **the editor** |
| 4 | `0x2C4` | `0x5E7620` | a mission |
| 5 | `0x7B0` | `0x515670` | the bunker |
| 6 | `0xDC` | `0x6082C0` | the start screen |

So the whole path from the click to a running editor is present and nothing on
it is stubbed out.

## It is simply there

The button is not hidden at all. It is drawn in the retail main menu with the
word EDITOR on its banner, on the right of the ring, between Multiplayer and
Credits - exactly at the rectangle the layout gives it. Nothing needs patching
and nothing needs unhiding: clicking it raises command 3, which logs
`AppState Start : Editor` and switches to state 7.

So the editor is reachable by anyone who owns the game, and always was.

## The other way round

Writing `.mis` files directly is the alternative, and the only route to maps
made by a script rather than by hand - terrain out of noise or real elevation
data, objects scattered by rule. It needs the rest of the format, which is
`Y2K_LS_Serialize.cpp` at `0x681850`, `0x681950`, `0x681BB0` and `0x682050`.
See [missions.md](missions.md) for how far the format is understood.

The two are not rivals. The editor gives a way to make a map and, just as
usefully, a way to open a generated one and see whether it is right.
