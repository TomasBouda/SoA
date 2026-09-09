import os, struct, sys

if len(sys.argv) < 3:
    print('usage: extract_iso.py <image.iso> <target_folder>')
    raise SystemExit(1)
SRC = sys.argv[1]
DST = sys.argv[2]
SS = 2048

f = open(SRC, 'rb')

def sect(lba, n=1):
    f.seek(lba * SS)
    return f.read(n * SS)

# --- find the Joliet supplementary volume descriptor ---
joliet_root = None
pvd_root = None
lba = 16
while True:
    d = sect(lba)
    vdtype = d[0]
    if d[1:6] != b'CD001':
        break
    if vdtype == 1:
        pvd_root = d[156:190]
    elif vdtype == 2:
        esc = d[88:120]
        if esc[:3] in (b'%/@', b'%/C', b'%/E'):
            joliet_root = d[156:190]
    elif vdtype == 255:
        break
    lba += 1

use_joliet = joliet_root is not None
root = joliet_root if use_joliet else pvd_root
print('Joliet:', use_joliet)

def entries(lba, size):
    data = sect(lba, (size + SS - 1) // SS)
    i = 0
    out = []
    while i < len(data):
        ln = data[i]
        if ln == 0:
            i = (i // SS + 1) * SS
            if i >= len(data):
                break
            continue
        rec = data[i:i + ln]
        flen = rec[32]
        raw = rec[33:33 + flen]
        if raw in (b'\x00', b'\x01'):
            i += ln
            continue
        if use_joliet:
            name = raw.decode('utf-16-be', errors='replace')
        else:
            name = raw.decode('latin1')
        name = name.split(';')[0]
        flags = rec[25]
        fsize = struct.unpack_from('<I', rec, 10)[0]
        elba = struct.unpack_from('<I', rec, 2)[0]
        out.append((name, bool(flags & 2), elba, fsize))
        i += ln
    return out

count = {'d': 0, 'f': 0, 'b': 0}

def extract(lba, size, path):
    os.makedirs(path, exist_ok=True)
    for name, isdir, elba, fsize in entries(lba, size):
        target = os.path.join(path, name)
        if isdir:
            count['d'] += 1
            extract(elba, fsize, target)
        else:
            count['f'] += 1
            count['b'] += fsize
            with open(target, 'wb') as o:
                remaining = fsize
                pos = elba
                while remaining > 0:
                    chunk = min(remaining, SS * 512)
                    n = (chunk + SS - 1) // SS
                    o.write(sect(pos, n)[:chunk])
                    pos += n
                    remaining -= chunk

rlba = struct.unpack_from('<I', root, 2)[0]
rsize = struct.unpack_from('<I', root, 10)[0]
extract(rlba, rsize, DST)
print('folders: %d, files: %d, total: %.1f MB' % (count['d'], count['f'], count['b'] / 1024 / 1024))
