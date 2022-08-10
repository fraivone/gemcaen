from gemcaen import BaseBoard,GemBoard
from datetime import datetime
import pathlib
import json
import math
import time
import os
from deepdiff import DeepDiff

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
                prev_data = monitored_data


if __name__ == '__main__':


    b = GemLogger("IntegrationStand",2)
    b.log()