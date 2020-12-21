# encoding: utf-8

from kivy.app import App
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import DictProperty, ObjectProperty, StringProperty, ListProperty
from kivy.uix.spinner import Spinner
import urllib.request
import json
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as dt
from datetime import datetime
from time import mktime, strptime
import os
from kivy.network.urlrequest import UrlRequest

class CoronaWidget(RelativeLayout):
    '''Shows infections for the current date and plots for daily and cumulative infections.

        Attributes:
        The attributes (excluding dataset[]) are bound by name to propertis in the kv file. Updating them will automatically update the displayed data in the visualisation
            continentsAndCountries (DictProperty):
                contains continents and correspondant countries
                {'europe': ['germany', 'france', ...], 'asia': ['china', 'singapore', ...]}
            continents (ListProperty):
                list holding all continents. Retrieved from continentsAndCountries.
            countries (ListProperty):
                list holding all countries of the selected continent.
                Retrieved from continentsAndCountries
            activeCountry (StringProperty, str):
                currently active country
            activeContinent (StringProperty, str):
                currently active continent
            newInfections (StringProperty, str):
                Infections which were reported for the latest date within activeCountry
            newInfectionsDate (StringProperty, str):
                Date at which the newInfections were reported
            weeklyCases (ListProperty):
                List holding all infections per week in the order from latest to oldest
            cumulativeCases (ListProperty):
                List holding all added up infections in the order from latest to oldest
            datesOfCases (ListProperty):
                List holding all dates for the dailyCases and cumulativeCases
            notification  (StringProperty, str):
                Error string. Shows exceptions, like no data available.
                Initially set to --.

            dataset (list):
                list holding all the downloaded data
    '''

    continentsAndCountries = DictProperty({})
    continents = ListProperty([])
    countries = ListProperty([])
    activeCountry = StringProperty('Germany')
    activeContinent = StringProperty('Europe')
    newInfections = StringProperty('--')
    newInfectionsDate = StringProperty('--')
    casesWeekly = ListProperty([])
    cumulativeCases = ListProperty([])
    datesOfCases = ListProperty([])
    notification = StringProperty('')
    dataset = []

    def __init__(self, **kwargs):
        super(CoronaWidget, self).__init__(**kwargs)

    def download_data(self, *args, **kwargs):
        '''download the current data from the ECDC'''
        url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/json/'
        
        UrlRequest(url = url, on_success = self.update_dataset, on_error = self.download_error, on_progress = self.progress, chunk_size = 40960)

    def update_dataset(self, request, result):
        '''write result of request into variable self.dataset'''
        self.dataset = result['records'] #data was json. Therefore directly decoded by the UrlRequest
        self.update_continent_spinner()
        self.update_active_country(country = self.activeCountry)
        self.notification = ''

    def download_error(self, request, error):
        '''notify on error'''
        self.notification = 'data could not be downloaded'

    def progress(self, request, current_size, total_size):
        '''show progress to the user'''
        self.notification = ('Downloading data: {} bytes of {} bytes'.format(current_size, total_size))        print(self.notification)

    def update_active_country(self, country, *args, **kwargs):
        '''update all data for a new selected country'''

        self.activeCountry = country
        
        self.casesWeekly.clear()
        self.datesOfCases.clear()

        for element in self.dataset:
            if element['countriesAndTerritories'] == country:
                self.casesWeekly.append(element['cases_weekly'])
                self.datesOfCases.append(element['year_week'])
                
        self.newInfections = str(self.casesWeekly[0])
        self.newInfectionsDate = self.datesOfCases[0]

        #cases are ordered from most current to past. Needs to be reversed to be added together
        self.cumulativeCases = self.casesWeekly.copy()
        self.cumulativeCases.reverse()

        for n in range(1,len(self.cumulativeCases)):
            self.cumulativeCases[n] = self.cumulativeCases[n] + self.cumulativeCases[n-1]

        self.cumulativeCases.reverse()

    def update_continent_spinner(self, *args, **kwargs):
        '''Update the spinners with all available continents and countries.
           Use preset values from self.activeContinent and self.activeCountry'''

        continentsAndCountries = {}

        for element in self.dataset:
            if not element.get('continentExp') in continentsAndCountries.keys():
                continentsAndCountries[element['continentExp']] = []
            if not element.get('countriesAndTerritories') in continentsAndCountries[element['continentExp']]:
                continentsAndCountries[element['continentExp']].append(element['countriesAndTerritories'])

        self.continentsAndCountries = continentsAndCountries
        self.continents = continentsAndCountries.keys()
        if self.activeContinent in self.continents:
            self.ids['spn1'].text = self.activeContinent
            if self.activeCountry in self.countries:
                self.ids['spn2'].text = self.activeCountry

class TwoPlotsSharedXWidget (FigureCanvasKivyAgg):
    '''Displays two datetimeplots with shared x-axis.

        Attributes:
        The attributes are bound by name to propertis in the kv file. Updating them will automatically update the displayed data in the visualisation
            sourceX (ListProperty):
                list of datetime values for the timeseries
            sourceY (ListProperty):
                list holding two lists of values corresponding with timestamp
            units (ObjectProperty, str):
                list of string. Holding the units of the y-axis.
                Initially set to --.
            titles (ObjectProperty, str):
                list of string. Holding the titles for the plots.
                Initially set to --.
            ax_colors (ObjectProperty, str):
                List, setting the color of the plot.
                Initially set to green.
                Other parameters to change to different colors can be found in the matplotib documentation https://matplotlib.org/2.1.1/api/_as_gen/matplotlib.pyplot.plot.html
            notification  (StringProperty, str):
                Error string. Shows exceptions, like no data available.
                Initially set to --.
    '''

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
        '''
        reads the latest data, updates the figure and plots it.
        
        Args:
            *args (): not used. For further development.
            **kwargs (): not used. For further development.

        Returns:
            Nothing.
        '''

        timestamp = []

        for element in self.sourceX:
            timestamp.append(datetime.fromtimestamp(mktime(strptime(element + '-1', "%Y-%W-%w"))))

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

class MyVisuApp(App):
    def build(self):
        #To Do:
        #1. check if covid.json exists and if it is up to date
        #2. if not load ist async
        return MyRootLayout()

if __name__ == '__main__':
    MyVisuApp().run()
