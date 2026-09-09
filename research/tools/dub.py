"""Prepare the game's speech for dubbing, and put a dub back.

Two jobs, and which one is needed depends on the route taken.

**Text to speech** is the route this game wants. Every spoken line is already
written down in the mission resource - `translate.py --speech Mission_1` prints
the lot - so a Czech recording is made from the Czech text and the original
audio is never involved. Nothing here has a minimum length.

**Voice cloning** is the other route, and it is where a minimum bites:
ElevenLabs will not take a sample under eleven seconds, and a line of game
dialogue is often one or two. The answer is not a longer line but more of them.
`--sample` gathers everything one character says and joins it into a single
clip, which for the main voices comes to a minute or more.

    python dub.py --voices Mission_1                  who speaks, and for how long
    python dub.py --sample Mission_1 "Aussenposten" out.mp3
    python dub.py --convert spoken.mp3 ready.mp3      into the game's own format

The speaker field carries stage directions as well as the name - the same
character appears as itself and as itself laughing, whispering, annoyed - so
the name is taken to be whatever comes before the first bracket or comma, and
all of it counts as one voice.

Needs ffmpeg on the path. The game's format is MPEG-1 layer 3, 64 kbit,
44100 Hz, mono; `--convert` produces exactly that, and the game reads a loose
file in preference to the archive, so `translate.py --dub` installs it.
"""
import argparse
import array
import collections
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate as T

# 64 kbit mono is 8000 bytes a second, near enough to judge a clip by its size
# without decoding it.
BYTES_A_SECOND = 8000.0


def ffmpeg():
    found = shutil.which('ffmpeg')
    if not found:
        raise SystemExit('ffmpeg is not on the path')
    return found


def plain(speaker):
    """The character, without the stage direction the field also carries."""
    name = re.split(r'[(,"]', speaker, maxsplit=1)[0]
    return ' '.join(name.split()).strip(' -')


def folded(name):
    """For comparing a name typed on a keyboard against a name in the data.

    The speakers are German - Aussenposten, Haendler - and nobody is going to
    type the sharp s or the umlauts, so both are folded away and the case with
    them. The field is careless about case anyway.
    """
    plainer = plain(name).lower().replace('ß', 'ss')
    stripped = unicodedata.normalize('NFD', plainer)
    return ''.join(c for c in stripped if not unicodedata.combining(c))


def audio_index(game):
    """{lower path: (archive, member, size)} across every archive.

    The text and the audio do not live together: the 1.1.1 patch carries the
    rewritten mission scripts while the recordings stayed in missions.ubn, so
    looking for a sound in the archive that held its line finds nothing. That
    is what the first version of this did, and it reported a mission with no
    voices in it rather than saying anything was wrong.
    """
    found = {}
    for name in T.ARCHIVES:
        path = os.path.join(game, name)
        if not os.path.exists(path):
            continue
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.filename.lower().endswith('.mp3'):
                    found[info.filename.lower()] = (path, info.filename, info.file_size)
    return found


def lines_of(game, mission):
    """[(key, archive, member, speaker, size)] for one mission."""
    archive, member = T.find(game, mission)
    if member is None:
        raise SystemExit('no mission called %s' % mission)
    version, rows, _ = T.read(T.raw_of(archive, member))
    if version != 4:
        raise SystemExit('%s carries no speech' % member)
    folder = member.rsplit('/', 2)[0]
    sounds = audio_index(game)
    out = []
    for r in rows:
        sound = r.strings[1].decode('latin1')
        if not sound or sound.lower() == 'leer':
            continue
        want = (folder + '/' + sound.replace('\\', '/')).lower()
        hit = sounds.get(want)
        if hit is None:
            continue
        out.append((r.key.decode('latin1'), hit[0], hit[1],
                    r.strings[3].decode('utf-8', 'replace'), hit[2]))
    return out


def voices(game, mission):
    rows = lines_of(game, mission)
    totals = collections.defaultdict(lambda: [0, 0])
    for _key, _archive, _member, speaker, size in rows:
        who = plain(speaker) or '(unnamed)'
        totals[who][0] += 1
        totals[who][1] += size
    print('%-34s %6s %9s' % ('voice', 'lines', 'audio'))
    for who, (n, size) in sorted(totals.items(), key=lambda kv: -kv[1][1]):
        seconds = size / BYTES_A_SECOND
        enough = 'enough to clone' if seconds >= 11 else ''
        print('%-34s %6d %7.1f s  %s' % (who[:34], n, seconds, enough))


def chosen(game, mission, who, seconds=60):
    """The clips a sample is made of, in order.

    Both --sample and --split go through here and neither has a copy of the
    rule, because the two must agree exactly: --split cuts a recording back
    into lines by counting along this list, and a list that had drifted would
    put the right Czech on the wrong line without anything looking wrong.
    """
    rows = lines_of(game, mission)
    want = folded(who)
    picked = [r for r in rows if folded(r[3]) == want]
    if not picked:
        picked = [r for r in rows if want and want in folded(r[3])]
    if not picked:
        raise SystemExit('nobody called %s speaks in %s - try --voices' % (who, mission))
    taken, total = [], 0
    for row in picked:
        if total / BYTES_A_SECOND >= seconds:
            break
        taken.append(row)
        total += row[4]
    return taken, len(picked)


def seconds_of(path):
    out = subprocess.check_output(
        [shutil.which('ffprobe') or 'ffprobe', '-v', 'error',
         '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', path])
    return float(out.decode().strip())


def extract(archive, member, to):
    with zipfile.ZipFile(archive) as z:
        open(to, 'wb').write(z.read(member))
    return to


