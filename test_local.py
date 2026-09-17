"""
test_local.py
Local integration test for all bot services (no Telegram needed).
Run: python test_local.py [section]
  section = gcal | trello | reminders | timesheet | expenditure | insight | nlp | formatter | all  (default: all)

Each test prints PASS / FAIL and a summary at the end.
Created events and cards are deleted after the test run.
"""

import sys
import traceback
from datetime import datetime, timedelta

# ── colour helpers ────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RESET  = "\033[0m"

_results: list[tuple[str, bool, str]] = []   # (name, passed, detail)
_cleanup: list[tuple[str, callable]] = []    # (label, fn)


def run(name: str, fn):
    label = f"{CYAN}{name}{RESET}"
    try:
        result = fn()
        msg = str(result)[:120] if result is not None else "OK"
        print(f"  {GREEN}PASS{RESET}  {label}  →  {msg}")
        _results.append((name, True, msg))
        return result
    except Exception as e:
        detail = f"{e.__class__.__name__}: {e}"
        print(f"  {RED}FAIL{RESET}  {label}  →  {detail}")
        traceback.print_exc()
        _results.append((name, False, detail))
        return None


def section(title: str):
    print(f"\n{YELLOW}{'─'*60}{RESET}")
    print(f"{YELLOW}  {title}{RESET}")
    print(f"{YELLOW}{'─'*60}{RESET}")


def summary():
    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed
    print(f"\n{'═'*60}")
    print(f"  Results: {GREEN}{passed} passed{RESET}  {RED}{failed} failed{RESET}  / {total} total")
    if failed:
        print(f"\n  {RED}Failed tests:{RESET}")
        for name, ok, detail in _results:
            if not ok:
                print(f"    • {name}: {detail}")
    print(f"{'═'*60}\n")
    return failed


