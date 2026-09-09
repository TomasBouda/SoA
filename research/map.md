# Which code belongs to which source file

Made by [tools/map_exe.py](tools/map_exe.py) - see the comment at the
top of it for how, and for what it cannot see.

538 source files are named in the exe and 537 of them could be placed in
code by following the trace calls back to the function they sit in.

## 3DObjects

| file | functions |
|---|---|
| fxObjects.cpp | `00629E20`, `0062A010`, `0062A170` |
| objects.cpp | `0062ACF0`, `0062AE10`, `0062AF60`, `0062B030`, `0062B400`, `0062C020`, `0062C8E0`, `0062CE20` and 2 more |
| objectsMgr.cpp | `0062FD50`, `0062FDC0`, `0062FFC0`, `00630075`, `006300B0`, `00630120`, `00630220`, `00630560` and 2 more |
| objects_mesh.cpp | `0062F5A0` |

## AbstractData

| file | functions |
|---|---|
| tsString.cpp | `0065A1F0` |
| tstring.cpp | `0065A71D`, `0065A850`, `0065AA40`, `0065AB40`, `0065AC80`, `0065ADC0`, `0065B118`, `0065B1F1` and 2 more |

## AnimationObject

| file | functions |
|---|---|
| AnimationDataObject.cpp | `004018F0`, `00401B50`, `00402024` |
| AnimationObject.cpp | `00697567`, `00697661` |

## App

| file | functions |
|---|---|
| DXAppDirect3D.cpp | `00622EA0`, `00622FA0`, `006230C0`, `006237B0`, `00623850`, `00623AE0`, `00623BE8`, `00623FD0` and 1 more |
| DXAppDirectDraw.cpp | `00624630`, `00624750`, `00624B80`, `00624CB0`, `00624D40`, `00625170`, `00625340`, `006256F0` and 2 more |
| DXAppDirectSound.cpp | `00625A84`, `00625C90`, `00625E50` |
| DXAppMain.cpp | `00626060`, `00626546`, `00626C6F`, `00626DF0`, `00626FA0`, `006272D0`, `006273E0`, `00627BB0` and 14 more |
| dxdebug.cpp | `00629B80`, `00629CC0` |

## Cursor

| file | functions |
|---|---|
| DXUICursors.cpp | `006518B1`, `00651A60` |

## DXAStateApp

| file | functions |
|---|---|
| DXAStateApp.cpp | `006456C0`, `00645830`, `006458A0`, `00645910`, `006459C0`, `00645A50`, `00645AD0`, `00645B40` and 5 more |

## EventObject

| file | functions |
|---|---|
| Event.cpp | `0069F0A0` |
| EventLibrary.cpp | `0069F300`, `0069F3C0`, `0069F5F0` |
| Trigger.cpp | `006A96C0`, `006A9910`, `006A9B00` |

## FX

| file | functions |
|---|---|
| DXASkyBox2.cpp | `00640800`, `006409B0`, `00640AD0`, `00641024`, `00641FE8`, `006420D0`, `0064252E`, `006426D0` and 5 more |
| DXFX.cpp | `006500D0`, `0065015C`, `00650B90`, `00650CB0`, `00650E30` |

## Folder

| file | functions |
|---|---|
| folders.cpp | `00652CC0`, `00653030`, `00653231`, `00653290`, `006533E0`, `006534C0`, `006535A0`, `00653880` and 2 more |

## Info

| file | functions |
|---|---|
| DXAMemInfo.cpp | `004498A0` |
| DXAVersionCheck.cpp | `0064EB90`, `0064F060` |

## KI

| file | functions |
|---|---|
| y2k_ki.cpp | `006AE930` |
| y2k_ki_unit.cpp | `006B0E40` |

## MessageObject

| file | functions |
|---|---|
| MessageObject.cpp | `006A29C0` |

## SkriptList

| file | functions |
|---|---|
| SkriptList.cpp | `006A49F0`, `006A50CE`, `006A527C`, `006A54D0`, `006A5974`, `006A5AB0`, `006A5BB0` |

## SoundObject

| file | functions |
|---|---|
| SoundObject.cpp | `006A64A0`, `006A6824`, `006A7150`, `006A7452`, `006A7600`, `006A7960`, `006A79D0`, `006A7A50` and 4 more |

## StateHandler

| file | functions |
|---|---|
| DXAEffectMgr.cpp | `0063C450`, `0063D2C0` |
| DXAStateHandler.cpp | `006460F0`, `006461D0`, `00646574`, `00646979`, `0064726F`, `00647590` |
| DXAStateHandler_impl.cpp | `00647A00`, `00647AD0`, `00647C30`, `00647D90`, `00647F50`, `00648110`, `00648290`, `00648470` and 20 more |
| DXAStateHandler_impl2.cpp | `0064B600`, `0064B83F`, `0064BA00`, `0064BB20`, `0064BE03`, `0064BFE8`, `0064C060`, `0064C230` and 4 more |

## TextResourceObject

| file | functions |
|---|---|
| TextResourceObject.cpp | `0050D3C0`, `0050D710`, `0050D8D0`, `0050DA90`, `0050DEB0`, `0050ED00` |

## TextureRender

| file | functions |
|---|---|
| DXATextureRender.cpp | `0064CC80`, `0064CDD0`, `0064CF00`, `0064D190`, `0064D410`, `0064DBE8`, `0064DE10`, `0064E01B` and 7 more |

## UI

| file | functions |
|---|---|
| Animation.cpp | `00401150`, `00401540` |
| Button.cpp | `00697D30`, `00697E00`, `006985A0` |
| Caption.cpp | `00698F40`, `006996E8`, `006999F0` |
| Combo.cpp | `00699BD0` |
| Control.cpp | `0069AF90`, `0069B2E0`, `0069C1E8` |
| Edit.cpp | `0069D070`, `0069D770`, `0069D840`, `0069E0E5` |
| Fade.cpp | `006A0045` |
| Field.cpp | `006A087B` |
| Image.cpp | `006A0C7E` |
| LayoutDataObject.cpp | `006A0F8B` |
| List.cpp | `006A1B23` |
| Panel.cpp | `006A2D75`, `006A3374` |
| ScrollBar.cpp | `006A3900`, `006A3C50` |
| Slider.cpp | `004F5690`, `004F5880` |
| Tree.cpp | `006A90D0` |
| UIContainer.cpp | `006AABE8`, `006AAFB0` |
| UIRenderControl.cpp | `006AC084`, `006AC38B`, `006AC430`, `006AC500`, `006AC790` |
| UIResourceControl.cpp | `006AD4E0`, `006AD88B` |

## UnbornStats

| file | functions |
|---|---|
| Y2KRPG_Character.cpp | `00603E90`, `00604000`, `006041C0` |

## Utils

