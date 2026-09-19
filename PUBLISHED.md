# What is published here

Everything in this repository comes out of a private one that also holds the game itself,
which is not ours to hand out. A file is here because a rule in
[research/tools/publish-manifest.json](research/tools/publish-manifest.json) names it - an allow list,
kept by [research/tools/publish.ps1](research/tools/publish.ps1), which the pipeline runs on every push
and which also writes this file. Nothing shaped like the game's data passes, whatever the rules say.

## the root - 2 files

The public repository's own front matter.

From `_public/`: `README.md`, `.gitignore`

- .gitignore
- README.md

## `docs/` - 3 files

The website, GitHub Pages serves docs/: the front page, the Arsenal, the page about the game.

From `_public/docs/`: `*.html`

- docs/arsenal.html
- docs/game.html
- docs/index.html

## `docs/img/` - 4 files

The website's pictures.

From `_public/docs/img/`: `*.png`, `*.jpg`

- docs/img/ak74.png
- docs/img/bm21_h.png
- docs/img/bmp1_h.png
- docs/img/rager_h.png

## `docs/img/patches/` - 8 files

From `_public/docs/img/patches/`: `*.png`, `*.jpg`

- docs/img/patches/airstrike-mig.jpg
- docs/img/patches/airstrike-pings.jpg
- docs/img/patches/airstrike-ring-menu.jpg
- docs/img/patches/camera-high.jpg
- docs/img/patches/launcher-map.png
- docs/img/patches/launcher-patches.png
- docs/img/patches/m34-burst.jpg
- docs/img/patches/m34-hud-hint.jpg

## `research/` - 20 files

The research: architecture.md, cheats.md, TODO.md and the rest.

From `_research/`: `*.md`

- research/architecture.md
- research/behavior.md
- research/cheats.md
- research/classes.md
- research/dataset-format.md
- research/editor-scripting.md
- research/editor.md
- research/map.md
- research/missions.md
- research/models.md
- research/object-ids.md
- research/packaging.md
- research/README.md
- research/saves.md
- research/sound-fix.md
- research/TODO.md
- research/trading.md
- research/translation.md
- research/upscale.md
- research/weapons.md

## `research/tools/` - 54 files

The tools, this manifest among them.

From `_research/tools/`: `*.py`, `*.ps1`, `addresses.json`, `publish-manifest.json`

- research/tools/add_sounds.py
- research/tools/addresses.json
- research/tools/airstrike_inject.py
- research/tools/build-package.ps1
- research/tools/check.py
- research/tools/dataset.py
- research/tools/decode_error.py
- research/tools/diff_memory.py
- research/tools/diff_save.py
- research/tools/diff3d.py
- research/tools/dub.py
- research/tools/edit_save.py
- research/tools/esrgan.py
- research/tools/extract_icon.py
- research/tools/find_units.py
- research/tools/fix_missing_sounds.py
- research/tools/fix_sounds.py
- research/tools/gen_catalog.py
- research/tools/gen_editor_docs.py
- research/tools/gen_game_web.py
- research/tools/gen_ids_doc.py
- research/tools/gen_keys_cs.py
- research/tools/gen_weapons_doc.py
- research/tools/gen_weapons_web.py
- research/tools/hud_contrast.py
- research/tools/import_texture.py
- research/tools/launch_game.ps1
- research/tools/list_ids.py
- research/tools/m34_icon.py
- research/tools/m34_patch.py
- research/tools/map_bits.py
- research/tools/map_exe.py
- research/tools/menu_bot.py
- research/tools/mis.py
- research/tools/mission_cheat.py
- research/tools/mod_m34.py
- research/tools/monitor-run.ps1
- research/tools/patch_exe.py
- research/tools/play_bot.py
- research/tools/probe.py
- research/tools/publish-manifest.json
- research/tools/publish.ps1
- research/tools/radio_clip.py
- research/tools/read_save.py
- research/tools/scan_memory.py
- research/tools/trainer_inject.py
- research/tools/translate.py
- research/tools/trs.py
- research/tools/ui_inject.py
- research/tools/upscale_details.py
- research/tools/upscale_faces.py
- research/tools/upscale_terrain.py
- research/tools/upscale_textures.py
- research/tools/who_is.py

## `research/tools/launcher/` - 19 files

The launcher's source.

From `_research/tools/launcher/`: `*.cs`, `catalog.txt`, `soa.ico`

