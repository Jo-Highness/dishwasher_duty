"""Constants for the Dishwasher Duty integration."""

from __future__ import annotations

DOMAIN = "dishwasher_duty"

# --- Config / Options keys -------------------------------------------------
CONF_SOURCE_SENSOR = "source_sensor"
CONF_FINISHED_VALUE = "finished_value"
CONF_RUNNING_VALUE = "running_value"
CONF_PERSONS = "persons"
CONF_ALLOW_CO_CLAIM = "allow_co_claim"
CONF_CO_CLAIM_WINDOW = "co_claim_window"
CONF_DEBOUNCE = "debounce_seconds"

# --- Defaults --------------------------------------------------------------
# Home Connect's "Operation state" sensor reports the finished/running phases.
# Depending on HA/integration version this is either the enum tail
# ("Finished"/"Run") or a normalised lowercase value. These are editable so
# other devices/languages can be covered.
DEFAULT_FINISHED_VALUE = "Finished"
DEFAULT_RUNNING_VALUE = "Run"
DEFAULT_ALLOW_CO_CLAIM = True
DEFAULT_CO_CLAIM_WINDOW = 90  # seconds
DEFAULT_DEBOUNCE = 0  # seconds; 0 = off

# States that must never be treated as a running/finished phase.
IGNORED_STATES = {"unavailable", "unknown", "none", ""}

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

ATTR_PERSON = "person"
ATTR_PERSONS = "persons"
ATTR_START = "start"
ATTR_END = "end"

# --- Dispatcher ------------------------------------------------------------
SIGNAL_UPDATE = f"{DOMAIN}_update"

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