| file | functions |
|---|---|
| DDUtilities.cpp | `00635350`, `006355C0`, `006377E8`, `0063799A` |
| DXAReduceColor.cpp | `00640072` |
| Utils.cpp | `006AE7A0` |
| picking.cpp | `00654FE8` |

## Version

| file | functions |
|---|---|
| versionInfo.cpp | `0065BE30`, `0065BFC0`, `0065C3E8` |

## Windows

| file | functions |
|---|---|
| WndPositions.cpp | `0065CDE0`, `0065CE90` |

## bink

| file | functions |
|---|---|
| BinkPlayer.cpp | `006BC650`, `006BC890`, `006BCC70`, `006BD3C0`, `006BD700` |

## bmfont

| file | functions |
|---|---|
| bmfont.cpp | `006310B0`, `00631424`, `006315B0`, `00631670`, `00631A10`, `00631B20`, `00631BE0`, `006321D0` and 11 more |

## camera

| file | functions |
|---|---|
| CameraTrack.cpp | `006BE760` |
| Y2KCamera.cpp | `006DCCC0`, `006DEA53`, `006DED00`, `006DF030` |

## char

| file | functions |
|---|---|
| EntryPositionWait.cpp | `004BE5E0`, `004BE6C0` |
| MoveScript.cpp | `006ED090`, `006ED3A0`, `006ED510`, `006EDC20`, `006EDE10`, `006EE080` |
| PauseScript.cpp | `006EE470`, `006EE4F0`, `006EE560`, `006EE5C0`, `006EE610` |

## diff

| file | functions |
|---|---|
| diff.cpp | `00637DD0`, `00637E50`, `00637EE0`, `00638140` |

## diff3D

| file | functions |
|---|---|
| diff3dLoader.cpp | `006383F0`, `00638520`, `006387E8`, `00638D40`, `00638E40`, `006392F0` |

## effectStates

| file | functions |
|---|---|
| y2k_effectstates.cpp | `006CC100`, `006CC520`, `006CC8F0` |

## error_debug

| file | functions |
|---|---|
| ErrorHandler.cpp | `00651CE0`, `00651E60`, `00652040`, `00652160` |

## fx

| file | functions |
|---|---|
| Y2KFX.cpp | `006889D0`, `00688B65`, `00688EF0` |
| Y2KFX_BloodSplash.cpp | `00688FB0`, `0068A330`, `0068AB90` |
| Y2KFX_BulletHit.cpp | `0068AE30`, `0068B150`, `0068B400`, `0068B590`, `0068B730`, `0068B8D0`, `0068BB70`, `0068BD00` |
| Y2KFX_Explosion.cpp | `0068C033`, `0068C3FF`, `0068C5A0`, `0068C740`, `0068C8E0`, `0068CAE8`, `0068CB20`, `0068D0D0` and 3 more |
| Y2KFX_Fire.cpp | `0068E880`, `0068EA10`, `0068F130`, `0068F445`, `0068F7E0`, `0068F970` |
| Y2KFX_FlameThrower.cpp | `0068FB70`, `0068FD20`, `006902E8` |
| Y2KFX_FlyingJunk.cpp | `00690690`, `00690830` |
| Y2KFX_Light.cpp | `006914A0`, `00691600`, `00691B80`, `00691E30`, `00691F90`, `00692300`, `00692510`, `00692610` and 2 more |
| Y2KFX_ShellHit.cpp | `00693530`, `006936D0`, `00693C20` |
| Y2KFX_Smoke.cpp | `00693D60`, `00693F60`, `006940E0`, `006944D0`, `00694670`, `00694BB0`, `00694DD0`, `00694F70` |
| Y2KFX_TracerAmmo.cpp | `00695770`, `00695870`, `00695BC0`, `00695CC0` |
| Y2KFX_VehicleSmoke.cpp | `00695F50`, `00696150`, `006962F0`, `006966D0`, `00696870` |
| globaleffects.cpp | `006C26D0`, `006C2940` |

## gui

| file | functions |
|---|---|
| AddHint.cpp | `006B8450` |
| Intro2.cpp | `006C2DA0`, `006C2E90`, `006C2EE0`, `006C2F30`, `006C2F80`, `006C30B0` |
| SelectorUI.cpp | `006C8F80` |
| startSky.cpp | `006C99E0` |

## image_support

| file | functions |
|---|---|
| DXA_img_bmp.cpp | `00620270`, `00620740` |
| DXA_img_png.cpp | `00620CB0`, `00620E70`, `00621040`, `00621530`, `006218D0`, `00621C24`, `00621EAB` |
| DXA_img_tga.cpp | `00622024`, `006221B0`, `006222E9`, `006226D0`, `00622B72`, `00622C00` |

## io

| file | functions |
|---|---|
| InflateReadStream.cpp | `0074E4F0`, `0074E700`, `0074E8D0`, `0074EBA0` |
| ReadStream.cpp | `0074EF10`, `0074F060`, `0074F130` |
| Win32_FileReadStream.cpp | `0074FAF0`, `0074FC50`, `0074FDB0`, `0074FF70`, `007500A0`, `00750260` |
| ZipReadStream.cpp | `00615590`, `00616030`, `00616120`, `0061622E`, `00616310`, `00616400` |

## item

| file | functions |
|---|---|
| Y2KItem.cpp | `006E1690`, `006E1FF0`, `006E2080`, `006E2410` |

## landscape

| file | functions |
|---|---|
| ItemRegion.cpp | `006C3350` |
| UnitPath.cpp | `006C9E80`, `006C9F30`, `006CA140` |
| Y2KLandscape.cpp | `00685940`, `00685B80`, `00685C50`, `00686028`, `00686130`, `006864FF`, `0068697C`, `00686CFF` and 12 more |
| Y2K_LS_AreaDetails.cpp | `0065E9E0`, `0065EDE0`, `0065F300`, `0065F7F0`, `0065FB60`, `00660072`, `006600C7`, `00660180` and 12 more |
| Y2K_LS_AreaTree.cpp | `00666CE0`, `00666D70`, `00667800`, `006678A0`, `00667900`, `00667960`, `006679C0`, `00667A20` and 24 more |
| Y2K_LS_AreaTreeRes.cpp | `0066EA50`, `0066ED70`, `0066F670`, `0066FC40`, `0066FD10` |
| Y2K_LS_Items.cpp | `00670910`, `006709C0`, `00670A60`, `00670B00`, `00670BA0`, `00670C40` |
| Y2K_LS_Path.cpp | `00672A20`, `00672BF0`, `006732A0`, `006736E8`, `006738F0`, `00675960`, `00675A40`, `006763F0` and 13 more |
| Y2K_LS_Serialize.cpp | `006814F8`, `0068178B`, `00681850`, `00681950`, `00681BB0`, `00681F74`, `00682050` |
| Y2K_LS_TerrainGenerator.cpp | `0068247E`, `0068286A`, `00682DEB`, `00683974`, `00683A50`, `00683C70` |
| detail_mappings.cpp | `0065CF90` |

