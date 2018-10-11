#!/bin/bash -e
if [ "$#" -ne 1 ]; then
    echo "Usage: stop.sh [robot-id]"
    exit
fi
sshpass -p 'passincleartextnoway' ssh drop@192.168.0.9$1 "echo 'stop' > /dropzone/stop"
echo "Thank you, come again!"
