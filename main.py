from json import dump, load
from urllib import parse
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

import requests


def get_text(id):
    addon = xbmcaddon.Addon(id=PLUGIN_ID)
    return addon.getLocalizedString(id).encode('utf-8')

def build_url(base_url, query):
    return f"{base_url}?{parse.urlencode(query)}"

def get_argument(arguments, text):
    argument = arguments.get(text, None)
    if argument:
        argument = argument[0]
    return argument

def add_directory(base_url, addon_handle, name: str, attributes: dict):
    localUrl = build_url(
        base_url,
        attributes
    )
    list_item = xbmcgui.ListItem(name)
    list_item.setArt(
        {
            "icon": "DefaultFolder.png"
        }
    )
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=list_item, isFolder=True)

def add_index_item(base_url, addon_handle, text_id: int, route: str):
    attributes = {
        "route": route
    }
    add_directory(base_url, addon_handle, get_text(text_id), attributes)

def add_station_item(base_url, addon_handle, route, station, is_my_station: bool = False):
    name = station["name"]
    favicon = station["favicon"]
    bitrate = station["bitrate"]
    stationuuid = station["stationuuid"]
    localUrl = build_url(
        base_url,
        {
            "route": route,
            "stationuuid": stationuuid
        }
    )
    list_item = xbmcgui.ListItem(name)
    list_item.setArt(
        {
            "icon": favicon,
            "thumb": favicon
        }
    )
    list_item.setProperty('IsPlayable', 'true')
    list_item.setInfo(
        type="music",
        infoLabels={
            "size":bitrate
        }
    )
    music_info = list_item.getMusicInfoTag()
    music_info.setTitle(name)

    if not is_my_station:
        contextUrl = build_url(
            base_url,
            {
                "route": "add_station",
                "stationuuid": stationuuid
            }
        )
        list_item.addContextMenuItems([(get_text(32010), 'RunPlugin(%s)'%(contextUrl))])
    else:
        contextUrl = build_url(
            base_url,
            {
                "route": "remove_station",
                "stationuuid": stationuuid
            }
        )
        list_item.addContextMenuItems([(get_text(32009), 'RunPlugin(%s)'%(contextUrl))])

    xbmcplugin.addDirectoryItem(handle=addon_handle, url=localUrl, listitem=list_item, isFolder=False)

def add_stations(endpoint):
    stations = request_radio_browser_api(endpoint)
    for station in stations:
        add_station_item(base_url, addon_handle, "play",station)

    xbmcplugin.endOfDirectory(addon_handle)


def index(base_url, addon_handle):
    add_index_item(base_url, addon_handle, 32008, "mystations")
    add_index_item(base_url, addon_handle, 32007, "search")
    add_index_item(base_url, addon_handle, 32000, "topclick")
    add_index_item(base_url, addon_handle, 32001, "topvote")
    add_index_item(base_url, addon_handle, 32002, "lastchange")
    add_index_item(base_url, addon_handle, 32003, "lastclick")
    add_index_item(base_url, addon_handle, 32004, "tags")
    add_index_item(base_url, addon_handle, 32005, "countries")
    xbmcplugin.endOfDirectory(addon_handle)

def request_radio_browser_api(endpoint):
    radio_browser_url = "https://all.api.radio-browser.info"
    request = f"{radio_browser_url}{endpoint}"
    xbmc.log(f"[ {request} ] Request URL")
    response = requests.get(request)
    response.raise_for_status()
    return response.json()


def load_my_stations():
    my_stations = {}
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdir(PROFILE)

    if xbmcvfs.exists(MY_STATIONS_PATHS):
        with xbmcvfs.File(MY_STATIONS_PATHS, "r") as my_stations_file:
            my_stations = load(my_stations_file)

    if "stations" not in my_stations:
        my_stations["stations"] = []
    return my_stations

def router(base_url, addon_handle, arguments):
    route = get_argument(arguments, "route")

    if route == "mystations":
        my_stations = load_my_stations()
        for station in my_stations["stations"]:
            station = request_radio_browser_api(f"/json/stations/byuuid/{station}")[0]
            add_station_item(base_url, addon_handle, "play", station, is_my_station = True)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if route == "add_station":
        stationuuid = get_argument(arguments, "stationuuid")
        my_stations = load_my_stations()
        if stationuuid not in my_stations["stations"]:
            my_stations["stations"].append(stationuuid)

        with xbmcvfs.File(MY_STATIONS_PATHS, "w") as my_stations_file:
            dump(my_stations, my_stations_file)

        return

    if route == "remove_station":
        stationuuid = get_argument(arguments, "stationuuid")
        my_stations = load_my_stations()
        my_stations["stations"].remove(stationuuid)

        with xbmcvfs.File(MY_STATIONS_PATHS, "w") as my_stations_file:
            dump(my_stations, my_stations_file)

        xbmc.executebuiltin("Container.Refresh")
        return

    if route == "search":
        dialog = xbmcgui.Dialog()
        search_query = dialog.input(get_text(32011), type=xbmcgui.INPUT_ALPHANUM)
        add_stations(f"/json/stations/byname/{search_query}?order=clickcount&reverse=true&hidebroken=true")
        return

    if route == "topclick":
        add_stations("/json/stations/topclick/100")
        return

    if route == "topvote":
        add_stations("/json/stations/topvote/100")
        return

    if route == "lastchange":
        add_stations("/json/stations/lastchange/100")
        return

    if route == "lastclick":
        add_stations("/json/stations/lastclick/100")
        return

    if route == "tag":
        tag = get_argument(arguments, "tag")
        add_stations(f"/json/stations/search?tag={tag}&tagExact=true&order=clickcount&reverse=true&hidebroken=true")
        return

    if route == "country":
        countrycode = get_argument(arguments, "countrycode")
        add_stations(f"/json/stations/search?countrycode={countrycode}&order=clickcount&reverse=true&hidebroken=true")
        return

    if route == "play":
        stationuuid = get_argument(arguments, "stationuuid")
        station = request_radio_browser_api(f"/json/stations/byuuid/{stationuuid}")[0]
        list_item = xbmcgui.ListItem(path=station["url"])
        list_item.setArt(
            {
                "thumb": station["favicon"]
            }
        )
        xbmcplugin.setResolvedUrl(addon_handle, True, list_item)
        return

    if route == "tags":
        tags = request_radio_browser_api("/json/tags")

        for tag in tags:
            attributes = {
                "route": "tag",
                "tag": tag["name"]
            }
            add_directory(base_url, addon_handle, tag["name"], attributes)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    if route == "countries":
        countries = request_radio_browser_api("/json/countries")

        for country in countries:
            attributes = {
                "route": "country",
                "countrycode": country["iso_3166_1"]
            }
            add_directory(base_url, addon_handle, country["name"], attributes)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    index(base_url, addon_handle)
    return

if __name__ == "__main__":
    PLUGIN_ID = "plugin.audio.radiobrowser"
    PROFILE = f"special://profile/addon_data/{PLUGIN_ID}"
    MY_STATIONS_PATHS = f"{PROFILE}/mystations.json"
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    xbmcplugin.setContent(addon_handle, 'songs')
    arguments = parse.parse_qs(sys.argv[2][1:])

    router(base_url, addon_handle, arguments)
