#!/bin/bash
if [ "$#" -ne 3 ]; then
    echo "Usage: load.sh [robot-id] [task-id] [uni-id]"
    exit
fi
rm -rf student/
echo "Cloning your repository..."
git clone https://$3@gitlab.cs.ttu.ee/$3/iti0201-2018.git student
echo "Copying your files to the robot..."
sshpass -p 'plaintextparoolrukiddingme???' scp student/$2/robot.py drop@192.168.0.9$1:/dropzone
echo "Removing your files..."
rm -rf student/
echo "Thank you, come again!"
