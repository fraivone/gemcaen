from gemcaen import BaseBoard,GemBoard
from threading import Thread
from datetime import datetime
import pathlib
import json
import math
import time
import os
from deepdiff import DeepDiff
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

class BaseLogger(Thread):
    __outdir = pathlib.Path(__file__).parent / "logs"
  
    def __init__(self,setup_name,cfg_HW,cfg_DB,isGEMDetector,rate=5):
        super().__init__()
        self.setup_name = setup_name
        self.outfile = self.__outdir / str("log_"+self.setup_name+".log")        
        self.cfg_HW = cfg_HW
        self.cfg_DB = cfg_DB      
        self.isGEMDetector = isGEMDetector
        self.rate = rate
        self.monitored_quantities = []
        self.update_board_quantities = False
  
    def set_monitored_quantities(self,monitored_quantities:list):
        ## TODO
        # Check that the actual quantities are parsed to the gemboard class
        # Implement a similar system for set_channels
        self.monitored_quantities = monitored_quantities
        self.update_board_quantities = True
    
    def store_dict(self,data_dict:dict,maxsize=3): ## stores log file, keeping size < maxsize MB            
        with open(self.outfile, "a+") as o:
            json.dump( data_dict, o )
            o.write('\n') 

        size = os.path.getsize(self.outfile)
        if round(size / 1024**2,2) > maxsize: ## 3 MB per log file
            now = datetime.now()
            year, month, day, hour, minute = now.year, now.month, now.day, now.hour, now.minute
            os.rename(self.outfile, self.__outdir / f"{year}{month}{day}_{hour}{minute}_{self.setup_name}.log")

    def yieldBoard(self):
        if self.isGEMDetector:
            return GemBoard(self.cfg_HW)
        else:
            return BaseBoard(self.cfg_HW)
        
    def updateDB(self,data):
        ## TODO
        # hot fix to make it work for GEM electrodes. To be taken from the board class
        channel_aliases = [
            "G3Bot",
            "G3Top",
            "G2Bot",
            "G2Top",
            "G1Bot",
            "G1Top",
            "Drift"
        ]

        influx_config = dict(
            bucket = self.cfg_DB["DB_BUCKET"],
            org = self.cfg_DB["ORG"],
            token = self.cfg_DB["TOKEN"],
            url = self.cfg_DB["URL"]
        )

        # Instantiate InfluxDB client and connect:
        client = influxdb_client.InfluxDBClient(
            url=influx_config["url"],
            token=influx_config["token"],
            org=influx_config["org"]
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)

        for ch,values in data.items():
            if type(ch) == int:
                for quantity,value in values.items():
                    point = influxdb_client.Point("HV").tag("ChannelName",channel_aliases[ch%7]).field(quantity,value)
                    write_api.write(bucket=influx_config["bucket"], org=influx_config["org"], record=point)

    def run(self):
        prev_data = dict()
        with self.yieldBoard() as board:
            if self.update_board_quantities: board.set_monitorables(self.monitored_quantities)
            while True:
                time.sleep(self.rate)
                monitored_data = board.log()
                ## Check if data are different wrt the previous reading
                if DeepDiff(monitored_data, prev_data, verbose_level=2, exclude_paths=["root['time']"]) == {}:
                    print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] No changes for setup {self.setup_name}")
                    continue

                self.store_dict(monitored_data)
                print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Stored data for setup {self.setup_name}")
                self.updateDB(monitored_data)
                print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Updated DB for setup {self.setup_name}")
                prev_data = monitored_data
