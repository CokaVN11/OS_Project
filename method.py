import itertools
import re
import sys
from io import BufferedReader

from wmi import WMI

# code for scripting non-printable character
all_chars = (chr(i) for i in range(sys.maxunicode))
categories = {'Cc'}
control_chars = ''.join(map(chr, itertools.chain(range(0x00, 0x20), range(0x7f, 0xa0))))
control_char_re = re.compile('[%s]' % re.escape(control_chars))


def remove_control_chars(s):
    return control_char_re.sub('', s)


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
    binary = "{:08b}".format(num)
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

        # read master boot record
        self.__disk = open(self.__path, "rb")
        mbr = self.__disk.read(512)
        i = 0
        while i < 4:
            index = int("1be", 16) + i * 16
            sec_begin = int.from_bytes(mbr[index + int("08", 16): index + int("08", 16) + 4], "little")
            if sec_begin <= 0:
                break  # reach the end of partition table
            status = "bootable" if "{:02x}".format(mbr[index]) == "80" else "non-bootable"
            chs_begin = convert_chs(mbr[index + int("01", 16): index + int("01", 16) + 3])
            chs_end = convert_chs(mbr[index + int("05", 16): index + int("05", 16) + 3])
            partition_type = convert_type(mbr[index + int("04", 16)])
            number_sector = int.from_bytes(mbr[index + int("0C", 16): index + int("0C", 16) + 4], "little")

            if partition_type == "FAT32":
                self.__partitions.append(
                    FAT32(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.__disk)
                )
                # self.__partitions[i].get_fat_table()
            elif partition_type == "NTFS":
                self.__partitions.append(
                    NTFS(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.__disk)
                )

            i += 1

    def __del__(self):
        if not self.__disk.closed:
            self.__disk.close()

    def __repr__(self):
        return f"Device({self.__name},{self.__path},{repr(self.__partitions)})"

    def __str__(self):
        x = "\n".join(str(x) for x in self.__partitions)
        return f"Name: {self.__name}\nPath: {self.__path}\nPartition:\n{x}"


class Entry:
    name = ""
    long_name = ""
    ext = ""
    type = ""
    time_created = ""
    date_created = ""
    cluster_begin = 0
    entry_size = 0

    @staticmethod
    def convert_name(bytes):
        return bytes.decode('utf-8')

    @staticmethod
    def convert_long_name(bytes):
        ret_arr = bytearray(bytes[1:11])
        ret_arr += bytearray(bytes[int('0e', 16): int('0e', 16) + 12])
        ret_arr += bytearray(bytes[int('1c', 16): int('1c', 16) + 4])

        try:
            ret_arr.remove(int(b'00', 16))
        except ValueError:
            pass
        try:
            ret_arr.remove(int(b'ff', 16))
        except ValueError:
            pass

        ret = ret_arr.decode("utf-16")
        return ret

    @staticmethod
    def convert_time(bytes):
        # bytes = int.from_bytes(bytes, "little")
        # if bytes == 0: return ""
        # bytes = bin(bytes)
        bytes = ''.join("{:08b}".format(x) for x in bytes[::-1])
        hour = int(bytes[0:5], 2)
        minute = int(bytes[5:12], 2)
        sec = int(bytes[11:18], 2)
        milli_sec = int(bytes[17: 25], 2)
        return f"{hour}:{minute}:{sec}:{milli_sec}"

    @staticmethod
    def convert_date(bytes):
        bytes = ''.join("{:08b}".format(x) for x in bytes[::-1])
        year = int(bytes[0:7], 2) + 1980
        month = int(bytes[7:11], 2)
        day = int(bytes[11:16], 2)
        return f"{year}-{month}-{day}"

    @staticmethod
    def convert_type(bytes):
        if "{:02x}".format(bytes) == '0f':
            return 'LFN'
        bytes = "{:08b}".format(bytes)
        ret = []
        if int(bytes[2]):
            ret.append('Archive')
        if int(bytes[3]):
            ret.append('Directory')
        if int(bytes[4]):
            ret.append('VolLabel')
        if int(bytes[5]):
            ret.append('System')
        if int(bytes[6]):
            ret.append('Hidden')
        if int(bytes[7]):
            ret.append('ReadOnly')
        return ret

    def __init__(self, name, long_name, ext, type, time_created, date_created, cluster_begin, size) -> None:
        self.name = name
        self.long_name = long_name
        self.ext = ext
        self.type = type
        self.time_created = time_created
        self.date_created = date_created
        self.cluster_begin = cluster_begin
        self.entry_size = size
        pass