## lights

| file | functions |
|---|---|
| DXALightFX.cpp | `0063D6D0`, `0063DA10`, `0063DC50`, `0063DEF0`, `0063DFD0`, `0063E450` |

## minimap

| file | functions |
|---|---|
| Y2KMinimap.cpp | `006E2840`, `006E2C50`, `006E2E20`, `006E3580`, `006E38D0`, `006E3B20`, `006E3B80`, `006E4300` and 8 more |

## network

| file | functions |
|---|---|
| CRC.cpp | `00447690`, `00447780` |
| Callbacks.cpp | `00446030`, `0044666F`, `004466F0`, `00446877`, `0044698A`, `004469D5`, `00446A20`, `00446A68` and 3 more |
| Data.cpp | `004486F0`, `00448820`, `00448960`, `00448AD0`, `00448B30`, `00448BE8`, `00448CE8`, `00448FA0` and 2 more |
| Network.cpp | `004E574F`, `004E5BE8`, `004E6260`, `004E67D0`, `004E6B20`, `004E6BE8`, `004E6CB0`, `004E71E0` and 16 more |
| Packet.cpp | `004EDA50`, `004EF8C1`, `004F00A0`, `004F02C7`, `004F0980`, `004F0BE8`, `004F12A0`, `004F1470` and 1 more |
| Replay.cpp | `004F2BD0`, `004F31C0`, `004F38E0`, `004F394F`, `004F4096`, `004F448D`, `004F464E`, `004F4700` and 3 more |

## objects

| file | functions |
|---|---|
| Y2K3DObject.cpp | `006CBF50` |
| y2k_RenderList.cpp | `006CD820` |
| y2k_objects.cpp | `006CCE60`, `006CD3B0` |

## options

| file | functions |
|---|---|
| DXAOptions.cpp | `00616F73`, `0061706D`, `00617110`, `00617265`, `00617690` |
| DXAOptionsDlg.cpp | `006182A0`, `006183E0` |
| DXASystemData.cpp | `0061BB10`, `0061C440`, `0061C750`, `0061CBA0`, `0061CE40`, `0061D480`, `0061D650`, `0061E140` and 1 more |
| EnterCDKey.cpp | `006C0D10` |
| ErrorReport.cpp | `006C1470`, `006C1BE8` |
| options.cpp | `006C6A90`, `006C7269`, `006C7590` |

## quell

