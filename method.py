from datetime import datetime
from queue import Queue
import time

from wmi import WMI


def get_usb():
    _drives = WMI().Win32_DiskDrive()
    _usb = []
    for drive in _drives:
        if drive.MediaType == "Removable Media":
            _usb.append(Device(name=drive.Caption, path=drive.DeviceID))
    return _usb


def convert_chs(chs_bits):
    # convert each byte into a binary string
    chs_bits = "".join("{:08b}".format(bit) for bit in chs_bits)
    # convert the binary string to a dictionary
    chs = {
        "head": int(chs_bits[0:8], 2),
        "sector": int(chs_bits[10:16], 2),
        "cylinder": int(chs_bits[8:10] + chs_bits[16:24], 2),
    }
    return chs


def convert_type(type_byte):
    if type_byte in [7, 11, 12]:
        return "NTFS"
    if type_byte in [11, 12]:
        return "FAT32"
    return "Not supported"


def convert2_complement(num):
    binary = "{:08b}".format(num)
    tmp = int(binary, 2)
    binary = bin((tmp ^ (2 ** (len(binary) + 1) - 1)) + 1)[3:]
    if len(binary) > 8:
        raise ValueError("Value is too large.")
    return int(binary, 2)


class Device:
    __name = ""
    __path = ""
    __partitions = []

    def __init__(self, name, path):
        self.__name = name
        self.__path = path.replace('\\', '/')
        self.__partitions = []
        self.__read_mbr()

    def __read_mbr(self):
        with open(self.__path, "rb") as disk:
            mbr = disk.read(512)
            self.__parse_mbr(mbr)

    def __parse_mbr(self, mbr):
        for i in range(4):
            index = int("1be", 16) + i * 16
            # read the beginning sector of the partition
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
                    FAT32(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.__path)
                )
            elif partition_type == "NTFS":
                self.__partitions.append(
                    NTFS(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.__path)
                )


    def __repr__(self):
        return f"Device({self.__name},{self.__path},{repr(self.__partitions)})"

    def __str__(self):
        x = "\n".join(str(x) for x in self.__partitions)
        return f"Name: {self.__name}\nPath: {self.__path}\nPartition:\n{x}"


class Entry:
    @staticmethod
    def convert_name(bytes):
        return bytes.decode('utf-8')

    @staticmethod
    def convert_long_name(bytes):
        byte_array = bytearray(bytes[1:11])
        byte_array += bytearray(bytes[14:26])
        byte_array += bytearray(bytes[28:32])
        ret = ""
        for i in reversed(range(0, len(byte_array), 2)):
            tmp = byte_array[i:i + 2]
            if tmp == b'\x00\x00' or tmp == b'\xff\xff':
                continue
            try:
                ret = tmp.decode('utf-16-le') + ret
            except UnicodeDecodeError:
                ret = "\\" + tmp.hex() + ret
        if ret == "":
            return None
        return ret

    @staticmethod
    def convert_time(bytes):
        bytes = ''.join("{:08b}".format(x) for x in bytes[::-1])
        try:
            hour = int(bytes[0:5], 2)
            minute = int(bytes[5:12], 2)
            sec = int(bytes[11:18], 2)
            milli_sec = int(bytes[17: 25], 2)
            return f"{hour}:{minute}:{sec}:{milli_sec}"
        except ValueError:
            return "Invalid time"

    @staticmethod
    def convert_date(bytes):
        try:
            bytes = ''.join("{:08b}".format(x) for x in bytes[::-1])
            year = int(bytes[0:7], 2) + 1980
            month = int(bytes[7:11], 2)
            day = int(bytes[11:16], 2)
            return f"{year}-{month}-{day}"
        except:
            return "unknown"

    @staticmethod
    def convert_type(bytes):
        # Check if it is a LFN entry
        if "{:02x}".format(bytes) == '0f':
            return 'LFN'

        # Check each bit and add the appropriate values to a list
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

    # def convert_type(bytes):
    #     # Convert bytes to binary
    #     bytes = "{:08b}".format(bytes)

    #     # Check if it is a LFN entry
    #     if "{:02x}".format(bytes) == '0f':
    #         return 'LFN'

    #     # Check each bit and add the appropriate values to a list
    #     ret = []
    #     if int(bytes[2]):
    #         ret.append('Archive')
    #     if int(bytes[3]):
    #         ret.append('Directory')
    #     if int(bytes[4]):
    #         ret.append('VolLabel')
    #     if int(bytes[5]):
    #         ret.append('System')
    #     if int(bytes[6]):
    #         ret.append('Hidden')
    #     if int(bytes[7]):
    #         ret.append('ReadOnly')
    #     return ret

    def __init__(self, name, long_name, ext, entry_type, time_created, date_created, cluster_begin, size):
        self.name = name
        self.long_name = long_name
        self.ext = ext
        self.entry_type = entry_type
        self.time_created = time_created
        self.date_created = date_created
        self.cluster_begin = cluster_begin
        self.entry_size = size


