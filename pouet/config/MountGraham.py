import requests
import numpy as np
import re
import os
import sys, inspect

sys.path.insert(0, '../pouet')
import util

import logging
logger = logging.getLogger(__name__)

class WeatherReport():
    """
    This class is dedicated to recovering the weather report at the Mount Graham site and feeding the
    wind direction, wind speed, temperature and humidity back to pouet.
    It must contain at least a `get` method that returns the above variable.
    """
    
    def __init__(self, name='MountGraham'):
        """
        Class constructor. Loads the MountGraham.cfg configuration file and saves it as attribute.
        
        :param name: name of the cfg file, only included for completeness.
        """

        self.config = util.readconfig(os.path.join(os.path.dirname(os.path.abspath(inspect.stack()[0][1])), "{}.cfg".format(name)))
        
    def get(self, debugmode, FLAG = -9999):
        """
        Get method that reads the weather reports off the web. In the LaSilla case, it download a `meteo.last` and interprets the data.
        
        :param debugmode: whether or not POUET is in debugmode. If true, it ought to return some static and dummy data
        :param FLAG: what to return in case the weather report cannot be downloaded or treated. Currently, POUET expect -9999 as a placeholder.
    
        :return: Wind direction, speed, temperature and humidity
        
        .. warning:: Such a method *must* return the following variables in that precise order: wind direction, wind speed, temperature and humidity
        
        """
        #todo: add a "no connection" message if page is not reachable instead of an error
        WS=[]
        WD=[]
        RH = None
        Temps = []
        
        error_msg = "Cannot download weather data. Either you or the weather server is offline!"
        
        if debugmode:
            fname = os.path.join(os.path.dirname(os.path.abspath(inspect.stack()[0][1])), "meteoDebugMode.last")
            fi = open(fname, mode='r')
            data = ""
            with fi:
                line = fi.read()
                data += line
        else:
            try:
                #data=urllib.request.urlopen(self.location.get("weather", "url")).read()
                data = requests.get(self.config.get("weather", "url")).content
            except requests.ConnectionError:
                logger.warning(error_msg)
                return FLAG, FLAG, FLAG, FLAG
            
            data = data.decode("utf-8")
            if "404 Not Found" in data:
                logger.warning(error_msg)
                return FLAG, FLAG, FLAG, FLAG
            
        data=data.split("\n") # then split it into lines
        for line in data:
            if re.match( r'WD', line, re.M|re.I):
                WD.append(int(line[20:25])) # AVG
            if re.match( r'WS', line, re.M|re.I):
                WS.append(float(line[20:25])) # AVG
            if re.match( r'RH', line, re.M|re.I):
                RH = float(line[20:25]) # AVG
            if re.match( r'T ', line, re.M|re.I):
                Temps.append(float(line[20:25])) # AVG
    
        # Remove out-of-band readings
        # WD is chosen between station 1 or 2 in EDP pour la Silla.  # TODO : update for MountGraham
        # We take average
        Temps = np.asarray(Temps, dtype=np.float)
        Temps = Temps[Temps < 100]
        Temps = np.mean(Temps)
    
        # Remove out-of-band readings
        # WD is chosen between station 1 or 2 in EDP pour la Silla.  # TODO : update for MountGraham
        # We take average
        WD = np.asarray(WD, dtype=np.float)
        WD = WD[WD < 360]
        WD = WD[WD > 0]
        WD = np.mean(WD)
        
        # WS should be either WS next to 3.6m or max
        # Remove WS > 99 m/s
        WS = np.asarray(WS, dtype=np.float)
        if WS[2] < 99:
            WS = WS[2]
        else:
            logger.warning("Wind speed from 3.6m unavailable, using other readings in LaSilla") # TODO : update for MountGraham
            WS = np.asarray(WS, dtype=np.float)
            WS = WS[WS > 0]
            WS = WS[WS < 99]
            WS = np.mean(WS)
    
        for var in [WD, WS, Temps, RH]:
            if not np.isnan(var):
                var = -9999
        
        WD = util.check_value(WD, FLAG)
        WS = util.check_value(WS, FLAG)
        Temps = util.check_value(Temps, FLAG)
        RH = util.check_value(RH, FLAG)
        
        return WD, WS, Temps, RH
    