- research/tools/launcher/App.cs
- research/tools/launcher/Catalog.cs
- research/tools/launcher/catalog.txt
- research/tools/launcher/CatalogData.cs
- research/tools/launcher/Console.cs
- research/tools/launcher/GameLink.cs
- research/tools/launcher/GamePath.cs
- research/tools/launcher/Inspect.cs
- research/tools/launcher/Inventory.cs
- research/tools/launcher/Keys.cs
- research/tools/launcher/KeysData.cs
- research/tools/launcher/Map.cs
- research/tools/launcher/Models.cs
- research/tools/launcher/ModelsWindow.cs
- research/tools/launcher/Patches.cs
- research/tools/launcher/Remote.cs
- research/tools/launcher/Saves.cs
- research/tools/launcher/SelfTest.cs
- research/tools/launcher/soa.ico

## `research/tools/launcher/catalog/` - 157 files

The catalog pictures are built out of the game's own data and are here by the owner's decision, the same one that put them in the public kit: the launcher is no use without them. The single exception to the rule that only our own work is published, and deliberate.

From `_research/tools/launcher/catalog/`: `*.png`

- research/tools/launcher/catalog/SET_2S3_152MMGUN.png
- research/tools/launcher/catalog/SET_2S3_TURMMG.png
- research/tools/launcher/catalog/SET_2S3.png
- research/tools/launcher/catalog/SET_AK74.png
- research/tools/launcher/catalog/SET_ALUKOFFER.png
- research/tools/launcher/catalog/SET_ARMBRUST.png
- research/tools/launcher/catalog/SET_BERETTA.png
- research/tools/launcher/catalog/SET_BETAEUBUNGSGRANATE.png
- research/tools/launcher/catalog/SET_BM21_MLRS.png
- research/tools/launcher/catalog/SET_BM21.png
- research/tools/launcher/catalog/SET_BMP1_73MMGUN.png
- research/tools/launcher/catalog/SET_BMP1_AT2.png
- research/tools/launcher/catalog/SET_BMP1_ROHRMG.png
- research/tools/launcher/catalog/SET_BMP1.png
- research/tools/launcher/catalog/SET_BOMBENAUFHAENGUNG.png
- research/tools/launcher/catalog/SET_BOX.png
- research/tools/launcher/catalog/SET_BTR80_MK.png
- research/tools/launcher/catalog/SET_BTR80_NEBELWERFER.png
- research/tools/launcher/catalog/SET_BTR80.png
- research/tools/launcher/catalog/SET_BULL.png
- research/tools/launcher/catalog/SET_CONTROLCHIP.png
- research/tools/launcher/catalog/SET_CRAWLERSENDER.png
- research/tools/launcher/catalog/SET_DRAGUNOV.png
- research/tools/launcher/catalog/SET_EAGLE.png
- research/tools/launcher/catalog/SET_FERNGLAS.png
- research/tools/launcher/catalog/SET_FLOGGER.png
- research/tools/launcher/catalog/SET_FLY.png
- research/tools/launcher/catalog/SET_FULCRUM.png
- research/tools/launcher/catalog/SET_GAZ.png
- research/tools/launcher/catalog/SET_GAZA.png
- research/tools/launcher/catalog/SET_HANDGRANATE.png
- research/tools/launcher/catalog/SET_HELI_AT2_4FACH.png
- research/tools/launcher/catalog/SET_HELI_AT6_4FACH.png
- research/tools/launcher/catalog/SET_HELI_AT6.png
- research/tools/launcher/catalog/SET_HELI_BORDMG.png
- research/tools/launcher/catalog/SET_HELI_MK.png
- research/tools/launcher/catalog/SET_HELI_SA7.png
- research/tools/launcher/catalog/SET_HELI_TOW.png
- research/tools/launcher/catalog/SET_HELI_UB20.png
- research/tools/launcher/catalog/SET_HELI_UV32.png
- research/tools/launcher/catalog/SET_HELI_UV7.png
- research/tools/launcher/catalog/SET_HIND.png
- research/tools/launcher/catalog/SET_HIP.png
- research/tools/launcher/catalog/SET_HUMMER.png
- research/tools/launcher/catalog/SET_HUMVEE_M60.png
- research/tools/launcher/catalog/SET_HUMVEE_PLAMJA.png
- research/tools/launcher/catalog/SET_HUMVEE_TOW.png
- research/tools/launcher/catalog/SET_M1A1_125MMGUN.png
- research/tools/launcher/catalog/SET_M1A1_GRANATWERFER.png
- research/tools/launcher/catalog/SET_M1A1_NEBELWERFER.png
- research/tools/launcher/catalog/SET_M1A1_ROHRMG.png
- research/tools/launcher/catalog/SET_M1A1.png
- research/tools/launcher/catalog/SET_M34.png
- research/tools/launcher/catalog/SET_M60.png
- research/tools/launcher/catalog/SET_M79.png
- research/tools/launcher/catalog/SET_MD500.png
- research/tools/launcher/catalog/SET_MEDIKIT.png
- research/tools/launcher/catalog/SET_MESSER.png
- research/tools/launcher/catalog/SET_MINENKOEDER.png
- research/tools/launcher/catalog/SET_MOLOTOW.png
- research/tools/launcher/catalog/SET_MP5.png
- research/tools/launcher/catalog/SET_MUN_125MMGUN_APSFDS.png
- research/tools/launcher/catalog/SET_MUN_125MMGUN_HE.png
- research/tools/launcher/catalog/SET_MUN_125MMGUN_HEAT.png
- research/tools/launcher/catalog/SET_MUN_152MMGUN_HE.png
- research/tools/launcher/catalog/SET_MUN_152MMGUN_LEUCHT.png
- research/tools/launcher/catalog/SET_MUN_152MMGUN_MINE.png
- research/tools/launcher/catalog/SET_MUN_152MMGUN_NEBEL.png
- research/tools/launcher/catalog/SET_MUN_250KGBOMBE.png
- research/tools/launcher/catalog/SET_MUN_500KGBOMBE.png
- research/tools/launcher/catalog/SET_MUN_73MMGUN_HEAT.png
- research/tools/launcher/catalog/SET_MUN_73MMGUN_HEFRAG.png
- research/tools/launcher/catalog/SET_MUN_9MM.png
- research/tools/launcher/catalog/SET_MUN_AK74.png
- research/tools/launcher/catalog/SET_MUN_ARMBRUST.png
- research/tools/launcher/catalog/SET_MUN_AT2.png
- research/tools/launcher/catalog/SET_MUN_AT6.png
- research/tools/launcher/catalog/SET_MUN_BETAEUBUNGSGRANATE.png
- research/tools/launcher/catalog/SET_MUN_BM21_HEFRAG.png
- research/tools/launcher/catalog/SET_MUN_BM21_MINE.png
- research/tools/launcher/catalog/SET_MUN_BM21_RAUCH.png
- research/tools/launcher/catalog/SET_MUN_DRAGUNOV.png
- research/tools/launcher/catalog/SET_MUN_FLAMMENWERFER.png
- research/tools/launcher/catalog/SET_MUN_HANDGRANATE.png
- research/tools/launcher/catalog/SET_MUN_MESSER.png
- research/tools/launcher/catalog/SET_MUN_MG.png
- research/tools/launcher/catalog/SET_MUN_MK.png
- research/tools/launcher/catalog/SET_MUN_MOLOTOW.png
- research/tools/launcher/catalog/SET_MUN_NEBELGRANATE.png
- research/tools/launcher/catalog/SET_MUN_PANZERNEBELGRANATE.png
- research/tools/launcher/catalog/SET_MUN_PLAMJA_BRAND.png
- research/tools/launcher/catalog/SET_MUN_PLAMJA_HE.png
- research/tools/launcher/catalog/SET_MUN_RPG7.png
- research/tools/launcher/catalog/SET_MUN_SA7.png
- research/tools/launcher/catalog/SET_MUN_SHOTGUN.png
- research/tools/launcher/catalog/SET_MUN_TOW.png
- research/tools/launcher/catalog/SET_MUN_UB20.png
- research/tools/launcher/catalog/SET_MUN_UNBORN_MINIGUN.png
- research/tools/launcher/catalog/SET_MUN_UNBORN_ROCKETLAUNCHER.png
- research/tools/launcher/catalog/SET_MUN_UV32.png
- research/tools/launcher/catalog/SET_NACHTSICHTGERAET.png
- research/tools/launcher/catalog/SET_NEBELGRANATE.png
- research/tools/launcher/catalog/SET_OH58.png
- research/tools/launcher/catalog/SET_PANZERMINE.png
- research/tools/launcher/catalog/SET_PEILSENDER.png
- research/tools/launcher/catalog/SET_RAGER.png
- research/tools/launcher/catalog/SET_RPG7.png
- research/tools/launcher/catalog/SET_RPK.png
- research/tools/launcher/catalog/SET_SA7.png
- research/tools/launcher/catalog/SET_SCHUTZWESTE_LEICHT.png
- research/tools/launcher/catalog/SET_SCHUTZWESTE_SCHWER.png
- research/tools/launcher/catalog/SET_SHILKA_MK.png
- research/tools/launcher/catalog/SET_SHILKA.png
- research/tools/launcher/catalog/SET_SHOTGUN.png
- research/tools/launcher/catalog/SET_SPRENGSATZ.png
- research/tools/launcher/catalog/SET_SUBSURFACEMINE.png
- research/tools/launcher/catalog/SET_T55_125MMGUN.png
- research/tools/launcher/catalog/SET_T55_NEBELWERFER.png
- research/tools/launcher/catalog/SET_T55_ROHRMG.png
- research/tools/launcher/catalog/SET_T55_TURMMG.png
- research/tools/launcher/catalog/SET_T55.png
- research/tools/launcher/catalog/SET_T80_125MMGUN.png
- research/tools/launcher/catalog/SET_T80_FLAMMENWERFER.png
- research/tools/launcher/catalog/SET_T80_NEBELWERFER.png
- research/tools/launcher/catalog/SET_T80_ROHRMG.png
- research/tools/launcher/catalog/SET_T80_TURMMG.png
- research/tools/launcher/catalog/SET_T80.png
- research/tools/launcher/catalog/SET_UNBORN_MINIGUN.png
- research/tools/launcher/catalog/SET_UNBORN_ROCKETLAUNCHER.png
- research/tools/launcher/catalog/SET_URAL.png
- research/tools/launcher/catalog/SET_UZI.png
- research/tools/launcher/catalog/SET_VULCAN_MK.png
- research/tools/launcher/catalog/SET_VULKAN.png
- research/tools/launcher/catalog/SET_WOLF.png
- research/tools/launcher/catalog/UNIT_2S3.png
- research/tools/launcher/catalog/UNIT_BM21.png
- research/tools/launcher/catalog/UNIT_BMP1.png
- research/tools/launcher/catalog/UNIT_BTR80.png
- research/tools/launcher/catalog/UNIT_BULL.png
- research/tools/launcher/catalog/UNIT_EAGLE.png
- research/tools/launcher/catalog/UNIT_FLOGGER.png
- research/tools/launcher/catalog/UNIT_FULCRUM.png
- research/tools/launcher/catalog/UNIT_GAZ.png
- research/tools/launcher/catalog/UNIT_GAZ2.png
- research/tools/launcher/catalog/UNIT_HIND.png
- research/tools/launcher/catalog/UNIT_HIP.png
- research/tools/launcher/catalog/UNIT_HUMMER.png
- research/tools/launcher/catalog/UNIT_M1A1.png
- research/tools/launcher/catalog/UNIT_MD500.png
- research/tools/launcher/catalog/UNIT_OH58.png
- research/tools/launcher/catalog/UNIT_RAGER.png
- research/tools/launcher/catalog/UNIT_SHILKA.png
- research/tools/launcher/catalog/UNIT_T55.png
- research/tools/launcher/catalog/UNIT_T80.png
- research/tools/launcher/catalog/UNIT_URAL.png
- research/tools/launcher/catalog/UNIT_VULCAN.png
- research/tools/launcher/catalog/UNIT_WOLF.png

