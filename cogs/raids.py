import datetime
import re
import discord
from discord.ext import commands
from discord import ui, app_commands
import logging
from pytz import timezone
from enum import Enum
from pymongo import MongoClient
import asyncio
import decor.perms as permissions
from errors.boterrors import *

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s: %(message)s',
    handlers=[
        logging.FileHandler('log.log', mode='a'),
        logging.StreamHandler()
    ])  # , datefmt="%Y-%m-%d %H:%M:%S")

# TODO: Add a command to update channel names manually for RLs
# TODO: Command to print template for things, store in txt maybe?
# TODO: Have the bot tell you when you overflow into Backup
# TODO: Have bot remove anyone not meeting the new limit requirement when changing limit

# Global variables for the MongoDB channels, set by set_channels function
global raids
global count
global defaults


class Role(Enum):
    DPS = "dps"
    HEALER = "healer"
    TANK = "tank"
    NONE = "none"


# There are a lot of instances were the DB is updated rather than created, so I made a function for that to save lines.
def update_db(channel_id, raid):
    try:
        logging.info(f"Updating Roster channelID: {channel_id}")
        new_rec = {'$set': {'data': raid.get_data()}}
        raids.update_one({'channelID': channel_id}, new_rec)
        logging.info(f"Roster channelID: {channel_id} - {raid.raid} updated")
    except Exception as e:
        logging.error(f"Save to DB Error: {str(e)}")
        raise IODBError(f"Unable to save to DB")


def get_raid(channel_id):
    """Loads raid information from a database or returns None if there is none"""
    try:
        rec = raids.find_one({'channelID': channel_id})
        if rec is None:
            return None
        raid = Raid(rec['data']['raid'], rec['data']['date'], rec['data']['leader'],
                    rec['data']['dps'],
                    rec['data']['healers'], rec['data']['tanks'],
                    rec['data']['backup_dps'],
                    rec['data']['backup_healers'], rec['data']['backup_tanks'],
                    rec['data']['dps_limit'],
                    rec['data']['healer_limit'], rec['data']['tank_limit'],
                    rec['data']['role_limit'], rec['data']['memo'])
        return raid
    except Exception as e:
        logging.error(f"Load Raid Error: {str(e)}")
        raise IODBError(f"Unable to load Raid from DB")


def update_runs(raid):
    """Updates the number of runs for people in the raid roster"""
    for i in raid.dps:
        counts = count.find_one({'userID': int(i)})
        if counts is None:
            new_data = {
                "userID": int(i),
                "raidCount": 1,
                "lastRaid": raid.raid,
                "lastDate": raid.date,
                "dpsRuns": 1,
                "tankRuns": 0,
                "healerRuns": 0
            }
            try:
                count.insert_one(new_data)
            except Exception as e:
                logging.error(f"Update Count Increase Error: {str(e)}")
                raise IODBError("Unable to update runs info")  # Will automatically return from here
        else:
            counts["raidCount"] += 1
            counts["lastRaid"] = raid.raid
            counts["lastDate"] = raid.date
            counts["dpsRuns"] += 1
            try:
                new_rec = {'$set': counts}
                count.update_one({'userID': int(i)}, new_rec)
            except Exception as e:
                logging.error(f"Update Count Increase Error: {str(e)}")
                raise IODBError("Unable to update runs info")
    for i in raid.healers:
        counts = count.find_one({'userID': int(i)})
        if counts is None:
            new_data = {
                "userID": int(i),
                "raidCount": 1,
                "lastRaid": raid.raid,
                "lastDate": raid.date,
                "dpsRuns": 0,
                "tankRuns": 0,
                "healerRuns": 1
            }
            try:
                count.insert_one(new_data)
            except Exception as e:
                logging.error(f"Update Count Increase Error: {str(e)}")
                raise IODBError("Unable to update runs info")
        else:
            counts["raidCount"] += 1
            counts["lastRaid"] = raid.raid
            counts["lastDate"] = raid.date
            counts["healerRuns"] += 1
            try:
                new_rec = {'$set': counts}
                count.update_one({'userID': int(i)}, new_rec)
            except Exception as e:
                logging.error(f"Update Count Error: {str(e)}")
                raise IODBError("Unable to update runs info")
    for i in raid.tanks:
        counts = count.find_one({'userID': int(i)})
        if counts is None:
            new_data = {
                "userID": int(i),
                "raidCount": 1,
                "lastRaid": raid.raid,
                "lastDate": raid.date,
                "dpsRuns": 0,
                "tankRuns": 1,
                "healerRuns": 0
            }
            try:
                count.insert_one(new_data)
            except Exception as e:
                logging.error(f"Update Count Increase Error: {str(e)}")
                raise IODBError("Unable to update runs info")
        else:
            counts["raidCount"] += 1
            counts["lastRaid"] = raid.raid
            counts["lastDate"] = raid.date
            counts["tankRuns"] += 1
            try:
                new_rec = {'$set': counts}
                count.update_one({'userID': int(i)}, new_rec)
            except Exception as e:
                logging.error(f"Update Count Error: {str(e)}")
                raise IODBError("Unable to update runs info")


def print_initial_menu(ctx):
    """Prints the initial startup menu"""
    try:
        counter = 0
        total = ""
        channels = {}
        rosters = raids.distinct("channelID")
        try:
            for i in rosters:
                channel = ctx.guild.get_channel(i)
                if channel is not None:
                    total += f"{str(counter + 1)}: {channel.name}\n"
                else:
                    total += f"{str(counter + 1)}: {i}\n"
                channels[counter] = i
                counter += 1
        except Exception as e:
            logging.error(f"Menu Print Error: Unable to get channel information: {str(e)}")
            raise DiscordError("Unable to fetch Discord Channel information")
        total += f"0: Exit \n"
        return total, channels
    except Exception as e:
        logging.error(f"Unable to print initial menu: {str(e)}")
        raise IODBError("Unable to load distinct roster information")

def set_channels(config):
    """Function to set the MongoDB information on cog load"""
    global raids
    global count
    global defaults
    client = MongoClient(config['mongo'])
    database = client['bot']  # Or do it with client.PyTest, accessing collections works the same way.
    raids = database.raids
    count = database.count
    defaults = database.defaults


def suffix(d):
    try:
        return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')
    except Exception as e:
        logging.error(f"Suffix Failure: {str(e)}")
        raise ValueError("Unable to set suffix value")

def setup_roster_join_information(og_cmd, user: discord.User, raid):
    """Function to handle people joining a roster"""

    use_msg = False
    slotted = Role.NONE
    msg = ""
    og_msg = ""
    use_default = True
    acceptable_roles = ["dps", "tank", "healer", "heals", "heal"]

    cmd_vals = og_cmd.split(" ", 2)
    if len(cmd_vals) > 1 and cmd_vals[1].lower() in acceptable_roles:
        use_default = False
        if len(cmd_vals) > 2:
            use_msg = True
            msg = cmd_vals[2]
    elif len(cmd_vals) >= 2:
        use_msg = True
        if len(cmd_vals) == 2:
            msg = cmd_vals[1]
        else:
            msg = cmd_vals[1] + " " + cmd_vals[2]
    user_id = user.id

    default_error_msg = f"You have no default set, please specify a role (ex: `{cmd_vals[0].lower()} dps`) or set a default "\
                        f"(ex: `!default dps`) then sign up again."

    # Role handling
    selected_role = None
    if use_default is True:
        default = defaults.find_one({'userID': user_id})
        if default is None:
            raise NoDefaultError(default_error_msg)
        selected_role = default['default']
    elif use_default is False:
        selected_role = cmd_vals[1].lower()
    if selected_role == "dps":
        role = Role.DPS
    elif selected_role == "tank":
        role = Role.TANK
    elif selected_role == "heal" or selected_role == "heals" or selected_role == "healer":
        role = Role.HEALER
    else:
        raise NoDefaultError(default_error_msg)

    user_id = str(user_id)

    # Check if the user swapped their role
    if user_id in raid.dps.keys():
        og_msg = raid.dps.get(user_id)
        slotted = Role.DPS
        raid.remove_dps(user_id)

    elif user_id in raid.backup_dps.keys():
        og_msg = raid.backup_dps.get(user_id)
        raid.remove_dps(user_id)
        slotted = Role.DPS

    elif user_id in raid.healers.keys():
        og_msg = raid.healers.get(user_id)
        raid.remove_healer(user_id)
        slotted = Role.HEALER

    elif user_id in raid.backup_healers.keys():
        og_msg = raid.backup_healers.get(user_id)
        raid.remove_healer(user_id)
        slotted = Role.HEALER

    elif user_id in raid.tanks.keys():
        og_msg = raid.tanks.get(user_id)
        raid.remove_tank(user_id)
        slotted = Role.TANK

    elif user_id in raid.backup_tanks.keys():
        og_msg = raid.backup_tanks.get(user_id)
        raid.remove_tank(user_id)
        slotted = Role.TANK

    # Determine if user is doing su or bu (assume su first)
    issu = True
    if cmd_vals[0].lower() == "!bu":
        issu = False

    # Check that the user is switching between two roles or re-signing up with the same role
    if slotted != Role.NONE and og_msg != "" and use_msg is False and slotted == role:
        msg = og_msg

    if issu is True:
        if role == Role.DPS:
            result = raid.add_dps(user_id, msg)
        elif role == Role.TANK:
            result = raid.add_tank(user_id, msg)
        elif role == Role.HEALER:
            result = raid.add_healer(user_id, msg)
        else:
            raise UnknownError(f"Roster Setup Unknown Error: ISSU TRUE ELSE REACHED INPUTS = {og_cmd} FROM {user.display_name}")
    elif issu is False:
        if role == Role.DPS:
            result = raid.add_backup_dps(user_id, msg)
        elif role == Role.TANK:
            result = raid.add_backup_tank(user_id, msg)
        elif role == Role.HEALER:
            result = raid.add_backup_healer(user_id, msg)
        else:
            raise UnknownError(f"Roster Setup Unknown Error: ISSU FALSE ELSE REACHED INPUTS = {og_cmd} FROM {user.display_name}")
    else:
        raise UnknownError(f"Roster Setup Unknown Error: ISSU TRUE OR FALSE ELSE REACHED INPUTS = {og_cmd} FROM {user.display_name}")

    return result, raid

