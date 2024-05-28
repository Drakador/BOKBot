from services import Utilities
from re import sub
from aws import Dynamo
import logging
from models import Roster

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s: %(message)s',
    handlers=[
        logging.FileHandler('log.log', mode='a'),
        logging.StreamHandler()
    ])  # , datefmt="%Y-%m-%d %H:%M:%S")

class RosterExtended:
    """Class of static methods for trial operations."""

    @staticmethod
    def factory(fact_leader, fact_raid, fact_date, fact_dps_limit, fact_healer_limit, fact_tank_limit,
            fact_role_limit, fact_memo, config):
        if fact_dps_limit is None and fact_healer_limit is None and fact_tank_limit is None:
            fact_dps_limit = config["raids"]["roster_defaults"]["dps"]
            fact_healer_limit = config["raids"]["roster_defaults"]["healers"]
            fact_tank_limit = config["raids"]["roster_defaults"]["tanks"]
        dps, healers, tanks, backup_dps, backup_healers, backup_tanks = {}, {}, {}, {}, {}, {}
        return Roster(fact_raid, fact_date, fact_leader, dps, healers, tanks, backup_dps, backup_healers,
                    backup_tanks, fact_dps_limit, fact_healer_limit, fact_tank_limit, fact_role_limit,
                    fact_memo)

    @staticmethod
    def get_sort_key(current_channels, config):
        try:
            current_raid = get_raid(current_channels.id)
            new_position = 0
            if current_raid is None:
                return current_channels.position  # Keep the channel's position unchanged
            elif current_raid.date == "ASAP":
                return 100
            else:
                # Calculate new positioning
                new_time = datetime.datetime.utcfromtimestamp(int(sub('[^0-9]', '', current_raid.date)))
                tz = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(
                    tz=timezone(config["raids"]["timezone"]))
                day = tz.day
                if day < 10:
                    day = int(f"0{str(day)}")
                weight = int(f"{str(tz.month)}{str(day)}{str(tz.year)}")
            return weight
        except Exception as e:
            logging.error(f"Sort Key Error: {str(e)}")
            raise Exception(e)

    @staticmethod
    def generate_channel_name(date, raid_name, tz_info):
        """Function to generate channel names on changed information"""
        date = date.strip()
        if date.upper() == "ASAP":
            new_name = f"{raid_name}-ASAP"
            return new_name

        new_time = datetime.datetime.utcfromtimestamp(int(sub('[^0-9]', '', date)))
        tz = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(
            tz=timezone(tz_info))
        weekday = tz.strftime("%a")
        day = tz.day
        new_name = f"{raid_name}-{weekday}-{str(day)}{Utilities.suffix(day)}"
        return new_name

    @staticmethod
    def format_date(date):
        """Formats the timestamp date to the correct version"""
        date = date.strip()
        if date.upper() == "ASAP":
            return date.upper()

        formatted_date = f"<t:{sub('[^0-9]', '', date)}:f>"
        return formatted_date

    @staticmethod
    def get_limits(table_config, roles_config, creds_config):
        """Create list of roles with nested lists for 1-3 indexes"""

        from services import Librarian

        list_roles = [
            roles_config['base'],
            [
                roles_config['first']['dps'], roles_config['first']['tank'], roles_config['first']['healer']
            ],
            [
                roles_config['second']['dps'], roles_config['second']['tank'], roles_config['second']['healer']
            ],
            [
                roles_config['third']['dps'], roles_config['third']['tank'], roles_config['third']['healer']
            ]
        ]

        prog_roles = Librarian.get_progs(table_config, creds_config)

        if prog_roles is not None and prog_roles[0] != "None":
            for i in prog_roles:
                list_roles.append(i)
        return list_roles