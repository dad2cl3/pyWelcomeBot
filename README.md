# pyWelcomeBot
Simple Discord bot written in Python to welcome new members to a Discord server and alert admins when members leave the server.

### Online Clan Members
Added a background task to the bot that builds a list of clan members in-game every two minutes. The list is written to a Redis cache in order to support faster retrieval from the bot.

Added the on_message event to listen for the command *!online*. The command calls an API endpoint that retrieves a list of clan members in-game and sends a direct message to the user who invoked the command.