def generate_channel_name(date, raid_name, tz_info):
    """Function to generate channel names on changed information"""
    date = date.strip()
    if date.upper() == "ASAP":
        new_name = f"{raid_name}-ASAP"
        return new_name

    new_time = datetime.datetime.utcfromtimestamp(int(re.sub('[^0-9]', '', date)))
    tz = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(
        tz=timezone(tz_info))
    weekday = tz.strftime("%a")
    day = tz.day
    new_name = f"{raid_name}-{weekday}-{str(day)}{suffix(day)}"
    return new_name


def format_date(date):
    """Formats the timestamp date to the correct version"""
    date = date.strip()
    if date.upper() == "ASAP":
        return date.upper()

    formatted_date = f"<t:{re.sub('[^0-9]', '', date)}:f>"
    return formatted_date


class Raid:
    """Class for handling roster and related information"""

    def __init__(self, raid, date, leader, dps={}, healers={}, tanks={}, backup_dps={}, backup_healers={},
                 backup_tanks={}, dps_limit=0, healer_limit=0, tank_limit=0, role_limit=0, memo="delete"):
        self.raid = raid
        self.date = date
        self.leader = leader
        self.dps = dps
        self.tanks = tanks
        self.healers = healers
        self.backup_dps = backup_dps
        self.backup_tanks = backup_tanks
        self.backup_healers = backup_healers
        self.dps_limit = dps_limit
        self.tank_limit = tank_limit
        self.healer_limit = healer_limit
        self.role_limit = role_limit
        self.memo = memo

    def get_data(self):
        all_data = {
            "raid": self.raid,
            "date": self.date,
            "leader": self.leader,
            "dps": self.dps,
            "healers": self.healers,
            "tanks": self.tanks,
            "backup_dps": self.backup_dps,
            "backup_healers": self.backup_healers,
            "backup_tanks": self.backup_tanks,
            "dps_limit": self.dps_limit,
            "healer_limit": self.healer_limit,
            "tank_limit": self.tank_limit,
            "role_limit": self.role_limit,
            "memo": self.memo
        }
        return all_data

    # Add people into the right spots
    def add_dps(self, n_dps, p_class=""):
        if len(self.dps) < self.dps_limit:
            self.dps[n_dps] = p_class
            return "Added as DPS"
        else:
            self.backup_dps[n_dps] = p_class
            return "DPS spots full, slotted for Backup"

    def add_healer(self, n_healer, p_class=""):
        if len(self.healers) < self.healer_limit:
            self.healers[n_healer] = p_class
            return "Added as Healer"
        else:
            self.backup_healers[n_healer] = p_class
            return "Healer spots full, slotted for Backup"

    def add_tank(self, n_tank, p_class=""):
        if len(self.tanks) < self.tank_limit:
            self.tanks[n_tank] = p_class
            return "Added as Tank"
        else:
            self.backup_tanks[n_tank] = p_class
            return "Tank spots full, slotted for Backup"

    def add_backup_dps(self, n_dps, p_class=""):
        self.backup_dps[n_dps] = p_class
        return "Added for backup as DPS"

    def add_backup_healer(self, n_healer, p_class=""):
        self.backup_healers[n_healer] = p_class
        return "Added for backup as Healer"

    def add_backup_tank(self, n_tank, p_class=""):
        self.backup_tanks[n_tank] = p_class
        return "Added for backup as Tank"

    # remove people from right spots
    def remove_dps(self, n_dps):
        if n_dps in self.dps:
            del self.dps[n_dps]
        else:
            del self.backup_dps[n_dps]

    def remove_healer(self, n_healer):
        if n_healer in self.healers:
            del self.healers[n_healer]
        else:
            del self.backup_healers[n_healer]

    def remove_tank(self, n_tank):
        if n_tank in self.tanks:
            del self.tanks[n_tank]
        else:
            del self.backup_tanks[n_tank]

    def change_role_limit(self, new_role_limit):
        self.role_limit = new_role_limit

    def change_dps_limit(self, new_dps_limit):
        self.dps_limit = new_dps_limit

    def change_healer_limit(self, new_healer_limit):
        self.healer_limit = new_healer_limit

    def change_tank_limit(self, new_tank_limit):
        self.tank_limit = new_tank_limit

    def fill_spots(self, num):
        try:
            loop = True
            while loop:
                if len(self.dps) < self.dps_limit and len(self.backup_dps) > 0:
                    first = list(self.backup_dps.keys())[0]
                    self.dps[first] = self.backup_dps.get(first)
                    del self.backup_dps[first]
                else:
                    loop = False
            loop = True
            while loop:
                if len(self.healers) < self.healer_limit and len(self.backup_healers) > 0:
                    first = list(self.backup_healers.keys())[0]
                    self.healers[first] = self.backup_healers.get(first)
                    del self.backup_healers[first]
                else:
                    loop = False
            loop = True
            while loop:
                if len(self.tanks) < self.tank_limit and len(self.backup_tanks) > 0:
                    first = list(self.backup_tanks.keys())[0]
                    self.tanks[first] = self.backup_tanks.get(first)
                    del self.backup_tanks[first]
                else:
                    loop = False
            logging.info(f"Spots filled in raid id {str(num)}")
        except Exception as e:
            logging.error(f"Fill Spots error: {str(e)}")
class TrialModal(discord.ui.Modal):
    def __init__(self, raid: Raid, interaction: discord.Interaction, config ):
        self.config = config
        self.leader_trial_val = None
        self.date_val = None
        self.limit_val = None
        self.role_nums_val = "8,2,2"
        self.memo_val = "None"
        self.new_roster = True
        if raid is not None:
            self.new_roster = False
            self.leader_trial_val = f"{raid.leader},{raid.raid}"
            self.date_val = f"{raid.date}"
            self.limit_val = f"{raid.role_limit}"
            self.role_nums_val = f"{raid.dps_limit},{raid.healer_limit},{raid.tank_limit}"
            self.memo_val = f"{raid.memo}"
        super().__init__(title='Trial Manager')
        self.initialize()

    def initialize(self):
        # Add all the items here based on what is above
        self.leader_trial =  discord.ui.TextInput(
            label='Raid Lead and Trial',
            placeholder='Format: Raid Lead, Trial',
            default = self.leader_trial_val,
            required=True
        )
        self.date = discord.ui.TextInput(
            label="Date",
            placeholder="Put Timestamp here",
            default = self.date_val,
            required=True
        )
        self.limit = discord.ui.TextInput(
            label="Role Limit",
            placeholder="Put Role Limit here",
            default=self.limit_val,
            required=True,
        )
        self.role_nums = discord.ui.TextInput(
            label="DPS/Healer/Tank Role Nums",
            default=self.role_nums_val,
            required=True
        )
        self.memo = discord.ui.TextInput(
            label="Memo",
            default=self.memo_val,
            placeholder="Type None if you do not want a memo.",
            style=discord.TextStyle.long,
            required=True
        )
        self.add_item(self.leader_trial)
        self.add_item(self.date)
        self.add_item(self.limit)
        self.add_item(self.role_nums)
        self.add_item(self.memo)

    async def on_submit(self, interaction: discord.Interaction):
        def factory(fact_leader, fact_raid, fact_date, fact_dps_limit, fact_healer_limit, fact_tank_limit,
                    fact_role_limit, fact_memo, config):
            if fact_dps_limit is None and fact_healer_limit is None and fact_tank_limit is None:
                fact_dps_limit = config["raids"]["roster_defaults"]["dps"]
                fact_healer_limit = config["raids"]["roster_defaults"]["healers"]
                fact_tank_limit = config["raids"]["roster_defaults"]["tanks"]
            if fact_role_limit == 0:
                fact_role_limit = config["raids"]["roles"]["base"]
            elif fact_role_limit == 1:
                fact_role_limit = config["raids"]["roles"]["first"]
            elif fact_role_limit == 2:
                fact_role_limit = config["raids"]["roles"]["second"]
            elif fact_role_limit == 3:
                fact_role_limit = config["raids"]["roles"]["third"]
            elif fact_role_limit == 4:
                fact_role_limit = config["raids"]["roles"]["fourth"]
            else:
                raise UnknownError("Error: Somehow the code reached this in theory unreachable spot. Time to panic!")

            dps, healers, tanks, backup_dps, backup_healers, backup_tanks = {}, {}, {}, {}, {}, {}
            return Raid(fact_raid, fact_date, fact_leader, dps, healers, tanks, backup_dps, backup_healers,
                        backup_tanks, fact_dps_limit, fact_healer_limit, fact_tank_limit, fact_role_limit,
                        fact_memo)

        try:
            # Split the values:
            role_limit = int(self.limit.value)
            if role_limit < 0 or role_limit > 4:
                await interaction.response.send_message(f"Invalid input, the role_limits must be between 0 and 4")
                return
            leader, raid = self.leader_trial.value.split(",")
            dps_limit, healer_limit, tank_limit = self.role_nums.value.split(",")
            dps_limit = int(dps_limit.strip())
            healer_limit = int(healer_limit.strip())
            tank_limit = int(tank_limit.strip())
            formatted_date = format_date(self.date.value)

            created = factory(leader, raid, formatted_date, dps_limit, healer_limit, tank_limit, role_limit, self.memo.value, self.config)

            logging.info(f"Creating new channel.")
            category = interaction.guild.get_channel(self.config["raids"]["category"])
            new_name = generate_channel_name(created.date, created.raid, self.config["raids"]["timezone"])
            channel = await category.create_text_channel(new_name)
            limiter = discord.utils.get(interaction.user.guild.roles, name=created.role_limit)
            embed = discord.Embed(
                title=f"{created.raid} {created.date}",
                description=f"Role Required: {limiter.mention}\n\nI hope people sign up for this.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Remember to spay or neuter your support!\nAnd mention your sets!")
            embed.set_author(name="Raid Lead: " + leader)
            embed.add_field(name="Calling Healers!", value='To Heal Us!', inline=False)
            embed.add_field(name="Calling Tanks!", value='To Be Stronk!', inline=False)
            embed.add_field(name="Calling DPS!", value='To Stand In Stupid!', inline=False)

            if created.memo != "None":
                embed_memo = discord.Embed(
                    title=" ",
                    color=discord.Color.dark_gray()
                )
                embed_memo.add_field(name=" ", value=created.memo, inline=True)
                embed_memo.set_footer(text="This is very important!")
                await channel.send(embed=embed_memo)
            await channel.send(embed=embed)
            logging.info(f"Created Channel: channelID: {str(channel.id)}")
        except Exception as e:
            await interaction.response.send_message(
                f"Error in creating category channel and sending embed. Please make sure all your inputs are correct.")
            logging.error(f"Raid Creation Channel And Embed Error: {str(e)}")
            return

        # Save raid info to MongoDB
        try:
            logging.info(f"Saving Roster channelID: {str(channel.id)}")
            rec = {
                'channelID': channel.id,
                'data': created.get_data()
            }
            raids.insert_one(rec)
            logging.info(f"Saved Roster channelID: {str(channel.id)}")
        except Exception as e:
            await interaction.response.send_message("Error in saving information to MongoDB, roster was not saved.")
            logging.error(f"Raid Creation MongoDB Error: {str(e)}")
            return
        await interaction.response.send_message(f"Created Roster and Channel")
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(f'I was unable to complete the command. Logs have more detail.')
        logging.error(f"Trial Creation Error: {str(error)}")

