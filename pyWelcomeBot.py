import discord, json

with open('config.json', 'r') as configFile:
    config = json.load(configFile)

discordConfig = config['Discord']

def getMsgDetails(member, action):

    response = {}

    # Find the server
    server = client.get_server(member.server.id)
    serverName = member.server.name
    # Get server config
    serverConfig = discordConfig['server'][serverName]

    for channel in server.channels:
        if channel.name == serverConfig['{0}Channel'.format(action)]:
            msgChannel = server.get_channel(channel.id)
            if action == 'join':
                msgMessage = serverConfig['{0}Message'.format(action)].format(member.id)
            elif action == 'remove':
                msgMessage = serverConfig['{0}Message'.format(action)].format(member.name)

    response['{0}Channel'.format(action)] = msgChannel
    response['{0}Message'.format(action)] = msgMessage

    return response

client = discord.Client()

@client.event
async def on_ready():
    print('Bot is ready...')

@client.event
async def on_member_join(member):
    print('{0} joined...'.format(member))

    join = getMsgDetails(member, 'join')

    msg = await client.send_message(join['joinChannel'], join['joinMessage'])

@client.event
async def on_member_remove(member):
    print('{0} departed...'.format(member))

    remove = getMsgDetails(member, 'remove')

    msg = await client.send_message(remove['removeChannel'], remove['removeMessage'])

client.run(discordConfig['token'])