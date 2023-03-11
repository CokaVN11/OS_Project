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


class Drive:
    @staticmethod
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

    @staticmethod
    def convertType(Type_byte):
        Type_byte = "{:02x}".format(Type_byte)
        if (Type_byte == '07'):
            return 'NTFS'
        if (Type_byte == '0c' or Type_byte == '0b'):
            return 'FAT32'
        if (Type_byte == '0e'):
            return 'FAT16'
        return 'Not supported'

    @staticmethod
    def convert2Complement(num):
        binary = '{:08b}'.format(num)
        tmp = int(binary, 2)
        binary = bin((tmp ^ (2 ** (len(binary)+1) - 1)) + 1)[3:]
        return int(binary, 2)

    def __init__(self):
        c = wmi.WMI()
        # --- Get usb ---
        # MediaType = "Removable Media";
        self.devices = []
        self.usb_number = -1
        self.disk_path = ''
        self.partitions = []
        self.partition_number = -1

        for drive in c.Win32_DiskDrive():
            if drive.MediaType == 'Removable Media':
                # print(drive)
                self.devices.append({
                    'Path': drive.DeviceID,
                    'BytePerSector': drive.BytesPerSector
                })

    def chooseUSB(self):
        if (len(self.devices) == 0):
            print("No USB supported!!!")
            return
        for i, usb in enumerate(self.devices):
            print(f"USB {i}:")
            for attribute, value in usb.items():
                print(f"    {attribute}: {value}")

        while (self.usb_number < 0 or self.usb_number >= len(self.devices)):
            self.usb_number = int(
                input("Choose usb you want to get information: "))
            if (self.usb_number >= 0 and self.usb_number < len(self.devices)):
                break
            print('The usb you choose is not exist')
        self.partitions.clear()
        self.bytesPerSector = self.devices[self.usb_number]['BytePerSector']

    # --- Get partitions informations---
    def readMBR(self):
        if (self.usb_number < 0 or self.usb_number >= len(self.devices)):
            self.chooseUSB()
        self.disk_path = self.devices[self.usb_number]['Path']
        with open(self.disk_path, 'rb') as f:
            mbr = f.read(512)
            for i in range(0, 4):
                index = int('1be', 16) + i * 16
                sec_begin = int.from_bytes(
                    mbr[index + int('08', 16): index + int('08', 16) + 4], 'little')
                if (sec_begin <= 0 and i != 0):
                    break
                partition = {
                    "Status": 'bootable' if "{:02x}".format(mbr[index]) == '80' else 'nonbootable',
                    "CHSBegin": self.convertCHS(mbr[index + int("01", 16): index + int("01", 16) + 3]),
                    "Type": self.convertType(mbr[index + int("04", 16)]),
                    "CHSEnd": self.convertCHS(mbr[index + int("05", 16): index + int("05", 16) + 3]),
                    "SecBegin": sec_begin,
                    "NumberSector": int.from_bytes(mbr[index + int('0C', 16): index + int('0C', 16) + 4], 'little')
                }
                self.partitions.append(partition)

    # Return partition informations
    def getPartition(self):
        if (len(self.partitions) <= 0):
            self.readMBR()
        return self.partitions

    def printPartition(self):
        for i, partition in enumerate(self.partitions):
            print(f"Partition {i}:")
            for attribute, value in partition.items():
                print(f"    {attribute}: {value}")
            print()

    # Read FAT32 Partition
    def readFAT32(self):
        if self.partitions[self.partition_number]['Type'] != 'FAT32':
            return

        partition = self.partitions[self.partition_number]
        begin_index = partition['SecBegin'] * self.bytesPerSector
        with open(self.disk_path, 'rb') as f:
            f.seek(begin_index)
            boot_sector = f.read(512)
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
            self.partitions[self.partition_number]['Property']= prop

    def readNTFS(self):
        if self.partitions[self.partition_number]['Type'] != 'NTFS':
            return

        partition = self.partitions[self.partition_number]
        begin_index = partition['SecBegin'] * self.bytesPerSector
        with open(self.disk_path, 'rb') as f:
            f.seek(begin_index)
            boot_sector = f.read(512)
            prop = {
                "BytesPerSector": int.from_bytes(boot_sector[int('0B', 16): int('0B', 16) + 2], 'little'),
                "SectorPerCluseter": int(boot_sector[int('0D', 16)]),
                "SectorPerTrack": int.from_bytes(boot_sector[int('18', 16): int('18', 16) + 2], 'little'),
                "NumberOfHead": int.from_bytes(boot_sector[int('1A', 16): int('1A', 16) + 2], 'little'),
                "NumberOfSector": int.from_bytes(boot_sector[int('28', 16): int('28', 16) + 8], 'little'),
                "MFTCluster": int.from_bytes(boot_sector[int('30', 16): int('30', 16) + 8], 'little'),
                "MFTBackupCluster": int.from_bytes(boot_sector[int('38', 16): int('38', 16) + 8], 'little'),
                "BytePerEntry": 2 ** self.convert2Complement(boot_sector[int('40', 16)])
            }
            self.partitions[self.partition_number]['Property']= prop

    def readPartition(self):
        if len(self.partitions) <= 0:
            self.readMBR()
            self.printPartition()

        while (self.partition_number < 0 or self.partition_number >= len(self.partitions)):
            self.partition_number = int(
                input("Choose partition you want to get information: "))
            if (self.partition_number >= 0 and self.partition_number < len(self.partitions)):
                break
            print('The partitions you choose is not exist')

        if self.partitions[self.partition_number]['Type'] == 'FAT32':
            self.readFAT32()
        elif self.partitions[self.partition_number]['Type'] == 'NTFS':
            self.readNTFS()

        print(self.partitions[self.partition_number]['Property'])

if __name__ == "__main__":
    drive = Drive()
    drive.chooseUSB()
    drive.readMBR()
    drive.printPartition()
    drive.readPartition()