class Folder(Entry):
    sub_rdet_index = 0
    sub_entry = None

    def __init__(self, name, long_name, ext, entry_type, time_created, date_created, cluster_begin, entry_size,
                 sub_entry):
        super().__init__(name, long_name, ext, entry_type, time_created, date_created, cluster_begin, entry_size)
        self.sub_entry = sub_entry

    def set_sub_entry(self, sub_entry):
        self.sub_entry = sub_entry


class Partition:
    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path):
        self._status = status
        self._chs_begin = chs_begin
        self._chs_end = chs_end
        self._type = partition_type
        self._sector_begin = sec_begin
        self._number_sector = number_sector
        self._path = path


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


WIN_EPOCH = 116444736000000000


class MftEntry:
    @staticmethod
    def convert_status(byte):
        # return is_using, is_directory
        return (int.from_bytes(byte, 'little') & 1) == 1, (int.from_bytes(byte, 'little') & 2) == 2

    @staticmethod
    def convert_attr_type(byte):
        attr_type = int.from_bytes(byte, 'little')
        if attr_type == int('10', 16):
            return "StandardInformation"
        if attr_type == int('30', 16):
            return "FileName"
        if attr_type == int('80', 16):
            return "Data"
        if attr_type == int('96', 16):
            return "VolumeName"
        if b'\xff' in byte:
            return "End"
        return None

    @staticmethod
    def convert_nano_second(byte):
        nano_second = int.from_bytes(byte, 'little')
        date = datetime.fromtimestamp((nano_second - WIN_EPOCH) // 10000000)
        return str(date)

    @staticmethod
    def convert_properties(byte):
        properties = int.from_bytes(byte, 'little')
        ret = []
        if properties & 0x0001:
            ret.append('Read Only')
        if properties & 0x0002:
            ret.append('Hidden')
        if properties & 0x0004:
            ret.append('System')
        if properties & 0x0020:
            ret.append('Archive')
        if properties & 0x8000000:
            ret.append('Directory')
        return ret

    def __init__(self, entry_bytes):
        self.magic = ''
        self.attr_offset = 0
        self.is_using = None
        self.is_dir = None
        self.used_size = 0
        self.allocated_size  = 0
        self.id = -1
        self.create_time = ''
        self.modify_time = ''
        self.mft_modify_time = ''
        self.access_time = ''
        self.parent_id = 0
        self.properties = []
        self.name = ''
        self.data_allocated_size = 0
        self.data_real_size = 0
        self.init_size = 0
        self.sub_list = []
        self.str = ''

        self.parse_header_entry(entry_bytes)
        self.parse_attr()

    def parse_header_entry(self, entry_bytes):
        self.magic = entry_bytes[0:4].decode('utf-8') # FILE || BAAD
        self.attr_offset = int.from_bytes(entry_bytes[20:22], 'little')
        self.is_using, self.is_dir = self.convert_status(entry_bytes[22:24])
        self.used_size = int.from_bytes(entry_bytes[24:28], 'little')
        self.allocated_size = int.from_bytes(entry_bytes[28:32], 'little')
        self.id = int.from_bytes(entry_bytes[44:48], 'little')
        self.attr = entry_bytes[self.attr_offset:]

    def parse_attr(self):
        while True:
            attr_type = self.convert_attr_type(self.attr[0:4])
            attr_size = int.from_bytes(self.attr[4:8], 'little')
            non_resident = self.attr[8]
            content_offset = 0
            if not non_resident:
                content_size = int.from_bytes(self.attr[16:20], 'little')
                content_offset = int.from_bytes(self.attr[20:22], 'little')
            if attr_type == "End":
                break
            elif attr_type == "StandardInformation":
                try:
                    self.parse_standard_information(content_offset)
                except Exception as e:
                    print("No $StandardInformation found: %s" % e)
            elif attr_type == "FileName":
                try:
                    self.parse_file_name(content_offset)
                except Exception as e:
                    print("No $FileName found: %s" % e)
            elif attr_type == "Data":
                try:
                    self.parse_data()
                except Exception as e:
                    print("No $Data found: %s" % e)
            elif attr_type == "VolumeName":
                try:
                    self.parse_volume_name(content_offset, content_size)
                except Exception as e:
                    print("No $VolumeName found: %s" % e)
            self.attr = self.attr[attr_size:]

    def parse_standard_information(self, offset):
        self.create_time = self.convert_nano_second(self.attr[offset: offset + 8])
        self.modify_time = self.convert_nano_second(self.attr[offset + 8: offset + 16])
        self.mft_modify_time = self.convert_nano_second(self.attr[offset + 16: offset + 24])
        self.access_time = self.convert_nano_second(self.attr[offset + 24: offset + 32])

    def parse_file_name(self, offset):
        self.parent_id = int.from_bytes(self.attr[offset: offset + 6], 'little')
        self.properties = self.convert_properties(self.attr[offset + 56: offset + 60])
        # attr[64] is length of name
        self.name = self.attr[offset + 66: offset + 66 + self.attr[offset + 64] * 2].decode('utf-16-le')

    def parse_data(self):
        self.data_allocated_size = int.from_bytes(self.attr[40:48], 'little')
        self.data_real_size = int.from_bytes(self.attr[48:56], 'little')
        self.init_size = int.from_bytes(self.attr[56:64], 'little')

    def parse_volume_name(self, offset, length):
        self.name = self.attr[offset: offset + length].decode('utf-16-le')

    def add_child(self, entry):
        self.sub_list.append(entry)

    def __str__(self) -> str:
        if self.str == '':
            self.str = f"{self.name}\n" \
                f"ID: {self.id}\n" \
                f"Parent ID: {self.parent_id}\n" \
                f"Properties: {self.properties}\n" \
                f"Init size: {self.init_size}\n"
        return self.str

class FAT32(Partition):
    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path):
        super().__init__(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path)
        # Read Boot sector
        with open(self._path, 'rb') as disk:
            disk.seek(self._sector_begin * 512)
            boot_sector = disk.read(512)
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
            self.__fat_table = self.__read_fat_table()
            # Read RDET entry table
            self.__entry_list = self.__read_rdet_entry(self.__rdet_sector)

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
        fat_table = []
        with open(self._path, "rb") as disk:
            table_index = self.__table_sector * self._bytes_per_sector
            disk.seek(table_index)
            tmp = int.from_bytes(disk.read(4), "little")
            while tmp != 0:
                if "ffffff8" <= "{:08x}".format(tmp)[1:] <= "fffffff":
                    # This is the last cluster of the file
                    fat_table.append("end")
                else:
                    fat_table.append(tmp)
                tmp = int.from_bytes(disk.read(4), "little")
        return fat_table

    """Read rdet and return entry_list with directory queue"""
    def __read_rdet_entry(self, sector):
        entry_list = []
        tmp_lfn = ''

        entry_name = None
        entry_long_name = None
        entry_ext = None
        entry_hour = None
        entry_day = None
        entry_cluster_begin = None
        entry_size = None

        sector_index = sector * self._bytes_per_sector
        with open(self._path, 'rb') as disk:
            if disk.tell() != sector_index:
                disk.seek(sector_index)
            entry_bytes = disk.read(32)

            while entry_bytes[int('0b', 16)] != 0:
                # deleted file
                if not entry_bytes[0] == int('e5', 16):
                    entry_type = Entry.convert_type(entry_bytes[int("0b", 16)])
                    if entry_type == 'LFN':
                        tmp_lfn = Entry.convert_long_name(entry_bytes[0:32]) + tmp_lfn
                    else:
                        entry_long_name = tmp_lfn
                        tmp_lfn = ''
                        entry_name = Entry.convert_name(entry_bytes[0x00: 0x00 + 8])
                        entry_ext = entry_bytes[0x08: 0x08 + 3].decode('utf-8')
                        entry_hour = Entry.convert_time(entry_bytes[0x0d: 0x0d + 3])
                        entry_day = Entry.convert_date(entry_bytes[0x10: 0x10 + 2])
                        entry_cluster_begin = int.from_bytes(entry_bytes[0x1a: 0x1a + 2], 'little')
                        entry_size = int.from_bytes(entry_bytes[0x1c: 0x1c + 4], 'little')
                        if 'VolLabel' in entry_type:
                            self.volume_name = entry_name
                        elif 'Directory' in entry_type:
                            next_sector = self.__rdet_sector + (entry_cluster_begin - 2) * self.__sector_per_cluster
                            if entry_cluster_begin != 0 and next_sector != sector:
                                entry_sub_list = self.__read_rdet_entry(next_sector)
                                entry_list.append(
                                    Folder(entry_name, entry_long_name, entry_ext, entry_type, entry_hour, entry_day,
                                           entry_cluster_begin, entry_size, entry_sub_list))
                        elif 'Archive' in entry_type:
                            entry_list.append(
                                Entry(entry_name, entry_long_name, entry_ext, entry_type, entry_hour, entry_day,
                                      entry_cluster_begin, entry_size))

                sector_index += 32
                if disk.tell() != sector_index:
                    disk.seek(sector_index)
                # entry_bytes = read_sector(self._path, __sector_index, 32)
                entry_bytes = disk.read(32)
            return entry_list

    def get_fat_table(self):
        return self.__fat_table

    def get_entry_list(self):
        return self.__entry_list


