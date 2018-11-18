from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

from operator import itemgetter

import datetime, json, os, pg8000, re, redis, requests, time

# create global dictionary of definitions
manifest_definitions = {}

# open redis connection
r = redis.StrictRedis(
    host=os.environ['redis_host'],
    port=os.environ['redis_port'],
    password=os.environ['redis_password'])

api_key = os.environ['api_key']


def execute_sql (pg_cursor, sql):
    print('Executing SQL SELECT...')

    #pg_cursor = conn.cursor()
    pg_cursor.execute(sql)
    results = pg_cursor.fetchall()

    return results


def get_clans(conn):
    pg_cursor = conn.cursor()

    sql = "SELECT clan_id, clan_name FROM groups.t_clans WHERE clan_name NOT IN ('Iron Orange 3rd Bn', 'Iron Orange Moon') ORDER BY clan_name"
    #clans = execute_sql(conn, sql)
    clans = execute_sql(pg_cursor, sql)

    return clans


def get_manifest_definition(table, hash):
    #print('Getting manifest definition...')

    # bring in globals
    global manifest_definitions

    start = time.time()
    definition_key = '{0}:{1}'.format(table, hash)
    #print(definition_key) # debugging

    if definition_key in manifest_definitions:
        return manifest_definitions[definition_key]
    else:
        definition = r.hget(definition_key, 'json')
        #print('Definition: {0}'.format(definition)) # debugging
        try:
            definition = json.loads(definition.decode('UTF-8'))
            return definition
        except AttributeError:
            print('NO DEFINITION FOUND: {0}'.format(definition_key))
            return {}


def get_activity_details(activity_hash):
    print('Getting activity detail...')
    #print(activity_hash) # debugging
    activity = get_manifest_definition('DestinyActivityDefinition', activity_hash)
    #print(activity)
    # default activity name to an empty string
    activity_name = ''
    if 'displayProperties' in activity:
        if 'name' in activity['displayProperties']:
            activity_name = activity['displayProperties']['name']
            print('Activity: {0}'.format(activity_name)) # debugging

    if activity != {}:
        activity_type_hash = activity['activityTypeHash']
        activity_type = get_manifest_definition('DestinyActivityTypeDefinition', activity_type_hash)
        if 'name' in activity_type['displayProperties']:
            activity_type_name = activity_type['displayProperties']['name']
            print('Activity Type: {0}'.format(activity_type_name)) # debugging
        else:
            activity_type_name = 'Orbit'
    else:
        activity_type_name = 'Orbit'

    #print('{0} {1}'.format(activity_type_name, activity_name))
    #print('{0} {1}'.format(activity_type_name, activity_name).strip())
    #print('{0} {1}'.format(activity_type_name, activity_name).strip().replace(' ', ' - '))

    activity_details = '{0} - {1}'.format(activity_type_name, activity_name)
    #print(activity_details)
    # fix missing activity name
    leading_hyphen = re.compile('^ - ')
    activity_details = re.sub(leading_hyphen, '', activity_details)
    #print(activity_details)
    # fix missing activity type
    trailing_hyphen = re.compile(' - $')
    activity_details = re.sub(trailing_hyphen, '', activity_details)
    #print(activity_details)
    #print(len(activity_details))

    return activity_details


def get_character_activity (request):
    print('Getting character activity...')

    url = request['profile_url']

    start = time.time()
    response = requests.get(url, headers={'X-API-Key': api_key})
    duration = time.time() - start
    print('Account Profile: {0:.2f}s'.format(duration))
    if response.status_code == 200:
        characters = response.json()['Response']['characterActivities']['data']
        #print(json.dumps(characters)) # debugging

        most_recent_hash = 0
        most_recent_ts = 0
        for character in characters:
            #print(character) # debugging
            current_activity = characters[character]['currentActivityHash']
            current_activity_start = characters[character]['dateActivityStarted']
            current_activity_ts = datetime.datetime.strptime(current_activity_start, '%Y-%m-%dT%H:%M:%SZ').timestamp()
            #print(current_activity)
            if current_activity != 0:
                if current_activity_ts > most_recent_ts:
                    most_recent_ts = current_activity_ts
                    most_recent_hash = current_activity

        most_recent_age = (time.time() - most_recent_ts)/60 # convert to minutes
        if most_recent_age < 0:
            most_recent_age = 0

        print('Most Recent Activity: {0:.2f}m'.format(most_recent_age))
        #print(most_recent_hash) # debugging
        activity_detail = get_activity_details(most_recent_hash)
        #print(activity_detail) # debugging
        request['activity_detail'] = '{0} ({1:.2f}m)'.format(activity_detail, most_recent_age).strip()

    return request


