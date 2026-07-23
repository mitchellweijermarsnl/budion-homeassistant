"""Birthday helpers for Budion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEvent


@dataclass(frozen=True)
class BirthdayPerson:
    """Someone with a known birth date."""

    key: str
    name: str
    birth_date: date
    birth_year_known: bool
    source: str


@dataclass
class BirthdayEntry:
    """An upcoming birthday occurrence."""

    key: str
    name: str
    birth_date: date
    next_occurrence: date
    days_until: int
    age: int | None
    source: str


def parse_date(value: str | None) -> date | None:
    """Parse an ISO date string."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def occurrence_on_year(birth: date, year: int) -> date:
    """Return the birthday date in a given calendar year."""
    try:
        return birth.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def next_occurrence(birth: date, *, today: date) -> tuple[date, int]:
    """Return the next birthday date and the age they will turn."""
    candidate = occurrence_on_year(birth, today.year)

    if candidate < today:
        candidate = occurrence_on_year(birth, today.year + 1)

    age = candidate.year - birth.year
    return candidate, age


def collect_birthday_people(
    contacts: list[dict[str, Any]],
    members: list[dict[str, Any]],
) -> list[BirthdayPerson]:
    """Collect everyone with a birth date from contacts and family members."""
    people: list[BirthdayPerson] = []

    for contact in contacts:
        birth = parse_date(contact.get("birth_date"))
        if birth is None:
            continue
        people.append(
            BirthdayPerson(
                key=f"contact-{contact['id']}",
                name=contact.get("full_name") or contact.get("first_name", "Onbekend"),
                birth_date=birth,
                birth_year_known=contact.get("birth_year_known", True),
                source="contact",
            )
        )

    for member in members:
        person = member.get("person") or {}
        birth = parse_date(person.get("birth_date"))
        if birth is None or person.get("id") is None:
            continue
        people.append(
            BirthdayPerson(
                key=f"member-{person['id']}",
                name=person.get("full_name") or person.get("first_name", "Onbekend"),
                birth_date=birth,
                birth_year_known=True,
                source="member",
            )
        )

    people.sort(key=lambda item: (item.birth_date.month, item.birth_date.day, item.name))
    return people


def upcoming_birthdays(
    people: list[BirthdayPerson],
    *,
    today: date | None = None,
    horizon_days: int = 365,
) -> list[BirthdayEntry]:
    """Return upcoming birthday occurrences within a horizon."""
    if today is None:
        today = date.today()

    entries: list[BirthdayEntry] = []

    for person in people:
        occurrence, age = next_occurrence(person.birth_date, today=today)
        days_until = (occurrence - today).days
        if days_until > horizon_days:
            continue
        entries.append(
            BirthdayEntry(
                key=person.key,
                name=person.name,
                birth_date=person.birth_date,
                next_occurrence=occurrence,
                days_until=days_until,
                age=age if person.birth_year_known else None,
                source=person.source,
            )
        )

    entries.sort(key=lambda item: (item.next_occurrence, item.name))
    return entries


def group_upcoming_by_date(entries: list[BirthdayEntry]) -> list[tuple[date, list[BirthdayEntry]]]:
    """Group upcoming birthdays by their next occurrence date."""
    grouped: dict[date, list[BirthdayEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.next_occurrence, []).append(entry)

    return sorted(grouped.items(), key=lambda item: item[0])


def format_upcoming_summary(entries: list[BirthdayEntry]) -> str | None:
    """Format the next birthday date with all names on that day."""
    if not entries:
        return None

    grouped = group_upcoming_by_date(entries)
    next_date, day_entries = grouped[0]
    names = ", ".join(entry.name for entry in day_entries)
    days_until = (next_date - date.today()).days

    if days_until == 0:
        return names
    if len(day_entries) == 1:
        return f"{names} ({days_until}d)"
    return f"{names} ({days_until}d, {len(day_entries)})"


def birthday_events_in_range(
    people: list[BirthdayPerson],
    start_date: datetime,
    end_date: datetime,
) -> list[CalendarEvent]:
    """Build calendar events for all birthdays within a datetime range."""
    start = start_date.date()
    end = end_date.date()
    events: list[CalendarEvent] = []

    for person in people:
        for year in range(start.year, end.year + 1):
            occurrence = occurrence_on_year(person.birth_date, year)
            if occurrence < start or occurrence > end:
                continue

            age = None
            if person.birth_year_known:
                age = year - person.birth_date.year

            summary = person.name
            if age is not None:
                summary = f"{person.name} ({age})"

            description_parts = [f"Verjaardag van {person.name}"]
            if age is not None:
                description_parts.append(f"Wordt {age}")
            description_parts.append(
                f"Geboren op {person.birth_date.strftime('%d-%m')}"
                if not person.birth_year_known
                else f"Geboren op {person.birth_date.strftime('%d-%m-%Y')}"
            )

            events.append(
                CalendarEvent(
                    uid=f"{person.key}-{year}",
                    summary=summary,
                    start=occurrence,
                    end=occurrence + timedelta(days=1),
                    description=" · ".join(description_parts),
                )
            )

    events.sort(key=lambda event: (event.start, event.summary or ""))
    return events
