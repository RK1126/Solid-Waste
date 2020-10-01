import MyDatabase as mDB
import networkx as nx
import datetime as dt
import globals as gb
import pandas as pd


silk_edge_list = pd.read_csv('edge_list.csv', index_col=0)
silk_node_list = pd.read_csv('node_list.csv', index_col=0)


def surreal():
    g = nx.Graph()
    for i, elrow in silk_edge_list.iterrows():
        g.add_edge(elrow[0], elrow[1], weight=elrow[2], attr_dict=elrow[3:].to_dict())
    for i, nlrow in silk_node_list.iterrows():
        attrs = {nlrow[0]: nlrow[1:].to_dict()}
        nx.set_node_attributes(g, attrs)
    return g


web = surreal()


def shortest_path_for_attack(spider_location, prey_location):
    return nx.dijkstra_path(web, spider_location, prey_location)


def shortest_path_length(spider_location, prey_location):
    return round(nx.dijkstra_path_length(web, spider_location, prey_location), 2)


def ready_spiders(spiders_id, c_time, to_center=False):
    for spider_id in spiders_id:
        capacity_of_spider = mDB.a_spider_capacity(spider_id)
        ordered_prey_ids_for_spider_to_attack = mDB.attack_on_prey_order(spider_id, c_time)
        if ordered_prey_ids_for_spider_to_attack is not None:
            # size of prey is constant
            if capacity_of_spider <= gb.prey_size:
                to_center = True
            attack(spider_id, ordered_prey_ids_for_spider_to_attack, to_center, c_time)


def hunting(c_time):

    gb.waiting_spider_list.loc[
        (pd.to_datetime(gb.waiting_spider_list['Waiting From Time']) <= c_time), ['Available']] = True

    # if spider on dumpy yard update capacity
    gb.waiting_spider_list.loc[gb.waiting_spider_list['Spider-Location-Id'] == 'dumpyard', ['Capacity']] = 8
    # get the spider that is filled and has to be schedule instantly
    spiders = gb.waiting_spider_list.loc[gb.waiting_spider_list['Scheduling Time'].dt.date == c_time.date()].sort_values(by='Scheduling Time')
    if spiders.shape[0] > 0:
        spiders_ready_to_attack = spiders[(spiders['Capacity'] < gb.prey_size) | (spiders['Scheduling Time'] <= c_time)]

        if spiders_ready_to_attack.shape[0] > 0:  # if any spider for attack
            # prey related to that spider in waiting time, priority order, distance
            ready_spiders(spiders_ready_to_attack['Spider-Id'], c_time)


def update_db(c_time):
    mDB.spider_daily_record_table.to_csv('spider_daily_record_table.csv')
    mDB.save_spider_prey_relation_table(c_time)
    gb.waiting_spider_list.to_csv('spider_status.csv')
    mDB.save_spider_nodes_visited(c_time)
    mDB.save_emergency_table(c_time)
    gb.write_header = False


