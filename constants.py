class Constants:
    def __init__(self):
        self.prefix:str = ";"
        self.guild_id:int = 932736074139185292
        self.log_channel_id:int = 975002976513060866

        self.command_exts:list[str] = [
            "extensions.eventRaffle",
            "extensions.restricted",
            "extensions.settings"
        ]

        self.slash_guild_ids:list[int] = [self.guild_id, 734890828698353704]

        self.DEBUG:bool = False

const = Constants()
