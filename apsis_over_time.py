from calendar import monthrange

import astropy.units as u
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests_cache
import seaborn as sns
from bs4 import BeautifulSoup
from matplotlib.dates import DateFormatter
from pandas.plotting import register_matplotlib_converters

from tletools import TLE

register_matplotlib_converters()
sns.set(font_scale=1.5, style="whitegrid")


def main(filename="zarya.txt"):
    '''
    mean height (average of apogee and perigee) over time
    from historic element sets provided by CFSCC via space-track.
    API call: https://www.space-track.org/basicspacedata/query/class/gp_history/NORAD_CAT_ID/25544/orderby/TLE_LINE1%20ASC/EPOCH/2021-01-01--2022-03-04/format/3le
    '''
    text_file = open(filename, "r")
    lines = text_file.readlines()
    text_file.close()

    # group list of TLES (three element)
    n = 3
    history = [lines[i:i + n] for i in range(0, len(lines), n)]
    rows = []
    prev_mean_height = 0
    for tlelines in history:
        tle = TLE.from_lines(*tlelines)
        s = tle.to_orbit()
        apogee = float(s.r_a.to_value(u.km))
        perigee = float(s.r_p.to_value(u.km))
        mean_height = round((apogee + perigee) / 2, 3)
        # if mean_height != prev_mean_height:
        rows.append({'datetime': str(tle.epoch), 'h': mean_height})
        delta = mean_height - prev_mean_height
        # output sudden changes for correlation with NOAA SWPC for solar activty and NASA Station reports for reboosts
        if delta < -.25:
            print(f"-{delta:.2f} {prev_mean_height:.1f} {mean_height:.1f} {delta:.1f} {tle.epoch}")
        if delta > .5:
            print(f"+{delta:.2f} {prev_mean_height:.1f} {mean_height:.1f} {delta:.1f} {tle.epoch}")
        prev_mean_height = mean_height

    df = pd.DataFrame.from_records(rows)
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S.%f')
    df.set_index(['datetime'], inplace=True)

    # plot it
    fig, ax = plt.subplots(figsize=(16, 9))
    plt.grid(b=None)
    ax.plot(df.index.values, df['h'], linewidth=3, color='purple')
    ax.set(xlabel="Date",
           ylabel="height (km)",
           title="International Space Station altitude")
    date_form = DateFormatter("%b")
    ax.xaxis.set_major_formatter(date_form)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.show()


def stationreports():
    '''
    fetch and parse NASA Blogs ISS Station Reports for mentions of reboost events
    '''
    s = requests_cache.CachedSession('nasa_blog_cache.sqlite')
    for year in range(2018, 2023):
        for month in range(1, 13):
            if year >= 2022 and month > 3:
                continue
            daysinmonth = monthrange(year, month)[1]
            for day in range(1, daysinmonth + 1):
                url = f"https://blogs.nasa.gov/stationreport/{year}/{month:02d}/{(daysinmonth - day):02d}"
                r = s.get(url)
                if 'Reboost' in r.text:
                    soup = BeautifulSoup(r.text, "html.parser")
                    h1 = soup.find('h1')
                    ps = soup.find_all('p')
                    for p in ps:
                        if 'boost' in p.text:
                            print(h1.text, p.text)

                if r.status_code >= 300:
                    continue


if __name__ == '__main__':
    main()
    stationreports()