| file | functions |
|---|---|
| Y2KAnimationData.cpp | `005117E8` |
| Y2KAppSoundNet.cpp | `00511AF0`, `00511F10`, `005124A0`, `00512540`, `00512BE0` |
| Y2KAudioTrackLibrary.cpp | `005132D0`, `00513580` |
| Y2KBaseTimer.cpp | `00514BC0` |
| Y2KBaseTimerLibrary.cpp | `00515450`, `00515530` |
| Y2KBunkerHaendler.cpp | `00524AA0`, `00525770` |
| Y2KBunkerLayoutStorage.cpp | `005274C0` |
| Y2KBunkerToolsObject.cpp | `0052F866`, `0052F8AF`, `0052FCB3`, `0052FD30`, `0052FD86` |
| Y2KEditorLayoutStorage.cpp | `00548410` |
| Y2KEditorScriptingIDsLibary.cpp | `00559BE8`, `00559C40` |
| Y2KEditorToolsObject.cpp | `0055F220`, `0055F2B0`, `0055F600`, `0055F690`, `00564081`, `005657E8`, `005664F0`, `00569770` |
| Y2KFreeCamera.cpp | `0056D0C0`, `0056D2F0` |
| Y2KGamePlayUtils.cpp | `0056DC30` |
| Y2KGlobalFileFormat.cpp | `0056E010`, `0056E330`, `0056E500`, `0056E650` |
| Y2KKIAdd.cpp | `00573F50`, `00574BB0` |
| Y2KKIAnim.cpp | `006EE8D0`, `006EEE10`, `006EF2B0`, `006EF5F0`, `006EFC90`, `006F0020`, `006F0240` |
| Y2KKIAnim_Antilope.cpp | `006F05C0` |
| Y2KKIAnim_Bear.cpp | `006F0890`, `006F0A2C` |
| Y2KKIAnim_Cow.cpp | `00576480` |
| Y2KKIAnim_Deer.cpp | `006F0BE0` |
| Y2KKIAnim_Horse.cpp | `00576780` |
| Y2KKIAnim_Hyaene.cpp | `006F0EA0` |
| Y2KKIAnim_Tiger.cpp | `006F21E0`, `006F234C` |
| Y2KKIAnim_WildDog.cpp | `00576A30` |
| Y2KKIAnim_Wulf.cpp | `006F2510`, `006F267C` |
| Y2KKIBasicObject.cpp | `00576E40`, `00577420`, `00578810`, `00578BD0`, `00579130`, `005795E0`, `0057A710`, `0057A8C9` and 7 more |
| Y2KKIBasicPartyObject.cpp | `0057F1F0`, `00580046`, `00580670`, `005807F0`, `00580930`, `00580A80`, `00580B40`, `00580E09` and 56 more |
| Y2KKIBird.cpp | `00588860`, `00588E30`, `00589100`, `005891B0` |
| Y2KKIBox.cpp | `00589790`, `00589840` |
| Y2KKIBuild.cpp | `00589FE8`, `0058A430`, `0058A5C0`, `0058A730`, `0058A8A0`, `0058AAD0`, `0058AF70`, `0058B2E0` and 1 more |
| Y2KKIChar.cpp | `006F2BA0`, `006F2F00`, `006F3D90`, `006F42F0`, `006F4C00`, `006F5120`, `006F5580`, `006F60F0` and 21 more |
| Y2KKIChar_Child_Boy.cpp | `0058C810`, `0058CBBF` |
| Y2KKIChar_Child_Girl.cpp | `0058CF10`, `0058D29F` |
| Y2KKIChar_Con_Man.cpp | `00701AF0`, `007030E2`, `00703130`, `00703192` |
| Y2KKIChar_Con_Woman.cpp | `00704720`, `007058C2`, `00705910`, `00705972` |
| Y2KKIChar_Monk.cpp | `00706F74`, `00708182`, `007081D0`, `00708232` |
| Y2KKIChar_Mutant.cpp | `0058D700`, `0058E3D2`, `0058E420`, `0058E482` |
| Y2KKIChar_Nitro_Man.cpp | `007097F0`, `0070AAE2`, `0070AB30`, `0070ABC9` |
| Y2KKIChar_UnbornKnight.cpp | `00714BA0`, `00715135`, `0071515C`, `00715320`, `007153A0` |
| Y2KKIComputerPlayer.cpp | `00590046` |
| Y2KKIDummy.cpp | `00590250` |
| Y2KKIEvent.cpp | `00592AE0`, `00595580`, `00597B20`, `00597BA0`, `00597C70`, `0059CB00`, `0059CBE0`, `0059D220` and 19 more |
| Y2KKIEventLibrary.cpp | `005A23F0`, `005A2440`, `005A2610` |
| Y2KKIFXList.cpp | `005A5F00` |
| Y2KKIFollowMine.cpp | `005A4BC0`, `005A4D30` |
| Y2KKIFollowMineDecoy.cpp | `005A5C10` |
| Y2KKIMine.cpp | `005A6D90`, `005A6DF0` |
| Y2KKIMission.cpp | `005A7740`, `005A7D80`, `005A7E10`, `005A7E80`, `005A7ED0`, `005A7F20`, `005A8930`, `005A89C0` |
| Y2KKINetworkPlayer.cpp | `005A98C0` |
| Y2KKIObjectLibrary.cpp | `005A9990`, `005AA090`, `005AA7E8`, `005AA9D0`, `005AAB70`, `005AAC60`, `005ABA60`, `005AC290` and 3 more |
| Y2KKIObjectLibrary_DatSet.cpp | `005B5660`, `005B5A92` |
| Y2KKIObjectSettings.cpp | `005BCA02`, `005BCAF0`, `005BCBF0`, `005BCDB0`, `005BCF40`, `005BD7D0`, `005BDCA4`, `005BDF80` and 4 more |
| Y2KKIPatrolPointDummy.cpp | `005BF010` |
| Y2KKIPlayer.cpp | `005C0320`, `005C0850`, `005C0B00`, `005C0C00`, `005C1A80`, `005C1AFC`, `005C1F60` |
| Y2KKIPlayerLibrary.cpp | `005C4E10`, `005C4FB0`, `005C5660`, `005C57E0`, `005C5A4C`, `005C5BC0` |
| Y2KKIRegionsLibrary.cpp | `005C7070`, `005C7266`, `005C796D` |
| Y2KKIRocket.cpp | `005C8AF7`, `005C8F20`, `005C9016`, `005C9DD6`, `005C9F50`, `005CA190` |
| Y2KKISoundDummy.cpp | `005CC9F0` |
| Y2KKIStartPointDummy.cpp | `005CCEF0` |
| Y2KKITimeBomb.cpp | `005CD620`, `005CD680` |
| Y2KKITrigger.cpp | `005CDBF0`, `005CDE40`, `005CDEA0`, `005CE330`, `005CFC00`, `005CFFB0`, `005D01C7`, `005D03C0` and 29 more |
| Y2KKIUIPlayer.cpp | `005D8420`, `005DA830` |
| Y2KKIUnit.cpp | `007166C0`, `00716C90`, `00717740`, `00717870`, `007179D0`, `00718060`, `00718690`, `00718B50` and 35 more |
| Y2KKIUnitAirplane.cpp | `00743A70`, `00743DA0`, `00743E40`, `00743ED0` |
| Y2KKIUnitHeli.cpp | `0074513D`, `007452A0`, `007453D0`, `007456B0`, `00745850`, `00745980`, `00745AE8`, `00745C90` |
| Y2KKIUnit_2S3.cpp | `00727FB0`, `00728220`, `00728C30`, `00729320`, `00729400`, `007296A0`, `007299D0`, `0072B060` and 1 more |
| Y2KKIUnit_BM21.cpp | `0072B8D0`, `0072BBC0` |
| Y2KKIUnit_BMP1.cpp | `0072C440`, `0072C9F0` |
| Y2KKIUnit_BTR80.cpp | `0072CDA0`, `0072D2C0` |
| Y2KKIUnit_Bull.cpp | `0072D660`, `0072D820` |
| Y2KKIUnit_EAGLE.cpp | `0072E3A0`, `0072E540` |
| Y2KKIUnit_FLOGGER.cpp | `0072E720`, `0072E8CF` |
| Y2KKIUnit_FULCRUM.cpp | `0072EA60`, `0072EC30` |
| Y2KKIUnit_GAZ.cpp | `0072EDE0`, `0072F010` |
| Y2KKIUnit_GAZ2PLUS2.cpp | `0072F270`, `0072F470` |
| Y2KKIUnit_HIND.cpp | `0072F890`, `00730730` |
| Y2KKIUnit_HIP.cpp | `007313D0`, `00731500`, `00731900` |
| Y2KKIUnit_HUMMER.cpp | `00732509`, `00732810`, `00732950`, `00733090`, `00733E80`, `00733F10`, `00734010`, `007342F0` |
| Y2KKIUnit_M1A1.cpp | `00734A00`, `00734DB0` |
| Y2KKIUnit_MD500.cpp | `007352C0`, `007356F0`, `00735820` |
| Y2KKIUnit_OH58.cpp | `00735CC0`, `00735D10`, `00735E40` |
| Y2KKIUnit_Rager.cpp | `00736080`, `007361E0` |
| Y2KKIUnit_SHILKA.cpp | `0073C550`, `0073C9E0` |
| Y2KKIUnit_T55.cpp | `0073CC40`, `0073D2A0`, `0073D470`, `0073EF40`, `0073F0B0`, `0073F4A0` |
| Y2KKIUnit_T80.cpp | `0073F5F0`, `0073F9C0`, `00740260`, `00740BC0`, `00741E90`, `00742060` |
| Y2KKIUnit_URAL.cpp | `00742290`, `007424F0` |
| Y2KKIUnit_VULCAN.cpp | `00742E90`, `00743390` |
| Y2KKIUnit_WOLF.cpp | `00743640`, `00743840` |
| Y2KKIUtil_Rotor.cpp | `0074BA50`, `0074C470`, `0074C5A0` |
| Y2KKIUtil_Shilka_Tower.cpp | `005DDF20` |
| Y2KKIUtil_Tower.cpp | `0074C8D0`, `0074C9C0`, `0074E020` |
| Y2KKIVeget.cpp | `005DE7B0`, `005DE830`, `005DEAD0`, `005DEB80` |
| Y2KKIWeapon.cpp | `005DF860`, `005DF970`, `005DFFE0`, `005E013D`, `005E0680`, `005E06E0`, `005E0740`, `005E07E0` and 17 more |
| Y2KKI_ModelTexture_Ressource.cpp | `00572E40`, `00572FA0`, `00573020` |
| Y2KMissionDialogHistoryObject.cpp | `005F5F5F`, `005F5FE0` |
| Y2KMissionDialogLibrary.cpp | `005F70F0`, `005F84F0`, `005F8D70` |
| Y2KMissionLayoutStorage.cpp | `005FADD0` |
| Y2KMissionShortInfo.cpp | `005FCC10`, `005FCFE8`, `005FD490` |
| Y2KMissionSkriptLibrary.cpp | `005FEB20`, `005FEFE0`, `005FF5B0` |
| Y2KSelectionObject.cpp | `006069F0`, `00606AD0` |
| Y2KSkriptList.cpp | `00606E20`, `00606E80`, `00606EE0`, `00606F40`, `00607F81`, `00608100` |
| Y2KStartLayoutStorage.cpp | `0060F890` |
| Y2KStateClassUtils.cpp | `006104FE` |
| Y2KWeather.cpp | `00612460`, `00612650`, `00612780`, `00612880`, `00612C40`, `00612F50`, `00613080`, `0061356A` and 8 more |
| synchedrand.cpp | `0050CF20`, `0050CFB0`, `0050D110`, `0050D1B0` |

