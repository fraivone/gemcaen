1. Install poetry https://python-poetry.org/docs/#osx--linux--bashonwindows-install-instructions
2. Install the project with poetry Install
3. Make sure that ```/pycaenhv/src/pycaenhv/utils/dll_finder.py``` finds the library libcaenhvwrapper.so.6.1. You can download it here https://www.caen.it/download/?filter=CAEN%20HV%20Wrapper%20Library.
4. (Optional) Modify pycaenhv so that the function `check_function_output` in func `init_system` in file `wrappers.py`, gets called with argument `should_raise` True 