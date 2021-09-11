# encoding: utf-8

from kivy.app import App
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import DictProperty, ObjectProperty, StringProperty, ListProperty
from kivy.uix.spinner import Spinner
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as dt
from datetime import datetime
from time import mktime, strptime, strftime
import os
from kivy.network.urlrequest import UrlRequest
from TwoPlotsSharedXWidgetApp import TwoPlotsSharedXWidget as TwoPlotsSharedXWidget
import pandas as pd


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

    dataset_vaccination = []
    vaccinationWeekly = ListProperty([])
    datesOfVaccination = ListProperty([])
    vaccines = {
        'AZ' : 'AstraZeneca',
        'JANSS' : 'Janssen',
        'MOD' : 'Moderna',
        'COM' : 'Pfizer / BioNTech',
        'SIN' : 'Sinovac',
        'SPU' : 'Sputnik V',
        'CN' : 'CNBG',
        'UNK' : 'Unknown'
    }


    def __init__(self, **kwargs):
        super(CoronaWidget, self).__init__(**kwargs)

    def download_data_infection(self, *args, **kwargs):
        '''download the current data from the ECDC. Infections and deaths by week from
        https://www.ecdc.europa.eu/en/publications-data/data-national-14-day-notification-rate-covid-19
        '''
        url = 'https://opendata.ecdc.europa.eu/covid19/nationalcasedeath/json/'

        UrlRequest(url=url, on_success=self.update_dataset_infection, on_error=self.download_error, on_progress=self.progress,
                   chunk_size=40960)

    def download_data_vaccination(self, *args, **kwargs):
        '''download the current data from the ECDC. Vaccination data from
        https://www.ecdc.europa.eu/en/publications-data/data-covid-19-vaccination-eu-eea
        '''
        url = 'https://opendata.ecdc.europa.eu/covid19/vaccine_tracker/json/'

        UrlRequest(url=url, on_success=self.update_dataset_vaccination, on_error=self.download_error, on_progress=self.progress,
                   chunk_size=40960)

    def update_dataset_infection(self, request, result):
        '''write result of request into variable self.dataset'''
        self.dataset = result  # data was json. Therefore directly decoded by the UrlRequest
        self.update_continent_spinner()
        self.update_active_country_infection(country=self.activeCountry)
        self.notification = ''

    def update_dataset_vaccination(self, request, result):
        self.dataset_vaccination = result['records']
        self.update_active_country_vaccination(country=self.activeCountry)

    def download_error(self, request, error):
        '''notify on error'''
        self.notification = 'data could not be downloaded'

    def progress(self, request, current_size, total_size):
        '''show progress to the user'''

        #modify. Two notifications necessary since two downloads in prallel
        self.notification = ('Downloading data: {} bytes of {} bytes'.format(current_size, total_size))

    def update_active_country_infection(self, country, *args, **kwargs):
        '''update all infection data for a new selected country'''

        self.activeCountry = country

        # update plot data for infections
        self.casesWeekly.clear()
        self.cumulativeCases.clear()
        self.datesOfCases.clear()

        for element in self.dataset:
            if element['country'] == country and element['indicator'] == 'cases':
                self.casesWeekly.append(element['weekly_count'])
                self.cumulativeCases.append(element['cumulative_count'])
                self.datesOfCases.append(
                    datetime.fromtimestamp(mktime(strptime(element['year_week'] + '-1', '%Y-%W-%w'))))

        try:
            self.ids['plt1'].update_plot()
        except:
            print('Infetions could not be updated. Check data')

        # update last week labels
        indexLastDate = self.datesOfCases.index(max(self.datesOfCases))
        self.newInfections = str(self.casesWeekly[indexLastDate])
        self.newInfectionsDate = self.datesOfCases[indexLastDate].strftime('%Y-%W')

    def update_active_country_vaccination(self, country, *args, **kwargs):
        '''update all vaccination data for a new selected country'''

        if not self.dataset_vaccination:
            return

        country_code = self.get_country_code(country_name=country, code='Alpha-2 code')

        #data sorted by week and all available vaccines
        self.vaccinationWeekly.clear()
        self.datesOfVaccination.clear()

        dates = []
        doses = []
        vaccines = []

        dates.clear()
        doses.clear()
        vaccines.clear()

        for element in self.dataset_vaccination:
            if element['ReportingCountry'] == country_code and element['TargetGroup'] == 'ALL':
                dates.append(datetime.fromtimestamp(mktime(strptime(element['YearWeekISO'].replace('W','') + '-1', '%Y-%W-%w'))))
                doses.append(element['FirstDose'])
                vaccines.append(self.vaccines[element['Vaccine']])

        #re-sort data by week and sum of all vaccines by week
        dates_unique = []
        doses_sum = []

        dates_unique.clear()
        doses_sum.clear()

        for date, dose in zip(dates, doses):
            if not date in dates_unique:
                dates_unique.append(date)
                doses_sum.append(dose)
            else:
                doses_sum[-1] = doses_sum[-1] + dose

        self.datesOfVaccination = dates_unique
        self.vaccinationWeekly = doses_sum

        try:
            self.ids['plt2'].update_plot()
        except Exception as e:
            print('Vaccination could not be updated')
            print(e)

    def update_continent_spinner(self, *args, **kwargs):
        '''Update the spinners with all available continents and countries.
           Use preset values from self.activeContinent and self.activeCountry'''

        continentsAndCountries = {}

        for element in self.dataset:
            try:
                if not element.get('continent') in continentsAndCountries.keys():
                    continentsAndCountries[element['continent']] = []
                if not element.get('country') in continentsAndCountries[element['continent']]:
                    continentsAndCountries[element['continent']].append(element['country'])
            except:
                self.notification = ('Unknown error in : {}').format(element)

        self.continentsAndCountries = continentsAndCountries
        self.continents = continentsAndCountries.keys()

        if self.activeContinent in self.continents:
            self.ids['spn1'].text = self.activeContinent
            if self.activeCountry in self.countries:
                self.ids['spn2'].text = self.activeCountry

    def get_country_code(self, country_name, code):
        xlsx = pd.ExcelFile('CountryCodes.xlsx')
        df = pd.read_excel(xlsx, sheet_name = 'Tabelle1', index_col = 0, usecols = 'A:D', engine = 'openpyxl')
        two_digit_code = df.loc[country_name, code]

        return two_digit_code

class CoronaTestLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(CoronaTestLayout, self).__init__(**kwargs)
        self.ids['wdgt1'].download_data_infection()
        self.ids['wdgt1'].download_data_vaccination()

class CoronaWidgetApp(App):
    def build(self):
        return CoronaTestLayout()

if __name__ == '__main__':
    CoronaWidgetApp().run()