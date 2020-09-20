# encoding: utf-8

from kivy.app import App
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import DictProperty, ObjectProperty, StringProperty, ListProperty
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
import urllib.request
import json
from time import gmtime, asctime, strftime, mktime, strptime
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as dt
from datetime import datetime
from time import gmtime, asctime, strftime, mktime, strptime
import os

class CoronaWidget(RelativeLayout):

    continentsAndCountries = DictProperty({})
    continents = ListProperty([])
    countries = ListProperty([])
    activeCountry = StringProperty('--')
    activeContinent = StringProperty('--')
    allCountries = ListProperty([])
    newInfections = StringProperty('--')
    newInfectionsDate = StringProperty('--')
    dailyCases = ListProperty([])
    cumulativeCases = ListProperty([])
    datesOfCases = ListProperty([])
    notification = StringProperty('')
    dataset = []

    def __init__(self, **kwargs):
        super(CoronaWidget, self).__init__(**kwargs)
    
    def get_http_to_json(self, url, file_name, *args, **kwargs):
        
        #open the url and decode the json data
        with urllib.request.urlopen(url) as f:
            data = json.loads(f.read().decode('utf-8'))

            #build the file name to save the file
            my_filename = file_name + '.json'
                
            #save the file
            with open(my_filename, 'w') as write_file:
                json.dump(data, write_file)

    def download_data(self, *args, **kwargs):
        '''download_data gets the weather data from openweathermap.org and writes it to
           json file'''
        
        url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/json'
        fileDir = os.path.dirname(os.path.abspath(__file__))
        absFilename = os.path.join(fileDir, 'covid')

        self.get_http_to_json(url, absFilename)


    def update_dataset(self, *args, **kwargs):

        #Read and store data for selected country
        try:
            fileDir = os.path.dirname(os.path.abspath(__file__))
            absFilename = os.path.join(fileDir, 'covid.json')
            with open(absFilename, 'r') as read_file:
                data=json.load(read_file)
                self.dataset = data['records']

        #if the file does not exist print an error message
        except FileNotFoundError as e:
            print(e)
            self.notification = 'No data available'

    def update_active_country(self, country, *args, **kwargs):

        self.activeCountry = country
        
        self.dailyCases.clear()
        self.datesOfCases.clear()

        for element in self.dataset:
            if element['countriesAndTerritories'] == country:
                self.dailyCases.append(element['cases'])
                self.datesOfCases.append(element['dateRep'])
                
        self.newInfections = str(self.dailyCases[0])
        self.newInfectionsDate = self.datesOfCases[0]

        #cases are ordered from most current to past. Needs to be reversed to be added together
        self.cumulativeCases = self.dailyCases.copy()
        self.cumulativeCases.reverse()

        for n in range(1,len(self.cumulativeCases)):
            self.cumulativeCases[n] = self.cumulativeCases[n] + self.cumulativeCases[n-1]

        self.cumulativeCases.reverse()

    def update_continent_spinner(self, *args, **kwargs):

        continentsAndCountries = {}

        for element in self.dataset:
            if not element.get('continentExp') in continentsAndCountries.keys():
                continentsAndCountries[element['continentExp']] = []
            if not element.get('countriesAndTerritories') in continentsAndCountries[element['continentExp']]:
                continentsAndCountries[element['continentExp']].append(element['countriesAndTerritories'])

        self.continentsAndCountries = continentsAndCountries
        self.continents = continentsAndCountries.keys()
        if 'Europe' in self.continents:
            self.ids['spn1'].text = 'Europe'
            if 'Germany' in self.countries:
                self.ids['spn2'].text = 'Germany'

class TwoPlotsSharedXWidget (FigureCanvasKivyAgg):

    plt.style.use('dark_background')

    sourceX = ListProperty([])
    sourceY = ListProperty([])
    units = ObjectProperty(['--','--'])
    titles = ObjectProperty(['--','--'])
    ax_colors = ObjectProperty(['g','g'])
    notification = StringProperty('')
    
    def __init__(self, **kwargs):
        '''__init__ takes the figure the backend is going to work with'''
        super(TwoPlotsSharedXWidget, self).__init__(plt.figure(), **kwargs)
        
    def update_plot(self, *args, **kwargs):

        timestamp = []

        for element in self.sourceX:
            timestamp.append(datetime.fromtimestamp(mktime(strptime(element,'%d/%m/%Y'))))

        #Clear the figure
        myfigure = self.figure
        myfigure.clf()

        axes = myfigure.subplots(2,1, sharex=True)

        #Add the data to the axes and modify their axis
        for n in range(len(axes)):
            axes[n].plot_date(timestamp, self.sourceY[n], self.ax_colors[n], xdate=True)             
            axes[n].set_ylabel(self.units[n])
            axes[n].set_title(self.titles[n])
            plt.ylim(min(self.sourceY[n])-2,max(self.sourceY[n])+2)
            axes[n].xaxis.set_major_locator(dt.MonthLocator(bymonth=range(1,13))) #show major ticks witha step widht of 1 month
            axes[n].xaxis.set_major_formatter(dt.DateFormatter('%d-%b'))

        #the axis labels for the first subplot are made invisible
        plt.setp(axes[0].get_xticklabels(which='both'), visible=False)

        #draw the figure
        myfigure.canvas.draw_idle()

class MyRootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(MyRootLayout, self).__init__(**kwargs)
        self.ids['wdgt1'].download_data()
        self.ids['wdgt1'].update_dataset()
        self.ids['wdgt1'].update_continent_spinner()

class MyVisuApp(App):
    def build(self):
        #To Do:
        #1. check if covid.json exists and if it is up to date
        #2. if not load ist async
        return MyRootLayout()

if __name__ == '__main__':
    MyVisuApp().run()
