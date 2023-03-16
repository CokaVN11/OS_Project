import wmi


# def get_usb_drive():
#     c = wmi.WMI()
#     devices = []
#     # MediaType = "Removable Media";
#     for drive in c.Win32_DiskDrive():
#         if drive.MediaType == 'Removable Media':
#             # print(drive)
#             devices.append({
#                 'Path': drive.DeviceID,
#                 'BytePerSector': drive.BytesPerSector
#             })
#     return devices


class Drive:
    @staticmethod
    def convert_chs(chs_bits):
        chs_bits = "".join("{:08b}".format(bit) for bit in chs_bits)
        # print(CHS_bits)
        chs = {
            'head': int(chs_bits[0: 8], 2),
            'sector': int(chs_bits[10: 16], 2),
            'cylinder': int(chs_bits[8:10] + chs_bits[16: 24], 2)
        }
        # print(chs)
        return chs

    @staticmethod
    def convert_type(type_byte):
        type_byte = "{:02x}".format(type_byte)
        if type_byte == '07':
            return 'NTFS'
        if type_byte == '0c' or type_byte == '0b':
            return 'FAT32'
        if type_byte == '0e':
            return 'FAT16'
        return 'Not supported'

    @staticmethod
    def convert2_complement(num):
        binary = '{:08b}'.format(num)
        tmp = int(binary, 2)
        binary = bin((tmp ^ (2 ** (len(binary) + 1) - 1)) + 1)[3:]
        return int(binary, 2)

    @staticmethod
    def detech_fat_node(node):
        node = bin(int.from_bytes(node, 'little'))

    def __init__(self):
        c = wmi.WMI()
        # --- Get usb ---
        # MediaType = "Removable Media";
        self.devices = []
        self.usb_number = -1
        self.disk_path = ''
        self.partitions = []
        self.partition_number = -1
        self.fat_table = []
        self.entry_size = 32
        self.bytesPerSector = 0

        for drive in c.Win32_DiskDrive():
            if drive.MediaType == 'Removable Media':
                # print(drive)
                self.devices.append({
                    'Path': drive.DeviceID,
                    'BytePerSector': drive.BytesPerSector
                })

    def choose_usb(self):
        if len(self.devices) == 0:
            print("No USB supported!!!")
            return
        for i, usb in enumerate(self.devices):
            print(f"USB {i}:")
            for attribute, value in usb.items():
                print(f"    {attribute}: {value}")

        while self.usb_number < 0 or self.usb_number >= len(self.devices):
            self.usb_number = int(
                input("Choose usb you want to get information: "))
            if 0 <= self.usb_number < len(self.devices):
                break
            print('The usb you choose is not exist')
        self.partitions.clear()
        self.bytesPerSector = self.devices[self.usb_number]['BytePerSector']

    # --- Get partitions information---
    def read_mbr(self):
        if self.usb_number < 0 or self.usb_number >= len(self.devices):
            self.choose_usb()
        self.disk_path = self.devices[self.usb_number]['Path']
        with open(self.disk_path, 'rb') as f:
            mbr = f.read(512)
            for i in range(0, 4):
                index = int('1be', 16) + i * 16
                sec_begin = int.from_bytes(
                    mbr[index + int('08', 16): index + int('08', 16) + 4], 'little')
                if sec_begin <= 0 and i != 0:
                    break
                partition = {
                    "Status": 'bootable' if "{:02x}".format(mbr[index]) == '80' else 'non-bootable',
                    "CHSBegin": self.convert_chs(mbr[index + int("01", 16): index + int("01", 16) + 3]),
                    "Type": self.convert_type(mbr[index + int("04", 16)]),
                    "CHSEnd": self.convert_chs(mbr[index + int("05", 16): index + int("05", 16) + 3]),
                    "SecBegin": sec_begin,
                    "NumberSector": int.from_bytes(mbr[index + int('0C', 16): index + int('0C', 16) + 4], 'little')
                }
                self.partitions.append(partition)

    # Return partition information
    def get_partition(self):
        if len(self.partitions) <= 0:
            self.read_mbr()
        return self.partitions

    def print_partition(self):
        for i, partition in enumerate(self.partitions):
            print(f"Partition {i}:")
            for attribute, value in partition.items():
                print(f"    {attribute}: {value}")
            print()

    # Read FAT32 Partition
    def read_fat32(self):
        if self.partitions[self.partition_number]['Type'] != 'FAT32':
            return

        partition = self.partitions[self.partition_number]
        begin_index = partition['SecBegin'] * self.bytesPerSector
        with open(self.disk_path, 'rb') as f:
            f.seek(begin_index)
            boot_sector = f.read(512)
            prop = {
                "BytesPerSector": int.from_bytes(boot_sector[int('0B', 16): int('0B', 16) + 2], 'little'),
                "SectorPerCluster": int(boot_sector[int('0D', 16)]),
                "SectorBeforeFat": int.from_bytes(boot_sector[int('0E', 16): int('0E', 16) + 2], 'little'),
                "NumberOfFat": int(boot_sector[int('10', 16)]),
                "VolumeSize": int.from_bytes(boot_sector[int('20', 16): int('20', 16) + 4], 'little'),
                "SectorPerFat": int.from_bytes(boot_sector[int('24', 16): int('24', 16) + 4], 'little'),
                "RDETCluster": int.from_bytes(boot_sector[int('2C', 16): int('2C', 16) + 4], 'little'),
                "Type": boot_sector[int('52', 16): int('52', 16) + 8]
            }
            self.partitions[self.partition_number]['Property'] = prop

    def read_ntfs(self):
        if self.partitions[self.partition_number]['Type'] != 'NTFS':
            return

        partition = self.partitions[self.partition_number]
        begin_index = partition['SecBegin'] * self.bytesPerSector
        with open(self.disk_path, 'rb') as f:
            f.seek(begin_index)
            boot_sector = f.read(512)
            prop = {
                "BytesPerSector": int.from_bytes(boot_sector[int('0B', 16): int('0B', 16) + 2], 'little'),
                "SectorPerCluster": int(boot_sector[int('0D', 16)]),
                "SectorPerTrack": int.from_bytes(boot_sector[int('18', 16): int('18', 16) + 2], 'little'),
                "NumberOfHead": int.from_bytes(boot_sector[int('1A', 16): int('1A', 16) + 2], 'little'),
                "NumberOfSector": int.from_bytes(boot_sector[int('28', 16): int('28', 16) + 8], 'little'),
                "MFTCluster": int.from_bytes(boot_sector[int('30', 16): int('30', 16) + 8], 'little'),
                "MFTBackupCluster": int.from_bytes(boot_sector[int('38', 16): int('38', 16) + 8], 'little'),
                "BytePerEntry": 2 ** self.convert2_complement(boot_sector[int('40', 16)])
            }
            self.partitions[self.partition_number]['Property'] = prop

    def read_partition(self):
        if len(self.partitions) <= 0:
            self.read_mbr()
            self.print_partition()

        while self.partition_number < 0 or self.partition_number >= len(self.partitions):
            self.partition_number = int(
                input("Choose partition you want to get information: "))
            if 0 <= self.partition_number < len(self.partitions):
                break
            print('The partitions you choose is not exist')

        if self.partitions[self.partition_number]['Type'] == 'FAT32':
            self.read_fat32()
        elif self.partitions[self.partition_number]['Type'] == 'NTFS':
            self.read_ntfs()

        print(self.partitions[self.partition_number]['Property'])

    def read_table(self):
        begin_sector = self.partitions[self.partition_number]['SecBegin']
        table_sector = begin_sector + self.partitions[self.partition_number]['Property']['SectorBeforeFat']
        table_index = table_sector * self.bytesPerSector

        with open(self.disk_path, 'rb') as f:
            f.seek(table_index)
            tmp = 1
            i = table_index
            while tmp != 0:
                tmp = int.from_bytes(f.read(4), 'little')
                if tmp == 0:
                    break
                if 'ffffff8' <= '{:08x}'.format(tmp)[1:] <= 'fffffff':
                    self.fat_table.append('end')
                else:
                    self.fat_table.append(tmp)
                i += 4
                f.seek(i)

        # self.fat_list = []

        # for i,x in enumerate(self.fat_table):
        #     print(x, end= " ")
        #     if (i % 4 == 3):
        # print()

        def read_rdet(self):
            self.rdet_table = []
            begin_sector = self.partitions[self.partition_number]['SecBegin']
            fat_sector = self.partitions[self.partition_number]['Property']['SectorBeforeFat']
            rdet_sector = begin_sector + fat_sector + self.partitions[self.partition_number]['Property'][
                'SectorPerFat'] * 2
            rdet_index = rdet_sector * self.bytePerSector
            with open(self.disk_path, 'rb') as f:
                for i in range(0, len(self.fat_table)):
                    f.seek(rdet_index)
                    entry = f.read(32)
                    entry_prop = {
                        "name": entry[int('00', 16): int('00', 16) + 8],
                        "ext": entry[int('08', 16): int('08', 16) + 3],
                        "type": entry[int('0b', 16)],
                        "hour": entry[int('0d', 16): int('0d', 16) + 3],
                        "day": entry[int('10', 16): int('10', 16) + 2],
                        "cluster_begin": entry[int('1a', 16): int('1a', 16) + 2],
                        "size": entry[int('1c', 16): int('1c', 16) + 4]
                    }


if __name__ == "__main__":
    drive = Drive()
    drive.choose_usb()
    drive.read_mbr()
    drive.print_partition()
    drive.read_partition()
    drive.read_table()
