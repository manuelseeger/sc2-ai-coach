import sc2reader
import pandas as pd
import glob
import os
import datetime
import bottle

REPLAY_FOLDER = os.getenv('REPLAY_FOLDER')
PLAYER = os.getenv('PLAYER')

RACES = {
    'Zerg': 'Z',
    'Terran': 'T',
    'Protoss': 'P'
}

SEASON_START = datetime.date(2022,1,7)

app = bottle.Bottle()

temp = ''
with open('template.html') as f: 
    temp = f.read()


def get_replays(today):
    list_of_files = glob.glob(os.path.join(REPLAY_FOLDER, '*.SC2Replay'))

    list_of_files = [f for f in list_of_files if today <= datetime.date.fromtimestamp(os.path.getmtime(f))]

    if len(list_of_files) == 0: 
        return ''
    data = []
    print('Scanning {} files'.format(len(list_of_files)))
    for file_path in list_of_files:
        replay = sc2reader.load_replay(file_path)
        if  replay.category == 'Ladder' and replay.region == 'eu' and replay.real_type == '1v1': 
            row = {
                'Map': replay.map_name, 
                'Player1': replay.players[0].name, 
                'Player1_Race': RACES[replay.players[0].play_race], 
                'Player1_Result': replay.players[0].result == 'Win', 
                'Player2': replay.players[1].name, 
                'Player2_Race': RACES[replay.players[1].play_race],
                'Player2_Result': replay.players[1].result == 'Win' 
            }
            data.append(row)
        else: 
            pass
    df = pd.DataFrame(data, columns=['Map', 'Player1', 'Player1_Race', 'Player1_Result', 'Player2', 'Player2_Race', 'Player2_Result'])

    player_as_zerg1 = (df['Player1'] == PLAYER) & (df['Player1_Race'] == 'Z')
    player_as_zerg2 = (df['Player2'] == PLAYER) & (df['Player2_Race'] == 'Z')
    p1 = df[player_as_zerg1].groupby(by=['Player1_Race', 'Player2_Race']).sum()
    p2 = df[player_as_zerg2].groupby(by=['Player1_Race', 'Player2_Race']).sum()
    p3 = p2.rename(columns={'Player2_Result':'Player1_Result', 'Player1_Result':'Player2_Result'})
    p = p1.copy()

    # yuck can't figure out how to elegantly deal with NaNs
    # this is necessary to initialize indices at the beginning of the stream (not all matchups played yet that day)
    if ('Z', 'P') not in p.index:
        p.loc[('Z', 'P'),:] = 0
    if ('Z', 'T') not in p.index:
        p.loc[('Z', 'T'),:] = 0
    if ('Z', 'Z') not in p.index:
        p.loc[('Z', 'Z'),:] = 0
    if ('P','Z') not in p3.index:
        p3.loc[('P','Z'),:] = 0
    if ('T','Z') not in p3.index:
        p3.loc[('T','Z'),:] = 0
    if ('Z', 'Z') not in p3.index:
        p.loc[('Z', 'Z'),:] = 0

    p.loc[('Z', 'P')] += p3.loc[('P','Z')]
    p.loc[('Z', 'T')] += p3.loc[('T','Z')]
    p.loc[('Z', 'Z')] += p3.loc[('Z','Z')]
    print(p.to_string(sparsify=False, index_names=False, float_format=lambda f: str(int(f))))
    return p.to_html(header=False, sparsify=False, index_names=False, border=0, float_format=lambda f: str(int(f)))

@app.route('/')
def get_stats():
    request_date = bottle.request.query.date or datetime.date.today().strftime('%Y-%m-%d')
    today = datetime.datetime.strptime(request_date, '%Y-%m-%d').date()

    replays_today = get_replays(today)

    replays_season = get_replays(SEASON_START)
    return bottle.template(temp, today=replays_today, season=replays_season)


if __name__ == '__main__':
    bottle.run(app, host='localhost', port=8080)