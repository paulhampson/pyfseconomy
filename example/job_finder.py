import argparse
from operator import itemgetter

import pyfseconomy as fse
from pyfseconomy.utils import plane_loader


def highest_paying_jobs(fse_client, plane_type, distance_limit=None, minimum_pay=0, top_n=5,
                        desired_trip_type=fse.TripTypes.TRIP_ONLY, username=None):
    """
    For a type of aircraft find the top N which are rentable and have best $/NM jobs (accounting for capacity)

    :param desired_trip_type: Set the trip type. Defaults to Trip Only.
    :param minimum_pay: Minimum pay the job should have
    :param distance_limit: Max distance you're interested in
    :param fse_client: FSE Client instance
    :param plane_type: String to define which requested_plane the query should be completed with
    :param top_n: How many top jobs to return
    :param username: Set this if search is constrained to only the planes owned by the specified username.
    :return: Top N potential jobs for this aircraft
    """
    # Search for non-rentable if choosing all in
    rentable_only = desired_trip_type != fse.TripTypes.ALL_IN
    if username:
        plane_list = fse_client.get_user_planes(username)
    else:
        plane_list = fse_client.get_planes_of_type(plane_type, rentable_only=rentable_only)
    plane_location_list = []
    for _, plane in plane_list.iterrows():
        if plane['Location'] != 'In Flight':
            plane_location_list.append(plane['Location'])
    plane_location_list = list(set(plane_location_list))  # ensure unique
    plane_list.set_index("SerialNumber", inplace=True)

    print(f"Searching for jobs in {len(plane_location_list)} airports for {len(plane_list)} planes")
    jobs = fse_client.get_location_available_jobs(plane_location_list,
                                                  limit_trip_type_to=desired_trip_type)
    print(f"Analysing {len(jobs)} jobs...")

    # Get a list of departure_icao locations
    # For each departure_icao location we:
    #   - find unique destinations
    #   - for each unique destination
    #       - calculate $/kg and sort (person weighs 77kg in FSE)
    #       - sum assignments to requested_plane based on top $/kg
    #       - calculate $/NM and store in list
    assignment_list = []
    departure_locations = list(set(jobs['Location'].tolist()))
    aircraft_data = client.get_plane_data()
    for plane_location in departure_locations:
        airport_assignments = jobs[(jobs['Location'] == plane_location)]
        assignment_destinations = list(set(airport_assignments['ToIcao'].tolist()))
        for destination in assignment_destinations:
            destination_assignments = airport_assignments[airport_assignments['ToIcao'] == destination]

            job_distance = fse.Airports.get_airport_distance(plane_location, destination)
            if distance_limit is not None and job_distance > distance_limit:
                continue

            planes_at_location = plane_list[plane_list['Location'] == plane_location]
            for serial, plane_at_location in planes_at_location.iterrows():
                plane_model_data = aircraft_data[plane_at_location['MakeModel']]
                trip_pay, trip_load_list = plane_loader(destination_assignments, serial,
                                                        fuel_pct=plane_at_location['PctFuel'],
                                                        aircraft_data=plane_model_data)
                if job_distance == 0:
                    job_distance = 1

                job_info = {'plane_id': serial,
                            'from': plane_location,
                            'to': destination,
                            'distance': job_distance,
                            'pay': trip_pay,
                            'assignments': trip_load_list,
                            'dollar_per_nm': trip_pay / job_distance
                            }

                if trip_pay > minimum_pay:
                    assignment_list.append(job_info)

    sorted_assignment_list_per_nm = sorted(assignment_list, key=itemgetter('dollar_per_nm'), reverse=True)
    sorted_assignment_list_total_pay = sorted(assignment_list, key=itemgetter('pay'), reverse=True)

    return sorted_assignment_list_per_nm[:top_n], sorted_assignment_list_total_pay[:top_n]


def print_jobs(jobs):
    print("{:<8} {:<8} {:<8} {:<8} {:<8} {:<8} {:<8}".format('From', 'To', 'Plane ID', 'Distance', 'Pay', '$/NM',
                                                             'Assignments'))
    for job in jobs:
        print(
            f"{job['from']:<8} {job['to']:<8} {job['plane_id']:<8} {job['distance']:>8.0f} {job['pay']:>8.0f} "
            f"{job['dollar_per_nm']:>8.2f} {job['assignments']}")


def info_wizard(user_search=False):
    """
    Gather the requested_plane type, minimum job pay, number of jobs to display and the trip type.

    :param user_search: Set to True if the search is going to be restricted to the users planes. In this case we won't
                        ask which planes they are interested in.
    :return: Values selected in response to queries.
    """
    if not user_search:
        plane_list = [fse.AircraftTypes.KING_AIR_350, fse.AircraftTypes.TBM_930, fse.AircraftTypes.CITATION_X,
                      fse.AircraftTypes.C172_SKYHAWK, fse.AircraftTypes.CESSNA_GRAND_CARAVAN,
                      fse.AircraftTypes.MSFS_A320, fse.AircraftTypes.HONDA_HJET]
        print("Select plane type:")
        for idx, plane in enumerate(plane_list):
            print(f"\t[{idx}] {plane}")
        plane_idx = int(input("? "))
        selected_plane = plane_list[plane_idx]
    else:
        print("INFO: Search will be constrained to user's planes.")
        selected_plane = "the user's planes"

    min_job_pay = int(input("Required minimum job pay? "))
    max_distance = int(input("Maximum distance between airports? "))
    job_count = int(input("How many jobs to display? "))

    print("Select trip type:")
    for enum_trip_type in fse.TripTypes:
        print(f"\t[{enum_trip_type.value}] {enum_trip_type}")
    trip_type_id = int(input("? "))
    selected_trip_type = fse.TripTypes(trip_type_id)

    return selected_plane, min_job_pay, job_count, max_distance, selected_trip_type


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tool to find the best paying jobs for a particular aircraft')
    parser.add_argument('--access-key', dest='access_key', nargs=1)
    parser.add_argument('--username', dest='username', nargs=1, default=None)
    args = parser.parse_args()

    run_again = True
    client = fse.Client(args.access_key)
    user_plane_search = args.username is not None
    requested_plane, min_pay, count, distance, trip_type = info_wizard(user_plane_search)
    while run_again:
        best_jobs_per_nm, best_jobs_pay = highest_paying_jobs(client, requested_plane, distance_limit=distance,
                                                              minimum_pay=min_pay,
                                                              top_n=count, desired_trip_type=trip_type,
                                                              username=args.username)
        print(f"\nBest jobs per nm for {requested_plane} over ${min_pay}, max distance of {distance}")
        print_jobs(best_jobs_per_nm)

        print(f"\nBest jobs by pay for {requested_plane} over ${min_pay}, max distance of {distance}")
        print_jobs(best_jobs_pay)

        run_again = "y" != input("\n\nQuit (Y/[N])? ").lower()
        if run_again:
            if "y" == input("New requirements (Y/[N])? ").lower():
                requested_plane, min_pay, count, distance, trip_type = info_wizard()

    print("Goodbye!")