## quellscript

| file | functions |
|---|---|
| MetaCommando.cpp | `004BEAC0`, `004BEC1F` |
| Y2KKIAnim_Script.cpp | `006F1290`, `006F1310`, `006F13A0`, `006F16F0`, `006F1750`, `006F1C60`, `006F1CE0`, `006F1E10` and 2 more |
| Y2KKIBuild_Script.cpp | `0058C2F0`, `0058C3C0`, `0058C4A0`, `0058C580`, `0058C5E0` |
| Y2KKICharScript_SitDownWait.cpp | `00715EF0` |
| Y2KKIChar_Disarm.cpp | `0058D4F0`, `0058D540` |
| Y2KKIChar_Script.cpp | `0070C060`, `0070C3E8`, `0070C430`, `0070C590`, `0070C900`, `0070C960`, `0070CA00`, `0070CC50` and 25 more |
| Y2KKIChar_ScriptActivateBomb.cpp | `00711A80` |
| Y2KKIChar_ScriptAttack.cpp | `00711C60`, `00712010`, `00712070` |
| Y2KKIChar_ScriptClimb.cpp | `007124C0`, `00712A60` |
| Y2KKIChar_ScriptExchange.cpp | `00712DD0`, `00712E30` |
| Y2KKIChar_ScriptFernglas.cpp | `0058FC60`, `0058FCC0` |
| Y2KKIChar_ScriptGetIn.cpp | `007132F0`, `00713850` |
| Y2KKIChar_ScriptPickUp.cpp | `00713C70`, `00714170` |
| Y2KKIChar_ScriptPutDown.cpp | `00714550`, `007145E0` |
| Y2KKIChar_Script_GetInOut.cpp | `00710BD0`, `00710C50`, `00710CD0`, `00710D40`, `00710D90`, `00710F00`, `00710FA0`, `00711050` and 5 more |
| Y2KKIFade_Script.cpp | `005A3D60`, `005A3DE0`, `005A3E70`, `005A3EE0`, `005A4170`, `005A41E0`, `005A4260`, `005A42D0` and 4 more |
| Y2KKIScriptAttack.cpp | `005CBED0`, `005CBF30` |
| Y2KKIScript_Commando.cpp | `005CA6C0`, `005CAD10`, `005CADB0` |
| Y2KKIUnitAirPlane_Script.cpp | `007441A0`, `007442B0`, `00744470`, `00744710`, `00744890` |
| Y2KKIUnitHeli_Script.cpp | `007477E8`, `00747874`, `00747AD0`, `00748610`, `00748840`, `00748E50`, `00748F00`, `007490C1` and 24 more |
| Y2KKIUnit_Script.cpp | `00736420`, `00736520`, `00736590`, `00736710`, `00736D30`, `00736F10`, `00736F63`, `00737E60` and 26 more |
| Y2KKIVeget_Script.cpp | `005DF4B0`, `005DF5E8`, `005DF690`, `005DF770`, `005DF7D0` |
| Y2KKI_Script.cpp | `00573260`, `00573340`, `00573440`, `00573690`, `00573780` |

## quellstateclasses

| file | functions |
|---|---|
| Y2KBunker.cpp | `00515670`, `005173B0`, `00517580`, `00517770`, `00517850`, `00517AE7`, `00517DF0`, `00517FA0` and 11 more |
| Y2KEditor.cpp | `00538BE0`, `0053B410`, `0053B620`, `0053B740`, `0053B880`, `0053BAE0`, `0053E540`, `0053E710` and 11 more |
| Y2KMission.cpp | `005E7620`, `005E8D40`, `005E9040`, `005E9490`, `005E9650`, `005E9910`, `005EA592`, `005EB3E9` and 16 more |
| Y2KMissionLoad.cpp | `005FB600`, `005FBCE0`, `005FBD60`, `005FBE50`, `005FBEA0`, `005FBF00`, `005FBFE8` |
| Y2KStart.cpp | `006082C0`, `006093F0`, `006095F0`, `00609910`, `00609980`, `00609AB0`, `00609B70`, `00609D20` and 2 more |

## quellui_bunker

