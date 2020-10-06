from sklearn.neighbors import NearestNeighbors
import RoutingAndScheduling as RaS
import MyDatabase as mDB
import datetime as dt
import globals as gb
import pandas as pd
import snoop


def emergency(prey_id, prey_vibration_generate_at, c_time, max_radius=4000):
    count = 0
    spider_id = None
    while True:
        spiders = nearer_spider(prey_id, max_radius=max_radius, maximum_number_of_spider=2, min_radius=2200)
        count = count + 1
        if spiders.shape[0] > 0:
            a_spider_id = hungry_level(spiders)

            if a_spider_id:
                allocated = spider_in_allocation(prey_id, prey_vibration_generate_at, a_spider_id, c_time)
                if allocated:
                    spider_id = a_spider_id
                    break
                else:
                    min_radius = max_radius
                    max_radius = max_radius + 500
            else:
                min_radius = max_radius
                max_radius = max_radius + 500
        else:
            min_radius = max_radius
            max_radius = max_radius + 500

        if count >= 2:
            break

    if count >= 2:
        max_radius = None

        prey_size = gb.prey_size
        spiders = gb.waiting_spider_list[(gb.waiting_spider_list['Available']) &
                                         (gb.waiting_spider_list['Capacity'] >=
                                          prey_size)].sort_values(by='Waiting From Time')
        if spiders.shape[0] > 0:
            spider_id = spiders['Spider-Id'].iloc[0]

            status = spider_in_allocation(prey_id, prey_vibration_generate_at, spider_id, c_time)
            if not status:
                spider_id = None
    df = pd.DataFrame([[prey_id, c_time, prey_vibration_generate_at, max_radius, spider_id]],
                      columns=['Prey-Id', 'Date-Time', 'Signal-Time', 'Max-Radius', 'Spider-Id'])
    mDB.emergency_table = mDB.emergency_table.append(df, ignore_index=True, sort=False)


def waiting_time(location_id, token):
    n = []
    if token == 'p':
        n = (20, 30, 60)  # waiting_time_for_prey
    elif token == 's':
        n = (2, 5, 10)  # waiting_time_for_spider in mid way
    prey_priority = mDB.a_prey_priority(location_id)
    if prey_priority == 1:
        waiting_time = dt.timedelta(minutes=n[0])
    elif prey_priority == 2:
        waiting_time = dt.timedelta(minutes=n[1])
    else:
        waiting_time = dt.timedelta(minutes=n[2])

    return waiting_time


def scheduling_time(prey_id, spider_in_mid_way, spider_id, c_time):  # distance from prey
    spider_loc_id = mDB.a_spider_location_id(spider_id)
    distance_from_prey = distance(spider_id, prey_id)

    time_to_reach_prey = dt.timedelta(minutes=distance_from_prey / gb.avg_speed)

    maximum_time_a_prey_can_wait = waiting_time(prey_id, 'p')

    if spider_in_mid_way is False:
        maximum_time_a_spider_can_wait = waiting_time(spider_loc_id, 's')
        time_before_scheduling = maximum_time_a_prey_can_wait - time_to_reach_prey
        if maximum_time_a_spider_can_wait < time_before_scheduling:
            time = maximum_time_a_spider_can_wait
        else:
            time = time_before_scheduling
    else:
        time = maximum_time_a_prey_can_wait - time_to_reach_prey

    return c_time + time

#@snoop
def distance(spider_id, prey_id):
    spider_loc_id = mDB.a_spider_location_id(spider_id)
    if spider_loc_id == prey_id:
        return 0
    else:
        dis = RaS.shortest_path_length(mDB.a_spider_location_id(spider_id), prey_id)
    return dis


def nearer_spider(prey_id, max_radius=2000, maximum_number_of_spider=5, min_radius=200):  # nearest three truck
    prey_x, prey_y = mDB.silk_node_list[['X', 'Y']][mDB.silk_node_list['Prey-Id'] == prey_id].values[0]
    dff = pd.DataFrame()
    for i in range(min_radius, max_radius, 200):
        nn = NearestNeighbors(radius=i, n_neighbors=maximum_number_of_spider)
        df = gb.waiting_spider_list[['X', 'Y']]
        nn.fit(df)
        points = nn.radius_neighbors([[prey_x, prey_y]])
        dff = pd.DataFrame(points[1][0], points[0][0])
        if 1 <= dff.shape[0]:

            dff['Distance'] = dff.index
            dff.sort_values(by=['Distance'], inplace=True)
            dff.reset_index(drop=True, inplace=True)
            dff = pd.merge(dff, gb.waiting_spider_list, left_on=[0], right_on=gb.waiting_spider_list.index,
                           how='inner').drop(columns=[0])
            break
    return dff[0:3]


def is_spider_in_mid_way(spider_id, c_time):
    # journey started time if spider in mid way or not
    x = gb.waiting_spider_list[['Scheduling Time', 'Journey Started']].loc[
        (gb.waiting_spider_list['Spider-Id'] == spider_id) &
        (pd.to_datetime(gb.waiting_spider_list['Scheduling Time']).dt.date == c_time.date())].values

    if not x.shape[0] > 0:
        current_scheduling_time = gb.system_init_time
        return False, current_scheduling_time
    else:
        current_scheduling_time = x[0][0]
        return True, current_scheduling_time

#@snoop
def allocate_a_spider(prey_id, prey_vibration_generation_at, spider_id, c_time):

    if not spider_in_allocation(prey_id, prey_vibration_generation_at, spider_id, c_time):
        emergency(prey_id, prey_vibration_generation_at, c_time)

