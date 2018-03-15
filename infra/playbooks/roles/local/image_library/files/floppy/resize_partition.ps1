# ==============================================================================
# Windows can't automagically resize partitions when qemu img size changes.
# This script does this when default user logs in.
# ==============================================================================
# This is C:\
$disk_num = 0
$partition_num = 2
$size = (Get-PartitionSupportedSize -DiskNumber $disk_num -PartitionNumber $partition_num)
Resize-Partition -DiskNumber $disk_num -PartitionNumber $partition_num -Size $size.SizeMax
