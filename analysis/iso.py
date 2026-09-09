import sys,struct
if len(sys.argv) < 2:
    print('usage: iso.py <image.iso|.mdf>')
    raise SystemExit(1)
p=sys.argv[1]
f=open(p,'rb')
def probe(ss,off):
    f.seek(16*ss+off); d=f.read(2048)
    return d[1:6]==b'CD001', d
for ss,off in ((2048,0),(2352,16),(2352,24),(2448,16)):
    ok,d=probe(ss,off)
    if ok:
        print(f'ISO9660 found: sector={ss} dataoff={off}')
        volid=d[40:72].decode('latin1').strip()
        print('Volume ID:', volid)
        rootrec=d[156:156+34]
        lba=struct.unpack_from('<I',rootrec,2)[0]; size=struct.unpack_from('<I',rootrec,10)[0]
        print('root lba',lba,'size',size)
        def read_lba(l,n=1):
            out=b''
            for i in range(n):
                f.seek((l+i)*ss+off); out+=f.read(2048)
            return out
        data=read_lba(lba,(size+2047)//2048)
        i=0
        while i < len(data):
            ln=data[i]
            if ln==0:
                i=(i//2048+1)*2048
                if i>=len(data): break
                continue
            rec=data[i:i+ln]
            flen=rec[32]
            name=rec[33:33+flen].decode('latin1')
            flags=rec[25]
            fsize=struct.unpack_from('<I',rec,10)[0]
            elba=struct.unpack_from('<I',rec,2)[0]
            if name not in ('\x00','\x01'):
                print(f'  {"DIR " if flags&2 else "FILE"} {name:40s} {fsize:>12} lba={elba}')
            i+=ln
        break
else:
    print('no ISO9660 header found at common offsets')