def sample(game, mission, who, out, seconds=60):
    """Everything one character says, joined into a single clip."""
    taken, of_how_many = chosen(game, mission, who, seconds)
    work = tempfile.mkdtemp(prefix='soa-dub-')
    try:
        listing = os.path.join(work, 'clips.txt')
        total = 0
        with open(listing, 'w', encoding='utf-8') as f:
            for n, (_key, archive, member, _speaker, size) in enumerate(taken):
                name = extract(archive, member, os.path.join(work, '%03d.mp3' % n))
                f.write("file '%s'\n" % name.replace('\\', '/'))
                total += size
        subprocess.check_call(
            [ffmpeg(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
             '-i', listing, '-c', 'copy', out])
        print('%s: %d of %d clips, about %.0f seconds -> %s'
              % (plain(who), len(taken), of_how_many, total / BYTES_A_SECOND, out))
        if total / BYTES_A_SECOND < 11:
            print('that is still under the eleven seconds a clone wants')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def split(game, mission, who, dubbed, out_dir, seconds=60):
    """Cut a dubbed sample back into the lines it was made of.

    A dub comes back as one recording of the whole sample, and the game wants
    one file per line. The cuts are made where the originals joined, scaled by
    however much the recording drifted - a dub that keeps its timing drifts by
    a fraction of a percent, and the scaling absorbs that rather than letting
    it pile up towards the end.

    The pieces are written out for listening to first. Nothing is installed
    until they have been heard, because a cut in the wrong place is a line that
    starts mid-word and there is no way to see that in a file listing.
    """
    taken, _ = chosen(game, mission, who, seconds)
    work = tempfile.mkdtemp(prefix='soa-split-')
    try:
        bounds, run = [], 0.0
        for key, archive, member, _speaker, _size in taken:
            length = seconds_of(extract(archive, member, os.path.join(work, 'x.mp3')))
            bounds.append((key, run, length))
            run += length
        drift = seconds_of(dubbed) / run
        print('%d lines over %.2f s; the dub runs %.2f s, %.2f%% different'
              % (len(bounds), run, seconds_of(dubbed), (drift - 1) * 100))
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        for key, start, length in bounds:
            out = os.path.join(out_dir, key + '.mp3')
            subprocess.check_call(
                [ffmpeg(), '-y', '-loglevel', 'error', '-ss', '%.3f' % (start * drift),
                 '-t', '%.3f' % (length * drift), '-i', dubbed,
                 '-codec:a', 'libmp3lame', '-b:a', '64k', '-ar', '44100', '-ac', '1', out])
            print('   %-22s %6.2f s at %6.2f  -> %s'
                  % (key, length * drift, start * drift, os.path.basename(out)))
        bad = [k for k, _s, _l in bounds if cut_mid_sound(os.path.join(out_dir, k + '.mp3'))]
        print('\n%d of %d pieces begin or end in the middle of sound.' % (len(bad), len(bounds)))
        if len(bad) > len(bounds) / 4:
            print('That is too many to be chance: the dub has re-timed the lines')
            print('inside the recording, so cutting where the originals joined no')
            print('longer lands in the gaps. Splitting a dubbed sample cannot be')
            print('made reliable this way - use the sample to clone a voice, then')
            print('speak each line on its own with that voice, and every file is')
            print('bounded correctly because it was made on its own.')
        else:
            print('Listen to them anyway. Each one goes in with')
            print('   translate.py --dub %s <KEY> %s' % (mission, os.path.join(out_dir, '<KEY>.mp3')))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cut_mid_sound(path, ms=140, loud=3000):
    """Whether a piece starts or ends while something is still being said.

    A cut that lands in a gap leaves quiet at both ends; a cut through a word
    does not. Reading the first and last fraction of a second is enough to tell
    the two apart, and it is the only way to catch a bad split without sitting
    and listening to every piece.
    """
    for where in ('head', 'tail'):
        args = [ffmpeg(), '-v', 'error']
        if where == 'head':
            args += ['-i', path, '-t', '%.3f' % (ms / 1000.0)]
        else:
            args += ['-sseof', '-%.3f' % (ms / 1000.0), '-i', path]
        args += ['-f', 's16le', '-ac', '1', '-ar', '16000', '-']
        raw = subprocess.run(args, capture_output=True).stdout
        if not raw:
            continue
        block = array.array('h')
        block.frombytes(raw[:len(raw) // 2 * 2])
        if block and max(abs(x) for x in block) > loud:
            return True
    return False


def convert(source, out):
    """Whatever came back, in the format the game's own files use."""
    subprocess.check_call(
        [ffmpeg(), '-y', '-loglevel', 'error', '-i', source,
         '-codec:a', 'libmp3lame', '-b:a', '64k', '-ar', '44100', '-ac', '1', out])
    print('%s -> %s  (64 kbit, 44100 Hz, mono, %d bytes)'
          % (source, out, os.path.getsize(out)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=T.GAME)
    ap.add_argument('--voices', metavar='MISSION')
    ap.add_argument('--sample', nargs=3, metavar=('MISSION', 'VOICE', 'OUT'))
    ap.add_argument('--seconds', type=int, default=60,
                    help='how much to gather for a sample (default 60)')
    ap.add_argument('--split', nargs=4, metavar=('MISSION', 'VOICE', 'DUBBED', 'OUTDIR'),
                    help='cut a dubbed sample back into the lines it was made of')
    ap.add_argument('--convert', nargs=2, metavar=('IN', 'OUT'))
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

    if args.voices:
        voices(args.game, args.voices)
    elif args.sample:
        sample(args.game, args.sample[0], args.sample[1], args.sample[2], args.seconds)
    elif args.split:
        split(args.game, args.split[0], args.split[1], args.split[2], args.split[3],
              args.seconds)
    elif args.convert:
        convert(args.convert[0], args.convert[1])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
