#!/usr/bin/python3

import os
import sys
import socket
import paramiko
import getpass
import pygit2
import shutil
import time
import threading


class Access:
    def __init__(self, access):
        self.repository_name = "groups"
        self.access = access
        self.run = True
        self.thread = threading.Thread(target=self.worker)
        self.thread.start()

    def remove_repository(self):
        path = os.getcwd() + "/" + self.repository_name + "/"
        try:
            shutil.rmtree(path)
        except:
            pass

    def worker(self):
        last_update = 0
        while self.run:
            now = time.time()
            if last_update + 10.0 < now:
                self.get_access_list()
                self.remove_repository()
                last_update = now
            time.sleep(0.1)

    def get_access_list(self):
        self.remove_repository()
        try:
            repository = pygit2.clone_repository("https://github.com/iti0201/" + self.repository_name, self.repository_name)
        except Exception as e:
            print("Unable to clone access repository ({})!".format(e))
            return
        try:
            with open(os.getcwd() + "/" + self.repository_name + "/" + self.repository_name + ".txt") as f:
                data = f.readlines()
                for row in data:
                    tokens = row.replace("\n", "").split(";")
                    if len(tokens) > 1 and len(tokens[0]) >= 6:
                        self.access[tokens[0]] = tokens[1:]
        except:
            print("Unable to read groups.txt!")
            return



class Loader:
    def __init__(self, password, session):
        self.host_keys = paramiko.util.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))
        self.userpass = pygit2.UserPass("robobot", password)
        self.callbacks = pygit2.RemoteCallbacks(credentials=self.userpass)
        self.callbacks.push_update_reference = self.push_update_ref
        self.access = {}
        self.session = session
        if self.session is not None:
            self.updater = Access(self.access)
        try:
            self.key = paramiko.RSAKey.from_private_key_file(os.path.join(os.environ["HOME"], ".ssh", "id_rsa"), password)
        except paramiko.ssh_exception.SSHException as e:
            print("Wrong password!")
            sys.exit(-1)
        self.sock = {"91": None, "92": None, "93": None, "94": None, "95": None} 
        self.transport = {}
    def push_update_ref(self, refname, message):
        if message is not None:
            print("FAILED TO PUSH LOG TO REPOSITORY!")
            print("MAKE SURE YOUR GITLAB iti0201-2019 repository settings are correct ('Settings -> Repository -> Protected Branches -> Allowed to push' = Developers + Maintainers)")

    def ssh_command(self, host, command, retry=False):
        print("Sending command to host({})...".format(host))
        try:
            chan = self.transport[host].open_session()
            print("Session opened!")
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
                        if ".py" in name:
                            source_files.append(str(os.path.join(root, name)))
        else:
            print("Path not found ({})".format(path))
        return source_files
            
    def connect(self, host):
        delay = 0.5
        try:
            print("Connecting to {}...".format(host)) 
            hostname = "192.168.0." + host
            self.sock[host] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

    def sftp_file(self, host, filename, command, retry=False):
        print("sftp_file({}, {})".format(host, filename))
        try:
            sftp = paramiko.SFTPClient.from_transport(self.transport[host])
            if command == "put":
                name = filename.split("/")[-1]
                sftp.put(filename, "test/" + name)
            else:
                sftp.get("test/" + filename, filename)
        except Exception as e:
            print("Unable to SFTP file ({}), retry to connect!".format(e))
            self.connect(host)
            if not retry:
                return self.sftp_file(host, filename, command, True)
            else:
                return False
        return True

    def remove_student_repository(self):
        path = os.getcwd() + "/student/"
        try:
            shutil.rmtree(path)
        except:
            pass

    def clone_repository(self, uni_id):
        self.remove_student_repository()
        try:
            self.repository = pygit2.clone_repository("https://gitlab.cs.ttu.ee/" + uni_id + "/iti0201-2022", "student", callbacks=self.callbacks)
            self.repository.init_submodules()
            self.repository.update_submodules(callbacks=self.callbacks)
        except Exception as e:
            print("Unable to clone repository ({})!".format(e))
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
            if self.ssh_command("9" + robot_id, "cd test && ROBOT_ID=" + robot_id + " timeout 300 python3 -u robot.py > output.txt 2>&1"):
                return True
        return False

    def kill(self, robot_id):
        print("kill({})".format(robot_id))
        if self.ssh_command("9" + robot_id, "pkill python3"):
            return True
        return False

    def load(self, uni_id, robot_id, task_id):
        print("load({}, {}, {})".format(uni_id, robot_id, task_id))
        if self.session is not None:
            # Check if in access list
            if len(self.access) > 0:
                student_access = self.access.get(uni_id, [self.session])
                if self.session not in student_access:
                    print("This student is not registered to this lab time! Your lab time is {}!".format(",".join(student_access)))
                    print("An exception can be added if you ask Gert or the assistants.")
                    return
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
                        if not self.sftp_file("9" + robot_id, filename, "put"):
                            print("Unable to upload file '{}'!".format(filename))
                            success = False
                            break
                    if success:
                        # Remove local files
                        self.remove_student_repository()
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
        if self.clone_repository(uni_id):
            # Get output.txt
            if self.sftp_file("9" + robot_id, "output.txt", "get"):
                # Remove log directory from repository
                path = os.getcwd() + "/student/logs"
                try:
                    shutil.rmtree(path)
                except:
                    pass
                os.mkdir("student/logs") 
                # Rename based on timestamp
                filename = str(int(time.time())) + ".txt"
                relpath = "student/logs/" + filename
                os.rename("output.txt", relpath)
                # Add log to git commit
                s = pygit2.Signature('Roboproge Logmaster', 'deal@with.it')
                file_contents = ""
                with open(relpath) as f:
                    for line in f.readlines():
                        file_contents += line
                contents = self.repository.create_blob(file_contents)
                self.repository.index.add(pygit2.IndexEntry("logs/" + filename, contents, pygit2.GIT_FILEMODE_BLOB))
                self.repository.index.write()
                tree = self.repository.index.write_tree()
                master = self.repository.lookup_branch("master")
                self.repository.create_commit('refs/heads/master',s,s,'Log upload', tree,[master.target])
                # Push commit
                self.repository.remotes["origin"].push(["refs/heads/master"], callbacks=self.callbacks)
                # Remove repository
                self.remove_student_repository()
            else:
                print("Unable to download output file!")
        else:
            print("Unable to clone repository!")

    def stop(self, robot_id):
        print("stop({})".format(robot_id))
        self.kill(robot_id)
        time.sleep(1)
        if self.ssh_command("9" + robot_id, "cd robot && ROBOT_ID=" + robot_id + " python3 stop.py"):
            return True
        return False

def main():
    session = None
    if len(sys.argv) == 2 and len(sys.argv[1]) == 3:
        session = sys.argv[1]
    password = getpass.getpass("Enter password: ")
    loader = Loader(password, session)
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
                    loader.remove_student_repository()
                    if loader.session is not None:
                        loader.updater.run = False
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
                if command == "l":
                    loader.load(uni_id, robot_id, task_id)
                elif command == "f":
                    loader.fetch(uni_id, robot_id)
                else:
                    loader.stop(robot_id)
        except (KeyboardInterrupt, EOFError) as e:
            print()
            continue

if __name__ == "__main__":
    main()
