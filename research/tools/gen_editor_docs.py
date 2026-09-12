"""Builds a reference overview of the scripting system of the mission editor.

Sources:
  - soa.exe                  the class names of the scripting elements (CY2KKI*)
  - TRES_EDITOR.trs          the editor labels and messages, which name the
                             elements in human terms and give away their
                             parameters
  - TRES_EDITOR_MISSIONGOALS.trs   the mission goal types

Output: _research/editor-scripting.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trs import load  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
EXE = os.path.join(ROOT, '_patched', 'soa.exe')
UBN = os.path.join(ROOT, '_patched', 'data.ubn')
OUT = os.path.join(ROOT, '_research', 'editor-scripting.md')

TRS_EDITOR = 'data/GUIData/TextResource_eng/TRES_EDITOR.trs'
TRS_GOALS = 'data/GUIData/TextResource_eng/TRES_EDITOR_MISSIONGOALS.trs'


def exe_strings(path, minlen=6):
    data = open(path, 'rb').read()
    return [m.group().decode('latin1')
            for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data)]


def classes(strings, prefix):
    pat = re.compile(r'%s_([A-Za-z0-9_]+)' % re.escape(prefix))
    found = set()
    for s in strings:
        for m in pat.finditer(s):
            name = m.group(1)
            # cut off method suffixes such as ::Tick
            name = name.split(':')[0]
            found.add(name)
    return sorted(found)


def human_names(rows):
    """Pull the human name and the parameter types out of the "deleted parameter" messages.

    Example id:   TRES_EDITOR_DELETED_SCRIPTING_MOVE_UNIT_PARAM_OBJECT
    Example text: ... that you have used in a "move unit"-event ...
    """
    out = {}
    pat = re.compile(r'TRES_EDITOR_DELETED_SCRIPTING_(.+)_PARAM_([A-Z]+)$')
    for rid, text in rows:
        m = pat.match(rid)
        if not m:
            continue
        key, param = m.group(1), m.group(2).lower()
        q = re.search(r'"([^"]+)"-(\w+)', text)
        label, kind = (q.group(1), q.group(2)) if q else (key.lower().replace('_', ' '), '?')
        rec = out.setdefault(key, {'label': label, 'kind': kind, 'params': set()})
        rec['params'].add(param)
    return out


def match_label(cls, humans):
    """Pair a class name (AttackObject) with a message key (ATTACKOBJECT / ATTACK_OBJECT)."""
    flat = cls.upper().replace('_', '')
    for key, rec in humans.items():
        if key.replace('_', '') == flat:
            return rec
    return None


def table(title, items, humans, note=None):
    lines = ['## %s' % title, '']
    if note:
        lines += [note, '']
    lines += ['| element | meaning | parameters |', '|---|---|---|']
    for c in items:
        rec = match_label(c, humans)
        if rec:
            lines.append('| `%s` | %s | %s |' % (c, rec['label'], ', '.join(sorted(rec['params']))))
        else:
            lines.append('| `%s` | — | — |' % c)
    lines.append('')
    return lines


def all_classes(path):
    """Every trigger and event class in soa.exe, in the order they sit in it.

    The editor's text resources name only the handful a mission author is shown
    a panel for. The classes themselves are all in the executable, as
    `CY2KKITrigger_...` and `CY2KKIEvent_...`, and they lie in two unbroken
    blocks - the compiler laid the name strings down in the order the classes
    are declared.

    **That order is very probably the numbering the mission files use** - a
    script element is stored as a number, not a name, since none of these words
    appears in a `.mis` - but it is not proven here, only likely. It is
    reported as the order it is, and nobody should count on the index until a
    mission has been decoded against it.
    """
    data = open(path, 'rb').read()
    pat = re.compile(rb'CY2KKI(Trigger|Event)_[A-Za-z0-9_]{2,48}')
    found = []
    for m in pat.finditer(data):
        name = m.group().decode('latin1')
        after = data[m.end():m.end() + 2]
        if after == b'::':
            continue                     # CY2KKITrigger_X::Tick, a method
        kind, rest = name[len('CY2KKI'):].split('_', 1)
        found.append((m.start(), kind, rest))
    return found


def main():
    strings = exe_strings(EXE)
    rows_editor = load(UBN, TRS_EDITOR)
    rows_goals = load(UBN, TRS_GOALS)
    humans = human_names(rows_editor)

    triggers = classes(strings, 'CY2KKITrigger')
    events = classes(strings, 'CY2KKIEvent')
    elements = classes(strings, 'CY2KKISkriptElement')
    unitscript = classes(strings, 'CY2KKIUnitScript')
    heliscript = classes(strings, 'CY2KKIHeliScript')
    airscript = classes(strings, 'CY2KKIUnitAirplaneScript')

    L = []
    L += ['# The scripting system of the mission editor', '']
    L += ['Soldiers of Anarchy ships a full mission editor reachable from the main menu,',
          'and no documentation for it was ever released. This overview is derived from',
          'the game data: the element names come from the classes in `soa.exe`, their',
          'meaning and parameters from the text resources of the editor',
          '(`TRES_EDITOR.trs`).', '']
    L += ['A script is made of **triggers** (the condition telling when something happens)',
          'and **events** (what happens). The parameters reference objects placed in the',
          'map, regions drawn in the editor or groups of units.', '']
    L += ['Generated by `_research/tools/gen_editor_docs.py`.', '']
    L += ['---', '']

    L += table('Triggers — when the script fires', triggers, humans)
    L += table('Events — what the script does', events, humans)

    L += ['## Script elements', '',
          'The building blocks the editor assembles the script items from.', '']
    L += ['| element |', '|---|']
    L += ['| `%s` |' % c for c in elements]
    L += ['']

    L += ['## Unit behaviour scripts', '',
          'Ready-made behaviour patterns that can be assigned to a unit.', '']
    for title, items in (('Ground units', unitscript),
                         ('Helicopters', heliscript),
                         ('Aeroplanes', airscript)):
        if items:
            L += ['**%s:** %s' % (title, ', '.join('`%s`' % c for c in items)), '']

    goals = [(rid, text) for rid, text in rows_goals
             if 'GOAL' in rid.upper() and text and text != 'leer']
    L += ['## Mission goal types', '',
          '%d text resources for mission goals in total. A sample:' % len(goals), '']
    L += ['| resource | text |', '|---|---|']
    for rid, text in goals[:25]:
        t = text.replace('|', '\\|')
        if len(t) > 90:
            t = t[:87] + '...'
        L += ['| `%s` | %s |' % (rid, t)]
    L += ['', 'Full listing: `python tools/trs.py ../_patched/data.ubn MISSIONGOALS`', '']

    every = all_classes(EXE)
    for kind in ('Trigger', 'Event'):
        rows = [(at, n) for at, k, n in every if k == kind]
        L += ['', '## Every %s class in the executable' % kind.lower(), '']
        if kind == 'Trigger':
            L += ["The tables above come from the editor's text resources and cover",
                  'only what a mission author is shown a panel for. These are all of',
                  'them, taken from the class names in `soa.exe`, in the order they',
                  'lie there.', '',
                  '**The order is probably the numbering the mission files use** and is',
                  'not proven to be. A script element is stored in a `.mis` as a number -',
                  'none of these words appears in one - and until a mission has been',
                  'decoded against this list, the index beside a name is where it sits in',
                  'the executable and nothing more.', '']
        L += ['| # | class | at |', '|---|---|---|']
        for n, (at, name) in enumerate(rows):
            L += ['| %d | `%s` | `%08X` |' % (n, name, at + 0x400000)]
    L += ['']

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print('written: %s' % OUT)
    print('  triggers: %d, events: %d, script elements: %d' %
          (len(triggers), len(events), len(elements)))
    print('  paired with a label: %d' %
          sum(1 for c in triggers + events if match_label(c, humans)))


if __name__ == '__main__':
    main()
