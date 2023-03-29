from datetime import datetime

WIN_EPOCH = 116444736000000000

class Entry:
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
        if attr_type == int('60', 16):
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
        self.is_dir = False
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

        self.__parse_header_entry(entry_bytes)
        self.__parse_attr()

    def __parse_header_entry(self, entry_bytes):
        self.magic = entry_bytes[0:4].decode('utf-8') # FILE || BAAD
        self.attr_offset = int.from_bytes(entry_bytes[20:22], 'little')
        self.is_using, self.is_dir = self.convert_status(entry_bytes[22:24])
        self.used_size = int.from_bytes(entry_bytes[24:28], 'little')
        self.allocated_size = int.from_bytes(entry_bytes[28:32], 'little')
        self.id = int.from_bytes(entry_bytes[44:48], 'little')
        self.attr = entry_bytes[self.attr_offset:]

    def __parse_attr(self):
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
                    self.__parse_standard_information(content_offset)
                except Exception as e:
                    print("No $StandardInformation found: %s" % e)
            elif attr_type == "FileName":
                try:
                    self.__parse_file_name(content_offset)
                except Exception as e:
                    print("No $FileName found: %s" % e)
            elif attr_type == "Data":
                try:
                    self.__parse_data()
                except Exception as e:
                    print("No $Data found: %s" % e)
            elif attr_type == "VolumeName":
                try:
                    self.__parse_volume_name(content_offset, content_size)
                except Exception as e:
                    print("No $VolumeName found: %s" % e)
            self.attr = self.attr[attr_size:]

    def __parse_standard_information(self, offset):
        self.create_time = self.convert_nano_second(self.attr[offset: offset + 8])
        self.modify_time = self.convert_nano_second(self.attr[offset + 8: offset + 16])
        self.mft_modify_time = self.convert_nano_second(self.attr[offset + 16: offset + 24])
        self.access_time = self.convert_nano_second(self.attr[offset + 24: offset + 32])

    def __parse_file_name(self, offset):
        self.parent_id = int.from_bytes(self.attr[offset: offset + 6], 'little')
        self.properties = self.convert_properties(self.attr[offset + 56: offset + 60])
        # attr[64] is length of name
        self.name = self.attr[offset + 66: offset + 66 + self.attr[offset + 64] * 2].decode('utf-16-le')

    def __parse_data(self):
        self.data_allocated_size = int.from_bytes(self.attr[40:48], 'little')
        self.data_real_size = int.from_bytes(self.attr[48:56], 'little')
        self.init_size = int.from_bytes(self.attr[56:64], 'little')

    def __parse_volume_name(self, offset, length):
        self.volume_name = self.attr[offset: offset + length].decode('utf-16-le')

    def add_child(self, entry):
        self.sub_list.append(entry)

    def get_entry_list(self):
        return self.sub_list if self.is_dir else None

    def get_name(self):
        return self.name

    def is_skip(self):
        if self.name == '$Volume':
            return True
        # if self.name == '.':
        #     return True
        return False

    def __str__(self) -> str:
        if self.str == '':
            self.str = f"{self.name}\n" \
                f"ID: {self.id}\n" \
                f"Parent ID: {self.parent_id}\n" \
                f"Properties: {self.properties}\n" \
                f"Init size: {self.init_size}\n"
        return self.str

    def get_info(self):
        prop = (
            f"Name: {self.name}\n"
            f"Attribute: {self.properties}\n"
            f"Date create: {self.create_time}\n"
            f"Size: {self.data_real_size}\n"
        )
        return prop

