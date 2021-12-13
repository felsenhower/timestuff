#!/usr/bin/env python3


"""
This Python script creates an overview of working times using LaTeX from
CSV files that are exported from Clockify.
"""


import argparse
from calendar import monthrange
import datetime
import subprocess
from typing import Tuple, List, Dict, Optional
import pandas as pd


def is_weekend(date: datetime.date) -> bool:
    """
    Determines if a date is a weekend.
    Args:
        date: datetime.date. The date to analyze.
    Returns:
        bool. True if the given date is a weekend (Saturday or Sunday).
    """
    return date.weekday() in (5, 6)


def add_duration_on_time(time: datetime.time,
                         duration: datetime.timedelta) -> datetime.time:
    """
    Adds a duration on a time.
    Args:
        time: datetime.time. The time to add to.
        duration: datetime.timedelta. The duration to add.
    Returns:
        datetime.time. The sum of time and duration.
    """
    dummy_date = datetime.date(1, 1, 1)
    return (datetime.datetime.combine(dummy_date, time) + duration).time()


def time_to_duration(time: datetime.time) -> datetime.timedelta:
    """
    Converts a time to a duration after midnight.
    Args:
        time: datetime.time. The time to convert.
    Returns:
        datetime.timedelta. The duration after midnight that time
        corresponds to.
    """
    return datetime.timedelta(seconds=time.second,
                              minutes=time.minute,
                              hours=time.hour)


def is_date_in_range(date: datetime.date, date_range:
                     Tuple[datetime.date, datetime.date]) -> bool:
    """
    Determines whether a date is in a date range.
    Args:
        date: datetime.date. The date to check.
        range: Tuple[datetime.date,datetime.date]. The two dates which
               represent the range to check.
    Returns:
        bool. True, if the date is in the range.
    """
    return date_range[0] <= date <= date_range[1]


def round_duration_to_quarter_hour(duration: datetime.timedelta) -> \
                                   datetime.timedelta:
    """
    Rounds a duration to multiples of 15 minutes.
    Args:
        duration: datetime.timedelta. The duration to round.
    Returns:
        datetime.timedelta. The rounded duration.
    """
    quarter_hours = round(duration.total_seconds() / (60 * 15))
    return datetime.timedelta(minutes=(quarter_hours * 15))


def round_time_to_quarter_hour(time: datetime.time) -> datetime.time:
    """
    Rounds a time to the closest multiple of 15 minutes after midnight.
    Args:
        time: datetime.time. The time to round.
    Returns:
        datetime.time. The rounded time.
    """
    midnight = datetime.time(0, 0, 0)
    duration_after_midnight = time_to_duration(time)
    duration_after_midnight = round_duration_to_quarter_hour(
        duration_after_midnight
    )
    return add_duration_on_time(midnight, duration_after_midnight)


def print_duration(duration: datetime.timedelta) -> str:
    """
    Gets the preferred string representation of durations.
    Args:
        duration: datetime.timedelta. The duration to print.
    Returns:
        str. The string representation.
    """
    return "{:0.2f}".format(duration.total_seconds() / 3600)


def print_time(time: datetime.time) -> str:
    """
    Gets the preferred string representation of times.
    Args:
        time: datetime.time. The time to print.
    Returns:
        str. The string representation.
    """
    return time.strftime("%H:%M")


def print_date(date: datetime.date) -> str:
    """
    Gets the preferred string representation of dates.
    Args:
        date: datetime.date. The date to print.
    Returns:
        str. The string representation.
    """
    return date.strftime("%d.%m.%Y")


def is_during_vacations(date: datetime.date,
                        vacations: List[Tuple[datetime.date,
                                              datetime.date,
                                              datetime.timedelta]]) -> \
                        Optional[Tuple[datetime.date,
                                       datetime.date,
                                       datetime.timedelta]]:
    """
    Determines if a the given date is during the given vacations.
    Args:
        date: datetime.date. The date to check.3
        vacations: List[Tuple[datetime.date,datetime.date,datetime.timedelta]].
                   A list of tuples which contain a start date, end date of a
                   vacation period and a duration of paid time per work day.
    Returns:
        Optional[Tuple[datetime.date,datetime.date,datetime.timedelta]].
        If the date is in one of the given vacation period, the vacation period
        is returned. Otherwise, None.
    """
    for vacation in vacations:
        if is_date_in_range(date, vacation[:2]):
            return vacation
    return None


