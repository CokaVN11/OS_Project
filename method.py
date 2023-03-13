from io import BufferedReader
from wmi import WMI
from abc import ABC, abstractmethod


def get_usb():
    _drives = WMI().Win32_DiskDrive()
    _usb = []
    for drive in _drives:
        if drive.MediaType == "Removable Media":
            _usb.append(Device(name=drive.Caption, path=drive.DeviceID))
    return _usb


def convert_chs(chs_bits):
    chs_bits = "".join("{:08b}".format(bit) for bit in chs_bits)
    # print(CHS_bits)
    chs = {
        "head": int(chs_bits[0:8], 2),
        "sector": int(chs_bits[10:16], 2),
        "cylinder": int(chs_bits[8:10] + chs_bits[16:24], 2),
    }
    # print(chs)
    return chs


def convert_type(type_byte):
    type_byte = "{:02x}".format(type_byte)
    if type_byte == "07":
        return "NTFS"
    if type_byte == "0c" or type_byte == "0b":
        return "FAT32"
    if type_byte == "0e":
        return "FAT16"
    return "Not supported"

def convert2_complement(num):
    binary = '{:08b}'.format(num)
    tmp = int(binary, 2)
    binary = bin((tmp ^ (2 ** (len(binary) + 1) - 1)) + 1)[3:]
    return int(binary, 2)


class Device:
    __name = ""
    __path = ""
    __partitions = []
    __disk = None

    def __init__(self, name, path):
        self.__name = name
        self.__path = path

        self.__disk = open(self.__path, "rb")
        mbr = self.__disk.read(512)
        i = 0
        while i < 4:
            index = int("1be", 16) + i * 16
            sec_begin = int.from_bytes(mbr[index + int("08", 16) : index + int("08", 16) + 4], "little")
            if sec_begin <= 0:
                break  # reach the end of partition table
            status = "bootable" if "{:02x}".format(mbr[index]) == "80" else "non-bootable"
            chs_begin = convert_chs(mbr[index + int("01", 16) : index + int("01", 16) + 3])
            chs_end = convert_chs(mbr[index + int("05", 16) : index + int("05", 16) + 3])
            partition_type = convert_type(mbr[index + int("04", 16)])
            number_sector = int.from_bytes(mbr[index + int("0C", 16) : index + int("0C", 16) + 4], "little")

            if partition_type == "FAT32":
                self.__partitions.append(
                    FAT32(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.__disk)
                )
            elif partition_type == "NTFS":
                self.__partitions.append(
                    NTFS(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.__disk)
                )

            i += 1

    # Read MBR

    def __del__(self):
        if not self.__disk.closed:
            self.__disk.close()

    def __repr__(self):
        return f"Device({self.__name},{self.__path},{repr(self.__partitions)})"

    def __str__(self):
        x = "\n".join(str(x) for x in self.__partitions)
        return f"Name: {self.__name}\nPath: {self.__path}\nPartition:\n{x}"


class Partition:
    _bytes_per_sector = None
    _status = ""
    _chs_begin = None
    _chs_end = None
    _type = ""
    _sector_begin = 0
    _number_sector = 0
    _disk: BufferedReader = None

    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk):
        self._status = status
        self._chs_begin = chs_begin
        self._chs_end = chs_end
        self._type = partition_type
        self._sector_begin = sec_begin
        self._number_sector = number_sector
        self._disk = disk
        pass

    def __del__(self):
        if self._disk != None and not self._disk.closed:
            self._disk.close()

    def __repr__(self):
        return f"Partition({self._status}, {self._chs_begin}, {self._chs_end}, {self._type}, {self._sector_begin},{self._number_sector})"

    def __str__(self):
        return (
            f"Status: {self._status}\n"
            f"CHSBegin: {self._chs_begin}\n"
            f"CHSEnd: {self._chs_end}\n"
            f"Sector begin: {self._sector_begin}\n"
            f"Type: {self._type}\n"
            f"Number sector: {self._number_sector}\n"
        )


