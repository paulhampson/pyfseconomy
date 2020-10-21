"""
This file contains useful functions that can be used to process data gathered from FSE data feeds via the client
"""
import math
from collections import OrderedDict
from operator import itemgetter

from pyfseconomy import Aircraft, TripTypes


class PlaneLoadingError(BaseException):
    pass


def order_assignment_by_value(assignments):
    """
    Calculate the value - the $/kg - of each of the assignments, then sort them by value into a dictionary keyed
    with the assignment ID

    :param assignments: Assigments dataframe
    :return: OrderedDict of assignments, keyed by ID - sorted by the value which is $/kg.
    """
    assignment_value_list = {}
    for _, assignment in assignments.iterrows():
        pay = assignment['Pay']
        weight = assignment['Amount']
        if pay > 0 and weight > 0:
            if assignment['UnitType'] == 'passengers':
                weight *= Aircraft.PAX_WEIGHT_KG
            value = pay / weight
            assignment_value_list[assignment['Id']] = value
    return OrderedDict(sorted(assignment_value_list.items(), key=itemgetter(1), reverse=True))


def load_assignments(assignment_list, assignments_by_id, intial_remaining_payload, intial_remaining_pax, aircraft_id):
    """
    Loads assignments up to the remaining payload or pax in the order given.

    :param assignment_list: A list of assignments in the order in which they should be loaded.
    :param assignments_by_id: Dataframe of assignments indexed by their FSE ID
    :param intial_remaining_payload: Starting available payload that can be used (include Pax in this)
    :param intial_remaining_pax: Starting available pax that can be used
    :param aircraft_id: FSE Aircraft identifier - used to load All In trips that are tied to a specific aircraft
    :return: Tuple of Total value of assignments and list of loaded assignment IDs
    """
    assignment_ids = []
    remaining_payload = intial_remaining_payload
    remaining_pax = intial_remaining_pax
    total_value = 0

    for assignment_id, _ in assignment_list.items():
        load_into_plane = True

        unit_type = assignments_by_id.at[assignment_id, "UnitType"]
        amount = assignments_by_id.at[assignment_id, "Amount"]
        pay = assignments_by_id.at[assignment_id, "Pay"]
        assignment_name = f"{amount} {assignments_by_id.at[assignment_id, 'Commodity']}"
        type_is_vip = assignments_by_id.at[assignment_id, "Type"] == str(TripTypes.VIP)
        type_is_allin = assignments_by_id.at[assignment_id, "Type"] == str(TripTypes.ALL_IN)
        exclusive_load = type_is_allin or type_is_vip

        if exclusive_load and remaining_payload != intial_remaining_payload:
            print("WARNING: Attempted to load VIP or All-In job with normal Trip payload")
            continue

        if assignments_by_id.at[assignment_id, "Type"] == str(TripTypes.ALL_IN):
            # Only load if it's associated with this requested_plane
            load_into_plane = aircraft_id == assignments_by_id.at[assignment_id, "AircraftId"]

        if unit_type == 'passengers':
            if amount > remaining_pax:
                load_into_plane = False
            amount *= Aircraft.PAX_WEIGHT_KG

        if amount > remaining_payload:
            load_into_plane = False

        if load_into_plane:
            assignment_ids.append((assignment_id, assignment_name))
            total_value += pay
            remaining_payload -= amount
            if unit_type == 'passengers':
                remaining_pax -= amount / Aircraft.PAX_WEIGHT_KG

        # no more jobs - we now have 1 exclusive payload
        if exclusive_load and load_into_plane:
            break

    return total_value, assignment_ids


def plane_loader(assignments, aircraft_id, max_payload=None, max_pax=None, fuel_pct=1.0,
                 aircraft_data=None):
    """
    Loads the most valuable assignments first until one doesn't fit and then continues to load the next most valuable
    that will fit up until the max_payload or max_pax is reached, but not exceeded.

    Will also only load planes with a single VIP or All in load.

    :param aircraft_id: ID/Serial number of the aircraft (not the registration)
    :param aircraft_data: Aircraft class populated with information about the aircraft to load
    :param fuel_pct: Percentage fuel that is in the requested_plane to be loaded.
    :param assignments: Dataframe containing full data for assignments in the assignment_list
    :param max_payload: Max total payload (including pax) the requested_plane and hold at the fuel level you want, set
                        to None for automatic values
    :param max_pax: Maximum number of passengers
    :return: Total value and list of loaded assignments IDs
    """
    assignments_by_id = assignments.set_index("Id")
    if aircraft_data is not None:
        starting_pax, starting_payload = aircraft_data.get_pax_cargo_for_fuel(fuel_pct)
    elif max_payload is not None and max_pax is not None:
        starting_payload = max_payload
        starting_pax = max_pax
    else:
        raise PlaneLoadingError("Expect max_payload and max_pax or aircraft_data")

    assignment_values = order_assignment_by_value(assignments)
    total_value, assignment_ids = load_assignments(assignment_values, assignments_by_id, starting_payload, starting_pax,
                                                   aircraft_id)

    return total_value, assignment_ids


class GeoLocation:
    """
    Porting of functions from http://janmatuschek.de/LatitudeLongitudeBoundingCoordinates#Java

    This assumes a sphere.
    """

    MIN_LAT = -math.pi / 2
    MAX_LAT = math.pi / 2
    MIN_LON = -math.pi
    MAX_LON = math.pi
    EARTH_RADIUS_KM = 6371.01

    def __init__(self, lat, lon):
        self.rad_lat = math.radians(lat)
        self.rad_lon = math.radians(lon)

    def bounding_coordinates(self, distance, radius=EARTH_RADIUS_KM):
        """
        Calculate the max latitude and longitude a distance from a point on a sphere

        :param distance: Max distance from the point, in KM
        :param radius: Radius of the sphere
        :return: min latitude, min longitude, max latitude, max longitude
        """

        # angular distance in radians on a great circle
        rad_dist = distance / radius

        min_lat = self.rad_lat - rad_dist
        max_lat = self.rad_lat + rad_dist

        # calculate the min & max longitude
        if min_lat > self.MIN_LAT and max_lat < self.MAX_LAT:
            delta_lon = math.asin(math.sin(rad_dist) / math.cos(self.rad_lat))

            min_lon = self.rad_lon - delta_lon
            if min_lon < self.MIN_LON:
                min_lon += 2 * math.pi

            max_lon = self.rad_lon + delta_lon
            if max_lon > self.MAX_LON:
                max_lon -= 2 * math.pi
        else:
            # pole is within bounding area
            min_lat = max(min_lat, self.MIN_LAT)
            max_lat = min(max_lat, self.MAX_LAT)
            min_lon = self.MIN_LON
            max_lon = self.MAX_LON

        return math.degrees(min_lat), math.degrees(min_lon), math.degrees(max_lat), math.degrees(max_lon)