| file | functions |
|---|---|
| BunkerErrorMessagePanel.cpp | `00404200` |
| BunkerExitPanel.cpp | `00406CB0` |
| BunkerFilePanel.cpp | `00407540`, `00408A90`, `00408D70` |
| BunkerHangarAreaPanel1.cpp | `00412620` |
| BunkerHangarAreaPanel2.cpp | `00412940` |
| BunkerHangarAreaPanel3.cpp | `00412C60` |
| BunkerHangarPanel.cpp | `00413430` |
| BunkerHangar_Bewaffnung_LagerListPanel.cpp | `0040A690` |
| BunkerHangar_Bewaffnung_UnitListPanel.cpp | `0040CB70` |
| BunkerHangar_Bewaffnung_UnitPanel.cpp | `0040D7C0`, `0040E4D0` |
| BunkerHangar_Reparatur_AuftragslistePanel.cpp | `00410390` |
| BunkerHangar_Reparatur_UnitListPanel.cpp | `00410D20` |
| BunkerHangar_Reparatur_UnitPanel.cpp | `004117E0` |
| BunkerLagerAreaPanel1.cpp | `0041F3B0` |
| BunkerLagerAreaPanel2.cpp | `0041F6E0` |
| BunkerLagerAreaPanel3.cpp | `0041FA00` |
| BunkerLagerAreaPanel4.cpp | `0041FD20` |
| BunkerLagerPanel.cpp | `00420550` |
| BunkerLager_Ausruestung_LagerPanel.cpp | `00413E50` |
| BunkerLager_Ausruestung_SoldierPanel.cpp | `00415120`, `00416180` |
| BunkerLager_Ausruestung_TeamPanel.cpp | `00419250` |
| BunkerLager_Handel_Haendler.cpp | `00419AB0` |
| BunkerLager_Handel_Handel.cpp | `0041B260` |
| BunkerLager_Handel_Lager.cpp | `0041CF60` |
| BunkerLager_Info_ListPanel.cpp | `0041DE70` |
| BunkerLager_Info_ObjectPanel.cpp | `0041E920`, `0041F1E0` |
| BunkerLazarettAreaPanel1.cpp | `00427700` |
| BunkerLazarettAreaPanel2.cpp | `00427A20` |
| BunkerLazarettAreaPanel3.cpp | `00427D40` |
| BunkerLazarettAreaPanel4.cpp | `00428060` |
| BunkerLazarettPanel.cpp | `00428880` |
| BunkerLazarett_ProduktionsPanel.cpp | `00421424` |
| BunkerLazarett_Steigern_AuftragslistePanel.cpp | `00422480` |
| BunkerLazarett_Steigern_EinheitenPanel.cpp | `00423A50` |
| BunkerLazarett_Steigern_EinheitenlistePanel.cpp | `00422EE0` |
| BunkerLazarett_Versorgen_AuftragslistePanel.cpp | `00424E60` |
| BunkerLazarett_Versorgen_EinheitenPanel.cpp | `00426430` |
| BunkerLazarett_Versorgen_EinheitenlistePanel.cpp | `004258B0` |
| BunkerNavigationPanel.cpp | `0042DFE8` |
| BunkerOptionsPanel.cpp | `0042E8CE` |
| BunkerStartplatzAreaPanel1.cpp | `004342E0` |
| BunkerStartplatzAreaPanel2.cpp | `00434600` |
| BunkerStartplatzAreaPanel3.cpp | `00434954` |
| BunkerStartplatzControl.cpp | `00435040` |
| BunkerStartplatz_EinsatzteamPanel.cpp | `0042EEE8` |
| BunkerStartplatz_HeliPanel.cpp | `0042FD60` |
| BunkerStartplatz_LagerPanel.cpp | `00430150` |
| BunkerStartplatz_SoldatenPanel.cpp | `004311B0` |
| BunkerStartplatz_SpecialSkillPanel.cpp | `00431824` |
| BunkerStartplatz_SpecialSkillSelektionPanel.cpp | `00432DB0` |
| BunkerStartplatz_UebersichtsPanel.cpp | `00433824` |
| BunkerStartplatz_UnitPanel.cpp | `00434040` |
| BunkerTaktikPanel.cpp | `00439590` |
| BunkerTaktik_MissionGoal1Panel.cpp | `00435C50` |
| BunkerTaktik_MissionGoal2Panel.cpp | `00436370`, `00436A70` |
| BunkerTaktik_MissionGoalVideoPanel.cpp | `00436BD0`, `004370E0` |
| BunkerTaktik_NotePanel.cpp | `004377B0`, `00438900` |
| BunkerTrackListPanel.cpp | `0043A3E8` |
| BunkerWerkstattAreaPanel1.cpp | `00444441` |
| BunkerWerkstattAreaPanel2.cpp | `004446E9` |
| BunkerWerkstattAreaPanel3.cpp | `00444990` |
| BunkerWerkstattAreaPanel4.cpp | `00444CB0` |
| BunkerWerkstattPanel.cpp | `00445530` |
| BunkerWerkstatt_Bewaffnung_LagerListPanel.cpp | `0043B5F0` |
| BunkerWerkstatt_Bewaffnung_UnitListPanel.cpp | `0043CFE8` |
| BunkerWerkstatt_Bewaffnung_UnitPanel.cpp | `0043D7C0`, `0043E910` |
| BunkerWerkstatt_Panzern_AuftragslistePanel.cpp | `0043FC8E` |
| BunkerWerkstatt_Panzern_UnitListPanel.cpp | `004404E0` |
| BunkerWerkstatt_Panzern_UnitPanel.cpp | `00441050`, `00441600` |
| BunkerWerkstatt_Reparatur_AuftragslistePanel.cpp | `00442040` |
| BunkerWerkstatt_Reparatur_UnitListPanel.cpp | `00442A10` |
| BunkerWerkstatt_Reparatur_UnitPanel.cpp | `00443824`, `00443A90` |

## quellui_editor