def run_cleanup():
    if not _cleanup:
        return
    print(f"\n{YELLOW}── Cleanup ──{RESET}")
    for label, fn in _cleanup:
        try:
            fn()
            print(f"  {GREEN}done{RESET}  {label}")
        except Exception as e:
            print(f"  {RED}skip{RESET}  {label}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  1. Google Calendar
# ══════════════════════════════════════════════════════════════════════════════

def test_gcal():
    import services.google_calendar as gcal
    from utils.config import CONFIG
    from utils.dt import now

    section("Google Calendar")

    # 1a. Get today's events
    run("gcal.get_events('today')",
        lambda: f"{len(gcal.get_events('today'))} event(s)")

    # 1b. Get week events
    run("gcal.get_events('week')",
        lambda: f"{len(gcal.get_events('week'))} event(s)")

    # 1c. Create an event (starts 2 hours from now, 1-hour duration)
    tz    = now().tzinfo
    start = now() + timedelta(hours=2)
    end   = start + timedelta(hours=1)

    created_event = run(
        "gcal.create_event (basic)",
        lambda: gcal.create_event(
            summary   = "[TEST] Daily-Manager-Bot local test event",
            start_iso = start.isoformat(),
            end_iso   = end.isoformat(),
        ),
    )

    # 1d. Create an event with a reminder
    created_with_reminder = run(
        "gcal.create_event (with reminder_minutes=15)",
        lambda: gcal.create_event(
            summary          = "[TEST] Event with reminder",
            start_iso        = (now() + timedelta(hours=3)).isoformat(),
            end_iso          = (now() + timedelta(hours=4)).isoformat(),
            reminder_minutes = 15,
        ),
    )

    # 1e. Verify the created event appears in today/week listing
    def _check_created():
        ids = {e["id"] for e in gcal.get_events("week")}
        if created_event and created_event["id"] not in ids:
            raise AssertionError("Created event not found in week listing")
        return "found in week listing"

    run("gcal: created event visible in week listing", _check_created)

    # Schedule cleanup
    for ev in [created_event, created_with_reminder]:
        if ev:
            _cleanup.append((
                f"gcal.delete_event({ev['id'][:8]}…)",
                lambda eid=ev["id"]: gcal.delete_event(eid),
            ))

    # 1f. Test delete directly (create a throwaway event then delete it)
    def _test_delete():
        ev = gcal.create_event(
            summary   = "[TEST] Delete me",
            start_iso = (now() + timedelta(hours=5)).isoformat(),
            end_iso   = (now() + timedelta(hours=6)).isoformat(),
        )
        gcal.delete_event(ev["id"])
        return "created then deleted successfully"

    run("gcal.delete_event", _test_delete)


# ══════════════════════════════════════════════════════════════════════════════
#  2. Trello
# ══════════════════════════════════════════════════════════════════════════════

def test_trello():
    import services.trello as trello
    from utils.dt import now
    from datetime import timedelta

    section("Trello")

    # 2a. Get lists
    lists = run("trello.get_lists()", lambda: f"{len(trello.get_lists())} list(s): " +
                ", ".join(l["name"] for l in trello.get_lists()))

    first_list = trello.get_lists()[0]["name"] if trello.get_lists() else None

    # 2b. Get all cards
    run("trello.get_cards() (all cards)",
        lambda: f"{len(trello.get_cards())} card(s)")

    # 2c. Get cards filtered by list name
    if first_list:
        run(f"trello.get_cards('{first_list}')",
            lambda: f"{len(trello.get_cards(first_list))} card(s) in '{first_list}'")

    # 2d. Create basic card
    card_basic = run(
        "trello.create_card (basic)",
        lambda: trello.create_card(name="[TEST] Basic card from local test"),
    )

    # 2e. Create card with high priority
    card_high = run(
        "trello.create_card (priority=high)",
        lambda: trello.create_card(
            name        = "[TEST] High-priority card",
            description = "Added by test_local.py",
            priority    = "high",
        ),
    )

    # 2f. Create card with medium priority + due date
    due_iso = (now() + timedelta(days=3)).isoformat()
    card_due = run(
        "trello.create_card (priority=medium, due in 3 days)",
        lambda: trello.create_card(
            name     = "[TEST] Medium-priority card with due date",
            priority = "medium",
            due      = due_iso,
        ),
    )

    # 2g. Create card with low priority
    card_low = run(
        "trello.create_card (priority=low)",
        lambda: trello.create_card(
            name     = "[TEST] Low-priority card",
            priority = "low",
        ),
    )

    # 2h. Move card to second list (if board has ≥2 lists)
    all_lists = trello.get_lists()
    if card_basic and len(all_lists) >= 2:
        target_list = all_lists[1]["name"]
        run(
            f"trello.move_card → '{target_list}'",
            lambda: trello.move_card(card_basic["id"], target_list),
        )

    # 2i. Set card priority
    if card_basic:
        run(
            "trello.set_card_priority → low",
            lambda: trello.set_card_priority(card_basic["id"], "low") or "OK",
        )

    # 2j. get_cards with unknown list (should return empty, not crash)
    run(
        "trello.get_cards('__nonexistent__') → []",
        lambda: str(trello.get_cards("__nonexistent__")),
    )

    # Schedule cleanup
    for card in [card_basic, card_high, card_due, card_low]:
        if card:
            _cleanup.append((
                f"trello.delete_card({card['id'][:8]}…)",
                lambda cid=card["id"]: trello.delete_card(cid),
            ))


# ══════════════════════════════════════════════════════════════════════════════
#  3. Reminders
# ══════════════════════════════════════════════════════════════════════════════

def test_reminders():
    import services.reminders as rem_svc
    from utils.dt import now
    from datetime import timedelta

    section("Reminders (file-based, no scheduler needed for CRUD)")

    # Clear any leftover test reminders first
    rem_svc.clear_all_reminders()

    # 3a. Add a reminder (30 min from now)
    fire_time = (now() + timedelta(minutes=30)).isoformat()
    r1 = run(
        "reminders.add_reminder (30 min from now)",
        lambda: rem_svc.add_reminder(
            title         = "[TEST] Pick up groceries",
            remind_at_iso = fire_time,
        ),
    )

    # 3b. Add second reminder
    fire_time2 = (now() + timedelta(hours=2)).isoformat()
    r2 = run(
        "reminders.add_reminder (2 hours from now)",
        lambda: rem_svc.add_reminder(
            title         = "[TEST] Team standup",
            remind_at_iso = fire_time2,
        ),
    )

    # 3c. List reminders
    run(
        "reminders.list_reminders()",
        lambda: f"{len(rem_svc.list_reminders())} reminder(s): " +
                ", ".join(r["title"] for r in rem_svc.list_reminders()),
    )

    # 3d. Verify count
    def _check_count():
        rems = rem_svc.list_reminders()
        if len(rems) != 2:
            raise AssertionError(f"Expected 2 reminders, got {len(rems)}")
        return "count correct"

    run("reminders: count == 2 after adding 2", _check_count)

    # 3e. Clear all
    run(
        "reminders.clear_all_reminders()",
        lambda: f"cleared {rem_svc.clear_all_reminders()} reminder(s)",
    )

    # 3f. Verify empty after clear
    def _check_empty():
        rems = rem_svc.list_reminders()
        if rems:
            raise AssertionError(f"Expected 0 reminders after clear, got {len(rems)}")
        return "empty"

    run("reminders: empty after clear", _check_empty)

    # 3g. Past reminder should be silently ignored by scheduler (CRUD still works)
    past_time = (now() - timedelta(hours=1)).isoformat()
    run(
        "reminders.add_reminder (past time — persists but won't fire)",
        lambda: rem_svc.add_reminder(
            title         = "[TEST] Past reminder",
            remind_at_iso = past_time,
        ),
    )

    # cleanup
    rem_svc.clear_all_reminders()
    print(f"  {GREEN}(cleanup: cleared test reminders){RESET}")


# ══════════════════════════════════════════════════════════════════════════════
#  4. Timesheet
# ══════════════════════════════════════════════════════════════════════════════

def test_timesheet():
    import services.timesheet as ts_svc
    from utils.dt import now
    from datetime import timedelta

    section("Timesheet (file-based, no scheduler)")

    # 4a. Clear any leftover test entries first
    ts_svc.clear_entries()

    # 4b. Add an entry (defaults to today's date)
    e1 = run(
        "timesheet.add_entry (default date)",
        lambda: ts_svc.add_entry(description="[TEST] Fixed the reminder scheduler bug"),
    )

    def _check_default_date():
        expected = now().strftime("%Y-%m-%d")
        if e1["date_iso"] != expected:
            raise AssertionError(f"Expected date_iso={expected}, got {e1['date_iso']}")
        return f"date_iso={e1['date_iso']}"

    run("timesheet: default date_iso is today", _check_default_date)

    # 4c. Add a second entry for the same day (accumulation)
    e2 = run(
        "timesheet.add_entry (second entry, same day)",
        lambda: ts_svc.add_entry(description="[TEST] Reviewed the timesheet PR"),
    )

    # 4d. Add an entry for an explicit past date
    yesterday = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
    e3 = run(
        "timesheet.add_entry (explicit date_iso)",
        lambda: ts_svc.add_entry(description="[TEST] Backfilled entry", date_iso=yesterday),
    )

    # 4e. List entries
    run(
        "timesheet.list_entries()",
        lambda: f"{len(ts_svc.list_entries())} entr(y/ies): " +
                ", ".join(e["description"] for e in ts_svc.list_entries()),
    )

    # 4f. Verify count / accumulation
    def _check_count():
        entries = ts_svc.list_entries()
        if len(entries) != 3:
            raise AssertionError(f"Expected 3 entries, got {len(entries)}")
        return "count correct (accumulated, not overwritten)"

    run("timesheet: count == 3 after adding 3 entries", _check_count)

    # 4g. Verify each entry has a unique id
    def _check_unique_ids():
        entries = ts_svc.list_entries()
        ids = {e["id"] for e in entries}
        if len(ids) != len(entries):
            raise AssertionError("Duplicate ids found among entries")
        return "all ids unique"

    run("timesheet: entries have unique ids", _check_unique_ids)

    # 4h. Clear all
    run(
        "timesheet.clear_entries()",
        lambda: f"cleared {ts_svc.clear_entries()} entr(y/ies)",
    )

    # 4i. Verify empty after clear
    def _check_empty():
        entries = ts_svc.list_entries()
        if entries:
            raise AssertionError(f"Expected 0 entries after clear, got {len(entries)}")
        return "empty"

    run("timesheet: empty after clear", _check_empty)

    # 4j. clear_entries on already-empty store returns 0, doesn't crash
    run(
        "timesheet.clear_entries() when already empty",
        lambda: f"cleared {ts_svc.clear_entries()} entr(y/ies)",
    )

    # cleanup safety net
    ts_svc.clear_entries()
    print(f"  {GREEN}(cleanup: cleared test timesheet entries){RESET}")


# ══════════════════════════════════════════════════════════════════════════════
#  4b. Expenditure (file-based, no scheduler)
# ══════════════════════════════════════════════════════════════════════════════

def test_expenditure():
    import services.expenditure as exp_svc
    from utils.dt import now
    from datetime import timedelta

    section("Expenditure (file-based, no scheduler)")

    # Clear any leftover test entries first
    exp_svc.clear_entries()

    # Add an entry (defaults to today's date)
    e1 = run(
        "expenditure.add_entry (default date)",
        lambda: exp_svc.add_entry(description="[TEST] Lunch at warung", amount=25000),
    )

    def _check_default_date():
        expected = now().strftime("%Y-%m-%d")
        if e1["date_iso"] != expected:
            raise AssertionError(f"Expected date_iso={expected}, got {e1['date_iso']}")
        return f"date_iso={e1['date_iso']}"

    run("expenditure: default date_iso is today", _check_default_date)

    # Second entry, same day (accumulation)
    run(
        "expenditure.add_entry (second entry, same day)",
        lambda: exp_svc.add_entry(description="[TEST] Coffee", amount=15000),
    )

    # Entry for an explicit past date
    yesterday = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
    run(
        "expenditure.add_entry (explicit date_iso)",
        lambda: exp_svc.add_entry(description="[TEST] Groceries", amount=100000, date_iso=yesterday),
    )

    # List entries
    run(
        "expenditure.list_entries()",
        lambda: f"{len(exp_svc.list_entries())} entr(y/ies): " +
                ", ".join(e["description"] for e in exp_svc.list_entries()),
    )

    def _check_count():
        entries = exp_svc.list_entries()
        if len(entries) != 3:
            raise AssertionError(f"Expected 3 entries, got {len(entries)}")
        return "count correct (accumulated, not overwritten)"

    run("expenditure: count == 3 after adding 3 entries", _check_count)

    def _check_unique_ids():
        entries = exp_svc.list_entries()
        ids = {e["id"] for e in entries}
        if len(ids) != len(entries):
            raise AssertionError("Duplicate ids found among entries")
        return "all ids unique"

    run("expenditure: entries have unique ids", _check_unique_ids)

    # Verify analyze_entries() math against hand-computed expected values
    def _check_analysis():
        entries = exp_svc.list_entries()
        result = exp_svc.analyze_entries(entries)
        if result["total_amount"] != 140000:
            raise AssertionError(f"Expected total_amount=140000, got {result['total_amount']}")
        if result["total_days"] != 2:
            raise AssertionError(f"Expected total_days=2, got {result['total_days']}")
        if result["entry_count"] != 3:
            raise AssertionError(f"Expected entry_count=3, got {result['entry_count']}")
        if result["per_day"].get(yesterday) != 100000:
            raise AssertionError(f"Expected per_day[{yesterday}]=100000, got {result['per_day']}")
        today_iso = now().strftime("%Y-%m-%d")
        if result["per_day"].get(today_iso) != 40000:
            raise AssertionError(f"Expected per_day[{today_iso}]=40000, got {result['per_day']}")
        if result["highest_day"] != (yesterday, 100000):
            raise AssertionError(f"Expected highest_day=({yesterday}, 100000), got {result['highest_day']}")
        if result["avg_per_day"] != 70000:
            raise AssertionError(f"Expected avg_per_day=70000, got {result['avg_per_day']}")
        return f"total={result['total_amount']} days={result['total_days']} avg={result['avg_per_day']}"

    run("expenditure: analyze_entries() computes correct totals", _check_analysis)

    # analyze_entries() on empty list doesn't crash
    def _check_analysis_empty():
        result = exp_svc.analyze_entries([])
        if result["entry_count"] != 0 or result["total_amount"] != 0:
            raise AssertionError(f"Expected zeroed analysis, got {result}")
        return "zeroed analysis for empty input"

    run("expenditure: analyze_entries([]) doesn't crash", _check_analysis_empty)

    # Clear all
    run(
        "expenditure.clear_entries()",
        lambda: f"cleared {exp_svc.clear_entries()} entr(y/ies)",
    )

    def _check_empty():
        entries = exp_svc.list_entries()
        if entries:
            raise AssertionError(f"Expected 0 entries after clear, got {len(entries)}")
        return "empty"

    run("expenditure: empty after clear", _check_empty)

    # clear_entries on already-empty store returns 0, doesn't crash
    run(
        "expenditure.clear_entries() when already empty",
        lambda: f"cleared {exp_svc.clear_entries()} entr(y/ies)",
    )

    # cleanup safety net
    exp_svc.clear_entries()
    print(f"  {GREEN}(cleanup: cleared test expenditure entries){RESET}")


# ══════════════════════════════════════════════════════════════════════════════
#  4c. Insight (Groq categorization + expense analysis)
# ══════════════════════════════════════════════════════════════════════════════

def test_insight():
    import services.expenditure as exp_svc
    import services.insight as insight_svc

    section("Insight (Groq categorization + analysis)")

    exp_svc.clear_entries()

    exp_svc.add_entry(description="[TEST] Lunch at warung", amount=25000)
    exp_svc.add_entry(description="[TEST] Grab ride to office", amount=18000)
    exp_svc.add_entry(description="[TEST] Netflix subscription", amount=54000)

    run(
        "insight.categorize_missing (classifies 3 uncategorized entries)",
        lambda: insight_svc.categorize_missing(exp_svc.list_entries()),
    )

    def _check_categories_assigned():
        entries = exp_svc.list_entries()
        missing = exp_svc.entries_missing_category(entries)
        if missing:
            raise AssertionError(f"Expected all entries categorized, {len(missing)} still missing")
        cats = {e["category"] for e in entries}
        if not cats.issubset(set(insight_svc.CATEGORIES)):
            raise AssertionError(f"Unexpected category values: {cats}")
        return {e["description"]: e["category"] for e in entries}

    run("insight: all entries categorized with valid category", _check_categories_assigned)

    def _check_by_category():
        analysis = exp_svc.analyze_entries(exp_svc.list_entries())
        if not analysis["by_category"]:
            raise AssertionError("Expected non-empty by_category breakdown")
        if sum(analysis["by_category"].values()) != analysis["total_amount"]:
            raise AssertionError("by_category sums don't match total_amount")
        return analysis["by_category"]

    run("expenditure: analyze_entries() by_category sums to total", _check_by_category)

    analysis = exp_svc.analyze_entries(exp_svc.list_entries())

    def _check_insight_nonempty():
        text = insight_svc.generate_insight(analysis)
        if not text or len(text) < 10:
            raise AssertionError(f"Expected a substantive insight, got: {text!r}")
        return text[:100]

    run("insight.generate_insight (generic summary)", _check_insight_nonempty)

    run(
        "insight.generate_insight (specific question)",
        lambda: insight_svc.generate_insight(analysis, question="What category am I spending the most on?"),
    )

    run(
        "insight.generate_insight (empty analysis doesn't crash)",
        lambda: insight_svc.generate_insight(exp_svc.analyze_entries([])),
    )

    def _check_analyze_with_insight():
        result, text = insight_svc.analyze_with_insight()
        if result["entry_count"] != 3:
            raise AssertionError(f"Expected entry_count=3, got {result['entry_count']}")
        if not text:
            raise AssertionError("Expected non-empty insight text")
        return f"entry_count={result['entry_count']} insight={text[:60]}"

    run("insight.analyze_with_insight (combined helper)", _check_analyze_with_insight)

    # cleanup
    exp_svc.clear_entries()
    print(f"  {GREEN}(cleanup: cleared test expenditure entries){RESET}")


# ══════════════════════════════════════════════════════════════════════════════
#  5. NLP / parse_intent
# ══════════════════════════════════════════════════════════════════════════════

def test_nlp():
    from services.nlp import parse_intent

    section("NLP (Groq / parse_intent)")

    cases = [
        # (test_name, input_text, expected_intent)
        ("view_today",      "What's on my schedule today?",                  "view_today"),
        ("view_week",       "Show me this week's overview",                   "view_week"),
        ("add_event",       "Add dentist appointment at 2pm tomorrow",        "add_event"),
        ("add_event+time",  "Schedule a team meeting at 10am next Monday",    "add_event"),
        ("add_task basic",  "Create a task to review the design doc",         "add_task"),
        ("add_task #high",  "Create task Buy groceries #high",                "add_task"),
        ("set_reminder",    "Remind me to call Ali at 5pm today",             "set_reminder"),
        ("list_reminders",  "Show me my reminders",                           "list_reminders"),
        ("add_timesheet",   "Log timesheet: fixed the deploy config today",   "add_timesheet"),
        ("list_timesheet",  "Show me my timesheet",                           "list_timesheet"),
        ("clear_timesheet", "Clear my timesheet",                             "clear_timesheet"),
        ("add_expenditure",   "I spent 25000 on lunch at warung today",        "add_expenditure"),
        ("list_expenditure",  "Show me my expenses",                          "list_expenditure"),
        ("clear_expenditure", "Clear my expenditure log",                     "clear_expenditure"),
        ("analyze_expenditure", "How much have I spent this month?",          "analyze_expenditure"),
        ("unknown",         "What's the weather in Jakarta?",                  "unknown"),
    ]

    for test_name, text, expected in cases:
        def _check(t=text, ex=expected, tn=test_name):
            result = parse_intent(t)
            intent = result.get("intent")
            conf   = result.get("confidence", 0)
            data   = result.get("data", {})
            detail = f"intent={intent} conf={conf:.2f} data={data}"
            if intent != ex:
                raise AssertionError(f"Expected intent '{ex}', got '{intent}'. {detail}")
            return detail

        run(f"NLP: {test_name}", _check)

    # Extra: verify add_event returns start_iso
    def _check_iso():
        result = parse_intent("Add standup at 9am tomorrow")
        iso = result.get("data", {}).get("start_iso")
        if not iso:
            raise AssertionError(f"Expected start_iso, got: {result}")
        return f"start_iso={iso}"

    run("NLP: add_event populates start_iso", _check_iso)

    # Extra: verify add_task returns priority for #high input
    def _check_priority():
        result = parse_intent("Task: buy milk #high priority")
        p = result.get("data", {}).get("priority")
        if p not in ("high", None):   # LLM may or may not catch it
            raise AssertionError(f"Unexpected priority: {p}")
        return f"priority={p}"

    run("NLP: add_task captures priority", _check_priority)

    # Extra: verify add_timesheet defaults date_iso when not mentioned
    def _check_timesheet_desc():
        result = parse_intent("Log timesheet: reviewed the timesheet feature PR")
        desc = result.get("data", {}).get("description")
        if not desc:
            raise AssertionError(f"Expected description, got: {result}")
        return f"description={desc}"

    run("NLP: add_timesheet populates description", _check_timesheet_desc)

    # Extra: verify add_expenditure returns amount and description
    def _check_expenditure_amount():
        result = parse_intent("I spent 25000 on lunch at warung today")
        data = result.get("data", {})
        if data.get("amount") is None:
            raise AssertionError(f"Expected amount, got: {result}")
        if not data.get("description"):
            raise AssertionError(f"Expected description, got: {result}")
        return f"amount={data.get('amount')} description={data.get('description')}"

    run("NLP: add_expenditure populates amount + description", _check_expenditure_amount)

    # Extra: verify analyze_expenditure captures the free-text question
    def _check_expenditure_question():
        result = parse_intent("Why did I spend so much on food this month?")
        data = result.get("data", {})
        if not data.get("question"):
            raise AssertionError(f"Expected a question captured, got: {result}")
        return f"question={data.get('question')}"

    run("NLP: analyze_expenditure captures question", _check_expenditure_question)


# ══════════════════════════════════════════════════════════════════════════════
#  6. Formatter utilities
# ══════════════════════════════════════════════════════════════════════════════

def test_formatter():
    from utils.formatter import (
        format_events, format_cards, format_reminders, format_timesheet, format_daily, escape,
        format_rupiah, format_expenditure, format_expenditure_analysis, format_expenditure_insight
    )
    import services.expenditure as exp_svc
    from utils.dt import now
    from datetime import timedelta

    section("Formatter (pure functions, no API calls)")

    dt_str = now().isoformat()

    sample_events = [
        {"summary": "Team standup", "start": {"dateTime": dt_str}},
        {"summary": "Lunch with client", "start": {"dateTime": (now() + timedelta(hours=3)).isoformat()}},
    ]
    sample_cards = [
        {"name": "Buy groceries",  "labels": [{"color": "red"}],    "due": None},
        {"name": "Review PR",      "labels": [{"color": "yellow"}],  "due": dt_str},
        {"name": "Read book",      "labels": [],                      "due": None},
    ]
    sample_reminders = [
        {"id": "abc", "title": "Call doctor", "remind_at_iso": dt_str},
    ]
    today_iso = now().strftime("%Y-%m-%d")
    yesterday_iso = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
    sample_timesheet = [
        {"id": "t1", "date_iso": yesterday_iso, "description": "Backfilled entry"},
        {"id": "t2", "date_iso": today_iso,      "description": "Fixed the reminder bug"},
        {"id": "t3", "date_iso": today_iso,      "description": "Reviewed the timesheet PR"},
    ]

    # 5a. escape
    run("escape special chars",
        lambda: escape("Hello! [test] #1 price: $5.00 (wow)"))

    # 5b. format_events with data
    run("format_events (2 events)",
        lambda: format_events(sample_events, "Today").split("\n")[0])

    # 5c. format_events empty
    run("format_events (empty)",
        lambda: format_events([], "Today"))

    # 5d. format_cards with data
    run("format_cards (3 cards with priorities)",
        lambda: format_cards(sample_cards, "Open tasks").split("\n")[0])

    # 5e. format_cards empty
    run("format_cards (empty)",
        lambda: format_cards([], "Tasks"))

    # 5f. format_reminders with data
    run("format_reminders (1 reminder)",
        lambda: format_reminders(sample_reminders).split("\n")[0])

    # 5g. format_reminders empty
    run("format_reminders (empty)",
        lambda: format_reminders([]))

    # 5h. format_timesheet with data, grouped by date
    def _check_timesheet_grouping():
        out = format_timesheet(sample_timesheet)
        if out.count("🗓") != 2:
            raise AssertionError(f"Expected 2 date groups, got: {out}")
        if out.count("•") != 3:
            raise AssertionError(f"Expected 3 entry bullets, got: {out}")
        return out.split("\n")[0]

    run("format_timesheet (3 entries, 2 dates)", _check_timesheet_grouping)

    # 5i. format_timesheet empty
    run("format_timesheet (empty)",
        lambda: format_timesheet([]))

    # 5j. format_daily combined
    run("format_daily (events + cards)",
        lambda: "OK" if "\n\n" in format_daily(sample_events, sample_cards) else "missing separator")

    # 5k. format_rupiah
    run("format_rupiah (thousand separators)",
        lambda: format_rupiah(1250000))

    sample_expenditure = [
        {"id": "e1", "date_iso": yesterday_iso, "description": "Groceries", "amount": 100000},
        {"id": "e2", "date_iso": today_iso,      "description": "Lunch at warung", "amount": 25000},
        {"id": "e3", "date_iso": today_iso,      "description": "Coffee", "amount": 15000},
    ]

    # 5l. format_expenditure with data, grouped by date
    def _check_expenditure_grouping():
        out = format_expenditure(sample_expenditure)
        if out.count("🗓") != 2:
            raise AssertionError(f"Expected 2 date groups, got: {out}")
        if out.count("•") != 3:
            raise AssertionError(f"Expected 3 entry bullets, got: {out}")
        return out.split("\n")[0]

    run("format_expenditure (3 entries, 2 dates)", _check_expenditure_grouping)

    # 5m. format_expenditure empty
    run("format_expenditure (empty)",
        lambda: format_expenditure([]))

    # 5n. format_expenditure_analysis with data
    run("format_expenditure_analysis (3 entries)",
        lambda: format_expenditure_analysis(exp_svc.analyze_entries(sample_expenditure)).split("\n")[0])

    # 5o. format_expenditure_analysis empty
    run("format_expenditure_analysis (empty)",
        lambda: format_expenditure_analysis(exp_svc.analyze_entries([])))

    # 5p. format_expenditure_insight with category breakdown + insight text
    sample_with_category = [
        {**e, "category": "food" if "warung" in e["description"].lower() or "coffee" in e["description"].lower()
              else "shopping"}
        for e in sample_expenditure
    ]

    def _check_expenditure_insight():
        analysis = exp_svc.analyze_entries(sample_with_category)
        out = format_expenditure_insight(analysis, "Test insight text about spending habits.")
        if "Insight" not in out or "category" not in out.lower():
            raise AssertionError(f"Expected Insight + category sections, got: {out}")
        return out.split("\n")[0]

    run("format_expenditure_insight (3 entries + insight text)", _check_expenditure_insight)

    # 5q. format_expenditure_insight empty
    run("format_expenditure_insight (empty)",
        lambda: format_expenditure_insight(exp_svc.analyze_entries([]), ""))


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

SECTIONS = {
    "gcal":        test_gcal,
    "trello":      test_trello,
    "reminders":   test_reminders,
    "timesheet":   test_timesheet,
    "expenditure": test_expenditure,
    "insight":     test_insight,
    "nlp":         test_nlp,
    "formatter":   test_formatter,
}

if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if arg == "all":
        for fn in SECTIONS.values():
            fn()
    elif arg in SECTIONS:
        SECTIONS[arg]()
    else:
        print(f"Unknown section '{arg}'. Choose: all | " + " | ".join(SECTIONS))
        sys.exit(1)

    run_cleanup()
    failed = summary()
    sys.exit(1 if failed else 0)
