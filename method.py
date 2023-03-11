import psutil

def choose_partition():
    partitions = psutil.disk_partitions()
    for partition in partitions:
        if (partition.opts == "rw,fixed"):
            print(f"Device: {partition.device}")
        

if __name__ == "__main__":
    choose_partition()
