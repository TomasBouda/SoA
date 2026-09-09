# Trading: what an item is worth

The trader in the base ("Seeker Wladimir") barters, he does not sell for money.
The player never sees a number, but every object carries one and the whole deal
is decided by simple arithmetic. This page is what came out of reading the code
in `soa.exe` 1.1.2.178.

## The value is field 0 of the Data.set record

Every record of `data/GameData/Data.set` starts, right after the four strings,
with a float that the parser in [tools/dataset.py](tools/dataset.py) reports as
field 0. In the loaded object it lands at member `+0x4C`, and that is the value
the trade works with.

Three item classes expose it in vtable slot `+0x28` as a plain getter:

```
005E05A0  mov eax, [ecx + 0x20]     ; the settings of the item
005E05A3  fld dword ptr [eax + 0x50]  ; the neighbouring field 1
005E05A6  ret
005E05B0  mov eax, [ecx + 0x20]
005E05B3  fld dword ptr [eax + 0x4c]  ; <- field 0, the value
005E05B6  ret
```

and the trade sums call exactly that slot (`call dword ptr [edx + 0x28]`).

The numbers make sense on their own: F-15 7000, Mi-24 HIND 6000, T-80 4000,
M1A1 3750, T-55 3000, HUMVEE 500, URAL 350, Dragunov 100, M60 50, AK-74 20,
Uzi 10, Beretta 5, a Medipack 10, a Box 3, and the quest Controlchip 1300. The
whole list is in `catalog.txt` next to the launcher (the `value` column) and the
catalog window shows it as "worth".

## A vehicle is worth less when it is damaged

Units do not use the value directly. `0x725C90` computes:

```
r1 = virt+0x84() / virt+0x7C()      ; a condition ratio
r2 = virt+0xB0() / virt+0xA8()      ; a second condition ratio
value = (2*r2 + r1) / 3 * settings[+0x4C]
```

So a vehicle at full health is worth its full value, a wreck a fraction of it.
Items are taken at their full value, no wear involved.

## What the trader demands

