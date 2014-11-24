# pylint:disable=C0103
import base, re, datetime, logging

def weekstart(ts, fmt=base.TIME_FMT, dayofweek=0, outfmt=None):
  """mon=0, sun=7"""
  if isinstance(ts, basestring):
    # python 2.5 doesn't support %f / microseconds...
    ts = base.strptime(re.sub(r'[.][0-9]+$', '', ts), fmt)
  res = (ts - datetime.timedelta(days=((ts.weekday() - dayofweek + 7) % 7))).replace(
    hour=0, minute=0, second=0, microsecond=0)
  return res.strftime(outfmt) if outfmt else res

def WEEKSTART(field, *args, **kwargs):
  return lambda rec: weekstart(getattr(rec, field), *args, **kwargs)

def TS(s, fmt=base.TIME_FMT, length=19):
  """length allows you to ignore chars-- if you want them, pass None or 999."""
  # TODO: sigh, python 2.5 doesn't support microseconds (%f)
  if not isinstance(s, basestring):
    if isinstance(s, datetime.datetime):
      return s
    raise base.DisplayableException("TS(): string passed that's not a date")
  if length is None or length > 30:
    base.strptime(s, fmt)
  return base.strptime(s[0:length], fmt)

def DATE(s, fmt="%Y-%m-%d", length=10):
  if not isinstance(s, basestring):
    if isinstance(s, datetime.datetime):
      return s
    raise base.DisplayableException("DATE(): string passed that's not a date")
  return TS(s, fmt, length)

def HASFIELD(field, allowblank=False):
  if allowblank:
    return lambda r: getattr(r, field, None) is not None
  return lambda r: getattr(r, field, None) not in [None, ""]

def MATCH_SELLER_CATS(include_cats, exclude_cats):
  """helper function to match seller categories"""
  return lambda rec: \
    sum([(1 if cat in include_cats else 0) for cat in re.split(r'; *', rec.categories)]) > 0 and \
    sum([(1 if cat in exclude_cats else 0) for cat in re.split(r'; *', rec.categories)]) == 0

def REC_NON_BLANK(fld):
  return lambda rec: getattr(rec, fld, "") != ""
  
def COUNT():
  return len
def COUNT_DISTINCT(*fields):
  return lambda recs: len(set(
        "\t".join(getattr(r, field, "") for field in fields) for r in recs))
def COUNT_IF(func):
  return lambda recs: len([r for r in recs if func(r)])
def COUNT_IFEQ(field, val, method="sum"):
  if method == "sum":
    return lambda recs: len([1 for r in recs if getattr(r, field, "") == val])
  if method == "pct":
    return lambda recs: 0.0 if len(recs) == 0 else \
        len([1 for r in recs if getattr(r, field, "") == val]) / float(len(recs)) * 100.0
  if method == "frac":
    return lambda recs: 0.0 if len(recs) == 0 else \
        len([1 for r in recs if getattr(r, field, "") == val]) / float(len(recs))

def ANY(field):
  return lambda recs: any([bool(getattr(r, field, False)) for r in recs])
def ALL(field):
  return lambda recs: all([bool(getattr(r, field, True)) for r in recs])

def SUM(field):
  return lambda recs: sum(float(getattr(r, field, 0.0)) for r in recs)
def SUM_DISTINCT(field):
  return lambda recs: sum(list(set(float(getattr(r, field, 0.0)) for r in recs)))
def SUM_IFEQ(field, val, otherfield=None):
  if otherfield is None:
    return lambda recs: sum([float(getattr(r, field, 0.0)) \
                               for r in recs if getattr(r, field) == val])
  return lambda recs: sum([float(getattr(r, otherfield, 0.0)) \
                             for r in recs if getattr(r, field) == val])
def SUM_IF(field, func):
  return lambda recs: sum([float(getattr(r, field, 0.0)) for r in recs if func(r)])

def SUMIF_GROUP_DAYS(field_name, comparison_fld, days_lookback_start, days_lookback_end,
                                         startdate=None, comparison_fld_func=TS):
  ''' For use as a groupby aggregator, does a sumif based on a days slicing
      field_name: fieldname to make summation of
      startdate: startdate for comparison
      days_lookback_start: N days prior to the startdate does this grouping slice start (inclusive)
      days_lookback_end: N days prior to the startdate does this groupin slice end (exclusive)
      comaprison_fld: datefield on the record to make groupings by
      comparison_fld_func: transform comparison_fld to date with this function '''
  def is_date_within(date_start, date_compare, date_end):
    try:
      return date_start >= date_compare >= date_end
    except: 
      logging.error("failure to compare dates: %s, %s, %s" , repr(date_start), repr(date_compare),
                                                                                     repr(date_end))
      return False
  startdate = startdate if startdate else datetime.datetime.now()
  return SUM_IF(field_name,
               lambda r: is_date_within(
                base.endofday(startdate-datetime.timedelta(days_lookback_start)),
                comparison_fld_func(getattr(r, comparison_fld)),
                base.startofday(startdate-datetime.timedelta(days_lookback_end))))


