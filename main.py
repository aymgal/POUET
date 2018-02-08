"""
Launch the application, link POUET functions to the design
"""


from PyQt5 import QtCore, QtGui, QtWidgets, uic
import os, sys
import obs, run, util, clouds 
import design
from astropy import units as u
from astropy.time import Time, TimeDelta
import copy
import ephem

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pylab as plt
from matplotlib.patches import Wedge
from matplotlib import gridspec
from matplotlib.colors import LinearSegmentedColormap

import numpy as np

import logging
#logging.basicConfig(format='%(asctime)s | %(name)s(%(funcName)s): %(message)s', level=logging.DEBUG)
#logger = logging.getLogger(__name__)

COLORWARN = "orange"
COLORLIMIT = "red"
COLORNOMINAL = 'black'
COLORSUCCESS = "green"

class MyLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.allskyWidget = QtWidgets.QPlainTextEdit(parent)
        self.allskyWidget.setGeometry(parent.geometry())
        self.allskyWidget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.allskyWidget.appendPlainText(msg)

        
class AllSkyView(FigureCanvas):
 
    def __init__(self, parent=None, width=6, height=4.5):
        #fig = Figure(figsize=(width, height), dpi=100)
        
        #self.figure.subplots_adjust(bottom=0.01)
        #self.figure.subplots_adjust(top=0.499)
        #self.figure.subplots_adjust(right=0.98)
        #self.figure.subplots_adjust(left=0.)
        
        
        self.figure = Figure(figsize=(width, height))
        self.figure.patch.set_facecolor((0.95,0.94,0.94,1.))
        
        self.axis = self.figure.add_subplot(111)
        
        FigureCanvas.__init__(self, self.figure)
        self.setParent(parent)
        
        self.axis.axis('off')
 
        FigureCanvas.setSizePolicy(self,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
 
    def display(self, meteo, plot_analysis=True):
        
        self.axis.clear()
        
        location = meteo.name 
        allsyk = meteo.allsky
        
        #TODO: We have an issue with the layout. It seems that there is a remaining padding due to the canevas...
        # It's a secondary issue, to be solved later
        #self.figure.tight_layout()
        
        try:
            rest = allsyk.im_masked
        except AttributeError:
            logging.warning("No All Sky image, by-passing")
            return
        
        if not plot_analysis:
            self.axis.imshow(allsyk.im_original, vmin=0, vmax=255, cmap=plt.get_cmap('Greys_r'))
            self.axis.set_ylim([np.shape(rest)[0], 0])
            self.axis.set_xlim([0, np.shape(rest)[1]])
        
            self.axis.set_axis_off()
            self.draw()
            return
        
        self.axis.imshow(rest, vmin=0, vmax=255, cmap=plt.get_cmap('Greys_r'))
        self.axis.imshow(allsyk.observability_map.T, cmap=plt.get_cmap('RdYlGn'), alpha=0.2)
        #self.draw()

        theta_coordinates = np.deg2rad(np.arange(0,360,15))
    
        params = clouds.get_params(location)

        ff = params['ff']
        k1 = params['k1']
        k2 = params['k2']
        r0 = params['r0']
        cx = params['cx']
        cy = params['cy']
        north = params['north']
        deltatetha = params['deltatetha']
        
        coordinatesx = np.cos(north + theta_coordinates) * r0 + cx
        coordinatesy = np.sin(north + theta_coordinates) * r0 + cy
        
        northx, northy = clouds.get_image_coordinates(np.deg2rad(0), np.deg2rad(24), location)
        eastx, easty = clouds.get_image_coordinates(np.deg2rad(90), np.deg2rad(20), location)

        self.axis.annotate('N', xy=(northx, northy), rotation=deltatetha,
          horizontalalignment='center', verticalalignment='center')
        
        self.axis.annotate('E', xy=(eastx, easty), rotation=deltatetha,
          horizontalalignment='center', verticalalignment='center')
        
        altshow = [15, 30, 45, 60, 75, 90]
        for angle in np.deg2rad(altshow):
            rr = clouds.get_radius(angle, ff, k1, k2, r0)
        
            #if angle >= np.pi/2: print rr/330.
            self.figure.gca().add_artist(plt.Circle((cx,cy),rr,color='k', fill=False, alpha=0.5))
        
            textx = np.cos(north + np.deg2rad(180)) * (rr - 2) + cx
            texty = np.sin(north + np.deg2rad(180)) * (rr - 2) + cy
            self.axis.annotate('%d' % (90-np.ceil(np.rad2deg(angle))), xy=(textx, texty), rotation=deltatetha,#prefered_direction['dir'],
              horizontalalignment='left', verticalalignment='center', size=10)

        #plt.plot([cx, northx], [cy, northy], lw=2, color='k')
        for ccx, ccy in zip(coordinatesx, coordinatesy):
            self.axis.plot([cx, ccx], [cy, ccy], lw=1, color='k', alpha=0.5)
        self.axis.set_ylim([np.shape(rest)[0], 0])
        self.axis.set_xlim([0, np.shape(rest)[1]])
        
        self.axis.set_axis_off()
        self.draw()

    def display_wind_limits(self, meteo):
        """
        Should this call some other function elsewhere? Maybe
        """
        
        params = clouds.get_params(meteo.name)
        
        r0 = params['r0']
        cx = params['cx']
        cy = params['cy']
        north = params['north']
        
        wpl = float(meteo.location.get("weather", "windWarnLevel"))
        wsl = float(meteo.location.get("weather", "windLimitLevel"))   
        WD = meteo.winddirection
        WS = meteo.windspeed
        WDd = WD
        WD = np.deg2rad(WD)

        if WS is not None and WS > wpl:
            wdcoordinatesx = np.cos(north - WD) * r0 + cx
            wdcoordinatesy = np.sin(north - WD) * r0 + cy
            Nd = np.rad2deg(north)# + 90.

            if WS > wsl :
                cw = COLORLIMIT
                self.axis.add_patch(Wedge([cx, cy], r0, Nd - WDd, Nd - WDd+360, fill=False, hatch='//', edgecolor=cw))
                self.axis.annotate('WIND LIMIT\nREACHED', xy=(cx, cy), rotation=0,
                      horizontalalignment='center', verticalalignment='center', color=cw, fontsize=35)
            elif WS > wpl :
                cw = COLORWARN
                wtcoordinatesx = np.cos(north - WD) * r0 / 2. + cx
                wtcoordinatesy = np.sin(north - WD) * r0 / 2. + cy

                self.axis.add_patch(Wedge([cx, cy], r0, -90+Nd-WDd, 90+Nd-WDd, fill=False, hatch='//', edgecolor=cw))
                self.axis.annotate('Pointing limit!', xy=(wtcoordinatesx, wtcoordinatesy), rotation=0,
                      horizontalalignment='center', verticalalignment='center', color=cw, fontsize=25)
                
            self.axis.plot([cx, wdcoordinatesx], [cy, wdcoordinatesy], lw=3, color=cw)

        self.draw()


class VisibilityView(FigureCanvas):
 
    def __init__(self, parent=None, width=4.5, height=4):
        #fig = Figure(figsize=(width, height), dpi=100)
        
        #self.figure.subplots_adjust(bottom=0.01)
        #self.figure.subplots_adjust(top=0.499)
        #self.figure.subplots_adjust(right=0.98)
        #self.figure.subplots_adjust(left=0.)
        
        
        self.figure = Figure(figsize=(width, height))
        self.figure.patch.set_facecolor((0.95,0.94,0.94,1.))
        
        self.figure.subplots_adjust(wspace=0.)
        self.figure.subplots_adjust(bottom=0.23)
        self.figure.subplots_adjust(top=0.95)
        self.figure.subplots_adjust(right=0.9)
        self.figure.subplots_adjust(left=0.13)
            
        gs = gridspec.GridSpec(1, 2, width_ratios=[20, 1]) 
        self.axis = self.figure.add_subplot(gs[0])
        self.cax = self.figure.add_subplot(gs[1])

        FigureCanvas.__init__(self, self.figure)
        self.parent = parent

        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
               
    def visbility_draw(self, obs_time, meteo, airmass, anglemoon, check_wind=True):
        
        self.axis.clear()
        self.cax.clear()
      
        ras, decs = util.grid_points()
        ra_g, dec_g = np.meshgrid(ras,decs)
        sep=np.zeros_like(ra_g)
        vis=np.zeros_like(ra_g)
        wind = np.zeros_like(ra_g) * np.nan

        tel_lat, tel_lon, tel_elev = meteo.get_telescope_params()

        observer = ephem.Observer()
        observer.date = obs_time.iso
        observer.lat = tel_lat.to_string(unit=u.degree, decimal=True)
        observer.lon = tel_lon.to_string(unit=u.degree, decimal=True)

        observer.elevation = tel_elev
              
        moon = ephem.Moon()
        moon.compute(observer)
        
        wpl = float(meteo.location.get("weather", "windWarnLevel"))
        wsl = float(meteo.location.get("weather", "windLimitLevel"))   
        WD = meteo.winddirection
        WS = meteo.windspeed

        do_plot_contour = False
        for i,ra in enumerate(ras):
            for j,dec in enumerate(decs):
                star = ephem.FixedBody()
                star._ra = ra
                star._dec = dec
                star.compute(observer)

                if util.elev2airmass(el=star.alt+0, alt=observer.elevation) < airmass:
                    vis[j,i]=1
                    s = ephem.separation((moon.ra, moon.dec), (ra, dec))+0.

                    if np.rad2deg(s)-0.5 > anglemoon: # Don't forget that the angular diam of the Moon is ~0.5 deg
                        sep[j,i]=np.rad2deg(s)
                        do_plot_contour = True
                        
                    else: sep[j,i]=np.nan
                    
                    if check_wind and WS >= wsl :
                        wind[j,i]=1.
                        cw = COLORLIMIT
                        ct = 'WIND LIMIT REACHED'
                        cts = 35
                    elif check_wind and WS >= wpl :
                        cw = COLORWARN
                        ct = 'Pointing limit!'
                        cts = 20
                        ws = ephem.separation((star.alt, np.deg2rad(WD)), (star.alt, star.az))
                        if ws < np.pi/2.:
                            wind[j,i]=1.
                else: 
                    sep[j,i]=np.nan
                    vis[j,i]=np.nan
        
            del star
            
        #########################################################
        

        ra_g=ra_g/2/np.pi*24
        dec_g=dec_g/np.pi*180
        v = np.linspace(anglemoon, 180, 100, endpoint=True)
        self.axis.contourf(ra_g,dec_g,vis,cmap=plt.get_cmap("Greys"))
        
        if do_plot_contour:
            CS=self.axis.contour(ra_g,dec_g, sep, levels=[50,70,90],colors=['yellow','red','k'],inline=1)
            self.axis.clabel(CS,fontsize=9,fmt='%d°')
            CS=self.axis.contourf(ra_g,dec_g,sep,v,)
            
            t = np.arange(anglemoon, 190, 10)
            tl = ["{:d}°".format(int(tt)) for tt in t]
            cbar = self.figure.colorbar(CS,ax=self.axis,cax=self.cax, ticks=t)
            cbar.ax.set_yticklabels(tl, fontsize=9)
        
        if check_wind and WS > wpl:
            
            cmap = LinearSegmentedColormap.from_list('mycmap', [(0., 'red'),
                                                    (1, cw)]
                                        )

            cs = self.axis.contourf(ra_g,dec_g, wind, hatches=['//'],
                          cmap=cmap, alpha=0.5)
            self.axis.annotate(ct, xy=(12, 75), rotation=0,
                              horizontalalignment='center', verticalalignment='center', color=cw, fontsize=cts)


        for tick in self.axis.get_xticklabels():
            tick.set_rotation(70)
        self.axis.set_xlabel('Right ascension',fontsize=9,)
        self.axis.set_ylabel('Declination',fontsize=9,)

        
        self.axis.set_xticks(np.linspace(0,24,25))
        self.axis.set_yticks(np.linspace(-90,90,19))
        
        
        self.axis.set_xlim([0,24])
        lat = float(tel_lat.to_string(unit=u.degree, decimal=True))
        self.axis.set_ylim([np.max([lat-90, -90]),np.min([lat+90, 90])])

        self.axis.set_title("%s - Moon sep %d deg - max airmass %1.2f" % (observer.date,\
             anglemoon, airmass), fontsize=9)
        
        self.axis.grid()

        self.draw()

class MultiPopup(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(460, 320)


        layout = QtWidgets.QGridLayout()

        self.nameColLabel = QtWidgets.QLabel("Name:")
        self.nameColValues = QtWidgets.QComboBox()
        self.nameColValues.addItems(["name1", "name2"])

        layout.addWidget(self.nameColLabel, 0, 0)
        layout.addWidget(self.nameColValues, 0, 1)

        self.alphaColLabel = QtWidgets.QLabel("Alpha:")
        self.alphaColValues = QtWidgets.QComboBox()
        self.alphaColValues.addItems(["alpha1", "alpha2"])

        layout.addWidget(self.alphaColLabel, 1, 0)
        layout.addWidget(self.alphaColValues, 1, 1)

        self.okButton = QtWidgets.QPushButton('OK', self)
        self.okButton.clicked.connect(self.saveandclose)
        layout.addWidget(self.okButton, 2, 0)


        self.cancelButton = QtWidgets.QPushButton()
        self.cancelButton.setText('Cancel')
        layout.addWidget(self.cancelButton, 2, 1)

        self.setLayout(layout)
        self.exec()

    def saveandclose(self):
        self.namecol_value = self.nameColValues.currentIndex()
        self.alphacol_index = self.alphaColValues.currentIndex()
        self.deltacol_index = self.deltaColValues.currentIndex()



        self.accept()

class POUET(QtWidgets.QMainWindow, design.Ui_POUET):
    def __init__(self, parent=None):
        super(POUET, self).__init__(parent)
        self.setupUi(self)
        
        print("Starting up... This can take a minute...")
        self.set_configTimeNow()
        self.save_Time2obstime()
        
        # logger startup...
        logTextBox = MyLogger(self.verticalLayoutWidget)
        logTextBox.setFormatter(logging.Formatter(fmt='%(asctime)s | %(levelname)s: %(name)s(%(funcName)s): %(message)s', datefmt='%m-%d-%Y %H:%M:%S'))
        #logger.addHandler(logTextBox)
        
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)
        
        logging.info('Startup...')
        
        self.allsky_debugmode = False  
        self.name_location = 'LaSilla'
        self.cloudscheck = True
        self.currentmeteo = run.startup(name=self.name_location, cloudscheck=self.cloudscheck, debugmode=self.allsky_debugmode)

        # todo: do we want to load that at startup ?
        self.allsky = AllSkyView(parent=self.allskyView)
        self.allsky_redisplay()
        
        self.visibilitytool = VisibilityView(parent=self.visibilityView)
        self.visibilitytool_draw()
        
        self.site_display()
        self.weather_display()
        
        # signal and slots init...
        self.retrieveObs.clicked.connect(self.retrieve_obs)
        self.weatherDisplayRefresh.clicked.connect(self.weather_display)
        self.allSkyRefresh.clicked.connect(self.allsky_refresh)
        self.configCloudsShowLayersValue.clicked.connect(self.allsky_redisplay)
        self.checkObsStatus.clicked.connect(self.check_obs_status)
        self.configAutoupdateFreqValue.valueChanged.connect(self.set_timer_interval)
        self.configTimenow.clicked.connect(self.set_configTimeNow)
        self.configUpdate.clicked.connect(self.do_update)
        self.visibilityDraw.clicked.connect(self.visibilitytool_draw)
        self.configCloudsDebugModeValue.clicked.connect(self.set_debug_mode)

        # Stating timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(120000) #trigger every 2 minutes by default.
        self.timer.timeout.connect(self.auto_refresh)
        
        # testing stuff at startup...
        """
        run.refresh_status(self.observables, self.currentmeteo)
        for o in self.observables:
            o.get_observability(self.currentmeteo, cloudscheck=True, verbose=False)
        """
        # self.popup = MultiPopup()
        #self.popup.show()

        #print(self.popup.alpha_col)
        #sys.exit()

        #import headerloader
        #self.headerloader = headerloader.Ui_Dialog


        # Custom dialog loader
        #self.headerPopup = uic.loadUi("headerdialog.ui")
        #self.headerPopup.show()

    def print_status(self, msg, colour=COLORNOMINAL):
        self.statusLabel.setText(msg)
        self.statusLabel.setStyleSheet('color: {}'.format(colour))
        QtWidgets.QApplication.processEvents()
        
    def set_timer_interval(self):

        interval = self.configAutoupdateFreqValue.value() * 1000 * 60
        self.timer.setInterval(interval)
        logging.debug("Set auto-refresh to {} min".format(self.configAutoupdateFreqValue.value()))
        
    def set_configTimeNow(self):
        
        #get current date and time
        now = QtCore.QDateTime.currentDateTimeUtc()

        #set current date and time to the object
        self.configTime.setDateTime(now)
        
    def save_Time2obstime(self):
        
        self.obs_time = Time(self.configTime.dateTime().toPyDateTime(), scale="utc")
        logging.debug("obs_time is now set to {:s}".format(str(self.obs_time)))
        
    def set_debug_mode(self):
        
        if self.configCloudsDebugModeValue.checkState() == 0:
            goto_mode = False
        else:
            goto_mode = True
        
        if goto_mode != self.allsky_debugmode:
            
            if goto_mode:
                mode="debug"
            else:
                mode="production"
            
            self.print_status("Changing to {} mode...".format(mode), colour=COLORWARN)
            
            self.allsky_debugmode = goto_mode  
            self.currentmeteo = run.startup(name=self.name_location, cloudscheck=self.cloudscheck, debugmode=self.allsky_debugmode)
            self.auto_refresh()
            self.do_update()

            logging.warning("Now in {} mode for the All Sky!".format(mode))
            self.print_status("Change of mode complete.")

        
    def do_update(self):
        
        self.save_Time2obstime()
        self.site_display()
        self.visibilitytool_draw()
        logging.critical("CHECK do_update is complete (OBVISOULY NOT SINCE NO UPDATE TO OBS)!")

    def retrieve_obs(self):

        logmsg = ''

        model = QtGui.QStandardItemModel(self.listObs)

        self.listObs.clearSpans()
        filepath = QtWidgets.QFileDialog.getOpenFileName(self, "Select a file")[0]

        logmsg += '%s ' % filepath

        ext = os.path.splitext(filepath)[1]

        if ext != 'pouet':  # then it's a first load:
            obsprogramlist = run.retrieve_obsprogramlist()
            obsprogramnames = (o["name"] for o in obsprogramlist)

            # header popup
            self.headerPopup = uic.loadUi("headerdialog.ui")

            # split by tabs
            headers_input = open(filepath, 'r').readlines()[0].split('\n')[0].split()

            for cb in [self.headerPopup.headerNameValue, self.headerPopup.headerRAValue, self.headerPopup.headerDecValue, self.headerPopup.headerObsprogramValue]:
                for h in headers_input:
                    cb.addItem(h)
            self.headerPopup.headerObsprogramValue.addItem("None")

            # ok is 0 if rejected, 1 if accepted
            ok = self.headerPopup.exec()
            if ok:

                namecol = int(self.headerPopup.headerNameValue.currentIndex())+1
                alphacol = int(self.headerPopup.headerRAValue.currentIndex())+1
                deltacol = int(self.headerPopup.headerDecValue.currentIndex())+1

                if self.headerPopup.headerObsprogramValue.currentText() == "None":
                    obsprogramcol = None
                else:
                    obsprogramcol = int(self.headerPopup.headerDecValue.currentIndex())+1


                # obsprogram popup
                self.popup = QtWidgets.QInputDialog()
                #todo rename Cancel button as default if possible
                obsprogram, okop = self.popup.getItem(self, "Select an observing program", "Existing programs - hit Cancel to use the default configuration. This setting applies only to the observables that do not already have an obsprogram defined in the input file", obsprogramnames, 0, False)

                if okop:
                    logmsg += 'as %s ' % obsprogram
                else:
                    obsprogram = None
                    logmsg += 'as default '

            else:
                # we exit the load function
                logging.info("Load of % aborted by user" % filepath)
                return

        else:  # then it's a pouet file. We assume it follows our own convention for the rdbimport
            # col#1 = name, col#2 = alpha, col#3 = dec, col#4 = obsprogram
            pass


        try:
            if ext != 'pouet':
                self.observables = obs.rdbimport(filepath, obsprogram=obsprogram, namecol=namecol, alphacol=alphacol, deltacol=deltacol, obsprogramcol=obsprogramcol)
                run.refresh_status(self.currentmeteo, self.observables)

            else:
                self.observables = obs.rdbimport(filepath, obsprogram=obsprogram)
                run.refresh_status(self.currentmeteo, self.observables)


            for o in self.observables:
                o.get_observability(self.currentmeteo, cloudscheck=False, verbose=False)

                name = QtGui.QStandardItem(o.name)
                alpha = QtGui.QStandardItem(o.alpha.to_string(unit=u.hour, sep=':'))
                delta = QtGui.QStandardItem(o.delta.to_string(unit=u.degree, sep=':'))
                observability = QtGui.QStandardItem(str(o.observability))
                obsprogram = QtGui.QStandardItem(o.obsprogram)

                name.setCheckable(True)
                model.appendRow([name, alpha, delta, observability, obsprogram])
                model.setHorizontalHeaderLabels(['Name', 'Alpha', 'Delta', 'Observability', 'Program'])


            self.listObs.setModel(model)
            logmsg += 'successfully loaded'
            logging.info(logmsg)
            #todo: replace by redirecting the message to a logger
            self.print_status("%s \n Sucessfully loaded" % filepath, COLORSUCCESS)

        except:
            logmsg += ' not loaded - format unknown'
            logging.error(logmsg)

            self.print_status("%s \n Format unknown" % filepath, COLORWARN)


    def check_obs_status(self):
        """

        :return:
        """

        #0 is not checked, 1 is partially checked, 2 is checked --> 0 or 2 for us
        model = self.listObs.model()

        statuses = [model.item(i, 0).checkState() for i in range(model.rowCount())]
        print(statuses)


    def weather_display(self):
        
        if not self.currentmeteo.lastest_weatherupdate_time is None and (Time.now() - self.currentmeteo.lastest_weatherupdate_time).to(u.s).value < 30:
            logging.info("Last weather report was downloaded more recently than 30 seconds ago, I don't download it again")
            draw_wind = False
        else:
            self.currentmeteo.updateweather()
            draw_wind = True
        
        self.weatherWindSpeedValue.setText(str('{:2.1f}'.format(self.currentmeteo.windspeed)))
        if float(self.currentmeteo.location.get("weather", "windLimitLevel")) <= self.currentmeteo.windspeed:
            self.weatherWindSpeedValue.setStyleSheet("QLabel { color : %s; }" % format(COLORLIMIT))
        elif float(self.currentmeteo.location.get("weather", "windWarnLevel")) <= self.currentmeteo.windspeed:
            self.weatherWindSpeedValue.setStyleSheet("QLabel { color : %s; }" % format(COLORWARN))
        else:
            self.weatherWindSpeedValue.setStyleSheet("QLabel { color : %s; }" % format(COLORNOMINAL))
        
        self.weatherWindDirectionValue.setText(str('{:3d}'.format(int(self.currentmeteo.winddirection))))
        
        self.weatherTemperatureValue.setText(str('{:2.1f}'.format(int(self.currentmeteo.temperature))))
        
        self.weatherHumidityValue.setText(str('{:3d}'.format(int(self.currentmeteo.humidity))))
        if float(self.currentmeteo.location.get("weather", "humidityLimitLevel")) <= self.currentmeteo.humidity:
            self.weatherHumidityValue.setStyleSheet("QLabel { color : %s; }" % format(COLORLIMIT))
        elif float(self.currentmeteo.location.get("weather", "humidityWarnLevel")) <= self.currentmeteo.humidity:
            self.weatherHumidityValue.setStyleSheet("QLabel { color : %s; }" % format(COLORWARN))
        else:
            self.weatherHumidityValue.setStyleSheet("QLabel { color : %s; }" % format(COLORNOMINAL))
        
        if draw_wind:
            self.allsky_redisplay()
        
        self.weatherLastUpdateValue.setText(str(self.currentmeteo.lastest_weatherupdate_time).split('.')[0])


    def site_display(self):
        
        self.siteLocationValue.setText(str('Lat={:s}\tLon={:s}\tElev={:s} m'.format(self.currentmeteo.location.get("location", "longitude"), self.currentmeteo.location.get("location", "latitude"), self.currentmeteo.location.get("location", "elevation"))))
        
        obs_time = self.obs_time
        
        #-------------------------------------------------------- Bright objects now
        
        sunAz, sunAlt = self.currentmeteo.get_sun(obs_time)
        sunAlt = sunAlt.to(u.degree).value
        sunAz = sunAz.to(u.degree).value
        
        self.sunCoordinatesValues.setText(str('RA={:s}  DEC={:s}'.format(self.currentmeteo.sun.ra.__str__(), self.currentmeteo.sun.dec.__str__())))
        self.sunAltazValue.setText(str('{:2.1f}°\t{:2.1f}°'.format(sunAlt, sunAz)))
        
        moonAz, moonAlt = self.currentmeteo.get_moon(obs_time)
        moonAlt = moonAlt.to(u.degree).value
        moonAz = moonAz.to(u.degree).value
        
        self.moonCoordinatesValues.setText(str('RA={:s}  DEC={:s}'.format(self.currentmeteo.moon.ra.__str__(), self.currentmeteo.moon.dec.__str__())))
        self.moonAltazValue.setText(str('{:2.1f}°\t{:2.1f}°'.format(moonAlt, moonAz)))
        
        self.brightLastUpdateValue.setText(str(obs_time).split('.')[0])
        
        #-------------------------------------------------------- Night here only (we change the obs_time so this must the last things to run!)
        
        cobs_time = copy.copy(obs_time)
        #cobs_time = Time('2018-02-08 01:00:00', format='iso', scale='utc')
        cobs_time.format = 'iso'
        cobs_time.out_subfmt = 'date'
        
        ref_time = Time('%s 12:00:00' % cobs_time, format='iso', scale='utc') #5h UT is approx. the middle of the night
        
        is_after_midday = (cobs_time-ref_time).value > 0
        
        if is_after_midday:
            day_before = copy.copy(cobs_time)
            night_date = cobs_time
            day_after = night_date + TimeDelta(1, format="jd")
        else:
            day_after = cobs_time
            night_date = cobs_time - TimeDelta(1, format="jd")
            day_before = cobs_time - TimeDelta(1, format="jd")
            
        sunrise, sunset = self.currentmeteo.get_twilights(night_date, twilight='civil')
        self.nightStartCivilValue.setText(str('{:s}'.format(str(sunset))))
        self.nightEndCivilValue.setText(str('{:s}'.format(str(sunrise))))
        
        sunrise, sunset = self.currentmeteo.get_twilights(night_date, twilight='nautical')
        self.nightStartNauticalValue.setText(str('{:s}'.format(str(sunset))))
        self.nightEndNauticalValue.setText(str('{:s}'.format(str(sunrise))))
        
        sunrise, sunset = self.currentmeteo.get_twilights(night_date, twilight='astronomical')
        self.nightStartAstroValue.setText(str('{:s}'.format(str(sunset))))
        self.nightEndAstroValue.setText(str('{:s}'.format(str(sunrise))))
        
        self.nightLastUpdateValueBefore.setText(str(day_before).split('.')[0])
        self.nightLastUpdateValueAfter.setText(str(day_after).split('.')[0])

    def allsky_refresh(self):
        
        self.print_status("Refreshing All Sky...", COLORWARN)

        self.currentmeteo.allsky.update()
        
        logging.info("Updated All Sky")
        
        self.allsky_redisplay()
        
        self.print_status("All Sky refresh done.", COLORNOMINAL)
        
    def allsky_redisplay(self):
        
        if self.configCloudsShowLayersValue.checkState() == 0:
            plot_analysis = False
        else:
            plot_analysis = True
        
        self.allsky.display(self.currentmeteo, plot_analysis=plot_analysis)
        self.allSkyUpdateValue.setText(str(self.currentmeteo.allsky.last_im_refresh).split('.')[0])
        
        self.allsky.display_wind_limits(self.currentmeteo)
        self.allSkyUpdateWindValue.setText("Wind update: {}".format(str(self.currentmeteo.lastest_weatherupdate_time).split('.')[0]))
        
        msg = "Drawn All Sky."
        logging.debug(msg)
        
    def visibilitytool_draw(self):
        
        airmass = self.visibilityAirmassValue.value()
        anglemoon = self.visibilityMoonAngleValue.value()
        
        if self.currentmeteo.lastest_weatherupdate_time is None or np.abs((self.obs_time - self.currentmeteo.lastest_weatherupdate_time).to(u.s).value / 60.) > 10:
            check_wind = False
            logging.info("Visibility is not considering the wind, too much difference between date weather report and obs time")
        else:
            check_wind = True
        
        self.visibilitytool.visbility_draw(obs_time=self.obs_time, meteo=self.currentmeteo, airmass=airmass, anglemoon=float(anglemoon), check_wind=check_wind)
        
        logging.debug("Drawn visibility with airmass={:1.1f}, anglemoon={:d}d".format(airmass, anglemoon))
        
    def auto_refresh(self):
        
        logging.info("Auto-refresh")
        self.print_status("Auto-refresh started...", COLORWARN)
        
        if self.configCloudsAutoRefreshValue.checkState() == 2:
            self.allsky_refresh()
        if self.configWindAutoRefreshValue.checkState() == 2:
            self.weather_display()
        if self.configWindAutoRefreshValue.checkState() == 2 and self.configCloudsAutoRefreshValue.checkState() == 0:
            self.allsky_redisplay()
        
        if self.currentmeteo.lastest_weatherupdate_time is None or (Time.now() - self.currentmeteo.lastest_weatherupdate_time).to(u.s).value / 60. > 10:
            self.allSkyUpdateWindValue.setStyleSheet("QLabel { color : %s; }" % format(COLORWARN))
            self.weatherLastUpdateValue.setStyleSheet("QLabel { color : %s; }" % format(COLORWARN))
        else:
            self.allSkyUpdateWindValue.setStyleSheet("QLabel { color : %s; }" % format(COLORNOMINAL))
            self.weatherLastUpdateValue.setStyleSheet("QLabel { color : %s; }" % format(COLORNOMINAL))
            
        if self.currentmeteo.allsky.last_im_refresh is None or (Time.now() - self.currentmeteo.allsky.last_im_refresh).to(u.s).value / 60. > 10:
            self.allSkyUpdateValue.setStyleSheet("QLabel { color : %s; }" % format(COLORWARN))
        else:
            self.allSkyUpdateValue.setStyleSheet("QLabel { color : %s; }" % format(COLORNOMINAL))

        self.print_status("Auto-refresh done.", COLORNOMINAL)

def main():
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication
    form = POUET()                 # We set the form to be our ExampleApp (design)
    form.show()                         # Show the form
    app.exec_()                         # and execute the app



if __name__ == '__main__':
    main()