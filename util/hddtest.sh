block_size='4096'
write_count=10
thread_count=10

outfile=./hdd-${HOSTNAME}-$(date '+%Y%m%d%H%M%S').report
num_re="^[0-9]+$"
data_dir='test_data'
test_file_prefix='test_file'

function test_if_integer {
    if ! [[ $1 =~ $num_re ]] ; then
        return 0
    else
        return 1
    fi
}

while test $# -gt 0; do
    case "$1" in 
        --help)
            echo "HDD multiprocess write speed testing utility"
            echo "options:"
            echo "--help            this help"
            echo "--block-size      write block size in Kb ($block_size)"
            echo "--thread-count    thread count ($thread_count)"
            echo "--write-count     writes per file count ($write_count)"
            exit 0
            ;;
        --block-size)
            shift
            if test $# -gt 0 && ! test_if_integer $1; then
                block_size=$1
            else
                echo "block size not specified or in the wrong format"
                exit 1
            fi
            shift
            ;;
        --thread-count)
            shift
            if test $# -gt 0 && ! test_if_integer $1; then
                thread_count=$1
            else
                echo "thread count not specified or in the wrong format"
                exit 1
            fi
            shift
            ;;
        --write-count)
            shift
            if test $# -gt 0 && ! test_if_integer $1; then
                write_count=$1
            else
                echo "write count not specified or in the wrong format"
                exit 1
            fi
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "Starting..."
echo "Thread count          $thread_count"
echo "Block size            $block_size"
echo "Write count (blocks)  $write_count"

rm -rf ${data_dir}
mkdir ${data_dir}

for i in $(seq -w 1 $thread_count); do
    { echo $(date +'%d%b%y:%H:%M:%S') $i; time dd if=/dev/zero of=${data_dir}/${test_file_prefix}$i bs=${block_size}k count=$write_count; } 2>&1 | paste -s -d " " | tr "\t" " " | tr -s " " | cut -d ' ' -f -1,11-17 >> $outfile &
done
wait

rm -rf ${data_dir}
