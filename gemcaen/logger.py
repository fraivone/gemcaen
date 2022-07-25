from gemcaen import BoardBase,GemBoard
from datetime import datetime
import pathlib
import json
import math
import time


class BaseLogger:
    __outdir = pathlib.Path(__file__).parent / "data"
  
    def __init__(self,*,setup_name:str,rate:int=2,monitored_quantities:list):
        self.setup_name = setup_name
        self.outfile = __outdir / "log_"+self.setup_name+".log"
        
        self.rate = rate
        self.monitored_quantities = None
  
    def set_monitored_quantities(self,monitored_quantities:list):
        self.monitored_quantities = monitored_quantities
    
    def store_dict(self,data_dict:dict,maxsize=3): ## stores log file, keeping size < maxsize MB
        size = os.path.getsize("/home/francesco/Summary_OH0.png")
        if round(size / 1024**2,2) > maxsize: ## 3 MB per log file
            now = datetime.now()
            year, month, day, hour, minute = now.year, now.month, now.day, now.hour, now.minute
            os.rename(self.outfile, __outdir / "{year}{month}{day}_{hour}{minute}_{self.setup_name}.log")

        with open(self.outfile, 'w') as f:
            f.write(data_dict)

    def run(self):
        while True:
            with BaseBoard(self.setup_name) as board:
                board.set_monitorables(self.monitored_quantities)
                monitored_data = board.monitor()
                self.store_dict(monitored_data)
            print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Stored data")
            time.sleep(self.rate)
