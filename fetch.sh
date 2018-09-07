#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Usage: fetch.sh [robot-id] [uni-id]"
    exit
fi
echo "Cloning your repository..."
git clone https://$2@gitlab.cs.ttu.ee/$2/iti0201-2018.git student
echo "Copying your output from the robot..."
sshpass -p 'iomgomoeirjgeorigj' scp drop@192.168.0.9$1:/dropzone/output.txt .
TIMESTAMP=$(date +%s)
rm -rf student/logs
mkdir student/logs
mv output.txt student/logs/$TIMESTAMP.txt
cd student
git add logs/$TIMESTAMP.txt
git config user.email "robottester@ttu.ee"
git config user.name "Robot Tester"
git commit -m "Output from robot test run @ $TIMESTAMP"
echo "Pushing the log file to your repository..."
git push origin master
echo "Removing your files..."
cd ..
rm -rf student/
