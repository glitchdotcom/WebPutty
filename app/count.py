from datetime import datetime
from livecount import counter
from livecount.counter import PeriodType

def count_view(name, period=None, period_types=None, namespace='default', delta=1, batch_size=223):
    if period is None:
        period = datetime.now()
    if period_types is None:
        period_types = [PeriodType.HOUR, PeriodType.DAY, PeriodType.WEEK, PeriodType.MONTH]
    counter.load_and_increment_counter(name, period=period, period_types=period_types, namespace=namespace, delta=delta, batch_size=batch_size)
    
def get_period_and_count(name, period_type, period):
    period = PeriodType.find_scope(period_type, period)
    count = counter.load_and_get_count(name, period_type=period_type, period=period)
    return period, count