def SUM_PCT(field, totalfield):
  """  NNN (mm.m%)  """
  def func(recs):
    totfld = sum(float(getattr(r, field, 0.0)) for r in recs)
    tot = sum(float(getattr(r, totalfield, 0.0)) for r in recs)
    return "%g (%.1f%%)" % (tot, base.safepct(totfld, tot))
  return func

def AVG(field):
  return lambda recs: 0 if len(recs) == 0 else \
      sum(float(getattr(r, field)) for r in recs)/len(recs)
def AVG_IFEQ(field, val, otherfield=None):
  def avg_ifeq_func(recs):
    total = count = 0.0
    for rec in recs:
      fieldval = getattr(rec, field)
      if fieldval == val:
        count += 1.0
        total += float(getattr(rec, otherfield)) if otherfield else fieldval
    return ((total / count) if count > 0.0 else 0.0)
  return avg_ifeq_func
def AVG_IF(field, func):
  def avg_if_func(recs):
    total = count = 0.0
    for rec in recs:
      if func(rec):
        count += 1.0
        total += float(getattr(rec, field))
    return ((total / count) if count > 0.0 else 0.0)
  return avg_if_func

def FIRST(field, include_blank=False):
  if include_blank:
    return lambda recs: getattr(recs[0], field)
  def func(recs):
    for rec in recs:
      val = getattr(rec, field, "")
      if val != "":
        return val
    return getattr(recs[0], field, "")
  return func
def LAST(field, include_blank=False):
  if include_blank:
    return lambda recs: getattr(recs[-1], field)
  def func(recs):
    revrecs = recs
    revrecs.reverse()
    for rec in revrecs: # reverse in place
      val = getattr(rec, field, "")
      if val != "":
        return val
    return getattr(revrecs[0], field, "")
  return func
def MIN(field):
  return lambda recs: min(getattr(rec, field) for rec in recs)
def MAX(field):
  return lambda recs: max(getattr(rec, field) for rec in recs)
def CONCAT(field, sep=",", filterfunc=None, sortfunc=None, uniquify=True):
  def concatfunc(recs):
    res = [str(getattr(rec, field)) for rec in recs if filterfunc is None or filterfunc(rec)]
    if uniquify:
      res = list(set(res))
    return sep.join(sorted(res, key=sortfunc))
  return concatfunc

def MERGEFIELDS(fields="", joinstr=" "):
  """across several fields, keep the first non-empty value."""
  def mergefunc(recs):
    res = {}
    for rec in recs:
      for fld in fields.split():
        val = getattr(rec, fld, "")
        if val != "":
          res[fld] = val
    return joinstr.join(str(res.get(fld, "")) for fld in fields.split())
  return mergefunc

def FLOAT(field):
  return lambda rec: float(getattr(rec, field))
def INT(field):
  return lambda rec: int(getattr(rec, field))

def lt_to_dict(tbl, keyfield, valfield=None):
  if valfield:
    return dict( (rec[keyfield], rec[valfield]) for rec in tbl.obs)
  return dict( (rec[keyfield], rec.__dict__) for rec in tbl.obs)

def shift_minutes(shiftstr, location="", name="", whos_on=None, numshifts=None):
  """parse a shiftstr like 9-5:00"""
  shiftstr=re.sub(r'[(].+[)]', '', shiftstr)  # ignore (...) in shifts
  shiftstr=re.sub(r'[^0-9:-]', '', shiftstr).strip()
  if shiftstr in ["", "-"]:
    return 0
  date = base.NOW
  try:
    shift=re.sub(r'^([0-9]+)-', r'\1:00-', shiftstr)   # 9-5:00 ==> 9:00-5:00
    shift=re.sub(r'-([0-9]+)$', r'-\1:00', shift)   # 9:00-5 ==> 9:00-5:00
    # prefix 2:30 with 02:30
    shift=re.sub(r'([^0-9])([0-9]):', r'\1xxx\2:', ' '+shift).replace('xxx', '0')
    shiftstart,shiftend=shift.split("-")
    shiftstart=shiftstart.strip()
    shiftstart_ts=base.strptime(date.strftime("%Y-%m-%d ")+shiftstart, "%Y-%m-%d %H:%M")
    shiftend=shiftend.strip()
    shiftend_ts=base.strptime(date.strftime("%Y-%m-%d ")+shiftend, "%Y-%m-%d %H:%M")
    if shiftend<="9:00" or shiftend<=shiftstart:
      shiftend_ts = shiftend_ts + datetime.timedelta(hours=12)
    if shiftend_ts - shiftstart_ts >= datetime.timedelta(hours=12):
      shiftstart_ts += datetime.timedelta(hours=12)
    ts = shiftstart_ts
    while ts < shiftend_ts:
      if whos_on:
        key=location+ts.strftime("%Y-%m-%d %H:%M")
        whos_on[key]=(whos_on[key]+","+name) if key in whos_on else name
      if numshifts:
        numshifts[name]=numshifts.get(name, 0)+1
      ts = ts + datetime.timedelta(minutes=30)
  except Exception, exc:  # pylint:disable=W0703,W0612
    return -1
    #add_result("could not parse shift: %s for weekday %s: %s  (start=%s, end=%s)"
    #           % (shiftstr, weekday, str(exc), shiftstart, shiftend))
  return int((ts - shiftstart_ts).seconds / 60)

