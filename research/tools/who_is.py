"""Whose side a named character is on in the running mission.

    python who_is.py "Ronny Knauth" "Olaf Sacher"

Scans the game's memory for the name, then walks every player's unit list
and reports the units that point at the name (from the unit itself or its
stats object at +0x320), with the player they belong to and that player's
diplomacy towards the squad - 0 neutral, 1 enemy, 2 friend. This is how the
developers in the name pool were found standing in the enemy lines (see
"Easter eggs" in architecture.md). Reads only.
"""
import struct
import sys

import play_bot
import scan_memory as sm


def find_all(h, needle):
    out = []
    for base, size in sm.regions(h):
        if size > 64 << 20:
            continue
        data = sm.read(h, base, size)
        if not data:
            continue
        i = data.find(needle)
        while i >= 0:
            out.append(base + i)
            i = data.find(needle, i + 1)
    return out


def main():
    g = play_bot.Game()
    names = sys.argv[1:] or ['Ronny Knauth']
    players = g.players()
    ui = [p for p in players if p['ui']][0]
    print('players', [(p['index'], p['ui'], len(p['units'])) for p in players])
    print('diplomacy towards the squad', ui['diplomacy'])
    for name in names:
        hits = find_all(g.h, name.encode('latin-1') + b'\0')
        print('%s: %d copies of the name in memory' % (name, len(hits)))
        for p in players:
            for u in p['units']:
                head = sm.read(g.h, u, 0x400)
                if not head or len(head) < 0x324:
                    continue
                stats = struct.unpack_from('<I', head, 0x320)[0]
                block = sm.read(g.h, stats, 0x200) if stats else b''
                for h in hits:
                    pointer = struct.pack('<I', h)
                    if pointer in head or (block and pointer in block):
                        print('   unit %08X  player %d%s  diplomacy %s  hp %s'
                              % (u, p['index'], ' (you)' if p['ui'] else '',
                                 ui['diplomacy'].get(p['index'], 'neutral'), g.unit(u).get('hp')))
                        break


if __name__ == '__main__':
    main()