def get_work_times(df: pd.DataFrame,
                   date_range: Optional[Tuple[datetime.date,
                                              datetime.date]]) -> \
                   Dict[datetime.date, Tuple[datetime.time,
                                             datetime.timedelta]]:
    """
    Extracts a Dict of working times from the given dataframe. If multiple
    working periods occured during one working day, the start time of the first
    is used and the duration of all is summed.
    Args:
        df: pd.DataFrame. The dataframe to analyze, which can simply be created
            by using pd.read_csv on a CSV file exported by Clockify.
        date_range: Optional[Tuple[datetime.date,datetime.date])]. The date
                    range to consider. This is simply used to filter out dates
                    that are not of interest and may be None.
    Returns:
        Dict[datetime.date,Tuple[datetime.time, datetime.timedelta]]. A Dict
        that maps dates of workdates to Tuples which contain the corresponding
        starting time and working duration.
    """
    df = df[["Start Date", "Start Time", "Duration (h)"]]
    work_times = dict()
    for _, row in df.iterrows():
        start_date = datetime.datetime.strptime(
            row["Start Date"], "%m/%d/%Y"
        ).date()
        if date_range is not None and not is_date_in_range(start_date,
                                                           date_range):
            continue
        start_time = datetime.datetime.strptime(
            row["Start Time"], "%H:%M:%S"
        ).time()
        duration = time_to_duration(datetime.datetime.strptime(
            row["Duration (h)"], "%H:%M:%S"
        ).time())
        if start_date not in work_times:
            work_times[start_date] = (start_time, duration)
        else:
            work_times[start_date] = (start_time,
                                      work_times[start_date][1] + duration)
    return work_times


def get_table_content(work_times: Dict[datetime.date,
                                       Tuple[datetime.time,
                                             datetime.timedelta]],
                      selected_year: int,
                      month: int,
                      vacations: List[Tuple[datetime.date, datetime.date,
                                            datetime.timedelta]]) -> str:
    """
    Acquires the table content for the LaTeX template.
    Args:
        work_times: Dict[datetime.date,Tuple[datetime.time,
                    datetime.timedelta]]. The work times as acquired from
                    get_work_times.
        selected_year: int. The year to use.
        month: The month to use.
        vacations: List[Tuple[datetime.date,datetime.date,datetime.timedelta]].
                   The vacations as a list of tuples that contain start date,
                   end date, and paid worktime per day.
        Returns:
            str. The table content as LaTeX.
    """
    _, number_of_days = monthrange(selected_year, month)
    table_content = ""
    for j in range(number_of_days):
        day = j + 1
        date = datetime.date(selected_year, month, day)
        if is_weekend(date):
            table_content += "\\weekend%\n"
        if date in work_times:
            if ((vacation := is_during_vacations(
                    date, vacations)) is not None):
                msg = (
                    "Found work time on day {} which is during" +
                    "vacations ({}–{})!"
                ).format(
                    print_date(date),
                    print_date(vacation[0]),
                    print_date(vacation[1])
                )
                raise RuntimeError(msg)
            start_time, duration = work_times[date]
            start_time = round_time_to_quarter_hour(start_time)
            duration = round_duration_to_quarter_hour(duration)
            end_time = add_duration_on_time(start_time, duration)
            pause_duration = datetime.time(0, 0, 0)
            table_content += (
                "{} & {} & {} & {} & {} & \\\\" +
                "\\hline \n"
            ).format(
                day,
                print_time(start_time),
                print_time(end_time),
                print_time(pause_duration),
                print_duration(duration)
            )
        elif (vacation := is_during_vacations(
            date, vacations)
        ) and not is_weekend(date):
            table_content += "{} & \\vacation{{{}}} \\\\ \\hline \n".format(
                day,
                print_duration(vacation[2])
            )
        else:
            table_content += "{} & & & & \\nosum{{}} & \\\\ \\hline \n".format(day)
    return table_content


def fill_template(template: str, table_content: str,
                  issue_date: datetime.date) -> str:
    """
    Fills the LaTeX template with the given table content and issue date.
    Args:
        template: str. The LaTeX template.
        table_content: str. The table content as acquired via
                       get_table_content.
        issue_date: datetime.date. The issue date of the sheet.
    Returns:
        str. The populated document as LaTeX.
    """
    output_tex = template
    output_tex = output_tex.replace("%placeholder_1%", print_date(issue_date))
    output_tex = output_tex.replace("%placeholder_2%", table_content)
    return output_tex


def run_command(command: List[str]) -> None:
    """
    Runs a command and echos this to the console.
    Args:
        command: List[str]. A command string as a list of strings, where the
                 first entry is the program and the remaining entries are the
                 parameters.
    """
    print("Running \"{}\"".format(" ".join(command)))
    subprocess.check_output(command)


def latexmk_available() -> bool:
    """
    Checks if latexmk is installed.
    Returns:
        True, if latexmk is installed. False otherwise.
    """
    return (subprocess.run(["which", "latexmk"],
                           capture_output=True,
                           check=True).returncode == 0)


def valid_date(s: str) -> datetime.date:
    """
    Checks if the given string contains a valid date in YYYY-MM-DD format.
    Args:
        s: str. The string to check.
    Returns:
        The parsed date.
    """
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        msg = "not a valid date: {0!r}".format(s)
        raise argparse.ArgumentTypeError(msg) from e


