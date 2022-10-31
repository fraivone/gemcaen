Communication tool for CAEN boards installed in mainframes SY1527,SY2527 and SY4527. Triple-GEM specific options are available.
Allows the monitoring and logging of the available channel quantities (i.e VMon, IMon, Temp, ...) and their storage on influxDB. 
We use it to log our lab setups and display the status plots with Grafana.
---
### Installation
#### Tools you need
1. A poetry installation. Instructions [here](https://python-poetry.org/docs/#osx--linux--bashonwindows-install-instructions);
1. Caen HV library `libcaenhvwrapper.so.6.1`. You can download the library [here](https://www.caen.it/download/?filter=CAEN%20HV%20Wrapper%20);
1. `python 3.6.1` or newer;
1. Patience, either the [old version](https://www.youtube.com/watch?v=ErvgV4P6Fzc) or a [more recent one](https://www.youtube.com/watch?v=ErvgV4P6Fzc);
#### Installation
1. `git clone git@github.com:fraivone/gemcaen.git`;
1. `cd gemcaen/`;
1. Install the project execute with ``poetry install``;                                                                      
1. If the installation succeeds, the package pycaenhv will be installed. But it needs to be tweaked:
   * Make sure that ```./pycaenhv/src/pycaenhv/utils/dll_finder.py``` finds the library `libcaenhvwrapper.so.6.1` previously downloaded. You'll have to edit `dll_finder.py` manually;
   *  Edit pycaenhv so that the function `check_function_output` in the function `init_system` in file `wrappers.py`, gets called with argument `should_raise = True`. Additionally change the line ``err_msg = Errors[command_output]`` into ``err_msg = Errors[abs(command_output)]``;
### How to run it
1. Prepare the config file, based on the template in the folder `config`;
2. Execute `poetry shell`;
3. To start logging the setups in `config.yml` execute: 
```
python main.py <setup_name1 from config.yml> <setup_name2 from config.yml> <setup_name3 from config.yml> 
```
### How it works
##### caen_classes
Base classes that handle the communication with the board:
* `BaseMainframe` handles the communication to the mainframe within a context manager;
* `BaseBoard` if provided with the mainframe connection, can communicate with a CAEN boardf in both direction;

##### logger_classes
Base classes that take care of the continuous monitoring and logging of the setups. They are childs of `threading.Thread`. 
* `MainframeLogger` simple child class of `threading.Thread` with re-written run method. Gets as input:
    1. A the configuration file for the mainframe connection;
    2. A list of device configuration for the boards connected to the mainframe;
    3. A `threading.Event` that signals the termination of the process;
    
    When ran:
    1. Opens a connection to the mainframe in a context manager;
    2. Acquires the handle for the connection;
    3. Initializes and starts the `DeviceLogger` classes;
    
    To avoid simultaneous mainframe calls, the `DeviceLogger`s are provided with a lock that allows no more than one communication at time a time to a given mainframe. `MainframeLogger` passes the `threading.Event` that signals the termination of the process to the `DeviceLogger`a and waits till their termination.
    It terminates when all the `DeviceLogger`s return and it exits the context manager closing the connection to the mainframe.
* `DeviceLogger`  simple child class of `threading.Thread` with re-written run method. Gets as input:
    1. The name of the device to be logged, so that the `Thread` is named properly;
    2. The device configuration (board, DB, monitorables, ...);
    3. The mainframe lock;
    4. The `threading.Event` that signals termination.
    
    When started it loops forever till the `threading.Event` termination. In loop:
    1. Acquires the mainframe lock;
    1. Fetches data;
    1. Publishes data to the DB if new_data != old_data or more than 5 mins have passed since last DB push.

##### config_parser.py
Contains helper functions to parse and organize the configuration file.
1. Loads the `config.yml` file and checks its format;
2. Groups the setups by mainframe. The idea is to keep one mainframe connection open and fetch data for the connected boards in turn.

##### prompt_logger.py
Contains the configuration for the module `logging`. The lines showed on the stdout come from this module. The same lines are normally stored under `./logs/debug.log`. 
The logging level is set to `INFO`. Detailed information can be accessed by setting it to `DEBUG`.

##### main
Basic script that takes that calls the others. 
Upon `KeyboardInterrupt` it turns the `threading.Event` true, so that the logging classes terminate.

##### config/config.yml
Contains the configuration parameters for the setups in yaml format.

### Pending
1. In `BaseMainframe`, the exceptions `pycaenhv.errors.CAENHVError` are handled. However, being the connection broken, the `BaseBoard` will raise `Invalid Mainframe handle` when monitor() gets called. Has to be verified.
1. `BaseBoard` does not catch  `handle = None` for other methods (i.e set_Ieq, print_board_status, ...). To be implemented
1. Conflicts with other devices connected to the same mainframe (i.e. "lab DCS") may cause crashes. To be checked.
1. The connection to the mainframe gets always closed when the program terminates. There should be no "zombie" connections left. To be checked.
### Future
In case of deep inspiration, code a webpage that allows to set the channel values.
