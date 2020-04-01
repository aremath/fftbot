#!/usr/bin/env python
# coding: utf-8

import json
import requests
import numpy as np
import pickle

def get_tips():
    with open("tooltips.json") as f:
        l = json.load(f)
    return l

def get_maps():
    out = []
    with open("maps.txt") as f:
        for l in f.readlines():
            out.append(l.rstrip())
    return out

def get_latest_data(n):
    tournaments_url = "https://fftbg.com/api/tournaments"
    mustadio_url = "http://mustad.io/api/tournaments/tournament_{}"
    params = {"limit" : n}
    r = requests.get(url=tournaments_url, params=params)
    tournaments = r.json()
    units = []
    out_tournaments = []
    for i,t in enumerate(tournaments):
        unit_url = mustadio_url.format(t["ID"])
        print("{0}: {1}".format(i, unit_url))
        r = requests.get(url=unit_url, params={})
        try:
            units.append(r.json())
            out_tournaments.append(t)
        except ValueError as e:
            print("ValueError")
    return out_tournaments, units

# Ungender the classes
def ungender(classes):
    u_classes = set()
    for c in classes:
        s = c.split(" ")
        if len(s) == 1:
            u_classes.add(c)
        if len(s) == 2:
            u_classes.add(s[0])
    return list(u_classes)


# In[26]:

def get_sorted_attributes():
    l = get_tips()
    items = list(l["Item"].keys())
    abilities = list(l["Ability"].keys())
    zodiacs = list(l["Zodiac"].keys())
    classes = list(l["Class"].keys())
    u_classes = ungender(classes)
    #print(u_classes)
    item_tag = "_item"
    ability_tag = "_ability"
    zodiac_tag = "_zodiac"
    i_tag = [i + item_tag for i in items]
    a_tag = [i + ability_tag for i in abilities]
    z_tag = [i + zodiac_tag for i in zodiacs]
    all_attributes = i_tag + a_tag + z_tag + u_classes + ["Male", "Female", "Monster"]
    # Canonical ordering for one-hot
    all_attributes_s = sorted(all_attributes)
    return all_attributes_s

# Get an ordering for the attributes (and a reverse mapping)
def mk_attrib_order(sorted_attributes):
    order = {}
    inv_order = {}
    for i,a in enumerate(sorted_attributes):
        assert a not in order, a
        order[a] = i
        inv_order[i] = a
    return order, inv_order

def mk_map_order(maps):
    order = {}
    inv_order = {}
    for i,m in enumerate(maps):
        map_number, map_name = m.split(")")
        map_number = int(map_number)
        order[map_number] = i
        inv_order[i] = m
    return order, inv_order

def get_orders():
    all_attributes_s = get_sorted_attributes()
    maps = get_maps()
    order, inv_order = mk_attrib_order(all_attributes_s)
    map_order, map_inv_order = mk_map_order(maps)
    return order, inv_order, map_order, map_inv_order

def mk_map_vec(map_name, map_order):
    n_maps = len(map_order)
    v = np.zeros(n_maps)
    #print(map_name)
    map_number, m = map_name.split(")")
    map_number = int(map_number)
    v[map_order[map_number]] = 1
    return v

def get_unit_attributes(json):
    item_tag = "_item"
    ability_tag = "_ability"
    zodiac_tag = "_zodiac"
    attributes = []
    # Class
    attributes.append(json["class"]["name"])
    #print(json["class"]["name"])
    # Abilities
    if "abilities" in json:
        abilities = json["abilities"]
    else:
        abilities = json["abilties"]
    if "mainActive" in abilities:
        for a in abilities["mainActive"]["learned"]:
            attributes.append(a["name"] + ability_tag)
    if "subActive" in abilities:
        for a in abilities["subActive"]["learned"]:
            attributes.append(a["name"] + ability_tag)
    if "react" in abilities:
        attributes.append(abilities["react"]["name"] + ability_tag)
    if "support" in abilities:
        attributes.append(abilities["support"]["name"] + ability_tag)
    if "move" in abilities:
        attributes.append(abilities["move"]["name"] + ability_tag)
    # Equipment
    equipment = json["equipment"]
    for e in equipment:
        attributes.append(e["name"] + item_tag)
    # Zodiac
    attributes.append(json["zodiac"] + zodiac_tag)
    # Gender
    attributes.append(json["gender"])
    return attributes

