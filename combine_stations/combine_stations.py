# !/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from six.moves import range

# standard library imports
import json  # for working with data files

# local module imports
from blinker import signal  # To receive station notifications
from sip import template_render  #  Needed for working with web.py templates
from gpio_pins import set_output
import gv  # Get access to SIP's settings
from urls import urls  # Get access to SIP's URLs
import web  # web.py framework
import webpages as wp
from webpages import ProtectedPage  # Needed for security

skip = 0

# Add new URLs to access classes in this plugin.
# fmt: off
urls.extend([
    u"/combine-sp", u"plugins.combine_stations.settings",
    u"/combine-save", u"plugins.combine_stations.save_settings"
    ])
# fmt: on

# Add this plugin to the PLUGINS menu ["Menu Name", "URL"], (Optional)
gv.plugin_menu.append([_(u"Combine Stations"), u"/combine-sp"])

com_stations = {}

def load_settings():
    """
    Load virtual station settings from json file.
    """
    global com_stations
    try:
        with open(
            u"./data/combine.json", u"r"
        ) as f:  # Read settings from json file if it exists
            com_stations = json.load(f)
            try:
                for key in com_stations:
                    if com_stations[key]:
                        gv.snames[int(key)] = u'V' + str(int(key) + 1) + u' runs ' +  com_stations[key]
                    else:
                        gv.snames[int(key)] = u'S' + str(int(key) + 1)
            except:
                pass
    except IOError:  # If file does not exist return empty value
        com_stations = {}
        
def set_stations(virt):
    """
    Astivate stations associated with a virtual station.
    Selected stations wil run concurrently.
    """
    global skip #  prevent endless recursion

    if not skip:
        vid = ((gv.sd['nbrd'] - 1) * 8) + virt
        print("ready to set stations uaing stations ", com_stations[str(vid)])  # - test
        for b in range(gv.sd[u"nbrd"] - 1):
            stn_list = [int(i) - 1 for i in com_stations[str(vid)].split(",")]
            for sid in stn_list:
                gv.srvals[sid] = 1 #  used to turn zones on or off (list of one byte per station, 1 = turn on, 0 = turn off)
                gv.sbits[b] |= 1 << sid #  station bits, used to display stations that are on in UI (list of bytes, one byte per board)
                gv.ps[sid][0] = 1 #  program schedule used for UI display (list of 2 element lists i.e. [program number, duration])
                if not gv.sd[u'mm']:
                    gv.sbits[b] &= 1 << vid #  station bits, used to display stations that are on in UI (list of bytes, one byte per board)
                    gv.rs[sid][1] =  gv.rs[vid][1]  #  run schedule (list [scheduled start time, scheduled stop time, duration, program number])
            skip = 1
            set_output()
    else:
        skip = 0


class settings(ProtectedPage):
    """
    Load an html page for entering plugin settings.
    """
    def GET(self):
        return template_render.combine_stations(com_stations)  # open settings page


class save_settings(ProtectedPage):
    """
    Save user input to json file.
    Will create or update file when SUBMIT button is clicked
    CheckBoxes only appear in qdict if they are checked.
    """
    def GET(self):
        qdict = (
            web.input()
        )  # Dictionary of values returned as query string from settings page.
        with open(u"./data/combine.json", u"w") as f:
            json.dump(qdict, f)  # save to file
        load_settings()
        raise web.seeother(u"/")  # Return user to home page.
    
### Control valves ###
def modify_zone_change(name, **kw):
    if gv.sd[u'seq']: #  if in sequential mode.      
        virtuals = gv.srvals[-8:]
        virt = next((i for i, x in enumerate(virtuals) if x), None)
        if virt is not None:
            set_stations(virt)    

zones = signal(u"zone_change")
zones.connect(modify_zone_change)    


#  Run when plugin is loaded
load_settings()
