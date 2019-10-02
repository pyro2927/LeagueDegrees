#!/usr/bin/env python
from matplotlib import pyplot as plt
from time import sleep
from os import getenv
import json
import networkx as nx
import numpy as np
import requests

G = nx.Graph()
API_KEY = getenv('RIOT_API_KEY')
PROCESSED_PLAYER_IDS = []

# cache decorator
def persist_to_file(file_name):
    def decorator(original_func):
        try:
            cache = json.load(open(file_name, 'r'))
        except (IOError, ValueError):
            cache = {}
        def new_func(param):
            if param not in cache:
                cache[param] = original_func(param)
                json.dump(cache, open(file_name, 'w'))
            return cache[param]
        return new_func
    return decorator

@persist_to_file('urls.json')
def safe_json(url):
    sleep(0.1)
    # print("Live URL called: {}".format(url))
    response = requests.get('{}?api_key={}'.format(url, API_KEY))
    if response.status_code == 200:
        bod = response.json()
        return bod
    elif response.status_code == 429:
        sleep(3)
        return safe_json(url)
    elif response.status_code == 401:
        import sys
        print("API key invalid, please get a new one")
        sys.exit(1)
    else:
        print(response.status_code)
        return {'participantIdentities': [], 'matches':[]}


# add a grouping of players that have played together
def add_players(player_list):
    for p in player_list:
        G.add_node(p)
        for p2 in player_list:
            if p != p2:
                G.add_edge(p, p2)

@persist_to_file('players.json')
def players_in_game(game_id):
    participants = safe_json('https://na1.api.riotgames.com/lol/match/v4/matches/{}'.format(game_id))['participantIdentities']
    return [p['player']['accountId'] for p in participants]

# account IDs are encrypted
@persist_to_file('matches.json')
def matches_for_player(account_id): 
    matches = safe_json('https://na1.api.riotgames.com/lol/match/v4/matchlists/by-account/{}'.format(account_id))['matches']
    return [m['gameId'] for m in matches]

@persist_to_file('summoners.json')
def get_account_id(summoner_name):
    return safe_json('https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{}'.format(summoner_name))['accountId']

@persist_to_file('accounts.json')
def get_summoner_name(account_id):
    return safe_json('https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-account/{}'.format(account_id))['name']

def sliced_matches_for_player(account_id, count):
    return matches_for_player(account_id)[0:count]

def render(start, end):
    # pos = nx.circular_layout(G, scale=400)
    pos = nx.spring_layout(G, k=100*1/np.sqrt(len(G.nodes())), iterations=20)
    nx.draw(G, pos, node_color='b')
    path = nx.shortest_path(G, start, end)
    # shortest path connection
    for account_id in path:
        print(get_summoner_name(account_id))
    path_edges = zip(path,path[1:])
    nx.draw_networkx_nodes(G,pos,nodelist=path,node_color='g')
    nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='r', width=3)
    plt.axis('equal')
    plt.show(block=True)

# allow us to get more than one level at a time
def get_games_and_players(account_id, game_count, depth):
    # Don't traverse account IDs multiple times
    if account_id in PROCESSED_PLAYER_IDS:
        print("{} already in graph, skipping traversal".format(p))
        return false
    PROCESSED_PLAYER_IDS.append(account_id)
    print("Adding {}...".format(account_id))
    for m in sliced_matches_for_player(account_id, game_count):
        players = players_in_game(m)
        add_players(players)
        if depth > 1:
            for p in players:
                get_games_and_players(p, game_count, depth - 1)

def find(first, last):
    # until we find a connection, do breadth first search starting from each end
    first_id = get_account_id(first)
    G.add_node(first_id)
    last_id = get_account_id(last)
    G.add_node(last_id)
    while not nx.has_path(G, first_id, last_id):
        # find all "leaves" in this graph that we have not traversed
        # https://stackoverflow.com/a/3462160
        leaves = list(set(G.nodes) - set(PROCESSED_PLAYER_IDS))
        for leaf in leaves:
            get_games_and_players(leaf, 10, 1)
    print("{} and {} have {} degrees of separation".format(first, last, len(nx.shortest_path(G, first_id, last_id)) - 1))
    render(first_id, last_id)

if __name__ == '__main__':
    find('S8 IS SO FUN', 'voyboy')