import struct,sys
d=open(sys.argv[1],'rb').read()
e=struct.unpack_from('<I',d,0x3c)[0]
coff=e+4; nsec=struct.unpack_from('<H',d,coff+2)[0]; opthdrsz=struct.unpack_from('<H',d,coff+16)[0]
opt=coff+20
ep=struct.unpack_from('<I',d,opt+16)[0]
sec=opt+opthdrsz
print('EntryPoint RVA: 0x%08x'%ep)
for i in range(nsec):
    o=sec+i*40
    name=d[o:o+8].rstrip(b'\0').decode()
    vs=struct.unpack_from('<I',d,o+8)[0]; va=struct.unpack_from('<I',d,o+12)[0]
    if va<=ep<va+vs: print('  -> in section:',name)
