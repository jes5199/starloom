Starloom 25

Starloom 25 is an attempt to use the learnings of StarLoom 24 to make a new set of tools useful for creating and retrieving ephemeris data.

The 24 repository is a mess, so let's try to rebuild it one piece at a time in a way that make sense. Let's try to keep the libaries straight, in 24 I didn't have a good sense of how Horizons and Weft were different, yet.


/lib/starloom

Shared interfaces and constants and whatnot

/lib/horizons

Libraries for interacting with the JPL Horizons API, and for caching results from the API in a SQLite database.

/lib/weft

Tools for working with Weft binary ephemeris files

/lib/time

Some general tools for working with datetimes and Julian Dates

the /scripts/ directory should have subdirectories for each library

Starloom is written in Python.
Datetimes should be timezone aware, and almost always in UTC.
