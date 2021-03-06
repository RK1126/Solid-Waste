# for all global
import datetime as dt
import pandas as pd
import numpy as np

system_init_time = dt.datetime(year=2019, month=1, day=1, hour=6, minute=0, second=0)

write_header = True


def spiders_list(total_number_of_spiders=3, c_time=system_init_time, init_x=(3164,), init_y=(1111,)):

    spiders = pd.DataFrame(columns=['Trip No'])
    spiders['Spider-Id'] = list(range(total_number_of_spiders))
    spiders['X'] = init_x  # current location
    spiders['Y'] = init_y
    spiders['Spider-Location-Id'] = 'Dumpyard'
    spiders['Available'] = True
    spiders['Waiting From Time'] = c_time
    spiders['Scheduling Time'] = system_init_time  # when spider should start scheduling
    spiders['Journey Started'] = system_init_time  # first time the truck started journey
    spiders['Capacity'] = 8  # cubic meter
    spiders['Spider in Allocation'] = False  # already allocated some and has some space still
    return spiders


avg_speed = 200  # (12km/hr)

prey_size = 0.66  # cubic meter

waiting_spider_list = spiders_list(3, init_x=[550, 1691, 1130], init_y=[1522, 940, 1297])  # a data frame


prey_already_sent_signal = []


def update_trip_id(spider_id, c_time):

    trip_id = get_trip_id(spider_id, c_time)
    trip_id = trip_id + 1
    waiting_spider_list.loc[(waiting_spider_list['Spider-Id'] == spider_id) &
                            (pd.to_datetime(waiting_spider_list['Waiting From Time']).dt.date == c_time.date()),
                            ['Trip No']] = trip_id


def get_trip_id(spider_id, c_time):
    x = waiting_spider_list['Trip No'][(waiting_spider_list['Spider-Id'] == spider_id) &
                                       (pd.to_datetime(waiting_spider_list['Waiting From Time']).dt.date
                                        == c_time.date())].values[0]
    if np.isnan(x):
        return 1
    return int(x)
