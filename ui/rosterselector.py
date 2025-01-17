from discord import ui, SelectOption, Interaction
from services import Utilities, Librarian
from modals import *


class RosterSelect(ui.Select):
    def __init__(self, interaction: Interaction, cmd_called, bot, user_language, roster_map, leader=None):
        self.channels = {}
        self.config = bot.config
        self.cmd_called = cmd_called
        self.roster_map = roster_map
        self.language = bot.language[user_language]['replies']
        self.ui_language = bot.language[user_language]['ui']
        self.user_language = user_language
        self.bot = bot
        self.channel_mapper = {}
        self.leader = leader

        options = []
        if roster_map is None or len(roster_map) == 0:
            options.append(SelectOption(label='N/A'))
        else:
            used = []
            for key in roster_map:
                label = self.roster_map[key].strip()
                if label == '':
                    label = key
                if label in used:
                    found = True
                    count = 1
                    while found:
                        new_label = f"{label}{count}".strip()
                        if new_label not in used:
                            label = new_label
                            self.channel_mapper[label] = key
                            found = False
                            break
                        count += 1
                options.append(SelectOption(label=label))
                self.channel_mapper[label] = key
                used.append(label)

        # discord.SelectOption(label="Option 1",emoji="👌",description="This is option 1!"),
        super().__init__(placeholder=self.ui_language['SelectRoster']['Placeholder'],max_values=1,min_values=1,options=options)

    def update_options_timeout(self):
        # Remove all options and set the placeholder to "Timed out"
        self.options = []
        self.placeholder = "Timed out"

    async def callback(self, interaction: Interaction):
        selected = self.values[0]

        if selected == 'N/A':
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['SelectRoster']['NoOptionsError'])}")
            return

        if self.roster_map is None:
            await interaction.response.send_message(f"{Utilities.format_error(self.user_language, self.language['SelectRoster']['NoMapError'])}")
            return

        # Fetch Key from value for channel ID
        channel_id = self.channel_mapper[selected]

        roster = Librarian.get_roster(channel_id=str(channel_id),
                                      table_config=self.config['Dynamo']["RosterDB"], credentials=self.config["AWS"])

        if self.cmd_called == "modify":
            await interaction.response.send_modal(TrialModal(roster=roster, interaction=interaction, bot=self.bot, lang=self.user_language,
                                                             roster_map=self.roster_map, channel=channel_id))
        elif self.cmd_called == "call":
            await interaction.response.send_modal(CallModal(roster, interaction, self.bot, self.user_language, channel_id))
        elif self.cmd_called == "close":
            await interaction.response.send_modal(CloseModal(roster=roster, interaction=interaction, bot=self.bot,
                                                             lang=self.user_language, roster_map=self.roster_map,
                                                             channel_id=channel_id, leader=self.leader))
        elif self.cmd_called == "remove":
            await interaction.response.send_modal(RemoveModal(roster, interaction, self.bot, self.user_language, channel_id))
        elif self.cmd_called == "run_count":
            await interaction.response.send_modal(RunCountModal(roster, interaction, self.bot, self.user_language, channel_id))
        elif self.cmd_called == "fill":
            await interaction.response.send_modal(FillModal(roster, interaction, self.bot, self.user_language, channel_id))


class RosterSelector(ui.View):
    def __init__(self, interaction: Interaction, bot, caller, cmd_called, user_language, roster_map, leader=None, *, timeout = 30):
        super().__init__(timeout=timeout)
        self.caller = caller
        self.bot = bot
        self.interaction = interaction
        self.roster_map = roster_map
        self.language = bot.language[user_language]
        self.user_language = user_language
        self.new_roster_select = RosterSelect(interaction, cmd_called, bot, user_language, roster_map)
        self.add_item(self.new_roster_select)
        self.leader = leader

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.caller.id:
            await interaction.response.send_message(f"{self.language['SelectRoster']['NotCaller']}", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        self.new_roster_select.update_options_timeout()
        self.clear_items()
        self.stop()
