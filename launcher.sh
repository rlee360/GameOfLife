#!/bin/bash
# $1 - hostfile
if [[ $# -eq 0 ]]; then
	HELP_RAW=$(./game_of_life.py -h 2>&1 | head -n 1)
	HELP="${HELP_RAW//"game_of_life.py"/"$0"" HOSTFILE_PATH"}"
	echo $HELP
	./game_of_life.py -h 2>&1 | tail -n +2
	exit 1
fi
for host in $(awk '{print $1}' $1); do
	if [[ $host != "localhost" && $host != "127.0.0.1" ]]; then
		echo $host
		scp game_of_life.py $host:`pwd`
	fi
done
ARGS=("$@")
THREADS=$(awk '{SUM+=$2}END{print SUM}' $1)
python -m scoop --hostfile $1 --tunnel game_of_life.py ${ARGS[@]:1} -t $THREADS