class Raids(commands.Cog, name="Trials"):
    """Commands related to Raids/Trials"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        set_channels(self.bot.config)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Event listener for when someone leaves the server to remove them from all rosters they are on."""
        try:
            was_on = False
            user_id = str(member.id)
            rosters = raids.distinct("channelID")
            private_channel = member.guild.get_channel(self.bot.config['administration']['private'])
            await private_channel.send(f"{member.name} - {member.display_name} has left the server")
            for i in rosters:
                raid = get_raid(i)
                channel = member.guild.get_channel(i)
                if user_id in raid.dps.keys():
                    raid.remove_dps(user_id)
                    await private_channel.send(f"Traitor was removed as a DPS from {channel.name}")
                    was_on = True
                    update_db(i, raid)
                elif user_id in raid.backup_dps.keys():
                    raid.remove_dps(user_id)
                    await private_channel.send(f"Traitor was removed as a backup DPS from {channel.name}")
                    was_on = True
                    update_db(i, raid)
                elif user_id in raid.healers.keys():
                    raid.remove_healer(user_id)
                    await private_channel.send(f"Traitor was removed as a Healer from {channel.name}")
                    was_on = True
                    update_db(i, raid)
                elif user_id in raid.backup_healers.keys():
                    raid.remove_healer(user_id)
                    await private_channel.send(f"Traitor was removed as a backup Healer from {channel.name}")
                    was_on = True
                    update_db(i, raid)
                elif user_id in raid.tanks.keys():
                    raid.remove_tank(user_id)
                    await private_channel.send(f"Traitor was removed as a Tank from {channel.name}")
                    was_on = True
                    update_db(i, raid)
                elif user_id in raid.backup_tanks.keys():
                    raid.remove_tank(user_id)
                    await private_channel.send(f"Traitor was removed as a backup Tank from {channel.name}")
                    was_on = True
                    update_db(i, raid)
            if was_on:
                await private_channel.send(f"The Traitor has been removed from all active rosters.")
            else:
                await private_channel.send(f"The Traitor was not on any active rosters.")
        except Exception as e:
            logging.error(f"User Roster Exit Removal Error: {str(e)}")
            raise OSError(f"Unable to remove user on exit from rosters.")

    @app_commands.command(name="trial", description="For Raid Leads: Opens Trial Creation Modal")
    @permissions.application_has_raid_lead()
    async def create_roster(self, interaction: discord.Interaction) -> None:
        raid = None
        await interaction.response.send_modal(TrialModal(raid, interaction, self.bot.config))

    @commands.command(name="trial", hidden=True)
    async def old_trial_alert(self, ctx: commands.Context):
        await ctx.reply(f"This command has moved to an application command, look for /trial instead!")

    @commands.command(name="su")
    async def su(self, ctx: commands.Context):
        """Signs you up to a roster | `!su [optional role] [optional message]`"""
        try:
            channel_id = ctx.message.channel.id
            try:
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Sorry! This command only works in a roster channel!")
                    return
            except Exception as e:
                await ctx.send("Unable to load raid.")
                logging.error(f"SU Load Raid Error: {str(e)}")
                return

            limiter = discord.utils.get(ctx.message.author.guild.roles, name=raid.role_limit)
            if ctx.message.author not in limiter.members:
                if raid.role_limit == self.bot.config["raids"]["roles"]["base"]:
                    await ctx.reply(f"Hey wait, you should have {raid.role_limit} in order to see this channel!")
                elif raid.role_limit == self.bot.config["raids"]["roles"]["first"]:
                    await ctx.reply(
                        f"You need to be CP 160 to join this roster, if you are CP 160 then go to <#1102081398136909854> "
                        f"and select the **Kyne's Follower** role from the Misc Roles section.")
                else:
                    await ctx.reply(
                        f"You do not have the role to join this roster, please check <#933821777149329468> "
                        f"to see what you need to do to get the {raid.role_limit} role")
                return

            result, raid = setup_roster_join_information(ctx.message.content, ctx.author, raid)

            try:
                update_db(channel_id, raid)
            except Exception as e:
                await ctx.send("I was unable to save the updated roster.")
                logging.error(f"SU Error saving new roster: {str(e)}")
                return
            await ctx.reply(f"{result}")
        except (UnknownError, NoDefaultError) as e:
            raise e
        except Exception as e:
            await ctx.send(f"I was was unable to sign you up due to processing errors.")
            logging.error(f"SU Error: {str(e)}")
            return

    @commands.command(name="bu")
    async def bu(self, ctx: commands.Context):
        """Signs you up as a backup | `!bu [optional role] [optional message]`"""
        try:
            channel_id = ctx.message.channel.id
            try:
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Sorry! This command only works in a roster channel!")
                    return
            except Exception as e:
                await ctx.send("Unable to load raid.")
                logging.error(f"BU Load Raid Error: {str(e)}")
                return

            limiter = discord.utils.get(ctx.message.author.guild.roles, name=raid.role_limit)
            if ctx.message.author not in limiter.members:
                if raid.role_limit == self.bot.config["raids"]["roles"]["base"]:
                    await ctx.reply(f"Hey wait, you should have {raid.role_limit} in order to see this channel!")
                elif raid.role_limit == self.bot.config["raids"]["roles"]["first"]:
                    await ctx.reply(
                        f"You need to be CP 160 to join this roster, if you are CP 160 then go to <#1102081398136909854> "
                        f"and select the **Kyne's Follower** role from the Misc Roles section.")
                else:
                    await ctx.reply(
                        f"You do not have the role to join this roster, please check <#933821777149329468> "
                        f"to see what you need to do to get the {raid.role_limit} role")
                return

            result, raid = setup_roster_join_information(ctx.message.content, ctx.author, raid)

            try:
                update_db(channel_id, raid)
            except Exception as e:
                await ctx.send("I was unable to save the updated roster.")
                logging.error(f"BU Error saving new roster: {str(e)}")
                return
            await ctx.reply(f"{result}")
        except (UnknownError, NoDefaultError) as e:
            raise e
        except Exception as e:
            await ctx.send(f"I was was unable to sign you up due to processing errors.")
            logging.error(f"BU Error: {str(e)}")
            return

    @commands.command(name="wd")
    async def wd(self, ctx: commands.Context):
        """Will remove you from both BU and Main rosters"""
        try:
            worked = False
            channel_id = ctx.message.channel.id
            user_id = str(ctx.message.author.id)
            try:
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Sorry! This command only works in a roster channel!")
                    return
            except Exception as e:
                await ctx.send("Unable to load raid.")
                logging.error(f"WD Load Raid Error: {str(e)}")
                return

            if user_id in raid.dps.keys() or \
                    user_id in raid.backup_dps.keys():
                raid.remove_dps(user_id)
                worked = True

            elif user_id in raid.healers.keys() or \
                    user_id in raid.backup_healers.keys():
                raid.remove_healer(user_id)
                worked = True

            elif user_id in raid.tanks.keys() or \
                    user_id in raid.backup_tanks.keys():
                raid.remove_tank(user_id)
                worked = True
            else:
                if not worked:
                    await ctx.send("You are not signed up for this roster")
            if worked:
                try:
                    if worked is True:
                        update_db(channel_id, raid)
                except Exception as e:
                    await ctx.send("I was unable to save the updated roster.")
                    logging.error(f"WD Error saving new roster: {str(e)}")
                    return
                await ctx.reply("Removed :(")
        except Exception as e:
            await ctx.send("Unable to withdraw you from the roster")
            logging.error(f"WD error: {str(e)}")
            return

    @commands.command(name="status")
    async def send_status_embed(self, ctx: commands.Context):
        """Posts the current roster information"""
        try:
            channel_id = ctx.message.channel.id
            try:
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Sorry! This command only works in a roster channel!")
                    return
            except Exception as e:
                await ctx.send("Unable to load raid.")
                logging.error(f"Status Load Raid Error: {str(e)}")
                return

            dps_count = 0
            healer_count = 0
            tank_count = 0
            guild = self.bot.get_guild(self.bot.config['guild'])
            modified = False
            limiter = discord.utils.get(ctx.message.author.guild.roles, name=raid.role_limit)
            embed = discord.Embed(
                title=f"{raid.raid} {raid.date}",
                description=f"Role Required: {limiter.mention}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Remember to spay or neuter your support!\nAnd mention your sets!")
            embed.set_author(name="Raid Lead: " + raid.leader)
            names = ""
            if not len(raid.healers) == 0:
                to_remove = []
                for i in raid.healers:
                    member_name = guild.get_member(int(i))
                    if member_name is None:
                        to_remove.append(i)
                        # Check if there are no healers left, if so then set names to None
                        if len(to_remove) == len(raid.healers):
                            names = "None"
                    else:
                        names += f"{self.bot.config['raids']['healer_emoji']}{member_name.display_name} {raid.healers[i]}\n"
                        healer_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        raid.remove_healer(i)
                    modified = True
            # TANKS
            if not len(raid.tanks) == 0:
                to_remove = []
                tanks = raid.tanks
                for i in tanks:
                    member_name = guild.get_member(int(i))
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(raid.tanks):
                            names = "None"
                    else:
                        names += f"{self.bot.config['raids']['tank_emoji']}{member_name.display_name} {raid.tanks[i]}\n"
                        tank_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        raid.remove_tank(i)
                    modified = True
            # DPS
            if not len(raid.dps) == 0:
                to_remove = []
                dps = raid.dps
                for i in dps:
                    member_name = guild.get_member(int(i))
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(raid.dps):
                            names = "None"
                    else:
                        names += f"{self.bot.config['raids']['dps_emoji']}{member_name.display_name} {raid.dps[i]}\n"
                        dps_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        raid.remove_dps(i)
                    modified = True
            if not names == "":
                embed.add_field(name="Roster", value=names, inline=False)
                names = f"Healers: {str(healer_count)}/{str(raid.healer_limit)}\nTanks: {str(tank_count)}/{str(raid.tank_limit)}\nDPS: {str(dps_count)}/{str(raid.dps_limit)}"
                embed.add_field(name="Total", value=names, inline=False)
            names = ""

            # Show Backup/Overflow Roster
            dps_count = 0
            healer_count = 0
            tank_count = 0
            # BACKUP HEALERS
            if not len(raid.backup_healers) == 0:
                to_remove = []
                backup_healers = raid.backup_healers
                for i in backup_healers:
                    member_name = guild.get_member(int(i))
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(raid.backup_healers):
                            names = "None"
                    else:
                        names += f"{self.bot.config['raids']['healer_emoji']}{member_name.display_name} {raid.backup_healers[i]}\n"
                        healer_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        raid.remove_healer(i)
                    modified = True

            # BACKUP TANKS
            if not len(raid.backup_tanks) == 0:
                to_remove = []
                tanks = raid.backup_tanks
                for i in tanks:
                    member_name = guild.get_member(int(i))
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(raid.backup_tanks):
                            names = "None"
                    else:
                        names += f"{self.bot.config['raids']['tank_emoji']}{member_name.display_name} {raid.backup_tanks[i]}\n"
                        tank_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        raid.remove_tank(i)
                    modified = True
            # BACKUP DPS
            if not len(raid.backup_dps) == 0:
                to_remove = []
                dps = raid.backup_dps
                for i in dps:
                    member_name = guild.get_member(int(i))
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(raid.backup_dps):
                            names = "None"
                    else:
                        names += f"{self.bot.config['raids']['dps_emoji']}{member_name.display_name} {raid.backup_dps[i]}\n"
                        dps_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        raid.remove_dps(i)
                    modified = True

            if not names == "":
                embed.add_field(name="Backups", value=names, inline=False)
                names = f"Healers: {str(healer_count)}\nTanks: {str(tank_count)}\nDPS: {str(dps_count)}"
                embed.add_field(name="Total Backups", value=names, inline=False)

            if raid.memo != "delete":
                embed_memo = discord.Embed(
                    title=" ",
                    color=discord.Color.dark_gray()
                )
                embed_memo.add_field(name=" ", value=raid.memo, inline=True)
                embed_memo.set_footer(text="This is very important!")
                await ctx.send(embed=embed_memo)
            await ctx.send(embed=embed)
            if modified:
                try:
                    update_db(channel_id, raid)
                except Exception as e:
                    await ctx.send("I was unable to save the updated roster.")
                    logging.error(f"Status Error saving new roster: {str(e)}")
                    return
        except Exception as e:
            logging.error(f"Status check error: {str(e)}")
            await ctx.send("Unable to send status.")
            return

    @commands.command(name="msg", aliases=["message"])
    async def set_message(self, ctx: commands.Context):
        """Modifies your message in the roster | `!msg [message]`"""
        try:
            try:
                channel_id = ctx.message.channel.id
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Sorry! This command only works in a roster channel!")
                    return
            except Exception as e:
                await ctx.send("Unable to load raid.")
                logging.error(f"MSG Load Raid Error: {str(e)}")
                return
            msg = ctx.message.content
            msg = msg.split(" ", 1)
            if len(msg) == 1:
                msg = ""
            else:
                msg = msg[1]
            user_id = str(ctx.message.author.id)
            found = True
            if user_id in raid.dps.keys():
                raid.dps[user_id] = msg
            elif user_id in raid.backup_dps:
                raid.backup_dps[user_id] = msg
            elif user_id in raid.healers:
                raid.healers[user_id] = msg
            elif user_id in raid.backup_healers:
                raid.backup_healers[user_id] = msg
            elif user_id in raid.tanks:
                raid.tanks[user_id] = msg
            elif user_id in raid.backup_tanks:
                raid.backup_tanks[user_id] = msg
            else:
                await ctx.send("You are not signed up to the roster.")
                found = False
            if found:
                try:
                    update_db(channel_id, raid)
                except Exception as e:
                    await ctx.send("I was unable to save the updated roster.")
                    logging.error(f"Message Update Error saving new roster: {str(e)}")
                    return
                await ctx.reply("Updated!")
        except Exception as e:
            await ctx.send("Unable to update the roster message.")
            logging.error(f"Message Update Error: {str(e)}")
            return

    @commands.command(name="count")
    async def check_own_count(self, ctx: commands.Context):
        """A way for people to check their number of raid runs"""
        try:
            user = ctx.message.author
            counts = count.find_one({'userID': user.id})
            if counts is not None:
                embed = discord.Embed(
                    title=user.display_name,
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Thank you for coming! Come again!")
                embed.set_author(name=f"Runs with {ctx.guild.name}")
                embed.add_field(name="Total Runs:", value=counts["raidCount"], inline=True)
                embed.add_field(name="Last Ran:", value=counts["lastRaid"], inline=True)
                embed.add_field(name="Last Date:", value=counts["lastDate"], inline=True)
                embed.add_field(name="Stats", value="Role Runs", inline=False)
                embed.add_field(name="DPS Runs:", value=counts["dpsRuns"], inline=True)
                embed.add_field(name="Tank Runs:", value=counts["tankRuns"], inline=True)
                embed.add_field(name="Healer Runs:", value=counts["healerRuns"], inline=True)
                await ctx.send(embed=embed)
            else:
                new_data = {
                    "userID": user.id,
                    "raidCount": 0,
                    "lastRaid": "none",
                    "lastDate": "<t:0:f>",
                    "dpsRuns": 0,
                    "tankRuns": 0,
                    "healerRuns": 0
                }
                try:
                    count.insert_one(new_data)
                except Exception as e:
                    logging.error(f"Count empty initialization error: {str(e)}")
                    await ctx.send("I was unable to initialize a count.")
                    return
                embed = discord.Embed(
                    title=user.display_name,
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Thank you for coming! Come again!")
                embed.set_author(name=f"Runs with {ctx.guild.name}")
                embed.add_field(name="Total Runs:", value=0, inline=True)
                embed.add_field(name="Last Ran:", value="None", inline=True)
                embed.add_field(name="Last Date:", value="<t:0:f>", inline=True)
                embed.add_field(name="Stats", value="Role Runs", inline=False)
                embed.add_field(name="DPS Runs:", value="0", inline=True)
                embed.add_field(name="Tank Runs:", value="0", inline=True)
                embed.add_field(name="Healer Runs:", value="0", inline=True)
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Unable to check count")
            logging.error(f"Count check error: {str(e)}")

    @commands.command(name="fill")
    async def roster_fill(self, ctx: commands.Context):
        """ For Raid Leads: Lets you select the raid to fill the main list from backups."""
        try:
            try:
                role = discord.utils.get(ctx.message.author.guild.roles, name=self.bot.config['raids']['lead'])
                if role != "@everyone" and ctx.message.author not in role.members:
                    await ctx.reply(f"You do not have permission to use this command")
                    return
            except Exception as e:
                await ctx.send(
                    f"Unable to verify roles, check that the config is spelled the same as the discord role.")
                logging.error(f"creation error on role verification: {str(e)}")
                return
            run = True
            while run:
                try:
                    user = ctx.message.author

                    def check(m: discord.Message):  # m = discord.Message.
                        return user == m.author

                    total, channels = print_initial_menu(ctx)
                    await ctx.reply("Enter a number from the list below to have the roster closed and "
                                    "the channel deleted")
                    await ctx.send(total)
                    try:
                        msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, fill has timed out")
                        return
                    # msg = discord.Message
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                channel_id = channels.get(choice)
                                try:
                                    try:
                                        channel = ctx.guild.get_channel(channel_id)
                                        raid = get_raid(channel_id)
                                        if raid is None:
                                            await ctx.send(f"Unable to find roster information.")
                                            return

                                    except Exception as e:
                                        await ctx.send(f"Unable to get roster information.")
                                        logging.error(f"Fill Raid Get Error: {str(e)}")
                                        return

                                    await ctx.send(f"Fill Roster: {raid.raid} - {channel.name} (y/n)?")
                                    confirm = await self.bot.wait_for("message", check=check, timeout=15.0)
                                    confirm = confirm.content.lower()
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, fill has timed out")
                                    return
                                else:
                                    # Verify that the trial did happen, and if so then add a +1 to each person's count
                                    if confirm == "y":
                                        try:
                                            raid.fill_spots(channel_id)
                                            update_db(channel_id, raid)
                                        except Exception as e:
                                            await ctx.send("I was unable to save the updated roster.")
                                            logging.error(f"Message Update Error saving new roster: {str(e)}")
                                            return

                                        await ctx.send("Spots filled!")
                                        run = False
                                    else:
                                        if confirm == 'n':
                                            await ctx.send("Returning to menu.")
                                        else:
                                            await ctx.send("Invalid response, returning to menu.")
                            except KeyError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
                except Exception as e:
                    await ctx.send(
                        f"I was unable to fill the roster")
                    logging.error(f"Fill Error: {str(e)}")
        except Exception as e:
            await ctx.send(f"Unable to process the command")
            logging.error(f"Fill Roster Error: {str(e)}")
            return

    @commands.command(name="call")
    @permissions.has_raid_lead()
    async def send_message_to_everyone(self, ctx: commands.Context):
        """For Raid Leads: A way to send a ping to everyone in a roster."""
        try:
            user = ctx.message.author
            try:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                run = True
                while run:
                    try:
                        total, channels = print_initial_menu(ctx)
                        await ctx.reply("Enter a number from the list below to send a mass message.")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, call has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                channel_id = channels.get(choice)
                                try:
                                    await ctx.send("Enter the message to send, or cancel to exit.")
                                    confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                                    msg = confirm.content
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, call has timed out")
                                    return
                                else:
                                    if msg.lower() == "cancel":
                                        await ctx.send("Exiting command")
                                        return
                                    else:
                                        confirmation_message = f"Send this message:\n{msg}\n\ny/n?"
                                        await ctx.send(confirmation_message)
                                        confirm = await self.bot.wait_for("message", check=check, timeout=15.0)
                                        confirm = confirm.content
                                        if confirm.lower() == "y":
                                            try:
                                                try:
                                                    channel = ctx.guild.get_channel(channel_id)
                                                    raid = get_raid(channel_id)
                                                    if raid is None:
                                                        await ctx.send(f"Unable to find roster information.")
                                                        return
                                                except Exception as e:
                                                    await ctx.send(f"Unable to get roster information.")
                                                    logging.error(f"Call Raid Get Error: {str(e)}")
                                                    return
                                                names = "\nHealers \n"
                                                for i in raid.healers:
                                                    for j in ctx.guild.members:
                                                        if int(i) == j.id:
                                                            names += j.mention + "\n"
                                                if len(raid.healers) == 0:
                                                    names += "None " + "\n"

                                                names += "\nTanks \n"
                                                for i in raid.tanks:
                                                    for j in ctx.guild.members:
                                                        if int(i) == j.id:
                                                            names += j.mention + "\n"
                                                if len(raid.tanks) == 0:
                                                    names += "None" + "\n"

                                                names += "\nDPS \n"
                                                for i in raid.dps:
                                                    for j in ctx.guild.members:
                                                        if int(i) == j.id:
                                                            names += j.mention + "\n"
                                                if len(raid.dps) == 0:
                                                    names += "None" + "\n"
                                                await channel.send(f"A MESSAGE FOR:\n{names}\n{msg}")
                                            except Exception as e:
                                                await ctx.send("Error printing roster")
                                                logging.error("Summon error: " + str(e))
                                            run = False
                                            await ctx.send("Message sent.")
                                        elif confirm.lower() == "n":
                                            await ctx.send("Returning to start of section.")
                                        else:
                                            await ctx.send("Not a valid input, returning to start of section.")
                            except KeyError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            except Exception as e:
                logging.error(f"Call error: {str(e)}")
                await ctx.send("I was unable to call everyone")
                return
        except Exception as e:
            logging.error(f"Call error: {str(e)}")
            await ctx.send("I was unable to call everyone")
            return

    @commands.command(name="remove")
    @permissions.has_raid_lead()
    async def remove_from_roster(self, ctx: commands.Context):
        """For Raid Leads: Removes someone from the roster"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            while run:
                try:
                    total, channels = print_initial_menu(ctx)
                    await ctx.reply("Enter a number from the list below to select the roster")
                    await ctx.send(total)
                    #                        event = on_message without on_
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    # msg = discord.Message
                except asyncio.TimeoutError:
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.send(f"{ctx.author.mention}, remove has timed out")
                    return
                else:
                    # at this point the check has become True and the wait_for has done its work now we can do ours
                    try:
                        choice = int(msg.content)
                        choice -= 1  # Need to lower it by one for the right number to get
                        if choice == -1:
                            await ctx.send("Exiting command")
                            return
                        try:
                            try:
                                try:
                                    channel_id = channels.get(choice)
                                    raid = get_raid(channel_id)
                                    if raid is None:
                                        await ctx.send(f"Unable to find roster information.")
                                        return

                                except Exception as e:
                                    await ctx.send(f"Unable to get roster information.")
                                    logging.error(f"Remove Raid Get Error: {str(e)}")
                                    return
                                roster = []
                                counter = 1
                                total = ""
                                # Print out everyone and put them in a list to get from
                                for i in raid.dps.keys():
                                    roster.append(i)
                                    total += f"{counter}: {ctx.guild.get_member(int(i)).display_name}\n"
                                    counter += 1
                                for i in raid.healers.keys():
                                    roster.append(i)
                                    total += f"{counter}: {ctx.guild.get_member(int(i)).display_name}\n"
                                    counter += 1
                                for i in raid.tanks.keys():
                                    roster.append(i)
                                    total += f"{counter}: {ctx.guild.get_member(int(i)).display_name}\n"
                                    counter += 1
                                for i in raid.backup_dps.keys():
                                    roster.append(i)
                                    total += f"{counter}: {ctx.guild.get_member(int(i)).display_name}\n"
                                    counter += 1
                                for i in raid.backup_healers.keys():
                                    roster.append(i)
                                    total += f"{counter}: {ctx.guild.get_member(int(i)).display_name}\n"
                                    counter += 1
                                for i in raid.backup_tanks.keys():
                                    roster.append(i)
                                    total += f"{counter}: {ctx.guild.get_member(int(i)).display_name}\n"
                                    counter += 1
                                await ctx.send("Enter the number of who you want to remove.")
                                await ctx.send(total)
                                choice = await self.bot.wait_for("message", check=check, timeout=30.0)
                                choice = int(choice.content)
                                choice -= 1
                            except asyncio.TimeoutError:
                                await ctx.send(f"{ctx.author.mention}, remove has timed out")
                                return
                            else:
                                try:
                                    person = roster[choice]
                                    await ctx.send(
                                        f"Remove: {ctx.guild.get_member(int(person)).display_name} (y/n)?")
                                    confirm = await self.bot.wait_for('message', check=check, timeout=20.0)
                                    confirm = confirm.content.lower()
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, remove has timed out")
                                    return
                                else:
                                    if confirm == "y":
                                        worked = True
                                        found = False
                                        if person in raid.dps.keys() or person in raid.backup_dps.keys():
                                            raid.remove_dps(person)
                                            found = True
                                        if person in raid.healers.keys() or \
                                                person in raid.backup_healers.keys() and not found:
                                            raid.remove_healer(person)
                                            found = True
                                        if person in raid.tanks.keys() or \
                                                person in raid.backup_tanks.keys() and not found:
                                            raid.remove_tank(person)
                                        else:
                                            if not found:
                                                worked = False
                                                await ctx.send("Person not found.")
                                        if worked:
                                            await ctx.send(f"Removed "
                                                           f"{ctx.channel.guild.get_member(int(person)).display_name}")
                                            update_db(channel_id, raid)
                                        run = False
                                    else:
                                        if confirm == 'n':
                                            await ctx.send("Returning to menu.")
                                        else:
                                            await ctx.send("Invalid response, returning to menu.")
                        except KeyError:
                            await ctx.send("That is not a valid number, returning to menu.")
                    except ValueError:
                        await ctx.send("The input was not a valid number!")
        except Exception as e:
            logging.error(f"Remove error: {str(e)}")
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="add")
    @permissions.has_raid_lead()
    async def add_to_roster(self, ctx: commands.Context, p_type, member: discord.Member):
        """For Raid Leads: Manually add to roster | `!add [role] [@ the user]`"""
        try:
            channel_id = ctx.message.channel.id  # Get channel id, use it to grab trial, and add user into the trial
            raid = get_raid(channel_id)
            if raid is None:
                await ctx.send(f"Sorry! This command only works in a roster channel!")
                return

            def remove_for_add(member_id):
                if member_id in raid.dps.keys() or \
                        member_id in raid.backup_dps.keys():
                    raid.remove_dps(member_id)

                elif member_id in raid.healers.keys() or \
                        member_id in raid.backup_healers.keys():
                    raid.remove_healer(member_id)

                elif member_id in raid.tanks.keys() or \
                        member_id in raid.backup_tanks.keys():
                    raid.remove_tank(member_id)

            added_member_id = str(member.id)

            worked = False
            if p_type.lower() == "dps":
                remove_for_add(added_member_id)
                result = raid.add_dps(added_member_id, "")
                worked = True
            elif p_type.lower() == "healer":
                remove_for_add(added_member_id)
                result = raid.add_healer(added_member_id, "")
                worked = True
            elif p_type.lower() == "tank":
                remove_for_add(added_member_id)
                result = raid.add_tank(added_member_id, "")
                worked = True
            else:
                await ctx.send(f"Please specify a valid role. dps, healer, or tank.")
            if worked:  # If True
                update_db(channel_id, raid)
                await ctx.reply(f"{result}")
        except OSError as e:
            await ctx.send(f"Unable to get process information.")
            logging.error(f"Add To Roster Raid Get Error: {str(e)}")
        except Exception as e:
            await ctx.send("Something has gone wrong.")
            logging.error(f"Add To Roster Error: {str(e)}")

    @commands.command(name="leader")
    @permissions.has_raid_lead()
    async def leader(self, ctx: commands.Context):
        """For Raid Leads: Replaces the leader of a roster"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            while run:
                try:
                    total, channels = print_initial_menu(ctx)
                    await ctx.reply("Enter a number from the list below to select the roster")
                    await ctx.send(total)
                    #                        event = on_message without on_
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    # msg = discord.Message
                except asyncio.TimeoutError:
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.send(f"{ctx.author.mention}, remove has timed out")
                    return
                else:
                    # at this point the check has become True and the wait_for has done its work now we can do ours
                    try:
                        # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                        #   However, I already wrote it like this. Oh well.
                        choice = int(msg.content)
                        choice -= 1  # Need to lower it by one for the right number to get
                        if choice == -1:
                            await ctx.send("Exiting command")
                            return
                        try:
                            try:
                                channel_id = channels.get(choice)
                                raid = get_raid(channel_id)
                                if raid is None:
                                    await ctx.send(f"Unable to find roster information.")
                                    return

                            except Exception as e:
                                await ctx.send(f"Unable to get roster information.")
                                logging.error(f"Leader Replace Raid Get Error: {str(e)}")
                                return
                            try:
                                await ctx.send(f"Enter the new leader for {raid.raid}:")
                                confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                                leader = confirm.content
                            except asyncio.TimeoutError:
                                await ctx.send(f"{ctx.author.mention}, leader replace has timed out")
                                return
                            else:
                                try:
                                    old_leader = raid.leader
                                    raid.leader = leader
                                    update_db(channel_id, raid)
                                except Exception as e:
                                    await ctx.send("I was unable to update the roster information")
                                    logging.error(f"Leader Replace Error: {str(e)}")
                                    return
                                await ctx.send(f"Roster leader has been changed from {old_leader} to {leader}")
                                run = False
                        except KeyError:
                            await ctx.send("That is not a valid number, returning to menu.")
                    except ValueError:
                        await ctx.send("The input was not a valid number!")
        except Exception as e:
            logging.error(f"Leader change error: {str(e)}")
            await ctx.send("I was unable to complete the command")

    @commands.command(name="change")
    @permissions.has_raid_lead()
    async def change_raid(self, ctx: commands.Context):
        """For Raid Leads: Replaces the trial field"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            while run:
                try:
                    total, channels = print_initial_menu(ctx)
                    await ctx.reply("Enter a number from the list below to have the raid changed")
                    await ctx.send(total)
                    #                        event = on_message without on_
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    # msg = discord.Message
                except asyncio.TimeoutError:
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.send(f"{ctx.author.mention}, raid change has timed out")
                    return
                else:
                    # at this point the check has become True and the wait_for has done its work now we can do ours
                    try:
                        choice = int(msg.content)
                        choice -= 1  # Need to lower it by one for the right number to get
                        if choice == -1:
                            await ctx.send("Exiting command")
                            return
                        try:
                            channel_id = channels[choice]
                            try:
                                try:
                                    channel = ctx.guild.get_channel(channel_id)
                                    raid = get_raid(channel_id)
                                    if raid is None:
                                        await ctx.send(f"Unable to find roster information.")
                                        return

                                except Exception as e:
                                    await ctx.send(f"Unable to get roster information.")
                                    logging.error(f"Fill Raid Get Error: {str(e)}")
                                    return
                                await ctx.send("Enter the new Raid: ")
                                confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                                new_raid = confirm.content
                            except asyncio.TimeoutError:
                                await ctx.send(f"{ctx.author.mention}, change has timed out")
                                return
                            else:
                                old_raid = raid.raid
                                raid.raid = new_raid
                                try:
                                    update_db(channel_id, raid)
                                except Exception as e:
                                    await ctx.send("I was unable to save the updated roster.")
                                    logging.error(f"Raid Change Error saving new roster: {str(e)}")
                                    return
                                await ctx.send(f"Raid has been changed from {old_raid} to {new_raid}")
                                try:
                                    new_name = generate_channel_name(raid.date, raid.raid,
                                                                     self.bot.config["raids"]["timezone"])
                                    await channel.edit(name=new_name)
                                    run = False
                                except Exception as e:
                                    await ctx.send(
                                        "I was unable to update the Channel name. The roster is updated.")
                                    logging.error(f"Change Raid Error Channel Update: {str(e)}")
                                    return
                        except KeyError:
                            await ctx.send("That is not a valid number, returning to menu.")
                    except ValueError:
                        await ctx.send("The input was not a valid number!")
        except Exception as e:
            logging.error(f"Raid Change error: {str(e)}")
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="datetime", aliases=["date", "time"])
    @permissions.has_raid_lead()
    async def change_date_time(self, ctx: commands.Context):
        """For Raid Leads: Replaces the date of a raid"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            while run:
                try:
                    total, channels = print_initial_menu(ctx)
                    await ctx.reply("Enter a number from the list below to have the date/time changed")
                    await ctx.send(total)
                    #                        event = on_message without on_
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    # msg = discord.Message
                except asyncio.TimeoutError:
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.send(f"{ctx.author.mention}, datetime has timed out")
                    return
                else:
                    # at this point the check has become True and the wait_for has done its work now we can do ours
                    try:
                        choice = int(msg.content)
                        choice -= 1  # Need to lower it by one for the right number to get
                        if choice == -1:
                            await ctx.send("Exiting command")
                            return
                        try:
                            channel_id = channels[choice]
                            try:
                                try:
                                    channel = ctx.guild.get_channel(channel_id)
                                    raid = get_raid(channel_id)
                                    if raid is None:
                                        await ctx.send("Unable to find the raid information.")
                                        return

                                except Exception as e:
                                    await ctx.send(f"Unable to get roster information.")
                                    logging.error(f"Datetime Raid Get Error: {str(e)}")
                                    return
                                await ctx.send("Enter the new date/time: ")
                                confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                                new_date = confirm.content
                            except asyncio.TimeoutError:
                                await ctx.send(f"{ctx.author.mention}, datetime has timed out")
                                return
                            else:
                                formatted_date = format_date(new_date)
                                old_date = raid.date
                                raid.date = formatted_date
                                try:
                                    update_db(channel_id, raid)
                                except Exception as e:
                                    await ctx.send("I was unable to save the updated roster.")
                                    logging.error(f"Message Update Error saving new roster: {str(e)}")
                                    return
                                await ctx.send(f"Date/Time has been changed from {old_date} to {raid.date}")
                                try:
                                    new_name = generate_channel_name(raid.date, raid.raid,
                                                                     self.bot.config["raids"]["timezone"])
                                    await channel.edit(name=new_name)
                                    run = False
                                except Exception as e:
                                    await ctx.send(
                                        "I was unable to update the Channel name. The roster is updated.")
                                    logging.error(f"Change DateTime Error Channel Update: {str(e)}")
                                    return
                        except KeyError:
                            await ctx.send("That is not a valid number, returning to menu.")
                    except ValueError:
                        await ctx.send("The input was not a valid number!")
        except Exception as e:
            logging.error(f"DateTime Change error: {str(e)}")
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="close")
    @permissions.has_raid_lead()
    async def close_roster(self, ctx: commands.Context):
        """For Raid Leads: Closes out a roster"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            while run:
                total, channels = print_initial_menu(ctx)
                await ctx.reply("Enter a number from the list below to have the roster closed")
                await ctx.send(total)
                #                        event = on_message without on_
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                choice = int(msg.content)
                choice -= 1  # Need to lower it by one for the right number to get
                if choice == -1:
                    await ctx.send("Exiting command")
                    return
                channel_id = channels[choice]
                channel = ctx.guild.get_channel(channel_id)
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Unable to find roster information.")
                    return
                if channel is None:
                    await ctx.send(f"Delete Roster {raid.raid} - {str(channel_id)} (y/n)?")
                else:
                    await ctx.send(f"Delete Roster {raid.raid} - {channel.name} (y/n)?")
                confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                yesno = confirm.content.lower()
                if yesno == 'n':
                    await ctx.send(f"Exiting command")
                    return
                elif yesno != "y":
                    await ctx.send(f"Invalid input")
                    return

                await ctx.send(f"Increase everyone's Count (y/n)?")
                confirm = await self.bot.wait_for("message", check=check, timeout=15.0)
                confirm = confirm.content.lower()
                if confirm == 'y':
                    try:
                        update_runs(raid)
                    except OSError:
                        await ctx.send(
                            "I was unable to update the run count, Roster not closed.")
                        return
                elif confirm != 'n':
                    await ctx.send(f"Not y/n, exiting command.")
                    return

                to_delete = {"channelID": channel_id}
                raids.delete_one(to_delete)
                if channel is not None:
                    await channel.delete()
                    await ctx.send("Channel deleted, roster closed.")
                else:
                    await ctx.send("Roster closed")
                run = False

        except asyncio.TimeoutError:
            await ctx.send(f"{ctx.author.mention}, close has timed out")
            return
        except OSError:
            await ctx.send(f"I was unable to load the roster.")
        except ValueError:
            await ctx.send("The input was not a valid number!")
        except KeyError:
            await ctx.send("That is not a valid number, returning to menu.")
        except Exception as e:
            logging.error(f"Close error: {str(e)}")
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="rolenum")
    @permissions.has_raid_lead()
    async def change_role_nums(self, ctx: commands.Context):
        """For Raid Leads: Change role nums in a roster in dps, tank, healer format"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            while run:
                try:
                    total, channels = print_initial_menu(ctx)
                    await ctx.reply("Enter a number from the list below to have the role numbers changed")
                    await ctx.send(total)
                    #                        event = on_message without on_
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    # msg = discord.Message
                except asyncio.TimeoutError:
                    # at this point, the check didn't become True, let's handle it.
                    await ctx.send(f"{ctx.author.mention}, rolenum has timed out")
                    return
                else:
                    # at this point the check has become True and the wait_for has done its work now we can do ours
                    try:
                        choice = int(msg.content)
                        choice -= 1  # Need to lower it by one for the right number to get
                        if choice == -1:
                            await ctx.send("Exiting command")
                            return
                        try:
                            channel_id = channels[choice]
                            try:
                                try:
                                    raid = get_raid(channel_id)
                                    if raid is None:
                                        await ctx.send(f"Unable to find roster information.")
                                        return

                                except Exception as e:
                                    await ctx.send(f"Unable to get roster information.")
                                    logging.error(f"Rolenum Raid Get Error: {str(e)}")
                                    return
                                await ctx.send("Enter the new role nums in dps, tank, healer format: ")
                                confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                                new_nums = confirm.content
                            except asyncio.TimeoutError:
                                await ctx.send(f"{ctx.author.mention}, rolenum has timed out")
                                return
                            else:

                                # Change the number for each role here, if anyone is extra move from the back
                                #   to the backup roster.
                                nums = new_nums.split(",")

                                # update the numbers
                                old_dps = raid.dps_limit
                                raid.dps_limit = int(nums[0].strip())  # DPS comes first
                                old_tanks = raid.tank_limit
                                raid.tank_limit = int(nums[1].strip())
                                old_healers = raid.healer_limit
                                raid.healer_limit = int(nums[2].strip())

                                # TODO: Have it remove from overflow into backup.

                                try:
                                    update_db(channel_id, raid)
                                except Exception as e:
                                    await ctx.send("I was unable to save the updated roster.")
                                    logging.error(f"Role Nums Error saving new roster: {str(e)}")
                                    return
                                await ctx.send(f"Role Numbers have changed\n"
                                               f"DPS: {str(old_dps)} to {nums[0]}\n"
                                               f"Tanks: {str(old_tanks)} to {nums[1]}\n"
                                               f"Healers: {str(old_healers)} to {nums[2]}\n")
                                run = False
                        except KeyError:
                            await ctx.send("That is not a valid number, returning to menu.")
                    except ValueError:
                        await ctx.send("The input was not a valid number!")
        except Exception as e:
            logging.error(f"Rolenum Change error: {str(e)}")
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="runcount")
    @permissions.has_raid_lead()
    async def increase_run_count(self, ctx: commands.Context):
        """For Raid Leads: Increase rosters run count"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            run = True
            total, channels = print_initial_menu(ctx)
            while run:
                try:
                    await ctx.reply("Enter a number from the list below to have the runs increased")
                    await ctx.send(total)
                    #                        event = on_message without on_
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    choice = int(msg.content)
                    choice -= 1  # Need to lower it by one for the right number to get
                    if choice == -1:
                        await ctx.send("Exiting command")
                        return
                    channel_id = channels[choice]
                    channel = ctx.guild.get_channel(channel_id)
                    raid = get_raid(channel_id)
                    if raid is None:
                        await ctx.send(f"Unable to find roster information.")
                        return

                    if channel is None:
                        await ctx.send(f"Increase count for Roster {raid.raid} - {channel_id} (y/n)?")
                    else:
                        await ctx.send(f"Increase count for Roster {raid.raid} - {channel.name} (y/n)?")
                    confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                    yesno = confirm.content.lower()
                    if yesno == 'n':
                        await ctx.send(f"Exiting command")
                        return
                    confirmed = False
                    if channel is not None:
                        await ctx.send(f"Change Date too? (y/n)?")
                        confirm = await self.bot.wait_for("message", check=check, timeout=15.0)
                        confirm = confirm.content.lower()
                        if confirm == "y":
                            await ctx.send(f"Enter the new timestamp: ")
                            confirm = await self.bot.wait_for("message", check=check, timeout=30.0)
                            new_date = confirm.content
                            confirmed = True
                    try:
                        update_runs(raid)
                    except OSError:
                        await ctx.send("I was unable to update the run count, exiting command")
                        return
                    if confirmed is True:
                        try:
                            formatted_date = format_date(new_date)
                            old_date = raid.date
                            raid.date = formatted_date
                            update_db(channel_id, raid)
                        except Exception as e:
                            await ctx.send(
                                "I was unable to update the roster timestamp, count has been increased.")
                            logging.error(f"Run Count Update Roster Error: {str(e)}")
                            return
                        try:
                            new_name = generate_channel_name(raid.date, raid.raid,
                                                             self.bot.config["raids"]["timezone"])
                            await ctx.send(f"Date/Time has been changed from {old_date} to {raid.date}")
                            await channel.edit(name=new_name)
                        except Exception as e:
                            await ctx.send("I was unable to update the channel. The roster is updated.")
                            logging.error(f"Run Count Channel Update: {str(e)}")
                            return
                    run = False
                    await ctx.send(f"Runs have been updated")
                except ValueError:
                    await ctx.send("The input was not a valid number!")

                except KeyError:
                    await ctx.send("That is not a valid number!")

        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            await ctx.send(f"{ctx.author.mention} run count has timed out")
            return

        except Exception as e:
            logging.error(f"Run Count error: {str(e)}")
            await ctx.send("An error has occurred in the command.")
            return

    @commands.command(name="pin", aliases=["unpin"])
    @permissions.has_raid_lead()
    async def pin_message(self, ctx: commands.Context):
        """For Raid Leads: Allows pinning of a message"""
        try:
            ref = ctx.message.reference
            if ref is not None:
                # Is a reply - pin or unpin the reply message
                message = await ctx.fetch_message(ref.message_id)
                if message.pinned is True:
                    await message.unpin()
                    await ctx.reply(f"Message unpinned")
                    return
                else:
                    await message.pin()
                    return
            else:
                # Is not a reply - pin the command message
                await ctx.message.pin()
                return
        except Exception as e:
            await ctx.send("An unknown error has occurred with the command")
            logging.error(f"Pin Error: {str(e)}")

    @commands.command(name="memo")
    @permissions.has_raid_lead()
    async def create_modify_roster_memo(self, ctx: commands.Context):
        """For Raid Leads: Updates the memo for a roster"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            try:
                total, channels = print_initial_menu(ctx)
                await ctx.reply("Enter a number from the list below to modify the memo")
                await ctx.send(total)
            except OSError as e:
                await ctx.send(f"Unable to print menu")
                logging.error(f"Memo Error: {str(e)}")
                return

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                choice = int(msg.content)
                choice -= 1
                if choice == -1:
                    await ctx.send("Exiting command")
                    return
                channel_id = channels[choice]
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Unable to load roster information")
                    return
                await ctx.send(f"Enter the new memo. use `delete` to delete the memo.")
                msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                new_memo = msg.content
                if new_memo.lower() == "delete":
                    new_memo = "delete"
                raid.memo = new_memo
                update_db(channel_id, raid)
                await ctx.send(f"Memo updated.")
                return
            except KeyError:
                await ctx.send(f"Invalid value entered")
                return
            except ValueError:
                await ctx.send(f"Invalid value entered")
                return
            except asyncio.TimeoutError:
                await ctx.send(f"Memo has timed out")
            except OSError:
                await ctx.send("Unable to process DB changes.")
            except Exception as e:
                await ctx.send(f"Unable to complete command")
                logging.error(f"Memo error: {str(e)}")
        except Exception as e:
            await ctx.send("An unknown error has occurred with the command")
            logging.error(f"Memo Error: {str(e)}")

        # TODO: Think of adding a plaintext ` ` get of the memo

    @commands.command(name="limit")
    @permissions.has_raid_lead()
    async def modify_roster_limit(self, ctx: commands.Context):
        """For Raid Leads: Updates the role limit for a roster"""
        try:
            user = ctx.message.author

            def check(m: discord.Message):  # m = discord.Message.
                return user == m.author

            try:
                total, channels = print_initial_menu(ctx)
                await ctx.reply("Enter a number from the list below to modify the memo")
                await ctx.send(total)
            except OSError as e:
                await ctx.send(f"Unable to print menu")
                logging.error(f"Limit Error: {str(e)}")
                return
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                choice = int(msg.content)
                choice -= 1
                if choice == -1:
                    await ctx.send("Exiting command")
                    return
                channel_id = channels[choice]
                raid = get_raid(channel_id)
                if raid is None:
                    await ctx.send(f"Unable to load roster information")
                    return

                limits = f"Roles and Values:\n" \
                         f"0: Kyne's Founded\n" \
                         f"1: Kyne's Follower\n" \
                         f"2: Kyne's Hunters\n" \
                         f"3: Storm Chasers\n" \
                         f"4: Storm Riders"
                await ctx.send(f"{limits}\nEnter the new limit number")
                msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                new_limit_msg = int(msg.content)

                if new_limit_msg == 0:
                    new_limit = self.bot.config["raids"]["roles"]["base"]
                elif new_limit_msg == 1:
                    new_limit = self.bot.config["raids"]["roles"]["first"]
                elif new_limit_msg == 2:
                    new_limit = self.bot.config["raids"]["roles"]["second"]
                elif new_limit_msg == 3:
                    new_limit = self.bot.config["raids"]["roles"]["third"]
                elif new_limit_msg == 4:
                    new_limit = self.bot.config["raids"]["roles"]["fourth"]
                else:
                    await ctx.reply(f"Invalid input, enter a number between 0 and 4. Exiting.")
                    return

                raid.role_limit = new_limit
                update_db(channel_id, raid)
                await ctx.send(f"Limit updated to {new_limit}.")
                return
            except KeyError:
                await ctx.send(f"Invalid value entered")
                return
            except ValueError:
                await ctx.send(f"Invalid value entered")
                return
            except asyncio.TimeoutError:
                await ctx.send(f"Limit has timed out")
            except OSError:
                await ctx.send("Unable to process DB changes.")
            except Exception as e:
                await ctx.send(f"Unable to complete command")
                logging.error(f"Limit error: {str(e)}")
        except Exception as e:
            await ctx.send("An unknown error has occurred with the command")
            logging.error(f"Limit Error: {str(e)}")

    @commands.command(name="limits")
    @permissions.has_raid_lead()
    async def print_limits(self, ctx: commands.Context):
        """Prints a list of the role limits and their values for making a roster."""
        try:
            limits = f"Roles and Values:\n" \
                     f"0: Kyne's Founded\n" \
                     f"1: Kyne's Follower\n" \
                     f"2: Kyne's Hunters\n" \
                     f"3: Storm Chasers\n" \
                     f"4: Storm Riders"
            await ctx.send(f"{limits}")
        except Exception as e:
            await ctx.send(f"I was unable to print the limits")
            logging.error(f"Print Limits Error: {str(e)}")

    @commands.command(name="increase")
    @permissions.has_raid_lead()
    async def increase_raid_count(self, ctx: commands.Context, member: discord.Member = None):
        """Officer command to increase someone's ran count by 1"""
        try:
            if member is None:
                member = ctx.message.author
            counts = count.find_one({'userID': member.id})

            if counts is not None:
                counts["raidCount"] += 1
                try:
                    new_rec = {'$set': counts}
                    count.update_one({'userID': member.id}, new_rec)
                except Exception as e:
                    logging.error(f"Update Count Increase Error: {str(e)}")
                    await ctx.send("Unable to update the count")
                    return

                embed = discord.Embed(
                    title=member.display_name,
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Thank you for coming! Come again!")
                embed.set_author(name=f"Runs with {ctx.guild.name}")
                embed.add_field(name="Total Runs:", value=counts["raidCount"], inline=True)
                embed.add_field(name="Last Ran:", value=counts["lastRaid"], inline=True)
                embed.add_field(name="Last Date:", value=counts["lastDate"], inline=True)
                embed.add_field(name="Stats", value="Role Runs", inline=False)
                embed.add_field(name="DPS Runs:", value=counts["dpsRuns"], inline=True)
                embed.add_field(name="Tank Runs:", value=counts["tankRuns"], inline=True)
                embed.add_field(name="Healer Runs:", value=counts["healerRuns"], inline=True)
                await ctx.send(embed=embed)
            else:
                new_data = {
                    "userID": member.id,
                    "raidCount": 1,
                    "lastRaid": "none",
                    "lastDate": "<t:0:f>",
                    "dpsRuns": 0,
                    "tankRuns": 0,
                    "healerRuns": 0
                }
                try:
                    count.insert_one(new_data)
                except Exception as e:
                    logging.error(f"Update Count Increase Error: {str(e)}")
                    await ctx.send("Unable to update the count")
                    return
                embed = discord.Embed(
                    title=member.display_name,
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Thank you for coming! Come again!")
                embed.set_author(name=f"Runs with {ctx.guild.name}")
                embed.add_field(name="Total Runs:", value=1, inline=True)
                embed.add_field(name="Last Ran:", value="None", inline=True)
                embed.add_field(name="Last Date:", value="<t:0:f>", inline=True)
                embed.add_field(name="Stats", value="Role Runs", inline=False)
                embed.add_field(name="DPS Runs:", value="0", inline=True)
                embed.add_field(name="Tank Runs:", value="0", inline=True)
                embed.add_field(name="Healer Runs:", value="0", inline=True)
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("Unable to increase count")
            logging.error(f"Increase Count Error: {str(e)}")

    @commands.command(name="decrease")
    @permissions.has_raid_lead()
    async def decrease_raid_count(self, ctx: commands.Context, member: discord.Member = None):
        """Officer command to decrease someone's ran count by 1"""
        try:
            if member is None:
                member = ctx.message.author
            counts = count.find_one({'userID': member.id})
            if counts is not None:
                counts["raidCount"] -= 1
                if counts["raidCount"] < 0:
                    counts["raidCount"] = 1
                try:
                    new_rec = {'$set': counts}
                    count.update_one({'userID': member.id}, new_rec)
                except Exception as e:
                    logging.error(f"Update Count Decrease Error: {str(e)}")
                    await ctx.send("Unable to update the count")
                    return
                embed = discord.Embed(
                    title=member.display_name,
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Thank you for coming! Come again!")
                embed.set_author(name=f"Runs with {ctx.guild.name}")
                embed.add_field(name="Total Runs:", value=counts["raidCount"], inline=True)
                embed.add_field(name="Last Ran:", value=counts["lastRaid"], inline=True)
                embed.add_field(name="Last Date:", value=counts["lastDate"], inline=True)
                embed.add_field(name="Stats", value="Role Runs", inline=False)
                embed.add_field(name="Last Date:", value=counts["dpsRuns"], inline=True)
                embed.add_field(name="Last Date:", value=counts["tankRuns"], inline=True)
                embed.add_field(name="Last Date:", value=counts["healerRuns"], inline=True)
                await ctx.send(embed=embed)
            else:
                new_data = {
                    "userID": member.id,
                    "raidCount": 1,
                    "lastRaid": "none",
                    "lastDate": "<t:0:f>",
                    "dpsRuns": 0,
                    "tankRuns": 0,
                    "healerRuns": 0
                }
                try:
                    count.insert_one(new_data)
                except Exception as e:
                    logging.error(f"Update Count Decrease Error: {str(e)}")
                    await ctx.send("Unable to update the count")
                    return
                embed = discord.Embed(
                    title=member.display_name,
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Thank you for coming! Come again!")
                embed.set_author(name=f"Runs with {ctx.guild.name}")
                embed.add_field(name="Total Runs:", value=1, inline=True)
                embed.add_field(name="Last Ran:", value="None", inline=True)
                embed.add_field(name="Last Date:", value="<t:0:f>", inline=True)
                embed.add_field(name="Stats", value="Role Runs", inline=False)
                embed.add_field(name="DPS Runs:", value="0", inline=True)
                embed.add_field(name="Tank Runs:", value="0", inline=True)
                embed.add_field(name="Healer Runs:", value="0", inline=True)
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("Unable to decrease count")
            logging.error(f"Decrease Count Error: {str(e)}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Raids(bot))
