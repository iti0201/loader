#!/usr/bin/python3

import os
import sys
import socket
import paramiko
import getpass
import pygit2
import shutil
import time


class Loader:
    def __init__(self, password):
        self.host_keys = paramiko.util.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))
        self.userpass = pygit2.UserPass("robobot", password)
        self.callbacks = pygit2.RemoteCallbacks(credentials=self.userpass)
        try:
            self.key = paramiko.RSAKey.from_private_key_file(os.path.join(os.environ["HOME"], ".ssh", "id_rsa"), password)
        except paramiko.ssh_exception.SSHException as e:
            print("Wrong password!")
            sys.exit(-1)
        self.sock = {"91": None, "92": None, "93": None, "94": None, "95": None} 
        self.transport = {}
        for sock in self.sock:
            self.sock[sock] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def ssh_command(self, host, command, retry=False):
        print("Sending command to host({})...".format(host))
        try:
            chan = self.transport[host].open_session()
            print("Session opened!")
            print("Executing command {}".format(command))
            chan.exec_command(command) 
            return True
        except Exception as e:
            print("Unable to send command ({}), retry to connect!".format(e))
            self.connect(host)
            if not retry:
                return self.ssh_command(host, command, True)
            else:
                return False

    def get_source_files(self, task_id):
        path = os.getcwd() + "/student/" + task_id + "/"
        source_files = []
        if os.path.exists(path):
                for root, dirs, files in os.walk(path, topdown = False):
                    for name in files:
                        source_files.append(str(os.path.join(root, name)))
        else:
            print("Path not found ({})".format(path))
        return source_files
            
    def connect(self, host):
        delay = 0.5
        try:
            print("Connecting to {}...".format(host)) 
            hostname = "192.168.0." + host
            self.sock[host].connect((hostname, 22))
            print("Connected to {}!".format(host))
            self.transport[host] = paramiko.Transport(self.sock[host])
            try:
                self.transport[host].start_client()
            except paramiko.SSHException:
                print("SSH negotiation failed!")
                time.sleep(delay)
                return False
            print("Checking server key...")
            key = self.transport[host].get_remote_server_key()
            if hostname not in self.host_keys:
                #print("WARNING: Unknown host key!")
                pass
            elif key.get_name() not in self.host_keys[hostname]:
                #print("WARNING: Unknown host key!")
                pass
            elif self.host_keys[hostname][key.get_name()] != key:
                print("WARNING: Host key has changed!!!")
            else:
                print("Host key OK.")
        except Exception as e:
            print("Failed to connect to {} ({})!".format(host, e))
            time.sleep(delay)
            return False
        print("Authenticating...")
        self.transport[host].auth_publickey("loader", self.key)
        if self.transport[host].is_authenticated():
            print("Success!")
            return True
        else:
            print("Authentication failed!")
            self.transport[host].close()
        time.sleep(delay)
        return False

    def upload_file(self, host, filename, retry=False):
        print("upload_file({}, {})".format(host, filename))
        try:
            sftp = paramiko.SFTPClient.from_transport(self.transport[host])
            #print(sftp.listdir("."))
            name = filename.split("/")[-1]
            sftp.put(filename, "test/" + name)
        except Exception as e:
            print("Unable to upload file ({}), retry to connect!".format(e))
            self.connect(host)
            if not retry:
                return self.upload_file(host, filename, True)
            else:
                return False
        return True

    def clone_repository(self, uni_id):
        path = os.getcwd() + "/student/"
        try:
            shutil.rmtree(path)
        except:
            pass
        try:
            pygit2.clone_repository("https://gitlab.cs.ttu.ee/" + uni_id + "/iti0201-2019", "student", callbacks=self.callbacks)
        except:
            print("Unable to clone repository!")
            return False
        return True

    def prepare_filesystem(self, robot_id):
        print("prepare_filesystem({})".format(robot_id))
        if not self.ssh_command("9" + robot_id, "rm -rf test && cp -r robot test"):
            return False
        return True

    def execute(self, robot_id):
        print("execute({})".format(robot_id))
        if self.kill(robot_id):
            if self.ssh_command("9" + robot_id, "cd test && ROBOT_ID=" + robot_id + " timeout 300 python3 robot.py"):
                return True
        return False

    def kill(self, robot_id):
        print("kill({})".format(robot_id))
        if self.ssh_command("9" + robot_id, "pkill python3"):
            return True
        return False

    def load(self, uni_id, robot_id, task_id):
        print("load({}, {}, {})".format(uni_id, robot_id, task_id))
        # Clone student repository
        if self.clone_repository(uni_id):
            # Get source files
            files = self.get_source_files(task_id)
            # Prepare directory at robot
            if self.prepare_filesystem(robot_id):
                if len(files) > 0:
                    # Upload
                    success = True
                    for filename in files:
                        if not self.upload_file("9" + robot_id, filename):
                            print("Unable to upload file '{}'!".format(filename))
                            success = False
                            break
                    if success:
                        # Execute robot.py with redirected output
                        self.execute(robot_id)
                else:
                    print("Unable to get source files!")
            else:
                print("Unable to prepare filesystem!")
        else:
            print("Unable to clone student repository ({})!".format(uni_id))

    def fetch(self, uni_id, robot_id):
        print("fetch({}, {})".format(uni_id, robot_id))
        # Clone student repository
        # Get output.txt
        # Rename based on timestamp
        # Move timestamped file to "logs" directory
        # Add log to git commit
        # Push commit

    def stop(self, robot_id):
        print("stop({})".format(robot_id))
        # Execute kill python3 && stop.py

def main():
    password = getpass.getpass("Enter password: ")
    loader = Loader(password)
    command = "l"
    uni_id = ""
    robot_id = "1"
    task_id = "L1"
    while command != "q":
        try:
            candidate = input("Command (l=load, f=fetch, s=stop) [{}]:".format(command))
            if candidate == "":
                candidate = command
            if candidate in ["l", "q", "f", "s"]:
                command = candidate
                if command == "q":
                    sys.exit(0)
                candidate = "0"
                while len(candidate) > 1 or not candidate.isnumeric() or int(candidate) > 5 or int(candidate) < 1:
                    candidate = input("Robot ID [{}]:".format(robot_id))
                    if candidate == "":
                        candidate = robot_id
                if candidate != "":
                    robot_id = candidate
                if command != "s":
                    uni_id = ""
                    while uni_id == "":
                        uni_id = input("UNI-ID: ")
                    if command == "l":
                        candidate = "bla"
                        while len(candidate) != 2 or candidate[0] not in ["L", "O", "M"]:
                            candidate = input("Task ID [{}]: ".format(task_id))
                            if candidate == "":
                                candidate = task_id
                        task_id = candidate
                while True:
                    candidate = input("command={}  uni_id={}  robot_id={}  task_id={} - [Y/n]?".format(command, uni_id, robot_id, task_id))
                    if candidate in ["", "y", "Y", "n", "N"]:
                        if candidate == "":
                            candidate = "y"
                        break
                if candidate in ["y", "Y"]:
                    if command == "l":
                        loader.load(uni_id, robot_id, task_id)
                    elif command == "f":
                        loader.fetch(uni_id, robot_id)
                    else:
                        loader.stop(robot_id)
        except KeyboardInterrupt as e:
            print()
            continue


if __name__ == "__main__":
    main()
