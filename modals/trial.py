from models.roster import Roster
from discord.ui import Modal, TextInput
from discord import Interaction, TextStyle, Embed, Color
from discord.utils import get
from aws import Dynamo
from services import Utilities, RosterExtended, Librarian, EmbedFactory
import logging


logging.basicConfig(
    level=logging.INFO, format='%(asctime)s: %(message)s',
    handlers=[
        logging.FileHandler('log.log', mode='a'),
        logging.StreamHandler()
    ])  # , datefmt="%Y-%m-%d %H:%M:%S")


class TrialModal(Modal):
    def __init__(self, roster: Roster, interaction: Interaction, bot, lang, roster_map, channel=None ):
        self.language = bot.language[lang]['replies']
        self.ui_language = bot.language[lang]["ui"]
        self.config = bot.config
        self.leader_trial_val = None
        self.date_val = None
        self.limit_val = None
        self.role_nums_val = "8,2,2"
        self.memo_val = "None"
        self.new_roster = True
        self.new_name = f""
        self.user_language = lang
        self.roster_map = roster_map
        self.bot = bot
        self.channel = None
        self.change_name = True
        self.sort_channels = True
        self.roster = None
        if roster is not None:
            self.channel_id = channel
            self.new_roster = False
            self.roster = roster
            self.leader_trial_val = f"{roster.leader},{roster.trial}"
            self.date_val = f"{roster.date}"
            self.limit_val = f"{roster.role_limit}"
            self.role_nums_val = f"{roster.dps_limit},{roster.healer_limit},{roster.tank_limit}"
            self.memo_val = f"{roster.memo}"
        super().__init__(title=self.ui_language['TrialModify']['Title'])
        self.initialize()

    def initialize(self):
        # Add all the items here based on what is above
        self.leader_trial =  TextInput(
            label=self.ui_language["TrialModify"]["LeaderTrial"]["Label"],
            placeholder=self.ui_language["TrialModify"]["LeaderTrial"]["Placeholder"],
            default = self.leader_trial_val,
            required=True
        )
        self.date = TextInput(
            label=self.ui_language["TrialModify"]["Date"]["Label"],
            placeholder=self.ui_language["TrialModify"]["Date"]["Placeholder"],
            default = self.date_val,
            required=True
        )
        self.limit = TextInput(
            label=self.ui_language["TrialModify"]["Limit"]["Label"],
            placeholder=self.ui_language["TrialModify"]["Limit"]["Placeholder"],
            default=self.limit_val,
            required=True,
        )
        self.role_nums = TextInput(
            label=self.ui_language["TrialModify"]["RoleNums"]["Label"],
            default=self.role_nums_val,
            required=True
        )
        self.memo = TextInput(
            label=self.ui_language["TrialModify"]["Memo"]["Label"],
            default=self.memo_val,
            placeholder=self.ui_language["TrialModify"]["Memo"]["Placeholder"],
            style=TextStyle.long,
            required=True
        )
        self.add_item(self.leader_trial)
        self.add_item(self.date)
        self.add_item(self.limit)
        self.add_item(self.role_nums)
        self.add_item(self.memo)

    async def on_submit(self, interaction: Interaction):
        # Split the values:
        try:
            roles = RosterExtended.get_limits(table_config=self.config['Dynamo']['ProgDB'],
                                              roles_config=self.config['raids']['ranks'],
                                              creds_config=self.config['AWS'])

            role_limit = int(self.limit.value)
            if role_limit < 0 or role_limit > len(roles):
                await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['BadLimit'] % len(roles))}")
                return
        except (NameError, ValueError) as e:
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['InvalidLimit'] % self.limit.value)}")
            return
        try:
            leader, trial = self.leader_trial.value.split(",")
        except (NameError, ValueError):
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['BadLeaderTrial'] % self.leader_trial.value)}")
            return
        try:
            dps_limit, healer_limit, tank_limit = self.role_nums.value.split(",")
        except (NameError, ValueError):
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['BadRoleNums'] % self.role_nums.value)}")
            return
        try:
            dps_limit = int(dps_limit.strip())
        except ValueError:
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['InvalidDPS'] % dps_limit)}`")
            return
        try:
            healer_limit = int(healer_limit.strip())
        except ValueError:
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['InvalidHealers'] % healer_limit)}`")
            return
        try:
            tank_limit = int(tank_limit.strip())
        except ValueError:
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['InvalidTanks'] % tank_limit)}")
            return

        try:
            formatted_date = RosterExtended.format_date(self.date.value)
            category = interaction.guild.get_channel(self.config["raids"]["category"])

            if self.new_roster is False:
                old_date = self.roster.date
                old_trial = self.roster.trial
                # Update all values then update the DB
                self.roster.trial = trial
                self.roster.leader = leader
                self.roster.dps_limit = dps_limit
                self.roster.healer_limit = healer_limit
                self.roster.tank_limit = tank_limit
                self.roster.date = formatted_date
                self.roster.memo = self.memo.value
                self.roster.role_limit = role_limit

                self.channel = interaction.guild.get_channel(int(self.channel_id))

                try:
                    if not RosterExtended.did_day_change(old_date, self.roster.date, self.config["raids"]["timezone"]):
                        print("Day did not change")
                        self.sort_channels = False

                    if not RosterExtended.did_trial_change(old_trial, self.roster.trial):
                        print("name did not change")
                        self.change_name = False

                    if self.sort_channels or self.change_name:
                        self.new_name = RosterExtended.generate_channel_name(formatted_date, trial, self.config['raids']['timezone'])
                        await self.channel.edit(name=self.new_name)

                except ValueError as e:
                    await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['NewNameErr'])}")
                    logging.info(f"New Name Value Error Existing Roster: {e}")
                    return

            elif self.new_roster is True:
                try:
                    self.roster = RosterExtended.factory(leader, trial, formatted_date, dps_limit, healer_limit, tank_limit, role_limit, self.memo.value, self.config)

                    logging.info(f"Creating new channel.")
                    try:
                        self.new_name = RosterExtended.generate_channel_name(self.roster.date, self.roster.trial, self.config["raids"]["timezone"])
                    except ValueError as e:
                        await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['NewNameErr'])}")
                        logging.info(f"New Name Value Error New Roster: {e}")
                        return
                    try:
                        self.channel = await category.create_text_channel(self.new_name)
                    except Exception as e:
                        await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['CantCreate'])}")
                        logging.error(f"Unable To Create New Roster Channel: {str(e)}")
                        return
                    roles_req = ""
                    if isinstance(roles[role_limit], list):
                        # Need to work with 3 roles to check, dps | tank | healer order

                        limiter_dps = get(interaction.guild.roles, name=roles[role_limit][0])
                        limiter_tank = get(interaction.guild.roles, name=roles[role_limit][1])
                        limiter_healer = get(interaction.guild.roles, name=roles[role_limit][2])

                        roles_req += f"{limiter_dps.mention} {limiter_tank.mention} {limiter_healer.mention}"

                    else:
                        limiter = get(interaction.guild.roles, name=roles[role_limit])
                        roles_req += f"{limiter.mention}"

                        embed = EmbedFactory.create_new_roster(trial=self.roster.trial, date=self.roster.date,
                                                               roles_req=roles_req, leader=self.roster.leader, memo=self.roster.memo)
                        await self.channel.send(embed=embed)

                    logging.info(f"Roster Channel: channelID: {str(self.channel.id)}")
                    self.channel_id = self.channel.id
                except Exception as e:
                    await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['CantEmbed'])}")
                    logging.error(f"Raid Creation Channel And Embed Error: {str(e)}")
                    return
            else:
                await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['Unreachable'])}")
                return
        except Exception as e:
            logging.error(f"Trial/Modify Error During Channel Create and Embed: {str(e)}")
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['Unreachable'])}")
            return
        try:
            # Save Roster
            logging.info(f"Saving Roster channelID: {str(self.channel.id)}")
            Librarian.put_roster(channel_id=self.channel_id, data=self.roster.get_roster_data(),
                                 table_config=self.config['Dynamo']["RosterDB"], credentials=self.config["AWS"])
            logging.info(f"Saved Roster channelID: {str(self.channel.id)}")

            if len(self.new_name) != 0:
                # Save Roster Mapping
                logging.info(f"Updating Roster Map")
                self.roster_map[str(self.channel.id)] = self.new_name
                Librarian.put_roster_map(data=self.roster_map,
                                         table_config=self.config['Dynamo']["MapDB"], credentials=self.config["AWS"])
                self.bot.dispatch("reload_roster_map", self.roster_map)
                logging.info(f"Updated Roster Map")

        except Exception as e:
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['DBSaveError'])}")
            logging.error(f"Roster Save DynamoDB Error: {str(e)}")
            return

        if self.sort_channels:
            try:
                # Put new channel into the right position
                position = RosterExtended.get_channel_position(self.roster, self.config["raids"]["timezone"])
                self.channel.position = position
                await self.channel.edit(position=self.channel.position)
            except Exception as e:
                logging.error(f"Position Change Error: {str(e)}")
                await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['TrialModify']['CantPosition'])}")
                return

        if self.new_roster:
            await interaction.response.send_message(f"{self.language['TrialModify']['NewRosterCreated'] % self.new_name}")
        elif not self.new_roster:
            await interaction.response.send_message(f"{self.language['TrialModify']['ExistingUpdated'] % self.new_name}")

        self.bot.dispatch("update_rosters_data",self.channel_id, self.roster)
        return
    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['Incomplete'])}")
        logging.error(f"Trial Creation/Modify Error: {str(error)}")
        return
