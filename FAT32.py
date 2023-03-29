class Entry:
    @staticmethod
    def convert_name(bytes):
        return bytes.decode('utf-8', errors='ignore').strip(' ')

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
    def convert_time(bytes, is_create_time=False):
        bytes = ''.join("{:08b}".format(x) for x in bytes[::-1])
        try:
            hour = int(bytes[0:5], 2)
            minute = int(bytes[5:12], 2)
            sec = int(bytes[11:18], 2) if is_create_time else int(bytes[11:17], 2)
            milli_sec = int(bytes[17: 25], 2) if is_create_time else 0
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

    byte_map = {
            0x20: 'Archive',
            0x10: 'Directory',
            0x08: 'VolLabel',
            0x04: 'System',
            0x02: 'Hidden',
            0x01: 'ReadOnly'
        }

    @staticmethod
    def convert_type(bytes):
        if bytes == 0x0f:
            return "LFN"

        # Check each bit and add the appropriate values to a list
        ret = [Entry.byte_map[i] for i in Entry.byte_map if bytes & i]
        return ret

    def __init__(self, entry_bytes):
        """
        :param entry_bytes: bytes of entry which contains primary infor and secondary info
        """

        self.name = ''
        self.long_name = ''
        self.ext = ''
        self.entry_type = None
        self.time_created = None
        self.date_created = None
        self.cluster_begin = None
        self.entry_size = None
        self.is_dir = False
        self.sub_list = None

        self.entry_bytes = entry_bytes
        self.__parse_entry()

    def __parse_entry(self):
        while self.entry_bytes:
            if self.convert_type(self.entry_bytes[11]) == 'LFN':
                self.long_name = self.convert_long_name(self.entry_bytes[0:32]) + self.long_name
                self.entry_bytes = self.entry_bytes[32:]
                continue

            self.entry_type = self.convert_type(self.entry_bytes[11])
            if 'Directory' in self.entry_type:
                self.is_dir = True
            self.ext = self.convert_name(self.entry_bytes[8:11])
            # if self.ext == 'JPG':
            #     print()
            self.name = self.convert_name(self.entry_bytes[0:8])
            self.time_created = self.convert_time(self.entry_bytes[13:16])
            self.date_created = self.convert_date(self.entry_bytes[16:18])
            self.time_modified = self.convert_time(self.entry_bytes[22:24])
            self.date_modified = self.convert_date(self.entry_bytes[24:26])
            self.cluster_begin = (int.from_bytes(self.entry_bytes[20:22], 'little') << 16) + int.from_bytes(self.entry_bytes[26:28],'little')
            self.entry_size = int.from_bytes(self.entry_bytes[28:32],'little')
            break

    def add_child_list(self, child):
        self.sub_list = child
    def get_entry_list(self):
        return self.sub_list if self.is_dir else None

    def get_name(self):
        if self.long_name:
            return self.long_name
        return self.name + '.' + self.ext

    def is_skip(self):
        if 'VolLabel' in self.entry_type:
            return True
        return False

    def get_info(self):
        prop = (
            f"Name: {self.get_name()}\n"
            f"Date created: {self.date_created}\n"
            f"Time created: {self.time_created}\n"
            f"Size: {self.entry_size}\n"
        )
        return prop

