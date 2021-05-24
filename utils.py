import time
import datetime
from typing import Tuple

def gen_expiry_timestamp_and_str(days) -> Tuple[int, str]:
    today = datetime.date.today()
    days_later = today + datetime.timedelta(days=days)
    days_later_ending_milisecond = (int(time.mktime(time.strptime(str(days_later), '%Y-%m-%d'))) * 1000 - 1)
    days_later_date_str = days_later.strftime('%m_%d_%Y')
    return days_later_ending_milisecond, days_later_date_str