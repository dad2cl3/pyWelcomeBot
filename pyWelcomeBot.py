import asyncio, discord, json, requests, time

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

client = discord.Client()

async def refresh_online_report_task():
    await client.wait_until_ready()

    while not client.is_closed:
        print('Refreshing online report...')
        report_refresh_url = config['tasks']['online_report']['refresh_url']

        response = requests.get(report_refresh_url)
        #print(response.status_code) # debugging

        if response.status_code == 200:
            response_payload = response.json()

            print(json.dumps(response_payload))
        else:
            print('Error occurred...')

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
            description = config['tasks']['online_report']['report_description'].format(time.strftime('%m-%d-%Y %H:%m %p %Z'))
        )

        report_url = config['tasks']['online_report']['report_url']
        response = requests.get(report_url)
        if response.status_code == 200:
            active_members = response.json()
        else:
            active_members = {}

        for clan in active_members:
            online_report.add_field (
                name = clan,
                value = active_members[clan],
                inline = False
            )

        online_message = await client.send_message(user, embed=online_report)


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

client.loop.create_task(refresh_online_report_task())

client.run(discord_config['token'])