class FAT32(Partition):
    __sector_per_cluster = 0
    __sector_per_fat = 0
    __sector_before_fat = 0
    __number_of_fat = 1
    __volume_size = 0
    __sector_per_fat = 0
    __rdet_cluster = 0
    __fat_type = ""

    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk):
        super().__init__(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk)
        # Read Boot sector
        self._disk.seek(self._sector_begin * 512)
        boot_sector = self._disk.read(512)
        self._bytes_per_sector = int.from_bytes(boot_sector[int("0B", 16) : int("0B", 16) + 2], "little")
        self.__sector_per_cluster = int(boot_sector[int("0D", 16)])
        self.__sector_before_fat = int.from_bytes(boot_sector[int("0E", 16) : int("0E", 16) + 2], "little")
        self.__number_of_fat = int(boot_sector[int("10", 16)])
        self.__volume_size = int.from_bytes(boot_sector[int("20", 16) : int("20", 16) + 4], "little")
        self.__sector_per_fat = int.from_bytes(boot_sector[int("24", 16) : int("24", 16) + 4], "little")
        self.__rdet_cluster = int.from_bytes(boot_sector[int("2C", 16) : int("2C", 16) + 4], "little")
        self.__fat_type = boot_sector[int("52", 16) : int("52", 16) + 8].decode("utf-8")
        pass

    def __str__(self):
        prop = (
            f"Bytes per Sector: {self._bytes_per_sector}\n"
            f"Sector per Cluster: {self.__sector_per_cluster}\n"
            f"Sector before FAT: {self.__sector_before_fat}\n"
            f"Number of FAT: {self.__number_of_fat}\n"
            f"Volume size:  {self.__volume_size}\n"
            f"Sector per FAT: {self.__sector_per_fat}\n"
            f"RDET cluster: {self.__rdet_cluster}\n"
            f"Type: {self.__fat_type}\n"
        )
        return super().__str__() + prop


class NTFS(Partition):
    __sector_per_cluster = 0
    __sector_per_track = 0
    __number_head = 0
    __number_sector = 0
    __MFT_cluster = 0
    __MFT_backup_cluster = 0
    __byte_per_entry = 0

    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk):
        super().__init__(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk)
        # Read VBR
        self._disk.seek(self._sector_begin * 512)
        vbr = self._disk.read(512)
        self._bytes_per_sector = (int.from_bytes(vbr[int("0B", 16) : int("0B", 16) + 2], "little"))
        self.__sector_per_cluster = (int(vbr[int("0D", 16)]))
        self.__sector_per_track = (int.from_bytes(vbr[int("18", 16) : int("18", 16) + 2], "little"))
        self.__number_head = (int.from_bytes(vbr[int("1A", 16) : int("1A", 16) + 2], "little"))
        self.__number_sector = (int.from_bytes(vbr[int("28", 16) : int("28", 16) + 8], "little"))
        self.__MFT_cluster = (int.from_bytes(vbr[int("30", 16) : int("30", 16) + 8], "little"))
        self.__MFT_backup_cluster = (int.from_bytes(vbr[int("38", 16) : int("38", 16) + 8], "little"))
        self.__byte_per_entry = 2 ** convert2_complement(vbr[int("40", 16)])

        pass

    def __str__(self):
        prop = (
            f"Bytes Per Sector: {self._bytes_per_sector}\n"
            f"Sector Per Cluster: {self.__sector_per_cluster}\n"
            f"Sector Per Track: {self.__sector_per_track}\n"
            f"Number Of Head: {self.__number_head}\n"
            f"Number Of Sector: {self.__number_sector}\n"
            f"MFT Cluster: {self.__MFT_cluster}\n"
            f"MFT Backup Cluster: {self.__MFT_backup_cluster}\n"
            f"Byte Per Entry: {self.__byte_per_entry}\n"
        )
        return super().__str__() + prop


if __name__ == "__main__":
    usb_list = get_usb()
    for usb in usb_list:
        print(usb)
