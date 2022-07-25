from gemcaen import BoardBase,GemBoard
from datetime import datetime
import pathlib
import json
import math
import time
import os

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
        json.dump( data_dict, open( self.outfile, 'a+' ) )

        size = os.path.getsize(self.outfile)
        if round(size / 1024**2,2) > maxsize: ## 3 MB per log file
            now = datetime.now()
            year, month, day, hour, minute = now.year, now.month, now.day, now.hour, now.minute
            os.rename(self.outfile, __outdir / "{year}{month}{day}_{hour}{minute}_{self.setup_name}.log")

    def log(self):

        with BoardBase(self.setup_name) as board:
            if self.update_board_quantities: board.set_monitorables(self.monitored_quantities)
            while True:
                monitored_data = board.monitor()
                self.store_dict(monitored_data)
                print(f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Stored data")
                time.sleep(self.rate)



b = BaseLogger("IntegrationStand")
b.log()