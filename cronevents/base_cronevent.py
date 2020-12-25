class BaseCronEvent:

    def __init__(self, year='*', month='*', day='*', week='*', day_of_week='*', hour='*', minute='*', second=0):
        self.year = year
        self.month = month
        self.day = day
        self.week = week
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute
        self.second = second

    async def run(self, client):
        raise NotImplementedError
