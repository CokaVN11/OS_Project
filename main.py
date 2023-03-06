import psutil

# Lấy danh sách các ổ đĩa vật lý
partitions = psutil.disk_partitions()

# Liệt kê thông tin các ổ đĩa
for partition in partitions:
    print(f"Device: {partition.device}")
    print(f"Mountpoint: {partition.mountpoint}")
    print(f"Filesystem type: {partition.fstype}")
    print(f"Options: {partition.opts}")
    print(f"Usage: {psutil.disk_usage(partition.mountpoint)}")
    print("---------------------------")
