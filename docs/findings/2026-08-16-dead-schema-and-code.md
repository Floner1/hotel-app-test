# Dead schema and code: findings for sign-off

**Date:** 2026-08-16
**Status:** nothing deleted, nothing changed. Peter decides each of these.

Four items from the bug report where the right answer is a product call, not a
patch. Every claim below was checked against the code rather than taken from
the report, and two of them came back different from what the report said.

---

## 1. `hotel_keys_main` and `room_maintenance_logs` (bug 8)

Both tables are created by `tables v10 for hotel.sql`, at lines 94 and 127.
Neither has a Django model, a repository, a view, a template, or a test.
A search across every `.py` and `.html` file under `site1/` for either table
name, or for any plausible model name, returns nothing at all, so these are
tables the application has never once read or written. `room_maintenance_logs`
is the more awkward of the two, because README.md line 226 lists it as a
working feature, "Reported maintenance issues per room," and it is not.
`hotel_keys_main` is not in the README's table list, and its shape (`key_id`,
`hotel_id`, `room_key`) suggests physical key tracking that was never started.
`room_maintenance_logs` is more considered: it has a status CHECK constraint of
open/in_progress/resolved, a `resolved_at`, and foreign keys to both `rooms`
and `users`, which is a designed feature someone stopped short of building.

**Recommendation:** build the maintenance log, delete the keys table. The
maintenance table already models the workflow properly, the room dashboard is
the obvious home for it, and the room modal now has a natural hook: the Out of
Order button is the moment a staff member knows what is wrong with a room and
has nowhere to write it down. Until it is built, correct README.md line 226 so
it stops describing a feature that does not exist. `hotel_keys_main` has no
design behind it and nothing referencing it, so it is a straight delete. If you
would rather not touch the schema at all, the cheapest honest option is to
leave both tables and fix only the README line.

## 2. `home.Notification` (bug 9)

Defined at `site1/home/models.py:7`. Nothing constructs, queries, updates or
deletes one anywhere in the app. The only other matches for the word
"Notification" are unrelated: `EmailQueue.EMAIL_TYPES` has an
`admin_notification` entry, `EmailService.queue_admin_notification` builds a
subject line, and three templates carry a "Toast Notification" comment above a
JavaScript and CSS component that has no connection to this model. Unlike the
`data/` models this one is managed, so `home/migrations/0005_notification_delete_hotel.py`
really does create a `home_notification` table on any database where someone
ran `migrate`. The README setup flow never runs `migrate`, so on a database
provisioned the documented way, the model, its migration and its table are all
inert together.

**Recommendation:** delete the model. It carries `message`, `created_at`,
`is_read` and `booking_id`, which is an in-app notification centre nobody
started, and the app already tells staff things through `django.contrib.messages`
and through `email_queue`. Deleting it means a new migration in `home/`, which
is a different risk from the `data/` migrations in item 3, because `home/`
migrations describe real Django-managed tables and are consistent with
themselves. Say the word and I will write it. If you want an in-app
notification centre later, it is better designed against the real requirement
than resurrected from this stub.

## 3. `site1/data/migrations/` (bug 10)

The report's description is right and its prediction is wrong, so this one
needs care. `0001_initial.py` does define `Hotel` with a `hotel_address` field
and `db_table='hotel'`. `0003` renamed the table to `hotel_info` and stopped
there. The live model at `site1/data/models/hotel.py:124` has `address`, not
`hotel_address`, and every field carries `null=True, blank=True` and
`max_length=225`, none of which any migration records. So the model and the
recorded migration state do disagree, exactly as reported.

What does not follow is the consequence. I ran `manage.py makemigrations
--check --dry-run` and the `Hotel` drift does not appear in the output at all.
Django's autodetector only emits create and delete operations for unmanaged
models and never field-level ones, and every model in `data/` is
`managed = False`. What it does report is four missing models: `DiscountCode`,
`EmailCampaign`, `EmailQueue` and `EmailSubscriber`, all added to the codebase
without migrations. So anyone running `makemigrations` today gets a `0009` that
tries to create four tables the schema file already creates, and hears nothing
about `hotel_address`.

**Recommendation:** leave the whole folder alone, and I have not touched it.
The team applies schema by hand from the `.sql` file and never runs `migrate`,
so these files are documentation of a history nobody replays. Editing them to
match reality buys nothing and risks a great deal, because `0006`, `0007` and
`0008` contain real `RunSQL` that a stray `migrate` would execute against a
live database. If you want the trap closed rather than documented, the useful
move is not a migration at all: it is a `MIGRATION_MODULES = {'data': None}`
entry in settings, or a note at the top of `0001_initial.py` saying the folder
is historical and the schema file is authoritative. Both are outside the file
scope I was given, so neither is done.

## 4. The `runserver` monkeypatch in `home/apps.py`

Left in place, and untouched. `HomeConfig.ready()` reaches into
`django.contrib.staticfiles`'s runserver command and rewrites `default_addr`
from `127.0.0.1` to `localhost`, for every contributor, on every start. The
existing comment is honest about why: something on one machine forces HTTPS on
bare IP literals but not on the hostname, and the author ruled out browser
settings, the system proxy and known TLS-intercepting processes without
identifying the culprit. That matches a note in my own memory of this project,
so the underlying problem is real and still current, not a stale workaround.

**Recommendation:** keep it, and narrow it rather than remove it. It is a
one-line default change with no runtime effect outside `runserver`, so the cost
of keeping it is close to zero, while removing it breaks the dev loop of the
one person it was written for until they rediscover why. The improvement worth
making is to make it conditional, so it stops being imposed on everyone: read
an environment variable, or check `DEBUG`, and only patch when asked. The task
brief also asked for a comment in `apps.py` explaining why removing it is not
safe without checking. **`apps.py` is on the read-only list, so I have not
added it.** Here is the text, ready to paste, if you want it in:

```python
        # Do not remove this without checking with whoever hits the HTTPS
        # problem first. It looks like a stray local workaround and it is not
        # dead: the machine it was written for still forces HTTPS on
        # 127.0.0.1 but not on localhost, and the cause was never identified.
        # Removing it breaks that dev loop with a confusing symptom. The right
        # change is to make it conditional, not to delete it.
```

---

## What is being asked of you

| Item | Options |
|---|---|
| `hotel_keys_main` | Delete it, or leave it |
| `room_maintenance_logs` | Build the feature, delete the table, or leave it and fix the README line |
| `home.Notification` | Delete the model and write the migration, or leave it |
| `data/migrations/` | Leave alone (recommended), or close the trap with a settings entry or a header note |
| `apps.py` patch | Keep as is, make it conditional, or add the comment above |