| file | functions |
|---|---|
| EditorBackgroundSoundPanel.cpp | `0044A0E0` |
| EditorBoxEquipmentPanel.cpp | `0044B080` |
| EditorBunkerSetupPanel.cpp | `0044BD00` |
| EditorCameraTrackPanel.cpp | `0044C300` |
| EditorCharacterEquipmentPanel.cpp | `0044D640` |
| EditorCharacterPreferencesPanel.cpp | `00450230` |
| EditorDialogEditorFaceSelectPanel.cpp | `004522D0` |
| EditorDialogEditorObjectSelectPanel.cpp | `00453190` |
| EditorDialogEditorPanel.cpp | `00453A90` |
| EditorDialogEditorRegionSelectPanel.cpp | `00455A50` |
| EditorDialogEditorSelectPanel.cpp | `00456300` |
| EditorDialogPanel.cpp | `004572C0` |
| EditorDiplomacyPanel.cpp | `004576F0` |
| EditorErrorMessagePanel.cpp | `00458018` |
| EditorFilePanel.cpp | `00459450` |
| EditorGMMainPanel1.cpp | `0045B450` |
| EditorGMOptionsPanel.cpp | `0045B930` |
| EditorGMPlayerListPanel.cpp | `0045BE00` |
| EditorHeliEquipmentPanel.cpp | `0045CBF0` |
| EditorImportHeightsPanel.cpp | `0045F3E8` |
| EditorInfoPanel.cpp | `0045F980` |
| EditorInventoryPanel.cpp | `00460570` |
| EditorListItem_ScriptElement.cpp | `00462720` |
| EditorMGAllEventsPanel.cpp | `00468DB0` |
| EditorMGAllTriggersPanel.cpp | `0046B90B` |
| EditorMGCountPanel.cpp | `0046D0D0` |
| EditorMGEFollowMissionPanel.cpp | `0046DA00` |
| EditorMGEObjectStatePanel.cpp | `0046E010` |
| EditorMGPartyPanel.cpp | `0046E8CE` |
| EditorMGRegionPanel.cpp | `0046F070` |
| EditorMGSwitchPanel.cpp | `0046F7E8` |
| EditorMGUnitPanel.cpp | `00470045` |
| EditorMainPanel.cpp | `00463360`, `004637D6` |
| EditorMenuPanel_File.cpp | `004660E0` |
| EditorMenuPanel_Game.cpp | `004668F0` |
| EditorMenuPanel_Properties.cpp | `00466E30` |
| EditorMenuPanel_Scene.cpp | `00467390` |
| EditorMenuPanel_Script.cpp | `00467940` |
| EditorMenuPanel_Settings.cpp | `00467F80` |
| EditorMenuPanel_Tools.cpp | `00468650` |
| EditorMinimapPanel.cpp | `004703E0` |
| EditorMissionDesign1Panel.cpp | `00470EE0` |
| EditorMissionDesignAddToBunkerInterchangeParamsPanel.cpp | `00471FD0` |
| EditorMissionDesignAllGetOutParamsPanel.cpp | `00472AB0` |
| EditorMissionDesignAttackObjectParamsPanel.cpp | `00473160` |
| EditorMissionDesignCamraJumpParamsPanel.cpp | `00473BC0` |
| EditorMissionDesignCrawlerMinesParamsPanel.cpp | `00474747` |
| EditorMissionDesignDamageParamsPanel.cpp | `00475542` |
| EditorMissionDesignDialogEndsParamsPanel.cpp | `00476510` |
| EditorMissionDesignDialogParamsPanel.cpp | `00476F70` |
| EditorMissionDesignEnemySpottedParamsPanel.cpp | `00477A30` |
| EditorMissionDesignEreignissPanel.cpp | `00478400` |
| EditorMissionDesignFilePanel.cpp | `004798D0` |
| EditorMissionDesignGetInParamsPanel.cpp | `0047A640` |
| EditorMissionDesignGetOutParamsPanel.cpp | `0047AEB0` |
| EditorMissionDesignGlobalPanel.cpp | `0047B913` |
| EditorMissionDesignInGameMovieEndsParamsPanel.cpp | `0047C1C0` |
| EditorMissionDesignInsertObjectParamsPanel.cpp | `0047C860` |
| EditorMissionDesignIsApproachedParamsPanel.cpp | `0047D060` |
| EditorMissionDesignIsInInventoryParamsPanel.cpp | `0047DBE8` |
| EditorMissionDesignIsInsideUnitParamsPanel.cpp | `0047E240` |
| EditorMissionDesignJoinPartyParamsPanel.cpp | `0047EBB0` |
| EditorMissionDesignKnightCamouflageStateParamsPanel.cpp | `0047F760` |
| EditorMissionDesignMakeObjectUsableParamsPanel.cpp | `004802D0` |
| EditorMissionDesignMoveUnitParamsPanel.cpp | `00481024` |
| EditorMissionDesignMovieSelectionPanel.cpp | `00481BE0` |
| EditorMissionDesignObjectIsUsedParamsPanel.cpp | `00482444` |
| EditorMissionDesignObjectSelectPanel.cpp | `00482F90` |
| EditorMissionDesignObjectTreeListPanel.cpp | `004837C0` |
| EditorMissionDesignOwnUnitParamsPanel.cpp | `0048435F` |
| EditorMissionDesignPartyAttackedPartyParamsPanel.cpp | `00484CC0` |
| EditorMissionDesignPartySpottedInAreaParamsPanel.cpp | `00485550` |
| EditorMissionDesignPartySpottedPartyParamsPanel.cpp | `00485FE0` |
| EditorMissionDesignPartyStatisticParamsPanel.cpp | `00486783` |
| EditorMissionDesignPatrolParamsPanel.cpp | `004877C0` |
| EditorMissionDesignPatrolRoutePanel.cpp | `00488830` |
| EditorMissionDesignPickAddParamsPanel.cpp | `00488F40` |
| EditorMissionDesignRandomParamsPanel.cpp | `00489950` |
| EditorMissionDesignRegionParamsPanel.cpp | `0048AD20` |
| EditorMissionDesignRemoveObjectParamsPanel.cpp | `0048BD70` |
| EditorMissionDesignSetApproachableModeParamsPanel.cpp | `0048C640` |
| EditorMissionDesignSetCharImmortalParamsPanel.cpp | `0048CE90` |
| EditorMissionDesignSetDiplomacyParamsPanel.cpp | `0048DC68` |
| EditorMissionDesignSetFollowMissionParamsPanel.cpp | `0048E3E8` |
| EditorMissionDesignSetMissionExtroParamsPanel.cpp | `0048F068` |
| EditorMissionDesignSetMissionIntroParamsPanel.cpp | `0048F868` |
| EditorMissionDesignSetObjectStateParamsPanel.cpp | `00490160` |
| EditorMissionDesignSetUIMissionGoalParamsPanel.cpp | `00491090` |
| EditorMissionDesignShowBoxInventoryParamsPanel.cpp | `004917A0` |
| EditorMissionDesignStartScriptParamsPanel.cpp | `00492BE8` |
| EditorMissionDesignStartTimeParamsPanel.cpp | `00493470` |
| EditorMissionDesignStartVideoParamsPanel.cpp | `00494554` |
| EditorMissionDesignStartpingParamsPanel.cpp | `00492160` |
| EditorMissionDesignStopPingParamsPanel.cpp | `004950F0` |
| EditorMissionDesignSwitchParamsPanel.cpp | `00495C20` |
| EditorMissionDesignTextMessageParamsPanel.cpp | `00496F00` |
| EditorMissionDesignTimeParamsPanel.cpp | `00498DFF` |
| EditorMissionDesignTriggerLinksPanel.cpp | `00499860` |
| EditorMissionDesignUIGoalStatePanel.cpp | `0049A240` |
| EditorMissionDesignUnitBehaviourParamsPanel.cpp | `0049AE10` |
| EditorNewPanel.cpp | `0049D310` |
| EditorPlayerPreferencesPanel.cpp | `0049DDE0` |
| EditorPreviewPanel.cpp | `0049E6A0`, `0049E9B0` |
| EditorRegionPreferencesPanel.cpp | `0049ECB0` |
| EditorRenamePanel.cpp | `0049F2A0` |
| EditorScriptEditorPanel.cpp | `004A07E8` |
| EditorScriptEditorTimePanel.cpp | `004A2424` |
| EditorScriptInsertPanel.cpp | `004A2D10` |
| EditorScriptMainSentencePanel1.cpp | `004A4690` |
| EditorScriptRenamePanel.cpp | `004A63D0` |
| EditorScriptSelectionPanel.cpp | `004A70C1` |
| EditorSoundDummyPreferencesPanel.cpp | `004A7A60` |
| EditorStatisticPanel.cpp | `004A9260` |
| EditorTerrainDataPanel.cpp | `004AB020` |
| EditorTextureFloot1Panel.cpp | `004AB8E0` |
| EditorTextureFloot2Panel.cpp | `004AC6D0` |
| EditorTextureFloot3Panel.cpp | `004AE8CE` |
| EditorTextureFlootRegionPanel.cpp | `004AFA00` |
| EditorTextureReplacePanel.cpp | `004B01D0` |
| EditorTimePanel.cpp | `004B0A80` |
| EditorToolBarCameraPanel.cpp | `004B10E0` |
| EditorToolBarCharactersPanel.cpp | `004B1550` |
| EditorToolBarDummiesPanel.cpp | `004B1C40` |
| EditorToolBarFieldPanel.cpp | `004B21C0` |
| EditorToolBarObjectsPanel.cpp | `004B2800` |
| EditorToolBarPlayerPanel.cpp | `004B2D00` |
| EditorToolBarTerrainPanel.cpp | `004B3160` |
| EditorToolBarTexturesPanel.cpp | `004B3870` |
| EditorToolBarTreesPanel.cpp | `004B4060` |
| EditorToolBarUnitsPanel.cpp | `004B4953` |
| EditorTreeFloot1Panel.cpp | `004B50A0` |
| EditorTreeFloot2Panel.cpp | `004B67E8` |
| EditorTreeFloot3Panel.cpp | `004B7CB0` |
| EditorTreeFlootRegionPanel.cpp | `004B9040` |
| EditorUnitCrewPanel.cpp | `004B98E0` |
| EditorUnitEquipmentPanel.cpp | `004BAEE0` |
| EditorUnitPreferences1Panel.cpp | `004BD150` |
| EditorWeatherPanel.cpp | `004BDB20` |

