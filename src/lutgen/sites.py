from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Site:
    icao: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    site_type: Literal["wsr88d", "tdwr"]
    first_range_gate_m: int = 2125
    range_gate_spacing_m: int = 250
    max_range_m: int = 230_000
    n_azimuths: int = 720


# fmt: off
# Source: NWS NEXRAD Site ID database + FAA TDWR list
# Coordinates from official NWS/ROC records; # TODO: verify marks uncertain elevations

SITES: list[Site] = [
    # ── CONUS WSR-88D ──────────────────────────────────────────────────────────
    Site("KABR", "Aberdeen, SD",              lat=45.4558,  lon=-98.4131,   elevation_m=397.5,  site_type="wsr88d"),
    Site("KABX", "Albuquerque, NM",           lat=35.1497,  lon=-106.8240,  elevation_m=1789.0, site_type="wsr88d"),
    Site("KAKQ", "Norfolk/Richmond, VA",      lat=36.9839,  lon=-77.0078,   elevation_m=34.1,   site_type="wsr88d"),
    Site("KAMA", "Amarillo, TX",              lat=35.2333,  lon=-101.7092,  elevation_m=1093.0, site_type="wsr88d"),
    Site("KAMX", "Miami, FL",                 lat=25.6111,  lon=-80.4128,   elevation_m=4.0,    site_type="wsr88d"),
    Site("KAPX", "Gaylord, MI",               lat=44.9072,  lon=-84.7197,   elevation_m=447.0,  site_type="wsr88d"),
    Site("KARX", "La Crosse, WI",             lat=43.8228,  lon=-91.1912,   elevation_m=390.0,  site_type="wsr88d"),
    Site("KATX", "Seattle/Tacoma, WA",        lat=48.1945,  lon=-122.4958,  elevation_m=152.0,  site_type="wsr88d"),
    Site("KBBX", "Beale AFB, CA",             lat=39.4956,  lon=-121.6317,  elevation_m=52.0,   site_type="wsr88d"),
    Site("KBGM", "Binghamton, NY",            lat=42.1997,  lon=-75.9847,   elevation_m=490.0,  site_type="wsr88d"),
    Site("KBHX", "Eureka, CA",                lat=40.4981,  lon=-124.2919,  elevation_m=734.0,  site_type="wsr88d"),
    Site("KBIS", "Bismarck, ND",              lat=46.7708,  lon=-100.7603,  elevation_m=506.0,  site_type="wsr88d"),
    Site("KBLX", "Billings, MT",              lat=45.8539,  lon=-108.6067,  elevation_m=1097.0, site_type="wsr88d"),
    Site("KBMX", "Birmingham, AL",            lat=33.1722,  lon=-86.7697,   elevation_m=197.0,  site_type="wsr88d"),
    Site("KBOX", "Boston, MA",                lat=41.9558,  lon=-71.1369,   elevation_m=36.0,   site_type="wsr88d"),
    Site("KBRO", "Brownsville, TX",           lat=25.9158,  lon=-97.4189,   elevation_m=7.0,    site_type="wsr88d"),
    Site("KBUF", "Buffalo, NY",               lat=42.9489,  lon=-78.7369,   elevation_m=212.0,  site_type="wsr88d"),
    Site("KBYX", "Key West, FL",              lat=24.5975,  lon=-81.7033,   elevation_m=0.0,    site_type="wsr88d"),
    Site("KCAE", "Columbia, SC",              lat=33.9489,  lon=-81.1183,   elevation_m=70.0,   site_type="wsr88d"),
    Site("KCBW", "Houlton, ME",               lat=46.0392,  lon=-67.8067,   elevation_m=230.0,  site_type="wsr88d"),
    Site("KCBX", "Boise, ID",                 lat=43.4911,  lon=-116.2344,  elevation_m=935.0,  site_type="wsr88d"),
    Site("KCCX", "State College, PA",         lat=40.9228,  lon=-78.0039,   elevation_m=733.0,  site_type="wsr88d"),
    Site("KCLE", "Cleveland, OH",             lat=41.4133,  lon=-81.8597,   elevation_m=233.0,  site_type="wsr88d"),
    Site("KCLX", "Charleston, SC",            lat=32.6553,  lon=-81.0422,   elevation_m=9.0,    site_type="wsr88d"),
    Site("KCRP", "Corpus Christi, TX",        lat=27.7839,  lon=-97.5111,   elevation_m=14.0,   site_type="wsr88d"),
    Site("KCYS", "Cheyenne, WY",              lat=41.1519,  lon=-104.8061,  elevation_m=1876.0, site_type="wsr88d"),
    Site("KDAX", "Sacramento, CA",            lat=38.5011,  lon=-121.6778,  elevation_m=9.0,    site_type="wsr88d"),
    Site("KDDC", "Dodge City, KS",            lat=37.7208,  lon=-99.9689,   elevation_m=790.0,  site_type="wsr88d"),
    Site("KDFX", "Laughlin AFB, TX",          lat=29.2731,  lon=-100.2806,  elevation_m=344.0,  site_type="wsr88d"),
    Site("KDGX", "Brandon, MS",               lat=32.2800,  lon=-89.9844,   elevation_m=132.0,  site_type="wsr88d"),
    Site("KDLH", "Duluth, MN",                lat=46.8369,  lon=-92.2097,   elevation_m=439.0,  site_type="wsr88d"),
    Site("KDMX", "Des Moines, IA",            lat=41.7311,  lon=-93.7228,   elevation_m=300.0,  site_type="wsr88d"),
    Site("KDOX", "Dover AFB, DE",             lat=38.8258,  lon=-75.4400,   elevation_m=15.0,   site_type="wsr88d"),
    Site("KDTX", "Detroit, MI",               lat=42.6997,  lon=-83.4717,   elevation_m=325.0,  site_type="wsr88d"),
    Site("KDVN", "Davenport, IA",             lat=41.6117,  lon=-90.5808,   elevation_m=229.0,  site_type="wsr88d"),
    Site("KDYX", "Dyess AFB, TX",             lat=32.5386,  lon=-99.2544,   elevation_m=462.0,  site_type="wsr88d"),
    Site("KEAX", "Kansas City, MO",           lat=38.8103,  lon=-94.2644,   elevation_m=303.0,  site_type="wsr88d"),
    Site("KEMX", "Tucson, AZ",                lat=31.8933,  lon=-110.6303,  elevation_m=1586.0, site_type="wsr88d"),
    Site("KENX", "Albany, NY",                lat=42.5864,  lon=-74.0642,   elevation_m=556.0,  site_type="wsr88d"),
    Site("KEOX", "Fort Rucker, AL",           lat=31.4603,  lon=-85.4594,   elevation_m=132.0,  site_type="wsr88d"),
    Site("KEPZ", "El Paso, TX",               lat=31.8731,  lon=-106.6981,  elevation_m=1251.0, site_type="wsr88d"),
    Site("KESX", "Las Vegas, NV",             lat=35.7011,  lon=-114.8917,  elevation_m=1482.0, site_type="wsr88d"),
    Site("KEVX", "Eglin AFB, FL",             lat=30.5644,  lon=-85.9217,   elevation_m=55.0,   site_type="wsr88d"),
    Site("KEWX", "Austin/San Antonio, TX",    lat=29.7039,  lon=-98.0286,   elevation_m=193.0,  site_type="wsr88d"),
    Site("KEYX", "Edwards AFB, CA",           lat=35.0978,  lon=-117.5608,  elevation_m=817.0,  site_type="wsr88d"),
    Site("KFCX", "Roanoke, VA",               lat=37.0242,  lon=-80.2742,   elevation_m=874.0,  site_type="wsr88d"),
    Site("KFDR", "Altus AFB, OK",             lat=34.3622,  lon=-98.9764,   elevation_m=396.0,  site_type="wsr88d"),
    Site("KFDX", "Cannon AFB, NM",            lat=34.6353,  lon=-103.6297,  elevation_m=1417.0, site_type="wsr88d"),
    Site("KFFC", "Atlanta, GA",               lat=33.3636,  lon=-84.5658,   elevation_m=262.0,  site_type="wsr88d"),
    Site("KFSD", "Sioux Falls, SD",           lat=43.5878,  lon=-96.7294,   elevation_m=436.0,  site_type="wsr88d"),
    Site("KFSX", "Flagstaff, AZ",             lat=34.5742,  lon=-111.1983,  elevation_m=2261.0, site_type="wsr88d"),
    Site("KFTG", "Denver, CO",                lat=39.7867,  lon=-104.5458,  elevation_m=1675.0, site_type="wsr88d"),
    Site("KFWS", "Dallas/Fort Worth, TX",     lat=32.5728,  lon=-97.3028,   elevation_m=208.0,  site_type="wsr88d"),
    Site("KGGW", "Glasgow, MT",               lat=48.2064,  lon=-106.6250,  elevation_m=694.0,  site_type="wsr88d"),
    Site("KGJX", "Grand Junction, CO",        lat=39.0622,  lon=-108.2139,  elevation_m=2994.0, site_type="wsr88d"),
    Site("KGLD", "Goodland, KS",              lat=39.3669,  lon=-101.7006,  elevation_m=1113.0, site_type="wsr88d"),
    Site("KGRB", "Green Bay, WI",             lat=44.4986,  lon=-88.1111,   elevation_m=208.0,  site_type="wsr88d"),
    Site("KGRK", "Fort Hood, TX",             lat=30.7217,  lon=-97.3831,   elevation_m=166.0,  site_type="wsr88d"),
    Site("KGRR", "Grand Rapids, MI",          lat=42.8939,  lon=-85.5447,   elevation_m=237.0,  site_type="wsr88d"),
    Site("KGSP", "Greenville/Spartanburg, SC",lat=34.8833,  lon=-82.2203,   elevation_m=286.0,  site_type="wsr88d"),
    Site("KGWX", "Columbus AFB, MS",          lat=33.8969,  lon=-88.3289,   elevation_m=70.0,   site_type="wsr88d"),
    Site("KGYX", "Portland, ME",              lat=43.8914,  lon=-70.2564,   elevation_m=122.0,  site_type="wsr88d"),
    Site("KHDX", "Holloman AFB, NM",          lat=33.0769,  lon=-106.1228,  elevation_m=1286.0, site_type="wsr88d"),
    Site("KHGX", "Houston, TX",               lat=29.4719,  lon=-95.0789,   elevation_m=5.0,    site_type="wsr88d"),
    Site("KHNX", "Hanford, CA",               lat=36.3142,  lon=-119.6322,  elevation_m=74.0,   site_type="wsr88d"),
    Site("KHPX", "Fort Campbell, KY",         lat=36.7369,  lon=-87.2847,   elevation_m=175.0,  site_type="wsr88d"),
    Site("KHTX", "Huntsville, AL",            lat=34.9306,  lon=-86.0833,   elevation_m=536.0,  site_type="wsr88d"),
    Site("KICT", "Wichita, KS",               lat=37.6544,  lon=-97.4428,   elevation_m=407.0,  site_type="wsr88d"),
    Site("KICX", "Cedar City, UT",            lat=37.5908,  lon=-112.8625,  elevation_m=3239.0, site_type="wsr88d"),
    Site("KILN", "Wilmington, OH",            lat=39.4703,  lon=-83.8217,   elevation_m=319.0,  site_type="wsr88d"),
    Site("KILX", "Lincoln, IL",               lat=40.1506,  lon=-89.3367,   elevation_m=178.0,  site_type="wsr88d"),
    Site("KIND", "Indianapolis, IN",          lat=39.7075,  lon=-86.2803,   elevation_m=241.0,  site_type="wsr88d"),
    Site("KINX", "Tulsa, OK",                 lat=36.1753,  lon=-95.5647,   elevation_m=204.0,  site_type="wsr88d"),
    Site("KIWA", "Phoenix, AZ",               lat=33.2892,  lon=-111.6700,  elevation_m=412.0,  site_type="wsr88d"),
    Site("KIWX", "Fort Wayne, IN",            lat=41.3589,  lon=-85.7000,   elevation_m=292.0,  site_type="wsr88d"),
    Site("KJAX", "Jacksonville, FL",          lat=30.4847,  lon=-81.7019,   elevation_m=10.0,   site_type="wsr88d"),
    Site("KJGX", "Robins AFB, GA",            lat=32.6750,  lon=-83.3514,   elevation_m=160.0,  site_type="wsr88d"),
    Site("KJKL", "Jackson, KY",               lat=37.5908,  lon=-83.3131,   elevation_m=416.0,  site_type="wsr88d"),
    Site("KLBB", "Lubbock, TX",               lat=33.6542,  lon=-101.8142,  elevation_m=994.0,  site_type="wsr88d"),
    Site("KLCH", "Lake Charles, LA",          lat=30.1253,  lon=-93.2161,   elevation_m=4.0,    site_type="wsr88d"),
    Site("KLGX", "Langley Hill, WA",          lat=47.1158,  lon=-124.1069,  elevation_m=71.0,   site_type="wsr88d"),
    Site("KLIX", "New Orleans, LA",           lat=30.3367,  lon=-89.8256,   elevation_m=7.0,    site_type="wsr88d"),
    Site("KLNX", "North Platte, NE",          lat=41.9578,  lon=-100.5761,  elevation_m=905.0,  site_type="wsr88d"),
    Site("KLOT", "Chicago, IL",               lat=41.6044,  lon=-88.0847,   elevation_m=202.0,  site_type="wsr88d"),
    Site("KLRX", "Elko, NV",                  lat=40.7397,  lon=-116.8028,  elevation_m=2056.0, site_type="wsr88d"),
    Site("KLSX", "St. Louis, MO",             lat=38.6989,  lon=-90.6828,   elevation_m=185.0,  site_type="wsr88d"),
    Site("KLTX", "Wilmington, NC",            lat=33.9892,  lon=-78.4292,   elevation_m=18.0,   site_type="wsr88d"),
    Site("KLVX", "Louisville, KY",            lat=37.9753,  lon=-85.9439,   elevation_m=219.0,  site_type="wsr88d"),
    Site("KLWX", "Sterling, VA",              lat=38.9753,  lon=-77.4778,   elevation_m=83.0,   site_type="wsr88d"),
    Site("KLZK", "Little Rock, AR",           lat=34.8364,  lon=-92.2619,   elevation_m=173.0,  site_type="wsr88d"),
    Site("KMAF", "Midland/Odessa, TX",        lat=31.9433,  lon=-102.1894,  elevation_m=872.0,  site_type="wsr88d"),
    Site("KMAX", "Medford, OR",               lat=42.0811,  lon=-122.7172,  elevation_m=2289.0, site_type="wsr88d"),
    Site("KMBX", "Minot AFB, ND",             lat=48.3931,  lon=-100.8644,  elevation_m=456.0,  site_type="wsr88d"),
    Site("KMHX", "Morehead City, NC",         lat=34.7761,  lon=-76.8764,   elevation_m=9.0,    site_type="wsr88d"),
    Site("KMLB", "Melbourne, FL",             lat=28.1133,  lon=-80.6542,   elevation_m=10.0,   site_type="wsr88d"),
    Site("KMOB", "Mobile, AL",                lat=30.6794,  lon=-88.2397,   elevation_m=63.0,   site_type="wsr88d"),
    Site("KMPX", "Minneapolis, MN",           lat=44.8489,  lon=-93.5653,   elevation_m=299.0,  site_type="wsr88d"),
    Site("KMQT", "Marquette, MI",             lat=46.5311,  lon=-87.5483,   elevation_m=429.0,  site_type="wsr88d"),
    Site("KMRX", "Knoxville, TN",             lat=36.1683,  lon=-83.4017,   elevation_m=393.0,  site_type="wsr88d"),
    Site("KMSX", "Missoula, MT",              lat=47.0411,  lon=-113.9861,  elevation_m=2394.0, site_type="wsr88d"),
    Site("KMTX", "Salt Lake City, UT",        lat=41.2628,  lon=-112.4481,  elevation_m=1969.0, site_type="wsr88d"),
    Site("KMUX", "San Francisco, CA",         lat=37.1553,  lon=-121.8983,  elevation_m=1057.0, site_type="wsr88d"),
    Site("KMVX", "Grand Forks, ND",           lat=47.5281,  lon=-97.3253,   elevation_m=300.0,  site_type="wsr88d"),
    Site("KMXX", "Maxwell AFB, AL",           lat=32.5367,  lon=-85.7897,   elevation_m=125.0,  site_type="wsr88d"),
    Site("KNKX", "San Diego, CA",             lat=32.9189,  lon=-117.0419,  elevation_m=293.0,  site_type="wsr88d"),
    Site("KNQA", "Memphis, TN",               lat=35.3447,  lon=-89.8733,   elevation_m=84.0,   site_type="wsr88d"),
    Site("KOAX", "Omaha, NE",                 lat=41.3203,  lon=-96.3664,   elevation_m=350.0,  site_type="wsr88d"),
    Site("KOHX", "Nashville, TN",             lat=36.2472,  lon=-86.5625,   elevation_m=177.0,  site_type="wsr88d"),
    Site("KOKX", "New York City, NY",         lat=40.8656,  lon=-72.8644,   elevation_m=26.0,   site_type="wsr88d"),
    Site("KOTX", "Spokane, WA",               lat=47.6803,  lon=-117.6267,  elevation_m=726.0,  site_type="wsr88d"),
    Site("KPAH", "Paducah, KY",               lat=37.0683,  lon=-88.7717,   elevation_m=119.0,  site_type="wsr88d"),
    Site("KPBZ", "Pittsburgh, PA",            lat=40.5317,  lon=-80.2181,   elevation_m=361.0,  site_type="wsr88d"),
    Site("KPDT", "Pendleton, OR",             lat=45.6906,  lon=-118.8525,  elevation_m=461.0,  site_type="wsr88d"),
    Site("KPOE", "Fort Polk, LA",             lat=31.1556,  lon=-92.9761,   elevation_m=98.0,   site_type="wsr88d"),
    Site("KPUX", "Pueblo, CO",                lat=38.4595,  lon=-104.1811,  elevation_m=1624.0, site_type="wsr88d"),
    Site("KRAX", "Raleigh/Durham, NC",        lat=35.6656,  lon=-78.4897,   elevation_m=105.0,  site_type="wsr88d"),
    Site("KRGX", "Reno, NV",                  lat=39.7542,  lon=-119.4611,  elevation_m=2530.0, site_type="wsr88d"),
    Site("KRIW", "Riverton, WY",              lat=43.0661,  lon=-108.4772,  elevation_m=1697.0, site_type="wsr88d"),
    Site("KRLX", "Charleston, WV",            lat=38.3111,  lon=-81.7228,   elevation_m=329.0,  site_type="wsr88d"),
    Site("KSFX", "Pocatello, ID",             lat=43.1056,  lon=-112.6861,  elevation_m=1364.0, site_type="wsr88d"),
    Site("KSGF", "Springfield, MO",           lat=37.2353,  lon=-93.4006,   elevation_m=390.0,  site_type="wsr88d"),
    Site("KSHV", "Shreveport, LA",            lat=32.4508,  lon=-93.8411,   elevation_m=83.0,   site_type="wsr88d"),
    Site("KSJT", "San Angelo, TX",            lat=31.3711,  lon=-100.4922,  elevation_m=576.0,  site_type="wsr88d"),
    Site("KSOX", "Santa Ana Mountains, CA",   lat=33.8178,  lon=-117.6361,  elevation_m=948.0,  site_type="wsr88d"),
    Site("KSRX", "Fort Smith, AR",            lat=35.2906,  lon=-94.3619,   elevation_m=197.0,  site_type="wsr88d"),
    Site("KTBW", "Tampa, FL",                 lat=27.7056,  lon=-82.4017,   elevation_m=14.0,   site_type="wsr88d"),
    Site("KTFX", "Great Falls, MT",           lat=47.4597,  lon=-111.3856,  elevation_m=1132.0, site_type="wsr88d"),
    Site("KTLH", "Tallahassee, FL",           lat=30.3978,  lon=-84.3289,   elevation_m=19.0,   site_type="wsr88d"),
    Site("KTLX", "Oklahoma City, OK",         lat=35.3331,  lon=-97.2778,   elevation_m=370.0,  site_type="wsr88d"),
    Site("KTWX", "Topeka, KS",                lat=38.9969,  lon=-96.2325,   elevation_m=418.0,  site_type="wsr88d"),
    Site("KTYX", "Montague, NY",              lat=43.7556,  lon=-75.6800,   elevation_m=562.0,  site_type="wsr88d"),
    Site("KUDX", "Rapid City, SD",            lat=44.1247,  lon=-102.8297,  elevation_m=918.0,  site_type="wsr88d"),
    Site("KUEX", "Hastings, NE",              lat=40.3211,  lon=-98.4417,   elevation_m=602.0,  site_type="wsr88d"),
    Site("KVAX", "Moody AFB, GA",             lat=30.8903,  lon=-83.0019,   elevation_m=55.0,   site_type="wsr88d"),
    Site("KVBX", "Vandenberg AFB, CA",        lat=34.8381,  lon=-120.3981,  elevation_m=373.0,  site_type="wsr88d"),
    Site("KVNX", "Vance AFB, OK",             lat=36.7408,  lon=-98.1278,   elevation_m=369.0,  site_type="wsr88d"),
    Site("KVTX", "Los Angeles, CA",           lat=34.4117,  lon=-119.1794,  elevation_m=831.0,  site_type="wsr88d"),
    Site("KVWX", "Evansville, IN",            lat=38.2600,  lon=-87.7242,   elevation_m=178.0,  site_type="wsr88d"),
    Site("KYUX", "Yuma, AZ",                  lat=32.4953,  lon=-114.6558,  elevation_m=53.0,   site_type="wsr88d"),

    # ── Alaska WSR-88D ─────────────────────────────────────────────────────────
    Site("PABC", "Bethel, AK",                lat=60.7922,  lon=-161.8764,  elevation_m=51.0,   site_type="wsr88d"),
    Site("PACG", "Sitka, AK",                 lat=56.8528,  lon=-135.5292,  elevation_m=68.0,   site_type="wsr88d"),
    Site("PAEC", "Nome, AK",                  lat=64.5114,  lon=-165.2950,  elevation_m=19.0,   site_type="wsr88d"),  # TODO: verify
    Site("PAHG", "Anchorage, AK",             lat=60.7258,  lon=-151.3514,  elevation_m=246.0,  site_type="wsr88d"),
    Site("PAIH", "Middleton Island, AK",      lat=59.4614,  lon=-146.3006,  elevation_m=19.0,   site_type="wsr88d"),
    Site("PAKC", "King Salmon, AK",           lat=58.6794,  lon=-156.6294,  elevation_m=62.0,   site_type="wsr88d"),
    Site("PAPD", "Fairbanks, AK",             lat=65.0353,  lon=-147.5008,  elevation_m=790.0,  site_type="wsr88d"),

    # ── Hawaii WSR-88D ─────────────────────────────────────────────────────────
    Site("PHKI", "South Kauai, HI",           lat=21.8944,  lon=-159.5525,  elevation_m=179.0,  site_type="wsr88d"),
    Site("PHKM", "Kohala, HI",                lat=20.1256,  lon=-155.7783,  elevation_m=1167.0, site_type="wsr88d"),
    Site("PHMO", "Molokai, HI",               lat=21.1328,  lon=-157.1800,  elevation_m=410.0,  site_type="wsr88d"),
    Site("PHWA", "South Point, HI",           lat=19.0950,  lon=-155.5689,  elevation_m=422.0,  site_type="wsr88d"),

    # ── Puerto Rico WSR-88D ────────────────────────────────────────────────────
    Site("TJUA", "San Juan, PR",              lat=18.1156,  lon=-66.0781,   elevation_m=858.0,  site_type="wsr88d"),

    # ── Guam WSR-88D ──────────────────────────────────────────────────────────
    Site("PGUA", "Guam",                      lat=13.4544,  lon=144.8114,   elevation_m=74.0,   site_type="wsr88d"),

    # ── TDWR sites (n_azimuths=360) ────────────────────────────────────────────
    # Source: FAA TDWR site list
    Site("TATL", "Atlanta, GA",               lat=33.6367,  lon=-84.4281,   elevation_m=316.0,  site_type="tdwr", n_azimuths=360),
    Site("TBNA", "Nashville, TN",             lat=36.0739,  lon=-86.7503,   elevation_m=214.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TBOS", "Boston, MA",                lat=42.1675,  lon=-71.0033,   elevation_m=18.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TBWI", "Baltimore/Washington, MD",  lat=39.1019,  lon=-76.8914,   elevation_m=46.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TBUF", "Buffalo, NY",               lat=42.9400,  lon=-78.7319,   elevation_m=213.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TCLE", "Cleveland, OH",             lat=41.5078,  lon=-81.6831,   elevation_m=239.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TCRW", "Charlotte, NC",             lat=35.2144,  lon=-80.9431,   elevation_m=236.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TCVG", "Cincinnati, OH",            lat=39.0481,  lon=-84.6681,   elevation_m=270.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TADW", "Andrews AFB, MD",           lat=38.6953,  lon=-76.8453,   elevation_m=86.0,   site_type="tdwr", n_azimuths=360),
    Site("TDAY", "Dayton, OH",                lat=39.9019,  lon=-84.2192,   elevation_m=306.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TDEN", "Denver, CO",                lat=39.8561,  lon=-104.6561,  elevation_m=1655.0, site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TDET", "Detroit, MI",               lat=42.2119,  lon=-83.3539,   elevation_m=195.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TDFW", "Dallas/Fort Worth, TX",     lat=32.8978,  lon=-97.0311,   elevation_m=179.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TIAD", "Dulles/Washington, VA",     lat=38.9444,  lon=-77.4569,   elevation_m=91.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TIDS", "Indianapolis, IN",          lat=39.7325,  lon=-86.2942,   elevation_m=247.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TJFK", "New York JFK, NY",          lat=40.6214,  lon=-73.7789,   elevation_m=9.0,    site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TKCI", "Kansas City, MO",           lat=39.2978,  lon=-94.7139,   elevation_m=313.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TLAS", "Las Vegas, NV",             lat=36.0828,  lon=-115.1525,  elevation_m=645.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TLAX", "Los Angeles, CA",           lat=33.9425,  lon=-118.4081,  elevation_m=35.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMCO", "Orlando, FL",               lat=28.4292,  lon=-81.3089,   elevation_m=30.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMDW", "Chicago Midway, IL",        lat=41.7858,  lon=-87.7517,   elevation_m=186.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMEM", "Memphis, TN",               lat=35.0425,  lon=-89.9767,   elevation_m=87.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMIA", "Miami, FL",                 lat=25.9075,  lon=-80.2789,   elevation_m=3.0,    site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMKE", "Milwaukee, WI",             lat=42.9469,  lon=-87.8975,   elevation_m=205.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMSP", "Minneapolis, MN",           lat=44.8819,  lon=-93.2289,   elevation_m=274.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TMSY", "New Orleans, LA",           lat=29.9933,  lon=-90.2589,   elevation_m=2.0,    site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TOMA", "Omaha, NE",                 lat=41.3025,  lon=-96.0119,   elevation_m=366.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TORD", "Chicago O'Hare, IL",        lat=41.9742,  lon=-87.9075,   elevation_m=203.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TPHL", "Philadelphia, PA",          lat=39.8714,  lon=-75.2411,   elevation_m=28.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TPHX", "Phoenix, AZ",               lat=33.4289,  lon=-112.0156,  elevation_m=337.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TPIT", "Pittsburgh, PA",            lat=40.4914,  lon=-80.2325,   elevation_m=367.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TPVD", "Providence, RI",            lat=41.7239,  lon=-71.4281,   elevation_m=17.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TRDU", "Raleigh/Durham, NC",        lat=35.8778,  lon=-78.7875,   elevation_m=133.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TSDF", "Louisville, KY",            lat=38.1742,  lon=-85.7361,   elevation_m=149.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TSEA", "Seattle, WA",               lat=47.4431,  lon=-122.3014,  elevation_m=110.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TSJC", "San Jose, CA",              lat=37.3625,  lon=-121.9281,  elevation_m=14.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TSJU", "San Juan, PR",              lat=18.4394,  lon=-66.0014,   elevation_m=3.0,    site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TSLC", "Salt Lake City, UT",        lat=40.7789,  lon=-111.9619,  elevation_m=1288.0, site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TSTL", "St. Louis, MO",             lat=38.7489,  lon=-90.3703,   elevation_m=142.0,  site_type="tdwr", n_azimuths=360),  # TODO: verify
    Site("TTPA", "Tampa, FL",                 lat=27.9742,  lon=-82.5331,   elevation_m=10.0,   site_type="tdwr", n_azimuths=360),  # TODO: verify
]
# fmt: on

SITE_BY_ICAO: dict[str, Site] = {s.icao: s for s in SITES}
