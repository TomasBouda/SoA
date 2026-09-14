"""Builds docs/game.html on the public site - the game described for someone
who has not met it: the premise, the six in the bunker, the campaign and its
two forks, the factions - in the look of index.html, and puts a pointer to it
on index.html when there is none yet. The text is written here; the mission
titles are the MISSIONTITLE records of the mission texts and the forks are
what the mission files name as their successors (architecture.md, "Where
the campaign branches").

    python gen_game_web.py            writes _public/docs/game.html (publish.ps1 takes it out)
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, '..', '..', '_public', 'docs')

CSS = '''.story{display:grid;gap:26px;grid-template-columns:1.4fr 1fr;align-items:start}
@media(max-width:720px){.story{grid-template-columns:1fr}}
.people{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px}
.people h3{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin:0 0 12px}
.people li{padding:7px 0;border-bottom:1px solid var(--line);font-size:14.5px;color:var(--dim)}
.people li:last-child{border-bottom:0}
.people b{color:var(--text);font-weight:600}
.tree{margin:26px 0 8px;overflow-x:auto}
.tree svg{display:block;min-width:760px;width:100%;height:auto}
.tree.small svg{min-width:0;width:460px;height:208px;max-width:100%}
.tree .box{fill:var(--panel);stroke:var(--line)}
.tree .box.fork{stroke:var(--accent)}
.tree .num{fill:var(--accent);font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.tree .ttl{fill:var(--text);font:12px -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.tree .edge{stroke:var(--line);stroke-width:1.5;fill:none}
.tree .edge.fork{stroke:var(--accent)}
.factions{margin-top:26px}
.factions .card p{font-size:14.5px}
.factions .card .tag{display:inline-block;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
'''


def box(x, y, num, title, fork=False, w=134, h=44):
    cls = 'box fork' if fork else 'box'
    return ('<rect class="%s" x="%d" y="%d" width="%d" height="%d" rx="7"/>'
            '<text class="num" x="%d" y="%d">%s</text>'
            '<text class="ttl" x="%d" y="%d">%s</text>'
            % (cls, x, y, w, h, x + 10, y + 18, num, x + 10, y + 35, title))


def edge(x1, y1, x2, y2, fork=False):
    cls = 'edge fork' if fork else 'edge'
    if y1 == y2:
        return '<path class="%s" d="M%d %d H%d"/>' % (cls, x1, y1, x2)
    mx = (x1 + x2) / 2
    return '<path class="%s" d="M%d %d C%d %d %d %d %d %d"/>' % (cls, x1, y1, mx, y1, mx, y2, x2, y2)



W, GAP = 134, 16
xs = [10 + i * (W + GAP) for i in range(7)]   # seven columns
top, mid, bot = 12, 84, 156
c = lambda y: y + 22
svg = ['<svg viewBox="0 0 1070 212" xmlns="http://www.w3.org/2000/svg" role="img" '
       'aria-label="The campaign: missions 1 to 4 in a row, a fork into 5a-6a or 5b-6b that meets again in 7, '
       'and a fork into 8a-9a or 8b-9b that does not">']
# edges first, boxes on top
svg.append(edge(xs[0] + W, c(mid), xs[1], c(mid)))
svg.append(edge(xs[1] + W, c(mid), xs[2], c(mid)))
svg.append(edge(xs[2] + W, c(mid), xs[3], c(mid)))
svg.append(edge(xs[3] + W, c(mid), xs[4] - 140 + 140, c(top), True))
svg.append(edge(xs[3] + W, c(mid), xs[4], c(bot), True))
# 5a/6a on top row, 5b/6b on bottom - columns 4 and 5 hold 5x/6x, column 6 holds 7
svg.append(edge(xs[4] + W, c(top), xs[5], c(top)))
svg.append(edge(xs[4] + W, c(bot), xs[5], c(bot)))
svg.append(edge(xs[5] + W, c(top), xs[6], c(mid)))
svg.append(edge(xs[5] + W, c(bot), xs[6], c(mid)))
svg.append(box(xs[0], mid, '1', 'A leap in the dark'))
svg.append(box(xs[1], mid, '2', 'The raid'))
svg.append(box(xs[2], mid, '3', 'Market day'))
svg.append(box(xs[3], mid, '4', 'Two roads. One way.', True))
svg.append(box(xs[4], top, '5a', 'In the eye of the storm'))
svg.append(box(xs[5], top, '6a', 'They came in the dusk'))
svg.append(box(xs[4], bot, '5b', 'Heroes die Young'))
svg.append(box(xs[5], bot, '6b', 'They came in the dusk'))
svg.append(box(xs[6], mid, '7', 'And follow your destiny', True))
svg.append('</svg>')
tree1 = '\n'.join(svg)

# second row: 7 -> 8a/9a, 8b/9b
xs2 = [10 + i * (W + GAP) for i in range(3)]
svg = ['<svg viewBox="0 0 470 212" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="After mission 7: 8a then 9a, or 8b then 9b">']
svg.append(edge(xs2[0] + W, c(mid), xs2[1], c(top), True))
svg.append(edge(xs2[0] + W, c(mid), xs2[1], c(bot), True))
svg.append(edge(xs2[1] + W, c(top), xs2[2], c(top)))
svg.append(edge(xs2[1] + W, c(bot), xs2[2], c(bot)))
svg.append(box(xs2[0], mid, '7', 'And follow your destiny', True))
svg.append(box(xs2[1], top, '8a', 'Inside the rat hole'))
svg.append(box(xs2[2], top, '9a', 'The judgement'))
svg.append(box(xs2[1], bot, '8b', 'The sign'))
svg.append(box(xs2[2], bot, '9b', 'Everlasting life'))
svg.append('</svg>')
tree2 = '\n'.join(svg)


BODY = '''    <div class="story">
      <div>
        <p>Squad tactics in real time, 2002, from Silver Style in Berlin: a handful of soldiers you know
          by name, a few vehicles you have to find and keep running, and a campaign of thirteen missions
          on 1200-metre maps of a Russia nobody has been to for ten years.</p>
        <p>In November 2004 an engineered virus, SGDS, got out. Cities went under quarantine, Paris was
          bombed by its own government, and the world came apart. Six people at the Russian base
          Kalinina - four Russians, an American, a German - blew up the only road into their valley and
          went down into the bunker. That was ten years ago. Now the rations are the same, the radio has
          been silent for years, and they have decided they would rather die in fresh air than live
          another day underground. The campaign starts at the bunker door.</p>
        <p>Between missions you are back at the base: the hangar and the workshop for the vehicles, the
          hospital for the wounded, a trader who comes by, the equipment screen where every soldier is
          armed piece by piece. What you bring home from a mission is what you have for the next one -
          the T-55 you captured, the Hind you found in a barn, the sniper you talked into joining.</p>
        <p class="dim">The game's own text calls the world after the virus the <i>New Times</i>, and
          everything before it the <i>Old Times</i>.</p>
      </div>
      <div class="people">
        <h3>The six in the bunker</h3>
        <ul class="plain">
          <li><b>Roman Willstein</b> - German first lieutenant, the leader and the voice of the intro; a badly healed leg keeps him at the base.</li>
          <li><b>David Reaves</b> - US Army sergeant from Philadelphia; leads the squad in the field.</li>
          <li><b>Boris Kerkowitsch</b> - Russian lance sergeant, once head of the base guard; explosives.</li>
          <li><b>Prof. Sergej Petrow</b> - geneticist from Kiev, ran the base's research. The one who said to stay down.</li>
          <li><b>Prof. Vigo Jolinzky</b> - chemist, in a wheelchair since 2007, black humour intact; your voice on the radio.</li>
          <li><b>Sorana Sorgarowa</b> - Petrow's assistant, the medic.</li>
        </ul>
      </div>
    </div>

    <h3 style="margin-top:34px">The campaign, and where it forks</h3>
    <p class="dim" style="max-width:680px">Two choices change what comes next. In mission 4 you pick one of two
      gangs to fight for, and that decides which of two mirrored roads you take to mission 7; there the paths
      meet again. In mission 7 you choose a side once more, and this time the roads do not meet: two last
      missions, two endings. Nothing said here about which is which.</p>
    <div class="tree">
''' + tree1 + '''
    </div>
    <div class="tree small" style="margin-top:0">
''' + tree2 + '''
    </div>

    <h3 style="margin-top:34px">Who is out there</h3>
    <p class="dim" style="max-width:680px">As the game's own notes panel at the base describes them - the entry for
      each appears once you have met them.</p>
    <div class="cards factions">
      <div class="card"><span class="tag">Trade</span><h3>Seekers</h3><p>The traders of the New Times. They pick the
        ruins - and the battlefields - clean and sell what they find, each in a territory his guild assigns him.
        Nobody shoots a Seeker: the gangs need what he brings.</p></div>
      <div class="card"><span class="tag">Civilians</span><h3>Survivors</h3><p>Villages and free towns, run by whoever
        could work with their hands before the disaster. Loyal to each other, and handy enough with a rifle after
        years of the gangs.</p></div>
      <div class="card"><span class="tag">Gang</span><h3>Slingers</h3><p>Thugs and thieves who think they own the
        wasteland. They rob and kidnap villagers, have no training and little equipment, and run when a real
        fight starts.</p></div>
      <div class="card"><span class="tag">Gang</span><h3>Claws</h3><p>Alcohol, drugs and territory, held with the
        cruelty of the criminals most of them were. No military schooling, but years of practice with every weapon
        still around - and as well armed as anyone.</p></div>
      <div class="card"><span class="tag">Gang</span><h3>TFR</h3><p>Born of a Russian special unit and still fighting
        like one - tactically, with heavy equipment - and otherwise a gang of contract killers that wipes out whole
        villages. At war with the Claws.</p></div>
      <div class="card"><span class="tag">Science</span><h3>NOAH</h3><p>Scientists and soldiers in hidden laboratories,
        working on a vaccine and on how 2004 happened. Only their Seekers know where they are. Well armed for people
        who say they only do research.</p></div>
      <div class="card"><span class="tag">Sect</span><h3>COTUC</h3><p>The Church Of The Undying Child, an obscure
        1980s sect that came through the virus almost untouched and is now one of the largest armies there is, with
        weapons nobody else has. Suspected, for that reason, of having had a hand in 2004.</p></div>
      <div class="card"><span class="tag">Sect</span><h3>Undead Knights</h3><p>Half man, half machine: COTUC's cyborg
        soldiers, armoured against ordinary ammunition, weapons built into their bodies, loyal past doubt.</p></div>
    </div>
'''

EXTRA_CSS = '''.top{border-bottom:1px solid var(--line);padding:22px 0}
.top a{text-decoration:none;color:var(--dim);font-size:14px}
.top a:hover{color:var(--accent)}
.top .wrap{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.top .name{color:var(--accent);letter-spacing:.10em;text-transform:uppercase;font-size:13px}
header.page{padding:56px 0 30px}
h2.big{font-size:32px;letter-spacing:-.02em;text-transform:none;color:var(--text);margin:0 0 12px;font-weight:650}
'''

POINTER = '''<section>
  <div class="wrap">
    <h2>Never played it?</h2>
    <p style="max-width:680px">Squad tactics in real time in a Russia ten years after an engineered virus:
      six people come up out of a bunker, and everything they will have is what they find and bring
      home. Thirteen missions, two forks, two endings.</p>
    <a class="cta" href="game.html">Read what the game is &rarr;</a>
  </div>
</section>

'''


def main():
    index_path = os.path.join(DOCS, 'index.html')
    index = io.open(index_path, encoding='utf-8').read()
    style = re.search(r'<style>.*?</style>', index, re.S).group()
    style = style.replace('</style>', CSS + EXTRA_CSS + '</style>')
    body = BODY.replace("''' + tree1 + '''", tree1).replace("''' + tree2 + '''", tree2)
    page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Soldiers of Anarchy, the game</title>
<meta name="description" content="What Soldiers of Anarchy is: the premise, the six people in the bunker, the thirteen missions of the campaign and where it forks, and who is out there - the factions of the New Times.">
''' + style + '''
</head>
<body>

<div class="top">
  <div class="wrap">
    <span class="name">Soldiers of Anarchy &middot; 2002</span>
    <a href="index.html">&larr; Play it on Windows 11</a>
  </div>
</div>

<header class="page">
  <div class="wrap">
    <p class="sub">The game</p>
    <h2 class="big">For anyone who has not met it</h2>
    <p class="lede">What it is, who you are, where the thirteen missions go and who is waiting there -
      from the game's own texts, with nothing said about how it ends.</p>
  </div>
</header>

<section>
  <div class="wrap">
''' + body + '''  </div>
</section>

<footer>
  <div class="wrap">
    Written from the game's own text resources - the story intro, the notes panel at the base and the
    mission files - for <a href="index.html">the launcher's page</a>. The characters, the factions and the
    story belong to Silver Style Entertainment.
  </div>
</footer>
</body>
</html>
'''
    io.open(os.path.join(DOCS, 'game.html'), 'w', encoding='utf-8').write(page)
    print('game.html written')
    anchor = '<section>\n  <div class="wrap">\n    <h2>What comes with the launcher</h2>'
    if 'game.html' not in index and index.count(anchor) == 1:
        io.open(index_path, 'w', encoding='utf-8').write(index.replace(anchor, POINTER + anchor))
        print('index.html: the pointer added')


if __name__ == '__main__':
    main()