def attack(spider_id, preys_for_spider, last_station_center_of_web, c_time):

    preys_for_spider = preys_for_spider.tolist()
    if last_station_center_of_web:  # sent to dumpyard
        if preys_for_spider[-1] != 'dumpyard':
            # if dump-yard in route
            c = preys_for_spider.count('dumpyard')
            if c > 0:
                # last occurance of dump
                temp = preys_for_spider[::-1].index('dumpyard')
                index = len(preys_for_spider)-1-temp
                preys_for_spider.remove(preys_for_spider[index])
                preys_for_spider.append('dumpyard')
            else:
                preys_for_spider.append('dumpyard')
    list_of_silk_node_visited, work_time = routing(spider_id, preys_for_spider, c_time)

    init_x, init_y = mDB.spider_daily_record_table[['Init X', 'Init Y']][
        (mDB.spider_daily_record_table['Spider-Id'] == spider_id) & (mDB.spider_daily_record_table[
            'Date'] == c_time.date())].values[0]

    updated_waiting_from_time = c_time + work_time

    if last_station_center_of_web is True:  # i.e. dump-yard
        spider_init_loc_id = mDB.a_spider_location_id_based_on_coordinates(init_x, init_y)
        time_to_reach_init_loc = dt.timedelta(minutes=(shortest_path_length(spider_init_loc_id,
                                              'dumpyard')/gb.avg_speed))  # from dumyard to init location
        updated_waiting_from_time = updated_waiting_from_time + time_to_reach_init_loc
        gb.update_trip_id(spider_id, c_time)

    else:
        list_of_silk_node_visited = list_of_silk_node_visited[:-1]
    journey_starting_time = gb.waiting_spider_list['Journey Started'].loc[(gb.waiting_spider_list['Spider-Id'] == spider_id) &
                                                                          (gb.waiting_spider_list['Scheduling Time'].dt.date == c_time.date())].values[0]

    if journey_starting_time == gb.system_init_time:
        journey_starting_time = c_time

    try:
        spider_loc_id = list_of_silk_node_visited[-1]
        s_x, s_y = mDB.a_spider_coordinates_based_on_location_id(list_of_silk_node_visited[-1])
    except IndexError:
        spider_loc_id = gb.waiting_spider_list['Spider-Location-Id'][gb.waiting_spider_list['Spider-Id'] == spider_id]
        s_x, s_y = init_x, init_y
    gb.waiting_spider_list.loc[(gb.waiting_spider_list['Spider-Id'] == spider_id) &
                               (gb.waiting_spider_list['Scheduling Time'].dt.date == c_time.date()),
                               ['X', 'Y', 'Available', 'Waiting From Time', 'Spider in Allocation',
                                'Journey Started', 'Spider-Location-Id']] = s_x, s_y, False, updated_waiting_from_time, False, journey_starting_time, spider_loc_id

    update_db(c_time)


def routing(spider_id, preys_for_spider_ids, c_time):  # prey list as parameter

    tot_distance_travelled = mDB.total_distance_travelled(spider_id, c_time)

    nodes_visited_by_spider = []
    time_consumed_in_this_trip = dt.timedelta(seconds=0)
    # from waiting spider list
    working_time_of_today = mDB.today_working_time(spider_id, c_time)

    distance_travelled = 0

    for prey_node in preys_for_spider_ids:
        trip_no = gb.get_trip_id(spider_id, c_time)
        spider_loc_id = mDB.a_spider_location_id(spider_id)
        list_of_silk_node_visited = shortest_path_for_attack(spider_loc_id, prey_node)  # list output
        nodes_visited_by_spider = nodes_visited_by_spider + list_of_silk_node_visited

        for node_id in list_of_silk_node_visited:
            mDB.spider_nodes_visited = mDB.spider_nodes_visited.append(pd.DataFrame([[spider_id, c_time.date(), node_id, trip_no]],
                                                                                    columns=['Spider-Id', 'Date', 'Node-Id', 'Trip No']))

        mDB.spider_prey_relation_table.loc[(mDB.spider_prey_relation_table['Spider-Id'] == spider_id) &
                                            (mDB.spider_prey_relation_table['Prey-Id'] == prey_node) &
                                            (pd.to_datetime(mDB.spider_prey_relation_table['SA Date-Time']).dt.date ==
                                             c_time.date()), ['Trip No']] = trip_no

        distance_travelled = shortest_path_length(spider_loc_id, prey_node)
        tot_distance_travelled = tot_distance_travelled + distance_travelled

        if prey_node in gb.prey_already_sent_signal:
            if prey_node != 'dumpyard':
                gb.prey_already_sent_signal.remove(prey_node)

        time_consumed_in_this_trip = time_consumed_in_this_trip + dt.timedelta(seconds=round(distance_travelled/gb.avg_speed, 2))

    # update daily spider record

    mDB.spider_daily_record_table.loc[(mDB.spider_daily_record_table['Spider-Id'] == spider_id) &
                                      (mDB.spider_daily_record_table['Date'] == c_time.date()),
                                      ['Departure Time', 'Distance', 'Working Time']] = \
        c_time, round(tot_distance_travelled, 2), working_time_of_today + time_consumed_in_this_trip
    return nodes_visited_by_spider, time_consumed_in_this_trip
