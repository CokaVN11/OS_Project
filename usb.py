import wmi


def GetUSBDrive():
    c = wmi.WMI()
    devices = []
    # MediaType = "Removable Media";
    for drive in c.Win32_DiskDrive():
        if drive.MediaType == 'Removable Media':
            # print(drive)
            devices.append({
                'Path': drive.DeviceID,
                'BytePerSector': drive.BytesPerSector
            })
    return devices


disks = GetUSBDrive()


def convertCHS(CHS_bits):
    CHS_bits = "".join("{:08b}".format(bit) for bit in CHS_bits)
    # print(CHS_bits)
    CHS = {
        'head': int(CHS_bits[0: 8], 2),
        'sector': int(CHS_bits[10: 16], 2),
        'cyclinder': int(CHS_bits[8:10] + CHS_bits[16: 24], 2)
    }
    # print(CHS)
    return CHS


def convertType(Type_byte):
    Type_byte = "{:02x}".format(Type_byte)
    if (Type_byte == '07'):
        return 'NTFS'
    if (Type_byte == '0c' or Type_byte == '0b'):
        return 'FAT32'
    if (Type_byte == '0e'):
        return 'FAT16'
    return 'Not supported'


print(disks)


def GetPartitionSector(disk_path: str):
    partitions = []
    with open(disk_path, 'rb') as f:
        mbr = f.read(512)
        partition_index = int('1BE', 16)
        for i in range(0, 4):
            index = partition_index + 16 * i
            sec_begin = int.from_bytes(
                mbr[index + int('08', 16): index + int('08', 16) + 4], 'little')
            if (sec_begin <= 0 and i != 0):
                break
            partition = {
                "Status": 'bootable' if "{:02x}".format(mbr[index]) == '80' else 'nonbootable',
                "CHSBegin": convertCHS(mbr[index + int("01", 16): index + int("01", 16) + 3]),
                "Type": convertType(mbr[index + int("04", 16)]),
                "CHSEnd": convertCHS(mbr[index + int("05", 16): index + int("05", 16) + 3]),
                "SecBegin": sec_begin,
                "NumberSector": int.from_bytes(mbr[index + int('0C', 16): index + int('0C', 16) + 4], 'little')
            }
            partitions.append(partition)
        return partitions

def ReadFAT(disk_path,partition, bytesPerSector):
    if partition['Type'] != 'FAT32':
        return

    begin_index = partition['SecBegin'] * bytesPerSector
    with open (disk_path, 'rb') as f:
        f.seek(begin_index)
        boot_sector = f.read(512)
        # cnt = -1
        # for i in boot_sector:
        #     print('{:02x} '.format(i), end='')
        #     cnt+=1
        #     if cnt % 16 == 15:
        #         print()
        prop = {
            "BytesPerSector": int.from_bytes(boot_sector[int('0B', 16): int('0B', 16) + 2], 'little'),
            "SectorPerCluseter": int(boot_sector[int('0D', 16)]),
            "SectorBeforeFat": int.from_bytes(boot_sector[int('0E', 16): int('0E', 16) + 2], 'little'),
            "NumberOfFat": int(boot_sector[int('10', 16)]),
            "VolumeSize": int.from_bytes(boot_sector[int('20', 16): int('20', 16) + 4], 'little'),
            "SectorPerFat": int.from_bytes(boot_sector[int('24', 16): int('24', 16) + 4], 'little'),
            "RDETCluster": int.from_bytes(boot_sector[int('2C', 16): int('2C', 16) + 4], 'little'),
            "Type": boot_sector[int('52', 16): int('52', 16) + 8]
        }
        return prop

partis = GetPartitionSector(disks[0]['Path'])
print(ReadFAT(disks[0]['Path'] , partis[1], disks[0]['BytePerSector']))