## `research/tools/sandbox/` - 10 files

From `_research/tools/sandbox/`: `*.ps1`, `*.cmd`, `*.md`, `sandbox.template`

- research/tools/sandbox/after-run.cmd
- research/tools/sandbox/after-run.ps1
- research/tools/sandbox/check.ps1
- research/tools/sandbox/prepare.cmd
- research/tools/sandbox/README.md
- research/tools/sandbox/sandbox.template
- research/tools/sandbox/snap.cmd
- research/tools/sandbox/snap.ps1
- research/tools/sandbox/Verify.cmd
- research/tools/sandbox/verify.ps1

## `research/pictures/` - 12 files

Our own pictures: frames of the game with the patches at work, the launcher's windows.

From `_research/pictures/`: `*.png`, `*.jpg`

- research/pictures/airstrike-mig.jpg
- research/pictures/airstrike-pings.jpg
- research/pictures/airstrike-ring-menu.jpg
- research/pictures/camera-high.jpg
- research/pictures/launcher-map.png
- research/pictures/launcher-patches.png
- research/pictures/launcher.png
- research/pictures/m34-burst.jpg
- research/pictures/m34-dealer.jpg
- research/pictures/m34-equip.jpg
- research/pictures/m34-hud-hint.jpg
- research/pictures/m34-icon.png

## `research/translation/` - 2 files

From `_research/translation/`: `cs.tsv`, `glossary.md`

- research/translation/cs.tsv
- research/translation/glossary.md

## `analysis/` - 6 files

From `analysis/`: `*.py`

- analysis/ep.py
- analysis/extract_iso.py
- analysis/iso.py
- analysis/pe.py
- analysis/rarinfo.py
- analysis/strings.py

## `sandbox/` - 11 files

From `_sandbox/`: `*.ps1`, `*.cmd`, `*.wsb`

- sandbox/backup-saves.ps1
- sandbox/export-changes.ps1
- sandbox/export-saves.cmd
- sandbox/kit-test.cmd
- sandbox/KitTest.wsb
- sandbox/play.cmd
- sandbox/prepare.cmd
- sandbox/snap.cmd
- sandbox/snap.ps1
- sandbox/SoA.wsb
- sandbox/watch-saves.ps1

