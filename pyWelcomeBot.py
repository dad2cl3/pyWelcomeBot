import aiohttp, argparse, asyncio, datetime, discord, json, requests, time


class PyWelcomeBot (discord.Client):
    def __init__(self):
        super().__init__()

        self.bg_task = self.loop.create_task(self.stage_discord_accounts())
        #self.bg_task = self.loop.create_task(self.refresh_online_report_task())

    # Helper functions

    def get_msg_details(self, member, action):

        response = {}

        # Find the server
        guild = self.get_guild(member.guild.id)
        guild_name = member.guild.name
        # Get server config
        server_config = discord_config['server'][server_name]

        for channel in guild.channels:
            if channel.name == server_config['{0}Channel'.format(action)]:
                msg_channel = guild.get_channel(channel.id)
                if action == 'join':
                    msg_message = server_config['{0}Message'.format(action)].format(member.id)
                elif action == 'remove':
                    msg_message = server_config['{0}Message'.format(action)].format(member.name)

        response['{0}Channel'.format(action)] = msg_channel
        response['{0}Message'.format(action)] = msg_message

        return response


    def get_target_time (self, tgt_tm_hr, tgt_tm_min):

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


    def get_link_report (self):
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


    async def stage_discord_accounts(self):
        await self.wait_until_ready()

        tgt_tm_hr = config['tasks']['discord_accounts']['target_start_time_hour']
        tgt_tm_min = config['tasks']['discord_accounts']['target_start_time_minute']

        #print('Client is ready...')
        tgt_dt_tm = self.get_target_time(tgt_tm_hr, tgt_tm_min)
        print('Target time is...')
        print(datetime.datetime.fromtimestamp(tgt_dt_tm).strftime('%Y-%m-%d %H:%M:%S'))

        await asyncio.sleep(tgt_dt_tm - time.time())

        while not self.is_closed():
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


    '''async def refresh_online_report_task(self):
        await self.wait_until_ready()

        while not self.is_closed():
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

            await asyncio.sleep(config['tasks']['online_report']['refresh_interval'])'''

    # Events to monitor

    async def on_ready(self):
        print('Bot is ready...')


    async def on_message (self, message):

        if message.content.startswith('!online'):
            print('Getting online report...')
            sender_id = message.author.id
            user = await self.fetch_user(sender_id)

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

            online_message = await user.send(embed=online_report)
        elif message.content.startswith('!link'):
            # remove call to bot
            link_payload = message.content.replace('!link ', '')
            link_payload = link_payload.strip().lower()
            print(link_payload)
            if link_payload == 'report':
                # build report
                report_embed = self.get_link_report()

                await message.channel.send(embed=report_embed)

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
                    await message.channel.send(content=data['status'])



    async def on_member_join(self, member):
        print('{0} joined...'.format(member))

        join = get_msg_details(member, 'join')

        msg = await self.send(join['joinChannel'], join['joinMessage'])


    async def on_member_remove(self, member):
        print('{0} departed...'.format(member))

        remove = get_msg_details(member, 'remove')

        msg = await self.send(remove['removeChannel'], remove['removeMessage'])


# load the bot config
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# load the mode from the command line
parser = argparse.ArgumentParser()
parser.add_argument('--mode')
args = parser.parse_args()
environment = args.mode

discord_config = config['Discord']
token = discord_config[environment]['token']

client = PyWelcomeBot()
client.run(token)