def valid_vacation(s: str) -> \
                   Tuple[datetime.date, datetime.date, datetime.timedelta]:
    """
    Checks if the given string contains a valid vacation specifier in format
    YYYY-MM-DD:YYYY-MM-DD:hh, where the first entry of the colon-separated list
    is the start date in YYYY-MM-DD format, the second entry is the end date,
    and the third entry is the number of paid hours of working time per day.
    Args:
        s: The string to check.
    Returns:
        Tuple[datetime.date,datetime.date,datetime.timedelta]. The parsed
        vacation period.
    """
    fields = s.split(":")
    if len(fields) != 3:
        msg = (
            "Expected argument in form YYYY-MM-DD:YYYY-MM-DD:hh," +
            "but received: {0!r}"
        ).format(s)
        raise argparse.ArgumentTypeError(msg)
    vacation_start = valid_date(fields[0])
    vacation_end = valid_date(fields[1])
    if vacation_end < vacation_start:
        msg = "Vacation end must be after vacation start."
        raise argparse.ArgumentTypeError(msg)
    try:
        paid_time = datetime.timedelta(hours=float(fields[2]))
    except ValueError as e:
        msg = "Not a valid hours specifier: {0!r}".format(fields[2])
        raise argparse.ArgumentTypeError(msg) from e
    return (vacation_start, vacation_end, paid_time)


def get_args() -> argparse.Namespace:
    """
    Parses the script arguments.
    Returns:
        argparse.Namespace. The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Create worktime timetables from Clockify csv data.",
        allow_abbrev=False
    )
    parser.add_argument(
        "input_filename",
        metavar="<file.csv>",
        type=argparse.FileType("r"),
        help="The CSV file to use.",
    )
    parser.add_argument(
        "start_date",
        metavar="<start date>",
        help="The start date with format YYYY-MM-DD.",
        type=valid_date
    )
    parser.add_argument(
        "-p",
        help="Automatically create PDF with latexmk.",
        action="store_true"
    )
    parser.add_argument(
        "-c",
        help="Automatically cleanup LaTeX auxiliary files at the" +
             "end (requires -p).",
        action="store_true"
    )
    parser.add_argument(
        "-v",
        help="Schedule a vacation using the given paid time and the format" +
             "YYYY-MM-DD:YYYY-MM-DD:hh.",
        metavar="<start:end:paid time>",
        type=valid_vacation,
        nargs="+"
    )
    args = parser.parse_args()
    if args.c and not args.p:
        parser.error("-p is required when -c is set.")
    if args.p and not latexmk_available():
        parser.error("-p requires latexmk to be installed.")
    return args


def get_end_date(start_date: datetime.date) -> datetime.date:
    """
    Calculates the end date to the given start date.
    Args:
        start_date: datetime.date. The start date.
    Returns:
        datetime.date. The date that is exactly one month after start_date.
        This date is in the next month and the number of the day is decreased
        by one. E.g., if 2000-12-15 is passed, 2001-01-14 is returned.
    """
    if start_date.month < 12:
        end_year = start_date.year
        end_month = start_date.month + 1
    else:
        end_year = start_date.year + 1
        end_month = 1
    end_day = start_date.day - 1
    return datetime.date(end_year, end_month, end_day)


def get_selected_date_range(args: argparse.Namespace) -> \
                            Tuple[datetime.date, datetime.date]:
    """
    Determines the selected date range to consider.
    Args:
        args: argparse.Namespace. The script arguments.
    Returns:
        Tuple[datetime.date,datetime.date]. A tuple that contains the start
        date that was passed to the script and the end date which was
        calculated via get_end_date.
    """
    start_date = args.start_date
    end_date = get_end_date(start_date)
    date_range = (start_date, end_date)
    return date_range


def main() -> None:
    args = get_args()
    date_range = get_selected_date_range(args)
    vacations = args.v or []
    df = pd.read_csv(args.input_filename, quotechar="\"")
    with open("template.tex", "r") as f:
        template = f.read()
    work_times = get_work_times(df, date_range)
    if len(work_times) == 0:
        raise RuntimeError("There were no work times in the selected months.")
    output_filenames = []
    for i, (year, month) in enumerate(
        (date.year, date.month) for date in date_range
    ):
        table_content = get_table_content(work_times, year, month, vacations)
        output_tex = fill_template(template, table_content,
                                   issue_date=date_range[1])
        output_filename = "Zeiterfassung_{:04d}-{:02d}_{}.tex".format(
            year,
            month,
            "Ende" if i == 0 else "Anfang"
        )
        with open(output_filename, "w") as f:
            f.write(output_tex)
        output_filenames.append(output_filename)
    if args.p:
        for output_filename in output_filenames:
            run_command(["latexmk", "-pdf", output_filename])
        if args.c:
            run_command(["latexmk", "-c"])


if __name__ == "__main__":
    main()
