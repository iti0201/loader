#!/bin/bash -e
if [ "$#" -ne 1 ]; then
    echo "Usage: output.sh [robot-id]"
    exit
fi
sshpass -p 'passincleartextnoway' ssh drop@192.168.0.9$1 "tail -f /home/pi/output.txt"
