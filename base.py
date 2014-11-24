# basic tools

TIME_FMT = "%Y-%m-%d %H:%M:%S"
SLASH_TIME_FMT = "%Y/%m/%d %H:%M:%S" # for use in base.strptime, fmts convert to / instead of -

def strptime(date_str, optional_fmt=None): # returns None on bad conversion
  """wrapper for strptime that handles common US formats-- returns None if all fail."""
  # note: the formats tested are distinguishable, e.g. 12/12/2012 vs. 12/12/12 vs. 2012/12/12
  if date_str is None or not isinstance(date_str, basestring):
    return None
  fmts = ['%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d', SLASH_TIME_FMT]
  if optional_fmt:
    fmts.insert(0, re.sub("-", "/", optional_fmt))
  date_str = re.sub("-", "/", date_str.strip()) # we use both - and / delimited dates (convert to 1)
  for fmt in fmts:
    try:
      # pylint:disable=W9911
      return datetime.datetime.strptime(date_str, fmt)
      # pylint:enable=W9911
    except:
      continue
  return None