class NTFS:
    @staticmethod
    def convert2_complement(num):
        binary = "{:08b}".format(num)
        tmp = int(binary, 2)
        binary = bin((tmp ^ (2 ** (len(binary) + 1) - 1)) + 1)[3:]
        if len(binary) > 8:
            raise ValueError("Value is too large.")
        return int(binary, 2)

    def __init__(self, status, chs_begin, chs_end, partition_type, sec_begin, number_sector, path):
        self.status = status
        self.chs_begin = chs_begin
        self.chs_end = chs_end
        self.type = partition_type
        self.sector_begin = sec_begin
        self.number_sector = number_sector
        self.path = path

        self.__entry_list = []

        # Read VBR
        with open(self.path, 'rb') as disk:
            disk.seek(self.sector_begin * 512)
            vbr = disk.read(512)
            self.__parse_vbr(vbr)

        self.__read_mft_entry()

    def __parse_vbr(self, vbr_bytes):
        self.bytes_per_sector = int.from_bytes(vbr_bytes[11: 13], "little")
        self.sector_per_cluster = int(vbr_bytes[13])
        self.sector_per_track = int.from_bytes(vbr_bytes[24: 26], "little")
        self.number_head = int.from_bytes(vbr_bytes[26: 28], "little")
        self.number_sector = int.from_bytes(vbr_bytes[40: 48], "little")
        self.MFT_cluster = int.from_bytes(vbr_bytes[48: 56], "little")
        self.MFT_backup_cluster = int.from_bytes(vbr_bytes[56: 64], "little")
        self.byte_per_entry = 2 ** self.convert2_complement(vbr_bytes[64])

    def __read_mft_entry(self):
        with open(self.path, 'rb') as disk:
            # do entry dau tien doc attribute data offset x40: chia cho so byte cua 1 entry -> so entry
            mft_sector = self.sector_begin + self.MFT_cluster * self.sector_per_cluster
            disk.seek(mft_sector * self.bytes_per_sector)

            number_entry = 1
            cnt = 0
            self.record_id_dict = {}
            self.ref_id_dict = {}
            while number_entry:
                number_entry -= 1
                entry_bytes = disk.read(self.byte_per_entry)
                if entry_bytes[0] == 0:
                    continue

                entry = Entry(entry_bytes)
                if entry.name == '$MFT':
                    number_entry = entry.data_real_size // self.byte_per_entry - 1
                if entry.name == '$Volume':
                    self.volume_name = entry.volume_name

                self.ref_id_dict[entry.id] = cnt

                if not entry.parent_id == entry.id:
                    if entry.parent_id not in self.record_id_dict.keys():
                        self.record_id_dict[entry.parent_id] = [entry.id]
                    else:
                        self.record_id_dict[entry.parent_id].append(entry.id)

                self.__entry_list.append(entry)
                cnt += 1
            print()

        self.__build_folder_tree()
        # self.print_entry_list()

    def __build_folder_tree(self):
        tmp_list = []
        # root of directory is entry 5
        root_child_list = self.record_id_dict[5]
        for child in root_child_list:
            if child not in self.ref_id_dict.keys():
                continue
            child_entry = self.__entry_list[self.ref_id_dict[child]]
            tmp_list.append(child_entry)

        for parent, child_list in self.record_id_dict.items():
            if parent == 5:
                continue
            if parent not in self.ref_id_dict.keys():
                continue
            # check parent is in root directory or not
            # in_root = False
            # if parent in root_child_list:
            #     in_root = True
            parent_entry = self.__entry_list[self.ref_id_dict[parent]]
            for child in child_list:
                if child not in self.ref_id_dict.keys():
                    continue
                child_entry = self.__entry_list[self.ref_id_dict[child]]
                parent_entry.add_child(child_entry)


        self.__entry_list = tmp_list
        # self.print_entry_list()

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
            f"Bytes per sector: {self.bytes_per_sector}\n"
            f"Sectors per cluster: {self.sector_per_cluster}\n"
            f"Sectors per track: {self.sector_per_track}\n"
            f"Number of heads: {self.number_head}\n"
            f"Number of sectors: {self.number_sector}\n"
            f"MFT cluster: {self.MFT_cluster}\n"
            f"MFT backup cluster: {self.MFT_backup_cluster}\n"
        )
        return prop

    def print_entry_list(self):
        for entry in self.__entry_list:
            print(entry)
            for child in entry.sub_list:
                print("\t{}", child)

    def get_name(self):
        return self.volume_name

    def is_skip(self):
        return False
