"""
Handles information from the FSE airport database
"""
import os

import pandas as pd
from geographiclib.geodesic import Geodesic

from pyfseconomy.utils import GeoLocation

DATA_LOCATION = os.path.join(os.path.dirname(__file__), "icaodata.csv")


class Airports:
    """
    Class of methods that allow retrieval of useful information about airports.
    """
    METERS_PER_NM = 1852
    _airport_data = pd.read_csv(DATA_LOCATION)

    @classmethod
    def get_airport_distance(cls, departure_icao, arrival_icao):
        """
        Calculate the distance in nautical miles between two airports

        :param departure_icao: ICAO code of departure airport
        :param arrival_icao: ICAO code of arrival airport
        :return: Distance in NM between the two airports
        """
        distance_nm, _ = cls.get_airport_distance_bearing(departure_icao, arrival_icao)
        return distance_nm

    @classmethod
    def get_airport_bearing(cls, departure_icao, arrival_icao):
        """
        Calculate the bearing in degrees going from departure to arrival airport

        :param departure_icao: ICAO of departure airport
        :param arrival_icao: ICAO of arrival airport
        :return: Bearing in degrees to travel from dep to arr airport
        """
        _, bearing = cls.get_airport_distance_bearing(departure_icao, arrival_icao)
        return bearing

    @classmethod
    def get_airport_distance_bearing(cls, departure_icao, arrival_icao):
        """
        Calculate the distance and bearing between the departure and arrival

        :param departure_icao: ICAO of departure airport
        :param arrival_icao: ICAO of arrival airport
        :return: Distance in nautical miles and bearing
        """
        airport_data = cls._airport_data.set_index("icao")

        result = Geodesic.WGS84.Inverse(airport_data.at[departure_icao, 'lat'], airport_data.at[departure_icao, 'lon'],
                                        airport_data.at[arrival_icao, 'lat'], airport_data.at[arrival_icao, 'lon'])
        distance_nm = result['s12'] / cls.METERS_PER_NM
        bearing_def = result['azi1']

        if bearing_def < 0:
            bearing_def = 360 + bearing_def

        return distance_nm, bearing_def

    @classmethod
    def get_airports_within(cls, icao, max_distance, min_distance=0, civil_only=True):
        """
        Report a list of airports within a radius

        :param civil_only:
        :param min_distance:
        :param icao: Airport at centre
        :param max_distance: Search radius - in nautical miles
        :return: Dataframe of airports within radius, giving their distance and heading
        """
        airport_data_by_icao = cls._airport_data.set_index("icao")
        max_distance_km = max_distance * cls.METERS_PER_NM / 1000

        # get the bounding coordinates for the radius
        airport_location = GeoLocation(airport_data_by_icao.at[icao, 'lat'], airport_data_by_icao.at[icao, 'lon'])
        min_lat, min_lon, max_lat, max_lon = airport_location.bounding_coordinates(max_distance_km)

        # get locations within the bounding area, exclude self!
        locations = cls._airport_data[(min_lon <= cls._airport_data['lon']) & (cls._airport_data['lon'] <= max_lon) &
                                      (min_lat <= cls._airport_data['lat']) & (cls._airport_data['lat'] <= max_lat) &
                                      (icao != cls._airport_data['icao'])]
        if civil_only:
            locations = locations[(locations['type'] == 'civil')]

        locations.set_index('icao', inplace=True)
        icao_list = pd.DataFrame(columns=['icao', 'distance', 'bearing'])
        for location_icao, location in locations.iterrows():
            distance, bearing = cls.get_airport_distance_bearing(icao, location_icao)
            if min_distance < distance <= max_distance:
                df = pd.DataFrame([[location_icao, distance, bearing]], columns=icao_list.columns)
                icao_list = icao_list.append(df)

        icao_list.set_index('icao', inplace=True)
        return icao_list
