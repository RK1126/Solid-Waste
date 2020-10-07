import RoutingAndScheduling as RaS
import SpiderAllocation as Sa
import MyDatabase as mDB
import globals as gb

import datetime as dt
import pandas as pd
import numpy as np


prey_id_list = mDB.silk_node_list['Prey-Id'].tolist()

current_time = dt.datetime(year=2019, month=1, day=1, hour=6, minute=0, second=0, microsecond=0)


def prey_vibration_generator():
    num = np.random.randint(0, len(prey_id_list))
    if prey_id_list[num] != 'Dumpyard':
        return prey_id_list[num]
    else:
        prey_vibration_generator()


def day_end(c_time):
    spiders_id = gb.waiting_spider_list['Spider-Id'][gb.waiting_spider_list['Capacity'] < 8]
    RaS.ready_spiders(spiders_id, c_time, True)
    c_time = c_time + dt.timedelta(days=1)
    c_time = c_time.replace(hour=6, minute=0, second=0)
    gb.waiting_spider_list = gb.spiders_list(3, c_time, init_x=[550, 1691, 1130], init_y=[1522, 940, 1297])
    gb.prey_already_sent_signal = []
    mDB.prey_signal_generated_record = mDB.prey_signal_generated_record.iloc[0:0]
    return c_time


def clock(count, rand_num):

    while True:
        global current_time
        current_time = current_time + dt.timedelta(minutes=1)
        var = np.random.randint(1, 10)
        if var == 1:
            prey_id = prey_vibration_generator()
            if prey_id not in gb.prey_already_sent_signal:  # make it more random
                if prey_id is not None:
                    print(current_time.date(), ';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;')
                    df = pd.DataFrame({'Prey-Id': prey_id, 'Signal-Time': current_time, 'Spider_allocated': False},
                                      index=[0])
                    mDB.prey_signal_generated_record = mDB.prey_signal_generated_record.append(df, ignore_index=True,
                                                                                               sort=False)
                    gb.prey_already_sent_signal.append(prey_id)

                    count = count + 1
                    Sa.allocation([prey_id, current_time])

        RaS.hunting(current_time)
        if count == rand_num:  # day off
            break


def start():
    while True:
        global current_time
        count = 0
        rand_num = np.random.randint(40, 60)
        clock(count, rand_num)
        current_time = day_end(current_time)


if __name__ == "__main__":

    start()
