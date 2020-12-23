from server.server import Server
import shared.consts as consts
from server.audio_mixers.array_mixer import ArrayMixer

import subprocess
import os
import inspect
import multiprocessing
import threading
import time
import sys

def install_new_packages():
    subprocess.run(["python", '-m', "pip", "install", '-r', "requirements.txt"], capture_output=True)

def restart_program():
    os.execv(sys.executable, ['python'] + sys.argv)

# According to the documentation the 'git' library shouldn't be used in long-running programs due to memory leaks,
#   so we run it in a seperate process I guess.
def do_git_pull(cwd: str, did_pull: multiprocessing.Value):
    import git
    repo = git.Repo(cwd)
    old_head = repo.head.commit.hexsha
    new_head = repo.remote('origin').pull('master')[0].commit.hexsha
    did_pull.value = old_head != new_head  # 1 if different, 0 if same

def update_if_possible(server: Server) -> bool:
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    cwd = os.path.dirname(os.path.realpath(filename))
    while True:
        did_pull = multiprocessing.Value('b', 0)
        proc = multiprocessing.Process(target=do_git_pull, args=(cwd, did_pull,))
        proc.start()
        proc.join()
        if did_pull.value == 1:
            server.restarting()
            print("Found new update, restarting!")
            install_new_packages()
            restart_program()
        time.sleep(consts.GIT_UPDATE_CHECK_FREQUENCY)

def main():
    server = Server(ArrayMixer())
    try:
        server.setup_voice(consts.VOICE_PORT)
        server.setup_data(consts.DATA_PORT)
        server.listen()

        threading.Thread(target=update_if_possible, args=(server,), daemon=True).start()

        server.wait_for_commands()

    except Exception as e:
        print("Couldn't bind to port: " + str(e))
    except SystemExit:
        pass

        
if __name__ == "__main__":
    main()