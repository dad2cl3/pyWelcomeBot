import aiohttp, asyncio, datetime, discord, json, requests, time

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

discord_config = config['Discord']

def get_msg_details(member, action):

    response = {}

    # Find the server
    server = client.get_server(member.server.id)
    server_name = member.server.name
    # Get server config
    server_config = discord_config['server'][server_name]

    for channel in server.channels:
        if channel.name == server_config['{0}Channel'.format(action)]:
            msg_channel = server.get_channel(channel.id)
            if action == 'join':
                msg_message = server_config['{0}Message'.format(action)].format(member.id)
            elif action == 'remove':
                msg_message = server_config['{0}Message'.format(action)].format(member.name)

    response['{0}Channel'.format(action)] = msg_channel
    response['{0}Message'.format(action)] = msg_message

    return response


def get_target_time (tgt_tm_hr, tgt_tm_min):

    # get hour and minutes of current time
    cur_tm_hr = int(time.strftime('%H', time.localtime()))
    cur_tm_min = int(time.strftime('%M', time.localtime()))

    # combine today's date with target time
    tgt_dt_tm = datetime.datetime.combine(datetime.date.today(), datetime.time(tgt_tm_hr, tgt_tm_min))

    # compare target datetime to current datetime
    if tgt_dt_tm.timestamp() < time.time():
        # target datetime in past
        # add one day to target datetime
        tgt_dt_tm = tgt_dt_tm + datetime.timedelta(days=1)

    return time.mktime(tgt_dt_tm.timetuple())


def get_link_report ():
    print('Getting link report...')

    response = requests.get(config['tasks']['account_linking']['report']['report_url'])
    if response.status_code == 200:
        data = response.json()
        print(data)
        report_embed = discord.Embed(
            title=config['tasks']['account_linking']['report']['report_title'],
            description=config['tasks']['account_linking']['report']['report_description']
        )

        report_embed.set_footer(
            icon_url=config['tasks']['account_linking']['report']['footer_icon_url'],
            text=config['tasks']['account_linking']['report']['footer_text']
        )

        report_embed.add_field(
            name='Discord',
            value=data['discord'],
            inline=True
        )

        report_embed.add_field(
            name='Destiny',
            value=data['destiny'],
            inline=True
        )

        return report_embed
    else:
        return {}


client = discord.Client()


async def stage_discord_accounts():
    await client.wait_until_ready()

    tgt_tm_hr = config['tasks']['discord_accounts']['target_start_time_hour']
    tgt_tm_min = config['tasks']['discord_accounts']['target_start_time_minute']

    #print('Client is ready...')
    tgt_dt_tm = get_target_time(tgt_tm_hr, tgt_tm_min)
    print('Target time is...')
    print(datetime.datetime.fromtimestamp(tgt_dt_tm).strftime('%Y-%m-%d %H:%M:%S'))

    await asyncio.sleep(tgt_dt_tm - time.time())

    while not client.is_closed:
        print(time.strftime('%b %d %Y %H:%M:%S', time.localtime()))
        print('Target hour: {0}'.format(tgt_tm_hr))
        print('Target minute: {0}'.format(tgt_tm_min))

        member_list = []
        for server in client.servers:
            for member in server.members:
                roles = []
                for role in member.roles:
                    roles.append(str(role))

                discord_user = await client.get_user_info(member.id)

                user = {
                    'server_id': server.id,
                    'server_name': str(server),
                    'discord_id': member.id,
                    'discord_name': member.name,
                    'discord_bot': bool(discord_user.bot),
                    'discord_avatar_url': str(discord_user.avatar_url),
                    'discord_display_name': str(discord_user.display_name),
                    'discord_roles': roles
                }
                #print(user) # debugging
                member_list.append(user)

            response = {
                'members': member_list
            }

            url = config['tasks']['discord_accounts']['staging_url']

            print('Staging discord accounts...')
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(response)) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        print(response_data)
                    else:
                        print('Response: {0}'.format(response.status))

            print('Staged discord accounts...')
            tgt_dt_tm = get_target_time(tgt_tm_hr, tgt_tm_min)
            await asyncio.sleep(tgt_dt_tm - time.time())


async def refresh_online_report_task():
    await client.wait_until_ready()

    while not client.is_closed:
        print('Refreshing online report...')
        report_refresh_url = config['tasks']['online_report']['refresh_url']

        async with aiohttp.ClientSession() as session:
            async with session.get(report_refresh_url) as response:
                if response.status == 200:
                    response_data = await response.json()
                    #print(response_data)
                else:
                    print('Response: {0}'.format(response.status))

        print('Refreshed online report...')

        await asyncio.sleep(config['tasks']['online_report']['refresh_interval'])


@client.event
async def on_ready():
    print('Bot is ready...')


@client.event
async def on_message (message):

    if message.content.startswith('!online'):
        print('Getting online report...')
        sender_id = message.author.id
        user = await client.get_user_info(sender_id)

        online_report = discord.Embed(
            title = config['tasks']['online_report']['report_title'],
            description = config['tasks']['online_report']['report_description'].format(time.strftime('%m-%d-%Y %I:%M %p %Z'))
        )

        report_url = config['tasks']['online_report']['report_url']
        response = requests.get(report_url)
        if response.status_code == 200:
            active_members = response.json()
        else:
            active_members = {}

        for clan in active_members:
            print(clan)
            online_report.add_field (
                name=clan,
                value=active_members[clan],
                inline=False
            )

        online_message = await client.send_message(user, embed=online_report)
    elif message.content.startswith('!link'):
        # remove call to bot
        link_payload = message.content.replace('!link ', '')
        link_payload = link_payload.strip().lower()
        print(link_payload)
        if link_payload == 'report':
            # build report
            report_embed = get_link_report()

            await client.send_message(message.channel, embed=report_embed)

        elif 'gamertag:' in link_payload and 'discord:' in link_payload:
            payload = {
                'message': link_payload
            }
            print(payload) # debugging
            response = requests.post(config['tasks']['account_linking']['link_url'], data=json.dumps(payload))
            print(response.status_code) # debugging
            if response.status_code == 200:
                data = response.json()
                print(data)
                await client.send_message(message.channel, data['status'])


@client.event
async def on_member_join(member):
    print('{0} joined...'.format(member))

    join = get_msg_details(member, 'join')

    msg = await client.send_message(join['joinChannel'], join['joinMessage'])


@client.event
async def on_member_remove(member):
    print('{0} departed...'.format(member))

    remove = get_msg_details(member, 'remove')

    msg = await client.send_message(remove['removeChannel'], remove['removeMessage'])


client.loop.create_task(stage_discord_accounts())
client.loop.create_task(refresh_online_report_task())

client.run(discord_config['token'])