## quellui_mission

| file | functions |
|---|---|
| MissionBoxPanel.cpp | `004BF350` |
| MissionBreakPanel.cpp | `004C0180` |
| MissionCameraModePanel.cpp | `004C05F0` |
| MissionCompletePanel.cpp | `004C1030` |
| MissionCountDownPanel.cpp | `004C28D0`, `004C2D40` |
| MissionDialogHistoryPanel.cpp | `004C30D0` |
| MissionDialogPanel.cpp | `004C3950`, `004C3C30`, `004C4588`, `004C4941` |
| MissionErrorMessagePanel.cpp | `004C505F` |
| MissionExitPanel.cpp | `004C6720` |
| MissionFailedPanel.cpp | `004C6D60` |
| MissionFilePanel.cpp | `004C7A20`, `004C830D`, `004C8F00`, `004C90C1`, `004C9360` |
| MissionHelpPanel.cpp | `004C98A0` |
| MissionKIFlagsPanel.cpp | `004CA980` |
| MissionKeyHelpPanel.cpp | `004CA330` |
| MissionKontextMenu.cpp | `004CB7E8` |
| MissionListItemFinal_Unit.cpp | `004D2220` |
| MissionListItemQuickSel_Soldier.cpp | `004D2F90` |
| MissionListItemQuickSel_Unit1.cpp | `004D4A70` |
| MissionListItem_CrewSoldier.cpp | `004CD320` |
| MissionMPStatisticPanel.cpp | `004D9520` |
| MissionMPWaitingPanel.cpp | `004D9D90` |
| MissionMainInventoryPanel.cpp | `004D5640` |
| MissionMainInventoryPanel_UK.cpp | `004D7970` |
| MissionMinimapPanel.cpp | `004D7E70` |
| MissionMissionTargetsPanel.cpp | `004D8BA4` |
| MissionOptionsPanel.cpp | `004DA4A0` |
| MissionPausePanel.cpp | `004DAE70` |
| MissionQuickSelection.cpp | `004DB720` |
| MissionSelectionPanel1.cpp | `004DC310`, `004DC7F0`, `004DCC60`, `004DD190` |
| MissionSelectionPanel2.cpp | `004DDDE0`, `004DF560`, `004DFA50`, `004DFAC0`, `004DFB30`, `004DFB90` |
| MissionSelectionPanel_UK.cpp | `004E00C7`, `004E05A0`, `004E0850`, `004E08C0`, `004E0930`, `004E0990` |
| MissionTimerPanel.cpp | `004E0C60`, `004E1480` |
| MissionTrackListPanel.cpp | `004E1BE8` |
| MissionUIManager.cpp | `004E4C70` |
| MissionVideoPanel.cpp | `004E5110` |

## quellui_start

| file | functions |
|---|---|
| StartCampaignIntroPanel.cpp | `004F5EB0`, `004F6200`, `004F62B0`, `004F6770` |
| StartCreditsPanel.cpp | `004F6A40` |
| StartDifficultyLevelPanel.cpp | `004F7700` |
| StartErrorMessagePanel.cpp | `004F80B3` |
| StartIdPanel.cpp | `004F9470`, `004FA090`, `004FA160`, `004FA210` |
| StartMPCreateSessionPanel.cpp | `004FC770` |
| StartMPIPAdressPanel.cpp | `004FD7E8` |
| StartMPJoinSessionListPanel.cpp | `004FE7E8` |
| StartMPPasswordPanel.cpp | `004FF1F0` |
| StartMPStartPanel.cpp | `004FF9B0` |
| StartMPWaitingPanel.cpp | `00500BE8` |
| StartOPKeyPanel_Assign.cpp | `00503250` |
| StartOptionsSettingsPanel.cpp | `0050555F` |
| StartSPCMInfoButtonsPanel.cpp | `00506A10` |
| StartSPCMMissionInfoPanel.cpp | `00507230`, `00507520` |
| StartSPCMMissionListPanel.cpp | `00507D80`, `00508AA0` |
| StartSPSMInfoButtonsPanel.cpp | `00508FE8` |
| StartSPSMMissionInfoPanel.cpp | `00509660` |
| StartSPSMMissionListPanel.cpp | `0050A820` |
| StartSPStartPanel.cpp | `0050B6A0` |
| StartWelcomePanel.cpp | `0050C480`, `0050CC90` |

## resources

| file | functions |
|---|---|
| Resources.cpp | `00656230`, `00656572`, `00656D69`, `00656E6F`, `00657572` |

## scripts

| file | functions |
|---|---|
| AirStrike.cpp | `006B9390` |
| y2k_SplineWalker.cpp | `006CF360` |

## source

| file | functions |
|---|---|
| Y2K_SoundPlayer.cpp | `006CDC00`, `006CDC60`, `006CDCC0`, `006CDD30`, `006CDDC0`, `006CDE60`, `006CDFB7`, `006CE344` |
| Y2K_VideoPlayer.cpp | `006CF850`, `006CF94E`, `006CFA20`, `006CFA80`, `006CFAE0`, `006D0077`, `006D03F0`, `006D0820` and 1 more |

## streams

| file | functions |
|---|---|
| tsStream.cpp | `006590E0`, `00659180`, `006592C0`, `00659370`, `00659420`, `006594D0`, `00659B70`, `00659CC0` and 1 more |
| tsZipStream.cpp | `005105F0`, `00510660`, `005106D0`, `00510790`, `00510824`, `00510880` |

## util

| file | functions |
|---|---|
| CDKey.cpp | `006BEFC0` |
| CDKeyValidator.cpp | `006C0B40` |

## utils

| file | functions |
|---|---|
| RASHelper.cpp | `006C8BE8`, `006C8CB0` |

## weather

| file | functions |
|---|---|
| DXAWeatherFX.cpp | `0064F290`, `0064F390`, `0064FB90`, `0064FC40`, `0064FEE0` |

## y2k_source

| file | functions |
|---|---|
| Y2K.cpp | `006CABE8`, `006CB6D8` |
| Y2KApp.cpp | `006D0DC0`, `006D17E8`, `006D1EDE`, `006D2000`, `006D2200`, `006D2280`, `006D27E0`, `006D29D0` and 15 more |
| Y2KRocket.cpp | `006E7030` |
| Y2KUnitSel.cpp | `006E8220`, `006E83D0`, `006E8420`, `006E8BB0`, `006EA200`, `006EBB60` |

