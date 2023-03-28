import FAT32
import NTFS

from wmi import WMI

def get_usb():
    _drives = WMI().Win32_DiskDrive()
    _usb = []
    for drive in _drives:
        if drive.MediaType == "Removable Media":
            _usb.append(Device(name=drive.Caption, path=drive.DeviceID))
    return _usb

class Device:
    name = ""
    path = ""
    partitions = []

    @staticmethod
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

    @staticmethod
    def convert_type(type_byte):
        if type_byte in [7]:
            return "NTFS"
        if type_byte in [11, 12]:
            return "FAT32"
        return "Not supported"

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.partitions = []
        self.__read_mbr()

    def __read_mbr(self):
        with open(self.path, "rb") as disk:
            mbr = disk.read(512)
            mbr = mbr[int("1be", 16):]

        self.__parse_mbr(mbr)

    def __parse_mbr(self, mbr):
        for i in range(4):
            sec_begin = int.from_bytes(mbr[8: 12], "little")
            if sec_begin <= 0:
                break  # reach the end of partition table
            status = "bootable" if "{:02x}".format(mbr[0]) == "80" else "non-bootable"
            chs_begin = self.convert_chs(mbr[1: 4])
            chs_end = self.convert_chs(mbr[5: 5 + 3])
            partition_type = self.convert_type(mbr[4])
            number_sector = int.from_bytes(mbr[12:16], "little")

            if partition_type == "FAT32":
                self.partitions.append(
                    FAT32.FAT32(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.path)
                )
            elif partition_type == "NTFS":
                self.partitions.append(
                    NTFS.NTFS(status, chs_begin, chs_end, partition_type, sec_begin, number_sector, self.path)
                )
            mbr = mbr[16:]


    def __repr__(self):
        return f"Device({self.name},{self.path},{repr(self.partitions)})"

    def __str__(self):
        x = "\n".join(str(x) for x in self.partitions)
        return f"Name: {self.name}\nPath: {self.path}\nPartition:\n{x}"

if __name__ == "__main__":
    usb_list = get_usb()
    for usb in usb_list:
        print(usb)
