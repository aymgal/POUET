"""
Testing script, v1
"""

import os, sys, logging
from astropy.time import Time

import os, sys
path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '../pouet')
sys.path.append(path)

# symlink config and obprogram
os.system("ln -s ../pouet/config .")
os.system("ln -s ../pouet/obsprogram .")

import clouds, main, meteo, obs, plots, run, util

print(os.system("ls ."))

logging.basicConfig(format='PID %(process)06d | %(asctime)s | %(levelname)s: %(name)s(%(funcName)s): %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.critical("This should say Python >= 3.0: {}".format(sys.version))

logger.warning(os.getcwd())

# initialize meteo
currentmeteo = meteo.Meteo(name='LaSilla', cloudscheck=False, debugmode=False)

# load a catalogue of observables
observables = obs.rdbimport("../cats/2m2lenses.rdb", obsprogramcol=None, obsprogram='lens')

observables = [o for o in observables if o.name == "PSJ1606-2333"]

obs_night = Time("2018-02-12 01:00:00", format='iso', scale='utc')
#plots.shownightobs(observable=observables[0], meteo=currentmeteo, obs_night="2018-02-12", savefig=False, verbose=True)


# show current status of all observables
obs.showstatus(observables, currentmeteo, displayall=True)

# update meteo at now
currentmeteo.update(obs_time=Time.now())

# newtime
# todo create a new time object, play with it



# remove links
os.system("unlink config")
os.system("unlink obsprogram")