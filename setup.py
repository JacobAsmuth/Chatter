from cx_Freeze import setup, Executable

build_exe_options = {}

setup(  name = "client",
        version = "0.1",
        description = "client",
        options = {"build_exe": build_exe_options},
        executables = [Executable("client_startup.py")])