class Folder(Entry):
    sub_rdet_index = 0
    sub_entry = None

    def __init__(self, name, ext, type, time_created, date_created, cluster_begin, entry_size, sub_rdet_index):
        super().__init__(name, ext, type, time_created, date_created, cluster_begin, entry_size)
        self.sub_rdet_index = sub_rdet_index


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
        if self._disk is not None and not self._disk.closed:
            self._disk.close()

    def __repr__(self):
        return f"Partition({self._status}, " \
               f"{self._chs_begin}, " \
               f"{self._chs_end}, " \
               f"{self._type}, " \
               f"{self._sector_begin}, " \
               f"{self._number_sector})"

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
    __rdet_cluster = 0
    __fat_type = ""
    volume_name = ""
    __table_sector = 0  # begin sector of FAT table
    __fat_table = []  # an array storing info of RDET entry
    __entry_list = []

    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk):
        super().__init__(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, disk)
        # Read Boot sector
        self._disk.seek(self._sector_begin * 512)
        boot_sector = self._disk.read(512)
        self._bytes_per_sector = int.from_bytes(boot_sector[int("0B", 16): int("0B", 16) + 2], "little")
        self.__sector_per_cluster = int(boot_sector[int("0D", 16)])
        self.__sector_before_fat = int.from_bytes(boot_sector[int("0E", 16): int("0E", 16) + 2], "little")
        self.__number_of_fat = int(boot_sector[int("10", 16)])
        self.__volume_size = int.from_bytes(boot_sector[int("20", 16): int("20", 16) + 4], "little")
        self.__sector_per_fat = int.from_bytes(boot_sector[int("24", 16): int("24", 16) + 4], "little")
        self.__rdet_cluster = int.from_bytes(boot_sector[int("2C", 16): int("2C", 16) + 4], "little")
        self.__fat_type = boot_sector[int("52", 16): int("52", 16) + 8].decode("utf-8")

        self.__table_sector = self._sector_begin + self.__sector_before_fat
        self.__rdet_sector = self.__table_sector + self.__sector_per_fat * 2
        # Read FAT table
        self.__read_fat_table()
        # Read RDET entry table
        self.__read_rdet_table()

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

    def __read_fat_table(self):
        table_index = self.__table_sector * self._bytes_per_sector
        self._disk.seek(table_index)
        tmp = int.from_bytes(self._disk.read(4), "little")
        while tmp != 0:
            if "ffffff8" <= "{:08x}".format(tmp)[1:] <= "fffffff":
                self.__fat_table.append("end")
            else:
                self.__fat_table.append(tmp)
            table_index += 4
            self._disk.seek(table_index)
            tmp = int.from_bytes(self._disk.read(4), "little")

    def __read_rdet_table(self):
        rdet_index = self.__rdet_sector * self._bytes_per_sector
        self._disk.seek(rdet_index)
        entry_bytes = self._disk.read(32)
        tmp_lfn = ''
        while "".join("{:x}".format(x) for x in entry_bytes[int("00", 16): int("00", 16) + 8]) != "00000000":
            entry_type = Entry.convert_type(entry_bytes[int("0b", 16)])
            if entry_type == 'LFN':
                tmp_lfn = Entry.convert_long_name(entry_bytes[0:32]) + tmp_lfn
            else:
                entry_long_name = tmp_lfn
                tmp_lfn = ''
                entry_name = Entry.convert_name(entry_bytes[int("00", 16): int("00", 16) + 8])
                entry_ext = entry_bytes[int("08", 16): int("08", 16) + 3].decode('utf-8')
                entry_hour = Entry.convert_time(entry_bytes[int("0d", 16): int("0d", 16) + 3])
                entry_day = Entry.convert_date(entry_bytes[int("10", 16): int("10", 16) + 2])
                entry_cluster_begin = int.from_bytes(entry_bytes[int("1a", 16): int("1a", 16) + 2], 'little')
                entry_size = int.from_bytes(entry_bytes[int("1c", 16): int("1c", 16) + 4], 'little')

            rdet_index += 32
            self._disk.seek(rdet_index)
            entry_bytes = self._disk.read(32)

            if 'VolLabel' in entry_type:
                self.volume_name = entry_name
                continue

        pass

    def get_fat_table(self):
        for i, x in enumerate(self.__fat_table):
            print(x, end=" ")
            if i % 4 == 3:
                print()


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
        self._bytes_per_sector = int.from_bytes(vbr[int("0B", 16): int("0B", 16) + 2], "little")
        self.__sector_per_cluster = int(vbr[int("0D", 16)])
        self.__sector_per_track = int.from_bytes(vbr[int("18", 16): int("18", 16) + 2], "little")
        self.__number_head = int.from_bytes(vbr[int("1A", 16): int("1A", 16) + 2], "little")
        self.__number_sector = int.from_bytes(vbr[int("28", 16): int("28", 16) + 8], "little")
        self.__MFT_cluster = int.from_bytes(vbr[int("30", 16): int("30", 16) + 8], "little")
        self.__MFT_backup_cluster = int.from_bytes(vbr[int("38", 16): int("38", 16) + 8], "little")
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
