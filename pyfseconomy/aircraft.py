"""
Aircraft data
"""
from enum import Enum, auto


class AircraftTypes(Enum):
    """
    Enumeration of aircraft and associated FSEconomy alias strings
    """
    A320 = auto()
    MSFS_A320 = auto()
    KING_AIR_350 = auto()
    BOEING_737_800 = auto()
    BOEING_747_400 = auto()
    BOMBARDIER_CRJ_200 = auto()
    BOMBARDIER_CRJ_700 = auto()
    BOMBARDIER_DASH8_Q400 = auto()
    C172_SKYHAWK = auto()
    C152_AEROBAT = auto()
    CESSNA_GRAND_CARAVAN = auto()
    CITATION_CJ4_MSFS = auto()
    CITATION_X = auto()
    EMBRAER_PHENOM_300 = auto()
    TBM_930 = auto()
    TBM_850 = auto()

    @staticmethod
    def list():
        """
        Generate a list strings for all aircraft supported
        :return: List of all aircraft in the enumeration by their strings
        """
        return list(map(lambda a: str(a), AircraftTypes))

    def __str__(self):
        """
        Convert enumeration into FSE alias string
        :return: FSE alias string
        """
        if self.value == self.TBM_930.value:
            return "Socata TBM 930 (MSFS)"
        elif self.value == self.TBM_850.value:
            return "Socata TBM 850"
        elif self.value == self.KING_AIR_350.value:
            return "Beechcraft King Air 350"
        elif self.value == self.C172_SKYHAWK.value:
            return "Cessna 172 Skyhawk"
        elif self.value == self.C152_AEROBAT.value:
            return "Cessna 152 Aerobat"
        elif self.value == self.CITATION_X.value:
            return "Cessna Citation X"
        elif self.value == self.A320.value:
            return "Airbus A320"
        elif self.value == self.MSFS_A320.value:
            return "Airbus A320 (MSFS)"
        elif self.value == self.BOEING_737_800.value:
            return "Boeing 737-800"
        elif self.value == self.BOEING_747_400.value:
            return "Boeing 747-400"
        elif self.value == self.CESSNA_GRAND_CARAVAN.value:
            return "Cessna 208 Caravan"
        elif self.value == self.CITATION_CJ4_MSFS.value:
            return "Cessna Citation CJ4 (MSFS)"
        elif self.value == self.EMBRAER_PHENOM_300.value:
            return "Embraer Phenom 300"
        elif self.value == self.BOMBARDIER_CRJ_200.value:
            return "Bombardier CRJ-200ER"
        elif self.value == self.BOMBARDIER_CRJ_700.value:
            return "Bombardier CRJ700-ER"
        elif self.value == self.BOMBARDIER_DASH8_Q400.value:
            return "Bombardier Dash-8 Q400"
        else:
            return f"Unknown plane type - {self.name}"


class Aircraft:
    """
    Hold information relating to an aircraft
    """
    FUEL_KG_PER_GAL = 2.687344961
    PAX_WEIGHT_KG = 77

    def __init__(self, make_model, mtow, seats, crew, empty_weight, fuel_total):
        """

        :param make_model: Make and model string
        :param mtow: Maximum Takeoff Weight
        :param seats: Number of available seats
        :param crew: Number of required crew
        :param empty_weight: Empty weight
        :param fuel_total: Amount of fuel the plane is capable of carrying in total
        """
        self._name = make_model
        self._mtow = mtow
        self._seats = seats
        self._crew = crew
        self._empty_weight = empty_weight
        self._fuel_total_gal = fuel_total

    def get_name(self):
        """
        Get aircraft name

        :return: Name of aircraft
        """
        return self._name

    def get_max_pax(self):
        """
        Get maximum number of passengers

        :return: Number of passengers (pax = seats - crew - pilot)
        """
        return self._seats - self._crew - 1

    def get_pax_cargo_for_fuel(self, fuel_percent):
        """
        Return the amount of pax that can be carried given the fuel load in % or the total amount of cargo that can be
        carried.

        :param fuel_percent: Percentage total fuel load for the aircraft
        :return: Number of pax with onboard fuel and the maximum total available payload (including pax) for the fuel
        """
        fuel_weight = fuel_percent * self._fuel_total_gal * self.FUEL_KG_PER_GAL
        available_payload = self._mtow - self._empty_weight - fuel_weight
        available_pax = min(self.get_max_pax(), int(available_payload / self.PAX_WEIGHT_KG))

        return available_pax, available_payload

    @classmethod
    def aircraft_from_data(cls, csv_data):
        """
        Create an instance of an aircraft based on information from the FSE CSV.
        :param csv_data: Pandas CSV dataframe created from FSE CSV
        :return: Aircraft class
        """
        fuel_total = csv_data['Ext1'] + csv_data['LTip'] + csv_data['LAux'] + csv_data['LMain']
        fuel_total += csv_data['Center1'] + csv_data['Center2'] + csv_data['Center3']
        fuel_total += csv_data['RExt2'] + csv_data['RTip'] + csv_data['RAux'] + csv_data['RMain']

        return cls(csv_data['MakeModel'], csv_data['MTOW'], csv_data['Seats'], csv_data['Crew'],
                   csv_data['EmptyWeight'], fuel_total)
