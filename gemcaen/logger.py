from gemcaen import BaseBoard,GemBoard
from datetime import datetime
import pathlib
import json
import math
import time
import os
from deepdiff import DeepDiff
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

class BaseLogger:
    __outdir = pathlib.Path(__file__).parent / "logs"
  
    def __init__(self,setup_name,rate=2,monitored_quantities=list()):
        self.setup_name = setup_name
        self.outfile = self.__outdir / str("log_"+self.setup_name+".log")
        
        self.rate = rate
        self.monitored_quantities = monitored_quantities
        self.update_board_quantities = False
  
    def set_monitored_quantities(self,monitored_quantities:list):
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
            os.rename(self.outfile, __outdir / "{year}{month}{day}_{hour}{minute}_{self.setup_name}.log")

    def yieldBoard(self):
        yield  BaseBoard(self.setup_name)
        
    def updateDB(self,data):
        channel_names = [
            "G3Bot",
            "G3Top",
            "G2Bot",
            "G2Top",
            "G1Bot",
            "G1Top",
            "Drift"
        ]

        influx_config = dict(
            bucket = "GEM 904 integration stand",
            org = "CMS GEM project",
            token = "mDg5QyXVh3DxQcxdFtEqnPDwaiq4N_Vt5TLqJCx2c2nsl1Kuyhj8wiF0agLWgvkLsDevjBXpuDKUR1Zyms5DsA==",
            url = "http://gem904bigscreens:8086"
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
                    point = influxdb_client.Point(self.setup_name).tag("ChannelName",channel_names[ch%7]).field(quantity,value)
                    write_api.write(bucket=influx_config["bucket"], org=influx_config["org"], record=point)

    def log(self):
        prev_data = dict()
        with BaseBoard(self.setup_name) as board:
            if self.update_board_quantities: board.set_monitorables(self.monitored_quantities)
            while True:
                time.sleep(self.rate)
                monitored_data = board.log()
                if DeepDiff(monitored_data, prev_data, verbose_level=2, exclude_paths=["root['time']"]) == {}:
                    print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] No changes for setup {self.setup_name}")
                    continue
                self.store_dict(monitored_data)
                print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Stored data for setup {self.setup_name}")
                prev_data = monitored_data
        

class GemLogger(BaseLogger):
    
    def __init__(self,setup_name,gem_layer=None):
        super().__init__(setup_name) ## init parent class
        self.gem_layer = gem_layer
    
    def log(self):
        prev_data = dict()
        with GemBoard(self.setup_name,self.gem_layer) as board:
            if self.update_board_quantities: board.set_monitorables(self.monitored_quantities)
            while True:
                time.sleep(self.rate)
                monitored_data = board.log()
                if DeepDiff(monitored_data, prev_data, verbose_level=2, exclude_paths=["root['time']"]) == {}:
                    print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] No changes for setup {self.setup_name}")
                    continue
                self.store_dict(monitored_data)
                print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Stored data for setup {self.setup_name}")
                self.updateDB(monitored_data)
                print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Updated DB for setup {self.setup_name}")
                prev_data = monitored_data


if __name__ == '__main__':


    b = GemLogger("IntegrationStand",1)
    b.log()