class FAT32:
    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path):
        self._status = status
        self._chs_begin = chs_begin
        self._chs_end = chs_end
        self._type = partition_type
        self._sector_begin = sec_begin
        self._number_sector = number_sector
        self._path = path
        # Read Boot sector
        with open(self._path, 'rb') as disk:
            disk.seek(self._sector_begin * 512)
            boot_sector = disk.read(512)
            self.bytes_per_sector = int.from_bytes(boot_sector[int("0B", 16): int("0B", 16) + 2], "little")
            self.sector_per_cluster = int(boot_sector[int("0D", 16)])
            self.sector_before_fat = int.from_bytes(boot_sector[int("0E", 16): int("0E", 16) + 2], "little")
            self.number_of_fat = int(boot_sector[int("10", 16)])
            self.volume_size = int.from_bytes(boot_sector[int("20", 16): int("20", 16) + 4], "little")
            self.sector_per_fat = int.from_bytes(boot_sector[int("24", 16): int("24", 16) + 4], "little")
            self.rdet_cluster = int.from_bytes(boot_sector[int("2C", 16): int("2C", 16) + 4], "little")
            self.fat_type = boot_sector[int("52", 16): int("52", 16) + 8].decode("utf-8")

            self.table_sector = self._sector_begin + self.sector_before_fat
            self.rdet_sector = self.table_sector + self.sector_per_fat * 2
        # Read FAT table
        self.__fat_table = self.__read_fat_table()
        # Read RDET entry table
        self.__entry_list = self.__read_rdet_entry(self.rdet_cluster)

    def __str__(self):
        prop = (
            f"Bytes per Sector: {self.bytes_per_sector}\n"
            f"Sector per Cluster: {self.sector_per_cluster}\n"
            f"Sector before FAT: {self.sector_before_fat}\n"
            f"Number of FAT: {self.number_of_fat}\n"
            f"Volume size:  {self.volume_size}\n"
            f"Sector per FAT: {self.sector_per_fat}\n"
            f"RDET cluster: {self.rdet_cluster}\n"
            f"Type: {self.fat_type}\n"
        )
        return super().__str__() + prop

    def __read_fat_table(self):
        fat_table = []
        with open(self._path, "rb") as disk:
            table_index = self.table_sector * self.bytes_per_sector
            disk.seek(table_index)
            tmp = disk.read(self.sector_per_fat * self.bytes_per_sector)
            number_entry = int(self.sector_per_fat * self.bytes_per_sector // 4)
            # limit = number_entry - 1915904
            index = 0
            while tmp and index < number_entry:
                # print(index, end="\r")

                cluster = int.from_bytes(tmp[index + 0: index + 4], 'little')
                if 0xffffff8 <= cluster <= 0xffffffff:
                    # This is the last cluster of the file
                    fat_table.append("end")
                elif cluster  == 0x0:
                    fat_table.append("free")
                elif cluster  == 0xffffff7:
                    fat_table.append("bad")
                else:
                    fat_table.append(cluster)
                # tmp = tmp[4:]
                index += 4
        return fat_table

    # get fully rdet or sdet
    def __get_det(self, cluster_id):
        ret_bytes = b''
        next_cluster = cluster_id
        with open(self._path, 'rb') as disk:
            while next_cluster != "end":
                sector_index = self.rdet_sector + (next_cluster - 2) * self.sector_per_cluster
                byte_index = sector_index * self.bytes_per_sector
                if disk.tell() != byte_index:
                    disk.seek(byte_index)
                ret_bytes += disk.read(self.sector_per_cluster * self.bytes_per_sector)
                next_cluster = self.__fat_table[next_cluster]
        return ret_bytes

    def __read_rdet_entry(self, cluster_id, prev_cluster = 0):
        entry_list = []

        det = self.__get_det(cluster_id)
        tmp = None
        while True:
            entry_bytes = det[0:32]
            det = det[32:]
            if entry_bytes[int('0b', 16)] == 0:
                break
            # 0xe5 is deleted file
            if entry_bytes[0] == int('e5', 16):
                continue
            entry_type = Entry.convert_type(entry_bytes[int("0b", 16)])
            if entry_type == 'LFN':
                if tmp is None:
                    tmp = entry_bytes
                else:
                    tmp += entry_bytes
                continue
            if tmp is None:
                entry = Entry(entry_bytes)
            else:
                tmp += entry_bytes
                entry = Entry(tmp)
                tmp = None
            if 'VolLabel' in entry.entry_type:
                self.volume_name = entry.name
            elif 'Directory' in entry.entry_type:
                if entry.name == '.' or entry.name == '..':
                    continue
                entry_sub_list = self.__read_rdet_entry(entry.cluster_begin, cluster_id)
                entry.add_child_list(entry_sub_list)
            entry_list.append(entry)

        return entry_list

    def get_fat_table(self):
        return self.__fat_table

    def get_entry_list(self):
        return self.__entry_list

    def get_entry(self, name):
        stack = [(None, self.get_entry_list())]
        for parent, entry_list in stack:
            for entry in entry_list:
                if entry.get_name() == name:
                    return entry
                if entry.is_dir:
                    stack.append((entry, entry.get_entry_list()))
        return None

    def get_info(self):
        prop = (
            f"Bytes per Sector: {self.bytes_per_sector}\n"
            f"Sector per Cluster: {self.sector_per_cluster}\n"
            f"Sector before FAT: {self.sector_before_fat}\n"
            f"Number of FAT: {self.number_of_fat}\n"
            f"Volume size:  {self.volume_size}\n"
            f"Sector per FAT: {self.sector_per_fat}\n"
            f"RDET cluster: {self.rdet_cluster}\n"
            f"Type: {self.fat_type}\n"
        )
        return prop

    def get_name(self):
        return self.volume_name

    def is_skip(self):
        return False
