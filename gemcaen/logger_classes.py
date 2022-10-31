from prompt_logger import logger as logging
from caen_classes import BaseMainframe,BaseBoard,GemBoard
from threading import Thread
import threading
import pathlib
import time
import json
from deepdiff import DeepDiff
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

colors_mainframe = ["\033[1;46m","\033[1;42m","\033[1;43m", "\033[1;44m","\033[1;45m","\033[1;107m","\033[1;47m","\033[1;100m"]
colors_taken_mainframe = [ 1 for k in range(len(colors_mainframe))]
colors_device = ["\033[1;34m", "\033[1;35m", "\033[1;36m", "\033[1;37m", "\033[1;90m", "\033[1;94m", "\033[1;95m", "\033[1;96m"]
colors_taken_device = [ 1 for k in range(len(colors_device))]
def get_color(colors,book):
    try:
        index = book.index(1)
    except:
        book = [ 1 for k in range(len(colors))]
    index = book.index(1)
    value = colors[index] 
    book[index] = 0
    return value


class MainframeLogger(Thread):  
    def __init__(self,mainframe_cfg,device_cfgs,terminateEvent):
        self.terminateEvent = terminateEvent
        super().__init__(args=(self.terminateEvent))
        self.mainframe_cfg = mainframe_cfg
        self.name = get_color(colors_mainframe,colors_taken_mainframe)+f"Mainframe_{self.mainframe_cfg['CAENHV_BOARD_ADDRESS']}_Thread" + "\033[1;0m"
        self.device_configs = device_cfgs
        self.lock = threading.Lock()
        self.devices = {}

        # with BaseMainframe(self.mainframe_cfg) as mainframe:
        #     self.handle = mainframe.handle
        #     for device_name,device_cfg in self.device_configs.items():
        #         self.devices[device_name] = DeviceLogger(device_name,device_cfg,self.handle,self.lock)
        # print(self.handle)
    
    def run(self):
        with BaseMainframe(self.mainframe_cfg) as mainframe:
            handle = mainframe.handle
            for device_name, device_cfg in self.device_configs.items():
                self.devices[device_name] = DeviceLogger(device_name,device_cfg,handle,self.lock,self.terminateEvent)
                self.devices[device_name].start()
                logging.debug(f"{device_name} logging started")
            for device in self.devices.values():
                device.join()

class DeviceLogger(Thread):
    def __init__(self,device_name,cfg,handle,lock,terminateEvent):
        self.terminateEvent = terminateEvent
        super().__init__(args=(self.terminateEvent))
        self.name = get_color(colors_device,colors_taken_device) + f'{device_name}_Thread' + "\033[1;0m"
        self.handle = handle
        self.cfg = cfg
        self.device_name = device_name
        self.channel_names_map = {} ## Map containing the map from channel number to channel name. Gets filled when the comm is opened
        self.lock = lock
  
    def yieldBoard(self):
        if self.cfg["isGEMDetector"]:
            board = GemBoard(self.cfg["BOARD"],self.handle)
        else:
            board = BaseBoard(self.cfg["BOARD"],self.handle)
        return board
        
    def updateDB(self,data):
        ## Channel name alias, as we want them to appear in the DB
        ## used only if isGEMDetector
        channel_aliases = [
            "G3Bot",
            "G3Top",
            "G2Bot",
            "G2Top",
            "G1Bot",
            "G1Top",
            "Drift"
        ]
        # Instantiate InfluxDB client and connect:
        client = influxdb_client.InfluxDBClient(
            url=self.cfg["influxDB"]["URL"],
            token=self.cfg["influxDB"]["TOKEN"],
            org=self.cfg["influxDB"]["ORG"]
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)

        for ch,values in data.items():
            if type(ch) == int:
                for quantity,value in values.items():
                    if self.cfg["isGEMDetector"]:
                        point = influxdb_client.Point("HV").tag("ChannelName",channel_aliases[ch%7]).field(quantity,value)
                    else:
                        point = influxdb_client.Point("CAEN_Board_Monitor").tag("ChannelName",self.channel_names_map[ch]).field(quantity,value)
                    write_api.write(bucket=self.cfg["influxDB"]["DB_BUCKET"], org=self.cfg["influxDB"]["ORG"], record=point)

    def run(self):
        prev_data = dict()
        last_logged_time = 0
        
        with self.lock:
            board = self.yieldBoard()
            board.set_monitorables(self.cfg["Monitorables"])
            self.channel_names_map = board.channel_names_map
            logging.debug(f"Initialized {self.device_name}'s board. Monitoring {self.cfg['Monitorables']} for channels {self.channel_names_map}")

        while not self.terminateEvent.is_set():
            with self.lock: 
                logging.debug(f"Acquired lock")
                monitored_data = board.log()  
                logging.debug(f"Fetched data")
                logging.debug(f"Released lock")
            ## if there are no changes in the monitored data AND last DB update was done less than 5 mins ago
            if DeepDiff(monitored_data, prev_data, verbose_level=2, exclude_paths=["root['time']"]) == {} and monitored_data['time'] - last_logged_time < 5 * 60:
                pass
            else:
                try:
                    self.updateDB(monitored_data)
                    logging.info(f"Updated DB")
                    prev_data = monitored_data
                    last_logged_time = monitored_data['time']
                except Exception as a: 
                    logging.warning(f"Exception {a} caught while updating DB Retrying...skipping")


            time.sleep(self.cfg["HoldOffTime"])

if __name__=='__main__':
    pass
