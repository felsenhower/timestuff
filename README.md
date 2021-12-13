# timestuff


This script creates neat overviews of working hours using LaTeX if a CSV from
Clockify is supplied.

> :information_source: **The output is only in German, because I have no reason to change this atm.**

## Usage

```
usage: timestuff.py [-h] [-p] [-c] [-v <start:end:paid time> [<start:end:paid time> ...]] <file.csv> <start date>

Create worktime timetables from Clockify csv data.

positional arguments:
  <file.csv>            The CSV file to use.
  <start date>          The start date with format YYYY-MM-DD.

optional arguments:
  -h, --help            show this help message and exit
  -p                    Automatically create PDF with latexmk.
  -c                    Automatically cleanup LaTeX auxiliary files at theend (requires -p).
  -v <start:end:paid time> [<start:end:paid time> ...]
                        Schedule a vacation using the given paid time and the formatYYYY-MM-DD:YYYY-MM-DD:hh.
```

The basic usage is like the following:

```bash
$ ./timestuff.py Clockify.csv 2021-01-15
```

This will extract the data from the given `Clockify.csv` and only consider the
months `2021-01` (January 2021) and `2021-02` (February 2021). The first date will
be `2021-01-15` and the last date will be `2021-02-14`.

The output files created will be named
`Zeiterfassung_2021-01_Ende.pdf` and `Zeiterfassung_2021-02_Anfang.pdf`.

One can also pass the flag `-p` which will case `latexmk` to be run automatically
in the end, if it is installed.

If the flag `-c` is passed, `latexmk -c` is called in the end which cleans up
all auxiliary files of LaTeX.

The argument `-v` allows to pass vacation periods, e.g. 
```bash
$ ./timestuff.py Clockify.csv 2021-01-15 -v 2021-01-18:2021-01-20:8.0
```
which means that a vacation period will be inserted from `2021-01-18` to
`2021-01-20`, where each day accounts for 8 hours of paid vacation.

Multiple vacations can be passed.