#@snoop
def spider_in_allocation(prey_id, prey_vibration_generation_at, spider_id, c_time):
    # check for truck capacity
    spider_ava = gb.waiting_spider_list[(gb.waiting_spider_list['Spider-Id'] == spider_id) &
                                        (gb.waiting_spider_list['Available'])]
    if spider_ava.shape[0] > 0:
        spider_capacity = mDB.a_spider_capacity(spider_id)
        mDB.spider_daily_record_init(spider_id, c_time)
        distance_from_spider = distance(spider_id, prey_id)

        if spider_capacity >= gb.prey_size:
            # database update
            df = pd.DataFrame({'Prey-Id': [prey_id], 'SA Date-Time': c_time, 'Signal Time': prey_vibration_generation_at,
                               'Spider-Id': spider_id, 'Distance From Spider': distance_from_spider})
            mDB.spider_prey_relation_table = mDB.spider_prey_relation_table.append(df, ignore_index=True, sort=False)
            # change allocation status
            gb.waiting_spider_list.loc[gb.waiting_spider_list['Spider-Id'] == spider_id, ['Spider in Allocation']] = True
            # update capacity of the spider
            mDB.update_spider_capacity(spider_id)
            spider_in_mid_way, current_scheduling_time = is_spider_in_mid_way(spider_id, c_time)
            new_scheduling_time = scheduling_time(prey_id, spider_in_mid_way, spider_id, c_time)

            mDB.update_scheduling_time(current_scheduling_time, new_scheduling_time, spider_id)

            mDB.prey_signal_generated_record.loc[(mDB.prey_signal_generated_record['Prey-Id'] == prey_id) &
                                                 (pd.to_datetime(mDB.prey_signal_generated_record['Signal-Time']) ==
                                                  c_time), ['Spider_allocated']] = True

            return True
        else:
            return False


def distance_bw_two_spider(two_nearest_spider_in_vibration_range):
    a, b = two_nearest_spider_in_vibration_range['Spider-Location-Id'].tolist()
    return RaS.shortest_path_length(a, b)


def stomach_filled_level_of_two_spider(two_most_hungry_spiders):
    spider_1_id = two_most_hungry_spiders[['Spider-Id', 'Capacity']].iloc[0][0]
    spider_2_id = two_most_hungry_spiders[['Spider-Id', 'Capacity']].iloc[1][0]
    spider_1_capacity = two_most_hungry_spiders[['Spider-Id', 'Capacity']].iloc[0][1]
    spider_2_capacity = two_most_hungry_spiders[['Spider-Id', 'Capacity']].iloc[1][1]

    if spider_1_capacity > spider_2_capacity*1.5:
        return spider_1_id
    elif spider_2_capacity > spider_1_capacity*1.5:
        return spider_2_id
    else:
        return None


def hungry_level(spider_in_vibration_range):

    prey_size = gb.prey_size
    spider_sufficient_hungry = spider_in_vibration_range[spider_in_vibration_range['Capacity'] >= int(prey_size)]

    number_of_spider_sufficient_hungry = spider_sufficient_hungry.shape[0]

    if number_of_spider_sufficient_hungry == 0:
        return None
    elif number_of_spider_sufficient_hungry == 1:
        spider_id = spider_sufficient_hungry['Spider-Id'].values[0]
        return spider_id
    else:
        dbts = distance_bw_two_spider(spider_in_vibration_range[0:2])  # df is sorted based on dis in nearer spider fun
        if dbts >= 1000:  # meters
            near_spider_id = spider_in_vibration_range['Spider-Id'].tolist()[0]
            return near_spider_id
        else:
            sflots = stomach_filled_level_of_two_spider(spider_in_vibration_range.sort_values('Capacity')[0:2])
            if sflots is not None:
                return sflots  # spider id
            else:
                spider_with_highest_waiting_time = spider_in_vibration_range.sort_values('Waiting From Time').iloc[0]['Spider-Id']
                return spider_with_highest_waiting_time


def allocate_new_spider(prey_id, prey_vibration_generation_at, c_time):
    new_spiders = gb.waiting_spider_list[(~gb.waiting_spider_list['Spider in Allocation']) &
                                         (gb.waiting_spider_list['Available'])]

    if new_spiders.shape[0] > 0:
        new_spiders = new_spiders.sort_values(by='Waiting From Time')
        new_spider_id = new_spiders['Spider-Id'].iloc[0]
        allocate_a_spider(prey_id, prey_vibration_generation_at, new_spider_id, c_time)
    else:
        emergency(prey_id, prey_vibration_generation_at, c_time)


def hungry_level_action(spiders_in_distance_range, prey_id, prey_vibration_generation_at, c_time):
    a_spider_id = hungry_level(spiders_in_distance_range)
    if a_spider_id is None:
        allocate_new_spider(prey_id, prey_vibration_generation_at, c_time)
    else:
        allocate_a_spider(prey_id, prey_vibration_generation_at, a_spider_id, c_time)

#@snoop
def spider_check(prey_id, prey_vibration_generation_at, c_time):
    spiders_in_distance_range = nearer_spider(prey_id)
    if spiders_in_distance_range.shape[0] == 0:  # Allocate new spider
        allocate_new_spider(prey_id, prey_vibration_generation_at, c_time)
    elif spiders_in_distance_range.shape[0] == 1:  # Allocate that spider
        spider_id = spiders_in_distance_range['Spider-Id'][0]
        allocate_a_spider(prey_id, prey_vibration_generation_at, spider_id, c_time)
    else:  # Allocate most hungry spider
        hungry_level_action(spiders_in_distance_range, prey_id, prey_vibration_generation_at, c_time)


def allocation(prey_data):

    prey_id = prey_data[0]
    prey_vibration_generation_at = prey_data[1]
    c_time = prey_vibration_generation_at
    spider_check(prey_id, prey_vibration_generation_at, c_time)




