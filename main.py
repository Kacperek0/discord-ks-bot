import os
import logging

import boto3
from botocore.exceptions import ClientError
import discord
from discord.ext import commands, tasks
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

intents: discord.Intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot: commands.Bot = commands.Bot(command_prefix='!', intents=intents)

# Replace these with your channel names or IDs
DISCORD_SERVER_NAME: str = os.getenv('DISCORD_SERVER_NAME')
ONLINE_CHANNEL_NAME: str = os.getenv('ONLINE_CHANNEL_NAME')
REPORT_CHANNEL_NAME: str = os.getenv('REPORT_CHANNEL_NAME')
DELIVERY_CHANNEL_NAME: str = os.getenv('DELIVERY_CHANNEL_NAME')
EXCLUDE_GROUP_ROLE_NAME: str = os.getenv('EXCLUDE_GROUP_ROLE_NAME')

# This dictionary will store the mapping of player names to their possible locations
player_locations = defaultdict(list)

# This set will store the names of players that should be excluded
excluded_players = set()

status_message_id = None


def parse_parts(parts: list[str]) -> dict[str, str | None]:
    result = {
        'skull': None,
        'vocation': None,
        'name': None,
        'level': None
    }

    # Split the first part of the message to extract possible skull, vocation, and name
    split_text: list[str] = parts[0].split(':')

    # Parse skull
    if len(split_text) > 1:
        result['skull'] = split_text[1].strip()

    # Parse vocation
    if len(split_text) > 3:
        result['vocation'] = split_text[3].strip()

    # Parse name
    if split_text:
        result['name'] = split_text[-1].strip()

    # Parse level and other information that might be in other parts
    if len(parts) > 1:
        result['level'] = parts[1].strip()

    return result


def message_prettify(message_builder: list[str]) -> list[str]:
    # Add a header to the message
    message_builder.insert(0, 'This is the online ks list:\n')
    message_builder.insert(1, 'Each person on this list is to be treated as persona non grata.')
    message_builder.insert(2, ':dblackskull: is a top priority enemy. Do not play with them and please report if you see them around.')
    message_builder.insert(3, ':d_redskull: is an average priority enemy. Do not play with them.')
    message_builder.insert(4, ':d_whiteskull: is a low priority enemy. Do not play with them.')
    message_builder.insert(5, ':d_greenskull: is for people that did not yet settle deals with the dominando. You can play with them, but be cautious.\n')

    # Add a footer to the message
    message_builder.append('\nPowered by Ten Jack Ryan')


def read_state_from_dynamodb():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ks-bot')

    try:
        response = table.get_item(
            Key={
                'id': '1'
            }
        )
    except ClientError as e:
        logger.error(e.response['Error']['Message'])
    else:
        item = response['Item']
        logger.info(f"Item retrieved: {item}")

        excluded_players = item.get('excluded_players', set())
        status_message_id = item.get('status_message_id', None)

        return excluded_players, status_message_id


def save_to_dynamodb(excluded_players: set[str], status_message_id: str):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ks-bot')

    try:
        response = table.put_item(
            Item={
                'id': '1',
                'excluded_players': excluded_players,
                'status_message_id': status_message_id
            }
        )
    except ClientError as e:
        logger.error(e.response['Error']['Message'])
    else:
        logger.info('Data saved successfully')


@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    fetch_reports.start()
    check_online.start()


@tasks.loop(minutes=5)  # Adjust the timing as needed
async def fetch_reports():
    guild = discord.utils.get(bot.guilds, name=DISCORD_SERVER_NAME)
    report_channel = discord.utils.get(guild.channels, name=REPORT_CHANNEL_NAME)

    if report_channel:
        async for message in report_channel.history(limit=300):  # Adjust the number of messages as needed
            content = message.content
            logger.debug(f'Checking message: {content}')
            if content.startswith('!ks') and '>' in content:
                parts = content.split('>')
                if len(parts) >= 3:
                    player_name = parts[1].strip()
                    location = parts[2].strip()
                    player_locations[player_name].append(location)
                    logger.debug(f'Current_state: {player_locations}')


@bot.command()
async def ks(ctx, command, player_name):
    if command == "exclude":
        role_names = [role.name for role in ctx.author.roles]
        if EXCLUDE_GROUP_ROLE_NAME in role_names:
            excluded_players.add(player_name)
            save_to_dynamodb(excluded_players, status_message_id)
            await ctx.send(f'{player_name} has been excluded from tracking.')
        else:
            await ctx.send('You do not have permission to exclude players.')

    if command == "include":
        role_names = [role.name for role in ctx.author.roles]
        if EXCLUDE_GROUP_ROLE_NAME in role_names:
            excluded_players.remove(player_name)
            save_to_dynamodb(excluded_players, status_message_id)
            await ctx.send(f'{player_name} has been included in tracking.')
        else:
            await ctx.send('You do not have permission to include players.')


@tasks.loop(minutes=1)  # Adjust the timing as needed
async def check_online():
    global status_message_id

    message_builder = []
    guild = discord.utils.get(bot.guilds, name=DISCORD_SERVER_NAME)
    online_channel = discord.utils.get(guild.text_channels, name=ONLINE_CHANNEL_NAME)

    if online_channel:
        async for message in online_channel.history(limit=10): # Adjust the number as needed
            if "Online" in message.content:
                lines = message.content.split('\n')
                # Skip lines until the next line after "_"
                for i, line in enumerate(lines):
                    if line.startswith('_'):
                        lines = lines[i + 1:]
                        break
                # Remove the last line if necessary based on your message format
                lines = lines[:-1]
                for line in lines:
                    if any(skull in line for skull in [':d_whiteskull:', ':d_redskull:', ':d_blackskull:', ':d_greenskull:']):
                        parts = line.split(',')
                        player = parse_parts(parts)
                        if player['name'] not in excluded_players:
                            locations = set(player_locations.get(player['name'], []))
                            locations_str = ', '.join(list(locations)[-5:])
                            message_builder.append(f':{player["skull"]}: :{player["vocation"]}: {player["name"]}, {player["level"]} was last seen at: {locations_str}')
                            logger.debug(f'Player: {player["name"]}, {player["level"]}, {player["skull"]}, {player["vocation"]}, {locations_str}')

    send_channel = discord.utils.get(guild.text_channels, name=DELIVERY_CHANNEL_NAME)
    if send_channel:
        # Check if we should edit an existing message or send a new one
        message_prettify(message_builder)
        if status_message_id:
            try:
                msg_to_edit = await send_channel.fetch_message(status_message_id)
                await msg_to_edit.edit(content='\n'.join(message_builder) if message_builder else 'No current online players.')
                logger.debug('Message edited')
            except discord.NotFound:
                # The message was not found, likely deleted.
                status_message_id = None

        if not status_message_id:
            # Either there was no previous message, or it was deleted.
            sent_message = await send_channel.send('\n'.join(message_builder) if message_builder else 'No current online players.')
            status_message_id = sent_message.id  # Store the new message's ID
            save_to_dynamodb(excluded_players, status_message_id)
            logger.debug('Message sent')


if __name__ == '__main__':
    excluded_players, status_message_id = read_state_from_dynamodb()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