class NTFS(Partition):
    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path):
        super().__init__(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path)

        self._bytes_per_sector = 0
        self.__sector_per_cluster = 0
        self.__sector_per_track = 0
        self.__number_head = 0
        self.__number_sector = 0
        self.__MFT_cluster = 0
        self.__MFT_backup_cluster = 0
        self.__byte_per_entry = 0
        self.__entry_list = []

        # Read VBR
        with open(self._path, 'rb') as disk:
            disk.seek(self._sector_begin * 512)
            vbr = disk.read(512)
            self.__parse_vbr(vbr)

        self.__read_mft_entry()

    def __parse_vbr(self, vbr_bytes):
        self._bytes_per_sector = int.from_bytes(vbr_bytes[11: 13], "little")
        self.__sector_per_cluster = int(vbr_bytes[13])
        self.__sector_per_track = int.from_bytes(vbr_bytes[24: 26], "little")
        self.__number_head = int.from_bytes(vbr_bytes[26: 28], "little")
        self.__number_sector = int.from_bytes(vbr_bytes[40: 48], "little")
        self.__MFT_cluster = int.from_bytes(vbr_bytes[48: 56], "little")
        self.__MFT_backup_cluster = int.from_bytes(vbr_bytes[56: 64], "little")
        self.__byte_per_entry = 2 ** convert2_complement(vbr_bytes[64])

    def __read_mft_entry(self):
        with open(self._path, 'rb') as disk:
            # do entry dau tien doc attribute data offset x40: chia cho so byte cua 1 entry -> so entry
            mft_sector = self._sector_begin + self.__MFT_cluster * self.__sector_per_cluster
            disk.seek(mft_sector * self._bytes_per_sector)

            number_entry = 1
            cnt = 0
            self.record_id_dict = {}
            self.ref_id_dict = {}
            while number_entry:
                number_entry -= 1
                entry_bytes = disk.read(self.__byte_per_entry)
                if entry_bytes[0] == 0:
                    continue

                entry = MftEntry(entry_bytes)
                if entry.name == '$MFT':
                    number_entry = entry.data_real_size // self.__byte_per_entry - 1

                self.ref_id_dict[entry.id] = cnt

                if entry.parent_id not in self.record_id_dict.keys():
                    self.record_id_dict[entry.parent_id] = [entry.id]
                else:
                    self.record_id_dict[entry.parent_id].append(entry.id)


                self.__entry_list.append(entry)
                cnt += 1
            print()

        self.__build_folder_tree()
        self.print_entry_list()

    def __build_folder_tree(self):
        tmp_list = []
        for parent, child_list in self.record_id_dict.items():
            if parent not in self.ref_id_dict.keys():
                continue
            parent_entry = self.__entry_list[self.ref_id_dict[parent]]
            for child in child_list:
                if child not in self.ref_id_dict.keys():
                    continue
                child_entry = self.__entry_list[self.ref_id_dict[child]]
                parent_entry.add_child(child_entry)
            tmp_list.append(parent_entry)
        self.__entry_list = tmp_list

    def print_entry_list(self):
        for entry in self.__entry_list:
            print(entry)
            for child in entry.sub_list:
                print("\t{}", child)

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
