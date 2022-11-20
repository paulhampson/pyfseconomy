"""
Client for gathering information from FSEconomy's data feeds
"""
import datetime
import io
from enum import Enum, auto

import pandas as pd
import requests

from pyfseconomy import Aircraft


def str_to_timedelta(input_str):
    """
    Convert a string in the format hh:mm to a time delta

    :param input_str: String in format hh:mm
    :return: Time delta
    """
    parts = input_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    return datetime.timedelta(hours=hours, minutes=minutes)


class FSEConnectionError(BaseException):

    def __init__(self, message, full_response):
        self.message = message
        self.full_response = full_response
        super().__init__(self.message)


class FSEInvalidPlaneType(BaseException):
    pass


class TripTypes(Enum):
    VIP = auto()
    TRIP_ONLY = auto()
    ALL_IN = auto()

    def __str__(self):
        if self.value == self.VIP.value:
            return "VIP"
        if self.value == self.TRIP_ONLY.value:
            return "Trip-Only"
        if self.value == self.ALL_IN.value:
            return "All-In"

    @staticmethod
    def list():
        """
        Generate a list strings for all trip types supported
        :return: List of all trip types in the enumeration by their strings
        """
        return list(map(lambda a: str(a), TripTypes))


class Client:
    URL_ROOT = "https://server.fseconomy.net/data"

    class DataFormat(Enum):
        """
        Data format enumeration
        """
        XML = auto()
        CSV = auto()

        def __str__(self):
            if self.value == self.XML.value:
                return "xml"
            if self.value == self.CSV.value:
                return "csv"

    def __init__(self, access_key):
        self._access_key = access_key
        self._retrieval_format = self.DataFormat.CSV
        self._plane_data = None
        self._all_plane_info = None
        self._make_model_list = None

    def _run_request(self, query_parameters):
        """
        Executes the request to the FSE servers.

        Throws FSEConnectionError if the request is not successful.

        :param query_parameters: Dictionary of URL parameters
        :return: Requests class:`Response ` object
        """

        r = requests.get(self.URL_ROOT, params=query_parameters)

        if r.status_code != requests.codes.ok:
            raise FSEConnectionError(f"Unable to retrieve data - status code is {r.status_code}", r.text)
        if r.text.startswith("<Error>"):
            raise FSEConnectionError("Cannot collect data from FSE server", r.text)

        return r

    def get_plane_data(self, force_update=False):
        """
        Retrieves a list of planes from FSE and caches it. Will return the same list unless forced to update.

        :param force_update: Set to True to force a query from the FSE data feeds
        :return: List of requested_plane data objects and a make model list
        """
        if self._plane_data is None or force_update:
            query_parameters = {'userkey': self._access_key,
                                'format': str(self.DataFormat.CSV),
                                'query': 'aircraft',
                                'search': 'configs'}
            r = self._run_request(query_parameters)

            cleaned_text = "\n".join(r.text.splitlines())
            cleaned_text = cleaned_text.replace(",\n", "\n")
            self._plane_data = pd.read_csv(io.StringIO(cleaned_text), encoding=r.encoding)

            self._all_plane_info = {}

            for idx, plane_info in self._plane_data.iterrows():
                self._all_plane_info[plane_info['MakeModel']] = Aircraft.aircraft_from_data(plane_info)

        return self._all_plane_info

    def get_planes_of_type(self, plane_type, rentable_only=True, max_hours_since_100hr=95):
        """
        Retrieves details of all planes of a certain type. By default it only returns rentable planes.

        Rentable planes have a wet and or dry price and are not currently rented.

        :param plane_type: A string for a valid requested_plane type (checked against get_plane_list())
                           e.g. Socata TBM 930 (MSFS)
        :param rentable_only: Defaults to True, set to false if you wish to see all planes
        :param max_hours_since_100hr: Maximum number of hours since last 100hr service. Default is 95.
        :return: Pandas data frame with the result of the query, filtered as requested
        """
        if str(plane_type) not in self.get_plane_data().keys():
            raise FSEInvalidPlaneType(f"Invalid requested_plane type \"{plane_type}\"")

        query_parameters = {
            'userkey': self._access_key,
            'format': str(self.DataFormat.CSV),
            'query': 'aircraft',
            'search': 'makemodel',
            'makemodel': plane_type
        }
        r = self._run_request(query_parameters)

        plane_data = pd.read_csv(io.StringIO(r.text), encoding=r.encoding)

        # Filtering operations for rentable, time since last 100 hour
        if rentable_only:
            plane_data = plane_data[(plane_data['RentedBy'] == 'Not rented.') &
                                    ((plane_data['RentalDry'] > 0.0) | (plane_data['RentalWet'] > 0.0))]

        plane_data['TimeLast100hr'] = plane_data['TimeLast100hr'].map(str_to_timedelta)
        max_hours_since_100hr = datetime.timedelta(hours=max_hours_since_100hr)
        plane_data = plane_data[(plane_data['TimeLast100hr'] <= max_hours_since_100hr)]

        return plane_data

    def get_user_planes(self, username):
        """
        Retrieves details of planes that the user owns.

        :return: Pandas data frame with the result of the query, filtered as requested
        """

        query_parameters = {
            'userkey': self._access_key,
            'format': str(self.DataFormat.CSV),
            'query': 'aircraft',
            'search': 'ownername',
            'ownername': username
        }
        r = self._run_request(query_parameters)

        user_plane_data = pd.read_csv(io.StringIO(r.text), encoding=r.encoding)

        return user_plane_data

    def get_location_available_jobs(self, icao_list, max_cargo=100000, max_passengers=1000,
                                    limit_trip_type_to: TripTypes = None):
        """
        Get the available jobs going from a list of ICAOs

        :param limit_trip_type_to: List of trip types to limit to, None means no filter
        :param max_passengers:
        :param max_cargo:
        :param icao_list: List of ICAOs
        :return: Pandas dataframe with jobs for each ICAO
        """
        icao_list_for_query = "-".join(icao_list)
        query_parameters = {
            'userkey': self._access_key,
            'format': str(self.DataFormat.CSV),
            'query': 'icao',
            'search': 'jobsfrom',
            'icaos': icao_list_for_query
        }
        r = self._run_request(query_parameters)

        plane_data = pd.read_csv(io.StringIO(r.text), encoding=r.encoding)

        plane_data = plane_data[(((plane_data['UnitType'] == 'kg') & (plane_data['Amount'] < max_cargo)) |
                                 ((plane_data['UnitType'] == 'passengers') & (plane_data['Amount'] < max_passengers)))]

        if limit_trip_type_to is not None:
            plane_data = plane_data[(plane_data['Type'] == str(limit_trip_type_to))]

        return plane_data
