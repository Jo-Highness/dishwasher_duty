"""Constants for the Dishwasher Duty integration."""

from __future__ import annotations

DOMAIN = "dishwasher_duty"

DEFAULT_TITLE = "Dishwasher Duty"

# --- Config / Options keys -------------------------------------------------
CONF_SOURCE_SENSOR = "source_sensor"
CONF_FINISHED_VALUE = "finished_value"
CONF_RUNNING_VALUE = "running_value"
CONF_PERSONS = "persons"
CONF_ALLOW_CO_CLAIM = "allow_co_claim"
CONF_CO_CLAIM_WINDOW = "co_claim_window"
CONF_DEBOUNCE = "debounce_seconds"

# --- Defaults --------------------------------------------------------------
# Home Connect's "Operation state" sensor is an ENUM sensor that reports
# lowercase values ("run", "finished", ...) since HA 2025.1. Older versions
# reported "Run"/"Finished". State values are compared case-insensitively, so
# both spellings match; other devices can use any custom value.
DEFAULT_FINISHED_VALUE = "finished"
DEFAULT_RUNNING_VALUE = "run"
DEFAULT_ALLOW_CO_CLAIM = True
DEFAULT_CO_CLAIM_WINDOW = 90  # seconds
DEFAULT_DEBOUNCE = 0  # seconds; 0 = off

# Source-sensor states that are never treated as a phase. They are not stored
# as the "previous state" either, so run -> unavailable -> finished still
# counts as one cycle while unavailable -> finished (without run) does not.
IGNORED_STATES = frozenset({"unavailable", "unknown", "none", ""})

# --- Storage ---------------------------------------------------------------
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}."

# --- Cycle status ----------------------------------------------------------
STATUS_UNCLAIMED = "unclaimed"
STATUS_CLAIMED = "claimed"

# --- Services --------------------------------------------------------------
SERVICE_CLAIM = "claim"
SERVICE_CLAIM_MULTIPLE = "claim_multiple"
SERVICE_CANCEL_CLAIM = "cancel_claim"
SERVICE_GET_STATISTICS = "get_statistics"
SERVICE_RESET_STATISTICS = "reset_statistics"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_PERSON = "person"
ATTR_PERSONS = "persons"
ATTR_START = "start"
ATTR_END = "end"

# --- Repairs ---------------------------------------------------------------
ISSUE_SOURCE_SENSOR_MISSING = "source_sensor_missing"

# --- Entity attribute keys -------------------------------------------------
ATTR_LAST_CYCLE_FINISHED = "last_cycle_finished"
ATTR_CURRENT_CYCLE_CLAIMED_BY = "current_cycle_claimed_by"
ATTR_LAST_CLAIM_CREDITS = "last_claim_credits"

ATTR_CLAIM_OPEN_SINCE = "claim_open_since"
ATTR_CO_CLAIM_WINDOW_UNTIL = "co_claim_window_until"
ATTR_CURRENT_CLAIMERS = "current_claimers"

ATTR_CREDITS_TOTAL = "credits_total"
ATTR_CREDITS_TODAY = "credits_today"
ATTR_CREDITS_THIS_WEEK = "credits_this_week"
ATTR_CREDITS_THIS_MONTH = "credits_this_month"
ATTR_CREDITS_THIS_YEAR = "credits_this_year"
ATTR_CLAIMS_COUNT_TOTAL = "claims_count_total"
ATTR_LAST_CLAIM = "last_claim"