# Vector for a unit's data, not a unit vector
def mk_unit_vec(unit_json, order):
    #print(unit_json)
    n_attributes = len(order)
    v = np.zeros(n_attributes)
    unit_attributes = get_unit_attributes(unit_json)
    for a in unit_attributes:
        v[order[a]] = 1
    # Brave / Faith
    bf = np.zeros(2)
    brave = int(unit_json["brave"])
    faith = int(unit_json["faith"])
    return np.concatenate([v, bf])

def mk_team_vec(team_json, order):
    uvecs = [mk_unit_vec(u, order) for u in team_json["units"]]
    # Team vec is (n_attributes x 4)
    tvec = np.stack(uvecs, axis=1)
    return tvec

# Gets the json for the given team name
def get_team(team_name, units_json):
    return [i for i in units_json["teams"] if i["teamName"] == team_name][0]

def mk_match_vec(match, units_json, order, map_order):
    t1_s, t2_s, map_name, winner = match
    t1_json = get_team(t1_s, units_json)
    t2_json = get_team(t2_s, units_json)
    t1 = mk_team_vec(t1_json, order)
    t2 = mk_team_vec(t2_json, order)
    m = mk_map_vec(map_name, map_order)
    # Label is based on team order
    if winner == t1_s:
        w = 0
    elif winner == t2_s:
        w = 1
    else:
        assert False, "NO WINNER!"
    return np.concatenate([t1.flatten(), t2.flatten(), m]), w

init_tourney = ["red", "blue", "green", "yellow", "white", "black", "purple", "brown"]

# Returns the matches for a tournament
def get_matches(tourney):
    matches = []
    teams = init_tourney
    offset = 0
    winners = tourney["Winners"]
    maps = tourney["Maps"]
    assert len(winners) == 8
    assert len(maps) == 8
    assert tourney["Complete"]
    # Add each of the matches
    while len(teams) > 1:
        new_teams = []
        for i in range(0, len(teams), 2):
            t0 = teams[i]
            t1 = teams[i+1]
            w = winners[offset + (i//2)]
            m = maps[offset + (i//2)]
            matches.append((t0, t1, m, w))
            new_teams.append(w)
        offset = offset + (len(teams) // 2)
        teams = new_teams
    # And the champion match
    matches.append((w,"champion",maps[-1],winners[-1]))
    return matches

#TODO: memoize the vectors so that we don't have to build the vectors for each team over and over?
def mk_tournament_vecs(tournament_json, units_json, order, map_order):
    # AssertionError means either the tournament hasn't finished or something weird happened in the tournament
    try:
        matches = get_matches(tournament_json)
    except AssertionError as e:
        return []
    return [mk_match_vec(m, units_json, order, map_order) for m in matches]

def save_data(tournaments, units, pickle_file="data.pick"):
    with open(pickle_file, "wb") as f:
        pickle.dump((tournaments, units), f)

def save_and_merge_data(tournaments, units, pickle_file="data.pick"):
    t, u = load_data(pickle_file)
    ids = set()
    # Only add the tournaments if they have a unique ID
    for tournament in t:
        ids.add(tournament["ID"])
    for tournament, unit in zip(tournaments, units):
        if tournament["ID"] not in ids:
            t.append(tournament)
            u.append(unit)
    save_data(t, u, pickle_file)

def load_data(pickle_file="data.pick"):
    with open(pickle_file, "rb") as f:
        tournaments, units = pickle.load(f)
        return tournaments, units

def get_data(n, unpickle=True):
    if unpickle:
        return load_data()
    else:
        t,u = get_latest_data(n)
        save_and_merge_data(t, u)
        # TODO: return all of the saved data?
        return t,u

def mk_vecs(tournaments, units, order, map_order):
    out_x = []
    out_y = []
    for t,u in zip(tournaments, units):
        #print(t["ID"])
        t = mk_tournament_vecs(t,u, order, map_order)
        for x,y in t:
            out_x.append(x)
            out_y.append(y)
    return out_x, out_y

def get_vecs():
    tournaments, units = get_data(0)
    order, inv_order, map_order, map_inv_order = get_orders()
    return mk_vecs(tournaments, units, order, map_order)

