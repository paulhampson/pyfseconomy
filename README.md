# Python FSEconomy Interface Library

This package provides a python interface to the FSEconomy datafeeds. Your own personal data key can be retrieved from
the [FSEconomy data feeds page](https://server.fseconomy.net/datafeeds.jsp).

It provides access to the following data:

* Retrieval of assignments for a list of ICAOs - can be filtered by size/pax/trip type.
* Get a list of planes by type - can be filtered by hours since 100hr service/rentable
* Get a list of planes owned by a specific user by their username

To avoid too many calls to the data feed the library will cache the plane data internally. This cache can be requested
to update if required.

## Examples

### Job Finder

This script will search for the highest paying jobs both in terms of v$ per nautical miles and overall value for a 
selected aircraft - filtered based on maximum distance and overall distance.

Usage example:

`python examples/job_finder.py --access-key=<personal FSE data feed key>`