from datetime import datetime
import requests
from urllib.parse import urlencode, quote_plus
from typing import List
import time
from enum import Enum

from lib.time import julian
from lib.horizons.quantities import EphemerisQuantity, RequestQuantityForQuantity

from .planet import Planet

class EphemType(Enum):
    OBSERVER = "OBSERVER"
    VECTORS = "VECTORS"
    ELEMENTS = "ELEMENTS"
    SPK = "SPK"
    APPROACH = "APPROACH"

class HorizonsBasicRequest:
    def __init__(self):
        self.base_url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        self.post_url = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
        self.params = {
            "format": "text",
            "MAKE_EPHEM": "YES",
            "OBJ_DATA": "NO",
            "EPHEM_TYPE": EphemType.OBSERVER.value,
            "ANG_FORMAT": "DEG",
            "TIME_DIGITS": "FRACSEC",
            "EXTRA_PREC": "YES",
            "CSV_FORMAT": "YES",
            "CAL_FORMAT": "BOTH",
            #"QUANTITIES": "\"1,31,9,10,14,15,16,17,20,43\"",
        }
        self.max_url_length = 1843  # Determined by find_max_url_length.py
        self.max_tlist_length = 70
        self.tlist = []  # New attribute to store TLIST as an array

    def _make_request(self) -> str:
        get_url = self.get_url()
        if len(get_url) > self.max_url_length or len(self.tlist) > self.max_tlist_length:
            # URL too long ({len(get_url)} characters). Using POST request.
            return self._make_post_request()
        else:
            print(f"Requesting GET {get_url}")
            response = requests.get(get_url)
            response.raise_for_status()
            #print(f"GET response: {response.text}")
            return response.text
        
    def make_request(self) -> str:
        max_retries = 100
        delay = 1  # Initial delay in seconds
        maximum_delay = 60

        for attempt in range(max_retries):
            try:
                return self._make_request()
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"Waiting {delay} seconds before retrying...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    if delay > maximum_delay:
                        delay = maximum_delay
                else:
                    print("Max retries reached. Raising exception.")
                    raise
            except Exception as e:
                print(f"Error making request: {e}")
                raise

    def _make_post_request(self) -> str:
        print(f"Requesting POST {self.post_url} with {len(self.tlist)} TLIST items")
        post_data = self._format_post_data()
        
        # Prepare the data and files for the POST request
        data = {'format': 'text'}
        files = {'input': ('input.txt', post_data)}
        
        #print(f"POST data: {data}")
        #print(f"POST files content: {post_data}")
        
        try:
            response = requests.post(self.post_url, data=data, files=files)
            response.raise_for_status()
            # print(f"POST response: {response.text}")
            return response.text
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {e.response.status_code}: {e}")
            #print(f"Error response body: {e.response.text}")
            raise

    def _format_post_data(self) -> str:
        lines = ["!$$SOF"]
        for key, value in self.params.items():
            if key != 'format':  # Exclude 'format' from the input file
                lines.append(f"{key}='{value}'")
        
        # Handle TLIST separately
        # if self.tlist:
        #    tlist_str = " ".join(f"'{item}'" for item in self.tlist)
        #    lines.append(f"TLIST={tlist_str}")
        
        if self.tlist:
            for t in self.tlist:
                lines.append(f"TLIST='{t}'")

        lines.append("\n")
        return "\n".join(lines)

    def set_format(self, format):
        self.params["format"] = format

    def set_command(self, command: Planet):
        self.params["COMMAND"] = command.value

    def set_obj_data(self, obj_data):
        self.params["OBJ_DATA"] = obj_data

    def set_make_ephem(self, make_ephem):
        self.params["MAKE_EPHEM"] = make_ephem

    def set_ephem_type(self, ephem_type: EphemType):
        self.params["EPHEM_TYPE"] = ephem_type.value

    def set_start_time(self, start_time):
        jd = julian.julian_from_datetime(start_time)
        self.params["START_TIME"] = f"JD{jd}"

    def set_stop_time(self, stop_time):
        jd = julian.julian_from_datetime(stop_time)
        self.params["STOP_TIME"] = f"JD{jd}"

    def set_step_size(self, step_size):
        self.params["STEP_SIZE"] = step_size

    def set_tlist(self, tlist: list[float]):
        self.tlist = tlist  # Store as an array instead of joining into a string

    def set_quantities(self, quantities: list[int]):
        self.params["QUANTITIES"] = ",".join(map(str, quantities))

    def get_url(self) -> str:
        params = self.params.copy()
        
        # Handle TLIST separately for GET requests
        if self.tlist:
            tlist_str = ",".join(f"'{item}'" for item in self.tlist)
            params['TLIST'] = tlist_str
        
        # Quote any values containing commas or spaces
        for key, value in params.items():
            if isinstance(value, str) and (',' in value or ' ' in value):
                if not (value.startswith("'") and value.endswith("'")):
                    params[key] = f"'{value}'"
        
        query_string = urlencode(params, quote_via=quote_plus)
        return f"{self.base_url}?{query_string}"
    