`Y2KBunkerHaendler` keeps two lists: `+0x50` is what the player takes (the
trader's goods) and `+0x60` is what the player gives. The evaluation at
`0x524DB0` sums both sides and grades the deal:

```
take = sum of the values on the trader's side
give = sum of the values on the player's side

if ((factor + tolerance) * take < give)   grade 0    ; the player massively overpays
else if (factor * take < give)            grade 1
else if ((factor - tolerance) * take < give) grade 2 ; just barely enough
else                                      grade 3    ; too little -> refused
```

`0x524E30` executes the trade and returns false on grade 3, so **grade 3 is a
refusal**. `TRES_TRADER.trs` holds the trader's five answers in exactly that
order, which confirms the direction:

| grade | resource | what he says |
|---|---|---|
| 0 | `TRES_TRADER_TRADEGOOD1` | Delighted ! |
| 1 | `TRES_TRADER_TRADEOK1` | Ok, let's trade. |
| 2 | `TRES_TRADER_TRADEBAD1` | If you really want to... |
| 3 | `TRES_TRADER_TRADENO1` | Never! |
| — | `TRES_TRADER_QUESTION1` | What do you want to trade? |

The constructor at `0x524440` sets the numbers:

| member | value | meaning |
|---|---|---|
| `+0x04` | 1.5 | the current trade factor |
| `+0x08` | 1.0 | the floor the factor is measured against |
| `+0x0C` | 0.3 | tolerance |
| `+0x10` | 0.1 | how much the factor moves after a deal |

**In practice: to get a deal you have to offer more than
`(factor − tolerance) × take`, that is more than 1.2 times the value of what you
are taking** with the starting factor. The editor sets a Trade Factor per
trader (`Trader Inventory` panel), so a particular mission can be harsher or
milder, and the game option "Trader Attitude" adjusts the friendliness as well.

## The factor moves with how you deal

After every completed trade the same function adjusts the factor:

* grade 0 (the player heavily overpaid) → `factor -= 0.1`, the trader gets
  cheaper next time
* grade 2 (the player scraped through) → `factor += 0.1`, the trader gets
  greedier
* then the factor is clamped from below to `floor + tolerance` = 1.3, so the
  price never falls under 1.0 times the value

So haggling has a memory: being generous a few times pushes the exchange rate
from 1.2 down towards 1.0, but never below.

## What is worth trading

It follows from the numbers that the good things to hand over are the ones with
a high value and little use in the field — the aluminium Case (250), spare
launchers and vehicles you do not fly. Ammunition is cheap (9mm 1, 5.45mm 5,
7.62mm 15), so paying with ammunition means handing over crates of it.

The catalog window (`Play.exe -catalog`) shows the value of every item, so the
cheapest way to see the whole price list is to open it and read the "worth"
line.

## The price list

Generated from `catalog.txt`, which `tools/gen_catalog.py` builds out of
`Data.set`. A vehicle is listed at its full value - damage lowers what the
trader actually counts. The same vehicles appear twice: once as a machine in
the garage and once as an item in the storage.

### Vehicles

| vehicle | value |
|---|---|
| F-15 Eagle | 7000 |
| Mi-24 HIND | 6000 |
| MiG-29 | 6000 |
| MiG-27 | 5000 |
| Mi-8 HIP | 4000 |
| MBT T-80 | 4000 |
| MBT M1A1 | 3750 |
| OH-58 | 3500 |
| MD-500 | 3300 |
| BM-21 | 3200 |
| HOW 2S3 | 3000 |
| MBT T-55 | 3000 |
| AD SHILKA | 2200 |
| AD M163 | 1900 |
| ICV BMP | 1800 |
| APC BTR | 1500 |
| HUMVEE | 500 |
| URAL | 350 |
| RAGER | 300 |
| WOLF | 250 |
| BULL | 200 |
| GAZ A | 150 |
| GAZ | 100 |

### Gear and weapons (42)
| item | value | | item | value |
|---|---|---|---|---|
| Controlchip | 1300 | | AK74 | 20 |
| Unborn Minigun | 1000 | | Throwing Knife | 20 |
| Unborn Rocketlauncher | 1000 | | MP5 | 15 |
| Crawler Mine | 1000 | | Explosive | 15 |
| Bug | 300 | | UZI | 10 |
| Crawler Bug | 300 | | Shotgun | 10 |
| Case | 250 | | Hand Grenade | 10 |
| SA7 Grail | 200 | | Medipack | 10 |
| RPG7 Bazooka | 100 | | FLY Pills | 10 |
| Dragunov | 100 | | Beretta | 5 |
| M79 | 100 | | Molotov | 5 |
| Mine Bait | 100 | | Fog Grenade | 5 |
| RPK | 60 | | Tank Mine | 5 |
| M60 | 50 | | Box | 3 |
| HUMVEE M60 | 50 | | 73mm Kanone | 0 |
| Night Vision Gear | 50 | | 125mm Kanone | 0 |
| Heavy Vest | 50 | | 125mm Kanone | 0 |
| Light Vest | 35 | | 125mm Kanone | 0 |
| Crossbow | 30 | | Katjuscha MLRS | 0 |
| Stun Grenade | 25 | | 152mm Kanone | 0 |
| Binoculars | 25 | | Aufhängung Bombe | 0 |

### Vehicle weapons (29)
| item | value | | item | value |
|---|---|---|---|---|
| 4x AT6 Launcher | 500 | | rohrparalleles MG | 0 |
| AT6 Launcher | 225 | | Flammenwerfer | 0 |
| HUMVEE TOW | 200 | | rohrparalleles MG | 0 |
| TOW Launcher | 200 | | Granatwerfer | 0 |
| SA-7 Launcher | 200 | | Turmmg | 0 |
| UV-32 Launcher | 185 | | 4x 14,5mm Machinenkanone | 0 |
| UB-20 Launcher | 175 | | AT2 Llauncher | 0 |
| HUMVEE Plamya | 150 | | Gattling Gun | 0 |
| UV-7 Launcher | 100 | | Turmmg | 0 |
| 14,5mm Maschinenkanone | 0 | | Nebelwerfer | 0 |
| rohrparalleles MG | 0 | | Nebelwerfer | 0 |
| AT2 Startschiene | 0 | | Nebelwerfer | 0 |
| Gattling Gun | 0 | | Nebelwerfer | 0 |
| rohrparalleles MG | 0 | | Heli MG | 0 |
| Turmmg | 0 | |  |  |

### Ammunition (39)
| item | value | | item | value |
|---|---|---|---|---|
| 125mm APFSDS | 250 | | Kerosene Canister | 20 |
| 1000 LB BOMB | 250 | | 7,62mm x 50 | 15 |
| 500 LB BOMB | 150 | | 152mm FLARE | 15 |
| SA-7B HEFRAG | 100 | | 80mm AS | 12 |
| AT6 | 85 | | 40mm Plamja HE | 10 |
| 125mm HEFRAG | 75 | | 57mm AS | 10 |
| TOW HEAT | 75 | | 5,45mm x 30 | 5 |
| 14,5mm x 250 | 50 | | 40mm Plamja Fire | 5 |
| 73mm HEFRAG | 50 | | Fog Grenade | 5 |
| 125mm HEAT | 50 | | Crossbow Bolt x 6 | 3 |
| PG7 M HEAT | 50 | | 22mm Shells x 10 | 1.5 |
| BM21 HEFRAG | 50 | | 9mm x 20 | 1 |
| BM21 MINE | 45 | | Knife | 0 |
| 152mm HE | 40 | | Hand Grenade | 0 |
| 152mm MINE | 35 | | Molotov | 0 |
| AT2 | 35 | | Unborn Rounds | 0 |
| 73mm HEAT | 25 | | Unborn Rocket | 0 |
| Sniper Munition | 25 | | Nebelgranate (Mun) | 0 |
| 152mm FOG | 20 | | Betäubungsgranate (Mun) | 0 |
| BM21 SMOKE | 20 | |  |  |

The mounted vehicle weapons are mostly worth 0: they are part of the machine,
not goods, so nothing is gained by carrying them to the trader.

## What is not in the data

Neither `Data.set` nor `Units.olb` holds a link between a weapon system and its
carrier, so the catalog pairs vehicle armament by name - see
[dataset-format.md](dataset-format.md). Trading is not affected by that; the
value stands on its own for every item.
