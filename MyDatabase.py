import RoutingAndScheduling as RaS
import datetime as dt
import globals as gb
import pandas as pd
import math

spider_daily_record_table = pd.DataFrame(columns=['Spider-Id', 'Date', 'Init X', 'Init Y', 'Departure Time', 'Distance',
                                                  'Working Time'])  # working time in minutes
spider_nodes_visited = pd.DataFrame(columns=['Spider-Id', 'Date', 'Node-Id', 'Trip No'])
spider_nodes_visited['Date'] = spider_nodes_visited['Date'].astype('datetime64[ns]')
spider_prey_relation_table = pd.DataFrame(columns=['Prey-Id', 'SA Date-Time', 'Signal Time', 'Spider-Id',
                                                   'Distance From Spider', 'Trip No'])
emergency_table = pd.DataFrame(columns=['Prey-Id', 'Date-Time', 'Signal-Time', 'Max-Radius', 'Spider-Id'])
prey_signal_generated_record = pd.DataFrame(columns=['Prey-Id', 'Signal-Time', 'Spider_allocated'])

# database queries


def a_prey_priority(prey_id):
    return int(RaS.silk_node_list.where(RaS.silk_node_list['Prey-Id'] == prey_id).dropna()['Priority'])


def a_spider_location_id(spider_id):
    s_x, s_y = gb.waiting_spider_list[['X', 'Y']][gb.waiting_spider_list['Spider-Id'] == spider_id].values[0]
    return a_spider_location_id_based_on_coordinates(s_x, s_y)


def a_spider_location_id_based_on_coordinates(s_x, s_y):
    return RaS.silk_node_list['Prey-Id'][(RaS.silk_node_list['X'] == s_x) & (RaS.silk_node_list['Y'] == s_y)].values[0]


def a_spider_coordinates_based_on_location_id(spider_location_id):
    s_x, s_y = RaS.silk_node_list[['X', 'Y']][RaS.silk_node_list['Prey-Id'] == spider_location_id].values[0]
    return s_x, s_y


def a_spider_capacity(spider_id):
    return gb.waiting_spider_list['Capacity'][gb.waiting_spider_list['Spider-Id'] == spider_id].values[0]


def update_scheduling_time(current_sch_time, new_sch_time, spider_id):
    current_sch_time = pd.to_datetime(current_sch_time)
    if (current_sch_time == gb.system_init_time) | (current_sch_time > new_sch_time):
        gb.waiting_spider_list.loc[gb.waiting_spider_list['Spider-Id'] == spider_id, ['Scheduling Time']] = new_sch_time


def update_spider_capacity(spider_id):
    updated_spider_cap = gb.waiting_spider_list['Capacity'][gb.waiting_spider_list['Spider-Id']
                                                            == spider_id] - gb.prey_size
    gb.waiting_spider_list.loc[gb.waiting_spider_list['Spider-Id'] == spider_id, ['Capacity']] \
        = round(updated_spider_cap, 2)


def attack_on_prey_order(spider_id, c_time):  # working
    spider_waiting_from = gb.waiting_spider_list['Waiting From Time'][gb.waiting_spider_list['Spider-Id']
                                                                      == spider_id].values[0]
    preys_for_spider = spider_prey_relation_table[(spider_prey_relation_table['Spider-Id'] == spider_id) &
                                                  (pd.to_datetime(spider_prey_relation_table['Signal Time']).dt.date
                                                   == c_time.date()) &
                                                  (pd.to_datetime(spider_prey_relation_table['Signal Time']) >=
                                                   pd.to_datetime(spider_waiting_from))]
    if preys_for_spider.shape[0] > 0:
        df = pd.merge(preys_for_spider, RaS.silk_node_list, how='left', left_on='Prey-Id', right_on='Prey-Id')
        df.sort_values(['Signal Time', 'Priority', 'Distance From Spider'], inplace=True)
        return df['Prey-Id']
    else:
        return None


def spider_daily_record_init(spider_id, c_time):  # register spider per day to this table
    global spider_daily_record_table
    new_spiders = gb.waiting_spider_list[(gb.waiting_spider_list['Spider-Id'] == spider_id) &
                                         (~gb.waiting_spider_list['Spider in Allocation'])
                                         & (gb.waiting_spider_list['Available'])]
    if new_spiders.shape[0] > 0:
        waiting_time, available = new_spiders[['Waiting From Time', 'Available']][new_spiders['Spider-Id']
                                                                                  == spider_id].values[0]

        if (waiting_time <= c_time) & (available is True):
            spider_today_entry_in_table = spider_daily_record_table[(pd.to_datetime(spider_daily_record_table['Date'])
                                                                     .dt.date == c_time.date()) &
                                                                    (spider_daily_record_table['Spider-Id'] == spider_id)]
            if spider_today_entry_in_table.shape[0] == 0:
                spider_x, spider_y = new_spiders[['X', 'Y']].loc[new_spiders['Spider-Id'] == spider_id].values[0]
                df = pd.DataFrame([[spider_id, c_time.date(), spider_x, spider_y]],
                                  columns=['Spider-Id', 'Date', 'Init X', 'Init Y'])
                spider_daily_record_table = spider_daily_record_table.append(df, ignore_index=True, sort=False)


def save_to_file(df, filename):
    if gb.write_header:
        with open(filename, 'a') as f:
            df.to_csv(f, header=True, index=False)
    else:
        with open(filename, 'a') as f:
            df.to_csv(f, header=False, index=False)


def save_spider_prey_relation_table(c_time):
    global spider_prey_relation_table
    yesterday_data = spider_prey_relation_table[pd.to_datetime(spider_prey_relation_table['Signal Time']).dt.date <
                                                c_time.date()]
    spider_prey_relation_table = spider_prey_relation_table[~spider_prey_relation_table['Signal Time'].isin(
                                                            yesterday_data['Signal Time'].tolist())]

    save_to_file(yesterday_data, 'spider_prey_relation_table.csv')


def save_spider_nodes_visited(c_time):
    global spider_nodes_visited
    yesterday_data = spider_nodes_visited[spider_nodes_visited['Date'] < c_time.date()]
    spider_nodes_visited = spider_nodes_visited[~pd.to_datetime(spider_nodes_visited['Date']).isin(yesterday_data['Date'].tolist())]

    save_to_file(yesterday_data, 'spider_nodes_visited.csv')


def save_emergency_table(c_time):
    global emergency_table
    yesterday_data = emergency_table[pd.to_datetime(emergency_table['Signal-Time']).dt.date < c_time.date()]
    emergency_table = emergency_table[~emergency_table['Signal-Time'].isin(yesterday_data['Signal-Time'].tolist())]

    save_to_file(yesterday_data, 'emergency.csv')


def total_distance_travelled(spider_id, c_time):
    try:
        total_distance_t = float(spider_daily_record_table['Distance'][(spider_daily_record_table['Spider-Id'] ==
                                                                        spider_id) & (pd.to_datetime(spider_daily_record_table['Date']).dt.date
                                                                                      == c_time.date())].values[0])
    except IndexError:
        total_distance_t = 0
    if math.isnan(total_distance_t):
        total_distance_t = 0

    return total_distance_t


def today_working_time(spider_id, c_time):
    working_time_of_today = spider_daily_record_table['Working Time'][
        (spider_daily_record_table['Spider-Id'] == spider_id) & (spider_daily_record_table['Date'] == c_time.date())].values[0]

    if not isinstance(working_time_of_today, dt.timedelta):
        working_time_of_today = dt.timedelta(seconds=0)

    return working_time_of_today