def get_clan_members (request):
    print('Getting clan members...')
    #print(request)

    start = time.time()
    #print(request[2])
    response = requests.get(request[2], headers={'X-API-Key': api_key})
    #print(response.status_code)

    duration = time.time() - start
    print('Clans: {0:.2f}s'.format(duration))
    if response.status_code == 200:
        data = response.json()['Response']['results']
        request.append(data)
    else:
        request.append({})

    return request


def process_requests (requests):
    print('Processing clans...')

    responses = []

    request_count = len(requests)
    print('Requests {0}'.format(request_count))
    chunk_size = 25
    start = 0

    total_api_duration = 0

    for start in range(0, request_count, chunk_size):
        end = start + chunk_size - 1
        if end > request_count:
            end = request_count - 1

        #print('({0},{1})'.format(start, end))

        print('Processing chunk {0} - {1}'.format(str(start), str(end)))
        chunk = end - start + 1
        api_start_time = time.time()

        with ThreadPoolExecutor(chunk) as executor:
            future_to_url = {executor.submit(get_clan_members, request): request for request in requests[start:(end + 1)]}

        for response in futures.as_completed(future_to_url):
            responses.append(response.result())

        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        total_api_duration += api_duration
        print('Chunk API Execution: {0:.2f}s'.format(api_duration))

    print('Total API Execution: {0:.2f}s'.format(total_api_duration))
    return responses



def process_profile_requests (requests):
    print('Processing clans...')

    responses = []

    request_count = len(requests)
    print('Requests {0}'.format(request_count))
    chunk_size = 25
    start = 0

    total_api_duration = 0

    for start in range(0, request_count, chunk_size):
        end = start + chunk_size - 1
        if end > request_count:
            end = request_count - 1

        #print('({0},{1})'.format(start, end))

        print('Processing chunk {0} - {1}'.format(str(start), str(end)))
        chunk = end - start + 1
        api_start_time = time.time()

        with ThreadPoolExecutor(chunk) as executor:
            future_to_url = {executor.submit(get_character_activity, request): request for request in requests[start:(end + 1)]}

        for response in futures.as_completed(future_to_url):
            responses.append(response.result())

        api_end_time = time.time()
        api_duration = api_end_time - api_start_time
        total_api_duration += api_duration
        print('Chunk API Execution: {0:.2f}s'.format(api_duration))

    print('Total API Execution: {0:.2f}s'.format(total_api_duration))
    return responses

def handler(event, context):

    start_time = time.time()


    # open database connection
    pg = pg8000.connect(
        host=os.environ['database_host'],
        port=5432,
        database=os.environ['database_name'],
        user=os.environ['database_user'],
        password=os.environ['database_password']
    )

    # get clans
    pg_cursor = pg.cursor()
    pg_cursor.execute("SELECT clan_id, clan_name FROM groups.t_clans WHERE clan_name NOT IN ('Iron Orange 3rd Bn', 'Iron Orange Moon') ORDER BY clan_name")
    clans = pg_cursor.fetchall()

    # close database connection
    pg.close()

    # get active members
    active = {}

    request_details = []

    for clan in clans:
        url = os.environ['clan_url'].format(clan[0])
        #print(url) # debugging
        clan.append(url)
        request_details.append(clan)

    responses = process_requests(request_details)

    active_members = []

    for response in responses:
        for member in response[3]:
            if 'isOnline' in member.keys():
                if member['isOnline']:
                    #print(member['destinyUserInfo']['displayName']) # debugging
                    active_member = {}
                    active_member['clan_name'] = response[1]
                    active_member['gamertag'] = member['destinyUserInfo']['displayName']
                    active_member['destiny'] = member['destinyUserInfo']
                    active_member['profile_url'] = os.environ['character_url'].format(member['destinyUserInfo']['membershipType'], member['destinyUserInfo']['membershipId'])

                    active_members.append(active_member)

    #print(active_members) # debugging

    character_activities = process_profile_requests(active_members)
    #print(json.dumps(character_activities))
    print('Sorting character activities')
    character_activities = sorted(character_activities, key=itemgetter('clan_name'))

    actives = {}
    for gamertag in character_activities:
        if len(gamertag['activity_detail']) > 0:
            combined = '{0}: {1}'.format(gamertag['gamertag'], gamertag['activity_detail'])
        else:
            combined = gamertag['gamertag']

        if gamertag['clan_name'] not in actives:
            actives[gamertag['clan_name']] = []

        actives[gamertag['clan_name']].append(combined)

    active_members = {}

    print(json.dumps(actives))
    for clan in actives:
        sorted_actives = sorted(actives[clan], key=str.lower)
        single_string = '\n'.join(sorted_active for sorted_active in sorted_actives)

        active_members[clan] = {}
        active_members[clan] = single_string

    #print(json.dumps(active_members)) # debugging


    duration = time.time() - start_time
    print('Duration: {0:.2f}s'.format(duration))

    r.hmset('online', {"json": json.dumps(active_members)})

    return active_members