class HorizonsRequest:
    def __init__(self, planet: Planet):
        self.planet = planet
        self.dates = []  # List to store dates
        self.quantities = []  # List to store quantities
        self.start_time = None
        self.stop_time = None
        self.step_size = None

    def add_date(self, d: datetime):
        self.dates.append(d)

    def add_dates(self, dates: List[datetime]):
        self.dates.extend(dates)

    def add_quantity(self, quantity: EphemerisQuantity):
        self.quantities.append(quantity)

    def add_quantities(self, quantities: List[EphemerisQuantity]):
        self.quantities.extend(quantities)

    def add(self, d: datetime, q: EphemerisQuantity):
        self.add_date(d)
        self.add_quantity(q)

    def tlist(self) -> list[float]:
        return sorted(set(julian.julian_from_datetime(d) for d in self.dates))

    def quantities_list(self) -> list[int]:
        qs = set(self.quantities)
        rqs = [RequestQuantityForQuantity[q] for q in qs]
        ints = set(rq.value for rq in rqs if rq is not None)
        return list(ints)

    def set_time_range(self, start: datetime, stop: datetime, step: str):
        """Set time range and step size instead of using discrete dates.
        
        Args:
            start: Start datetime
            stop: Stop datetime
            step: Step size (e.g., '1d', '1h', '10m')
        """
        self.start_time = start
        self.stop_time = stop
        self.step_size = step

    def configure_request(self, req: HorizonsBasicRequest):
        req.set_command(self.planet)
        if self.start_time and self.stop_time and self.step_size:
            req.set_start_time(self.start_time)
            req.set_stop_time(self.stop_time)
            req.set_step_size(self.step_size)
        else:
            req.set_tlist(self.tlist())
        if self.quantities_list():
            req.set_quantities(self.quantities_list())

    def basic_request(self) -> HorizonsBasicRequest:
        req = HorizonsBasicRequest()
        self.configure_request(req)
        return req

    def make_request(self) -> str:
        req = self.basic_request()
        return req.make_request()

    def get_url(self) -> str:
        return self.basic_request().get_url()

class HorizonsSolarRequest(HorizonsRequest):
    def __init__(self, latitude: float, longitude: float, elevation: float = 0):
        super().__init__(Planet.SUN)
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation

    def configure_request(self, req: HorizonsBasicRequest):
        super().configure_request(req)
        # Set coordinates for the observer on Earth
        req.params["CENTER"] = f"coord@{Planet.EARTH.value}"
        req.params["SITE_COORD"] = f"{self.longitude},{self.latitude},{self.elevation}"
        req.params["COORD_TYPE"] = "GEODETIC"
        req.params["QUANTITIES"] = "4,7,34,42"
        req.params["APPARENT"] = "REFRACTED"

        #req.params["OBJ_DATA"] = "YES"
        req.params["SUPPRESS_RANGE_RATE"] = "NO"
