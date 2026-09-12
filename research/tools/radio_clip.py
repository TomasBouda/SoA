"""Makes the radio call the launcher plays when an air strike is called.

The game has no radio chatter of its own - its sounds are engines, bombs and
explosions - so this synthesises one: the Windows voices read the lines, and
the result is pushed through what a hand-held radio does to a voice: a narrow
band (300-3000 Hz), some overdrive, a hiss underneath, and a squelch click at
each end of every transmission. numpy does the filtering with an FFT, so
nothing beyond Python and Windows is needed.

The lines are a forward observer calling the strike and the pilot answering;
two voices, so it sounds like two ends of a radio.

Output: a 22050 Hz mono 16-bit wav, launcher/radio_airstrike_a.wav unless
--out says otherwise.

The shipped clips are not the Windows voices: the lines in launcher/radio
were made with ElevenLabs and went through the same treatment with --from,
after ffmpeg turned them into wav. There are three exchanges, a, b and c,
and the launcher plays one of them at random:

    ffmpeg -i operator1.mp3 -ac 1 -ar 22050 -sample_fmt s16 operator1.wav
    python radio_clip.py --from operator1.wav pilot1.wav operator2.wav pilot2.wav --out launcher/radio_airstrike_a.wav
    python radio_clip.py --from groundB_1.wav pilotB_1.wav groundB_2.wav pilotB_2.wav --out launcher/radio_airstrike_b.wav
    python radio_clip.py --from groundC_1.wav pilotC_1.wav groundC_2.wav pilotC_2.wav --out launcher/radio_airstrike_c.wav

The build packs every launcher/radio_airstrike_*.wav in as SoA.Radio.<letter>.

Usage:
    python radio_clip.py                     writes the wav from the Windows voices
    python radio_clip.py --play              writes it and plays it
    python radio_clip.py --from a.wav b.wav  the same treatment on recorded lines
                                             (one file per transmission; PCM wav)
"""
import argparse
import os
import subprocess
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'launcher', 'radio_airstrike_a.wav')
RATE = 22050

# (voice, rate, text) - one transmission each, with a squelch between them.
LINES = [
    ('Microsoft David Desktop', 3, 'Falcon One, Anarchy. Fire mission, grid sent. Danger close.'),
    ('Microsoft Zira Desktop', 2, 'Anarchy, Falcon One. Rolling in hot. Bombs away.'),
]


def speak(voice, rate, text):
    """Windows TTS into a temporary wav, through PowerShell's System.Speech."""
    path = os.path.join(tempfile.gettempdir(), 'soa-radio-%d.wav' % abs(hash(text)))
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('%s'); $s.Rate = %d;"
        "$s.SetOutputToWaveFile('%s');"
        "$s.Speak('%s'); $s.Dispose()"
        % (voice, rate, path.replace("'", "''"), text.replace("'", "''")))
    subprocess.run(['powershell', '-NoProfile', '-Command', script], check=True)
    with wave.open(path, 'rb') as w:
        frames = w.readframes(w.getnframes())
        channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
    data = np.frombuffer(frames, dtype='<i2').astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    os.remove(path)
    return trim(resample(data, rate, RATE))


def trim(data, threshold=0.02):
    """The synthesiser pads both ends with silence a radio would not."""
    loud = np.nonzero(np.abs(data) > threshold)[0]
    if len(loud) == 0:
        return data
    return data[max(0, loud[0] - RATE // 20):loud[-1] + RATE // 10]


def resample(data, rate_in, rate_out):
    if rate_in == rate_out:
        return data
    n = int(len(data) * rate_out / rate_in)
    x_old = np.linspace(0, 1, len(data), endpoint=False)
    x_new = np.linspace(0, 1, n, endpoint=False)
    return np.interp(x_new, x_old, data).astype(np.float32)


def bandpass(data, low, high):
    """A brick-wall band in the frequency domain; good enough for a radio."""
    spectrum = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1.0 / RATE)
    spectrum[(freqs < low) | (freqs > high)] = 0
    return np.fft.irfft(spectrum, len(data)).astype(np.float32)


def radio(voice):
    """What a small radio does to a voice."""
    voice = voice / (np.max(np.abs(voice)) + 1e-6)
    narrow = bandpass(voice, 300, 3000)
    driven = np.tanh(narrow * 4.0) * 0.8              # overdrive, the way a cheap speaker clips
    hiss = np.random.default_rng(7).normal(0, 0.02, len(driven)).astype(np.float32)
    hiss = bandpass(hiss, 300, 4000)
    return driven + hiss


def squelch(length=int(RATE * 0.06)):
    """The click and burst of static when the key goes down or up."""
    rng = np.random.default_rng(11)
    burst = rng.normal(0, 0.35, length).astype(np.float32)
    envelope = np.exp(-np.linspace(0, 6, length)).astype(np.float32)
    return bandpass(burst * envelope, 400, 5000)


def silence(seconds):
    return np.zeros(int(RATE * seconds), dtype=np.float32)


def load(path):
    """A PCM wav of any rate, mono or stereo, as mono float at RATE."""
    with wave.open(path, 'rb') as w:
        frames = w.readframes(w.getnframes())
        channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
    if width != 2:
        raise SystemExit('%s: only 16-bit PCM wav is read' % path)
    data = np.frombuffer(frames, dtype='<i2').astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return trim(resample(data, rate, RATE))


def build(recorded=None):
    parts = []
    voices = [load(path) for path in recorded] if recorded         else [speak(voice, rate, text) for voice, rate, text in LINES]
    for voice in voices:
        parts += [squelch(), silence(0.08), radio(voice),
                  silence(0.05), squelch(), silence(0.35)]
    clip = np.concatenate(parts)
    clip = clip / (np.max(np.abs(clip)) + 1e-6) * 0.9
    return clip


def write(clip, path):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((clip * 32767).astype('<i2').tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--play', action='store_true')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--from', dest='recorded', nargs='+', metavar='WAV',
                    help='recorded lines instead of the Windows voices, one file per transmission')
    args = ap.parse_args()
    clip = build(args.recorded)
    write(clip, args.out)
    print('wrote %s (%.1f s)' % (args.out, len(clip) / RATE))
    if args.play:
        subprocess.run(['powershell', '-NoProfile', '-Command',
                        "(New-Object Media.SoundPlayer '%s').PlaySync()" % args.out])


if __name__ == '__main__':
    main()
