#!/usr/bin/python3

import os
import sys
import socket
import paramiko
import getpass
import pygit2
import shutil


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

        self.connect(94)
        files = self.get_source_files("S")
        #print(files)

    def copy(self):
        sftp = paramiko.SFTPClient.from_transport(self.transport[94])
        print(sftp.listdir("."))
        #sftp.put("myfile", "robot/myfile")

    def command(self):
        chan = self.transport[94].open_session()
        res = chan.exec_command("sleep 10")

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
            return False
        print("Authenticating...")
        self.transport[host].auth_publickey("loader", self.key)
        if self.transport[host].is_authenticated():
            print("Success!")
            return True
        else:
            print("Authentication failed!")
            self.transport[host].close()
        return False

    def copy_file():
        pass

def main():
    path = os.getcwd() + "/student/"
    try:
        shutil.rmtree(path)
    except:
        pass
    password = getpass.getpass("Enter password: ")
    userpass = pygit2.UserPass("robobot", password)
    callbacks = pygit2.RemoteCallbacks(credentials=userpass)
    pygit2.clone_repository("https://gitlab.cs.ttu.ee/gert.kanter/iti0201-2019", "student", callbacks=callbacks)
    loader = Loader(password)

if __name__ == "__main__":
    main()
