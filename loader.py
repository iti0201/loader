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
        try:
            self.key = paramiko.RSAKey.from_private_key_file(os.path.join(os.environ["HOME"], ".ssh", "id_rsa"), password)
        except paramiko.ssh_exception.SSHException as e:
            print("Wrong password!")
            sys.exit(-1)
        self.sock = {91: None, 92: None, 93: None, 94: None, 95: None} 
        self.transport = {}
        for sock in self.sock:
            self.sock[sock] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def ssh_command(self, host, command):
        print("Sending command to host({})...".format(host))
        try:
            chan = self.transport[host].open_session()
            res = chan.exec_command(command) 
        except Exception as e:
            print("Unable to open session, retry to connect!")
            self.ssh_command(host, command)

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
            hostname = "192.168.0."+str(host)
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
            print("Failed to connect to {}!".format(host))
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

    def upload_file(self, host, filename):
        try:
            sftp = paramiko.SFTPClient.from_transport(self.transport[host])
            #print(sftp.listdir("."))
            sftp.put(filename, "robot/" + filename)
        except Exception as e:
            print("Unable to open session, retry to connect!")
            self.upload_file(host, filename)

    def clone_repository(self, uni_id):
        path = os.getcwd() + "/student/"
        try:
            shutil.rmtree(path)
        except:
            pass
        try:
            userpass = pygit2.UserPass("robot", self.password)
            callbacks = pygit2.RemoteCallbacks(credentials=userpass)
            pygit2.clone_repository("https://gitlab.cs.ttu.ee/" + uni_id + "/iti0201-2019", "student", callbacks=callbacks)
        except:
            print("Unable to clone repository!")
            return False
        return True

    def load(self, uni_id, robot_id, task_id):
        print("load({}, {}, {})".format(uni_id, robot_id, task_id))

    def fetch(self, uni_id, robot_id):
        print("fetch({}, {})".format(uni_id, robot_id))

def main():
    password = getpass.getpass("Enter password: ")
    loader = Loader(password)
    command = "l"
    robot_id = "1"
    task_id = "L1"
    while command != "q":
        try:
            candidate = input("Command (l=load, f=fetch) [{}]:".format(command))
            if candidate == "":
                candidate = command
            if candidate in ["l", "q", "f"]:
                command = candidate
                if command == "q":
                    sys.exit(0)
                uni_id = ""
                while uni_id == "":
                    uni_id = input("UNI-ID: ")
                one_shot = True
                while one_shot or len(candidate) > 1:
                    one_shot = False
                    candidate = input("Robot ID [{}]:".format(robot_id))
                if candidate != "":
                    robot_id = candidate
                if command == "l":
                    one_shot = True
                    while one_shot or len(candidate) != 2 or candidate[0] not in ["L", "O", "M"]:
                        one_shot = False
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
                    else:
                        loader.fetch(uni_id, robot_id)
        except KeyboardInterrupt as e:
            continue
    # Test commands
    #loader.ssh_command(94, "ls")
    #loader.connect(94)
    #files = loader.get_source_files("S")
    #print(files)

if __name__ == "__main__":
    main()
