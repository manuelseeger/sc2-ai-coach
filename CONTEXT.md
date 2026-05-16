# SC2 AI Coach Admin Data

This context covers the persisted coaching data that operators inspect through the standalone admin API and webapp. It defines the domain objects the admin surface is built around and the relationships that make those objects useful together.

## Language

**Replay**:
A recorded StarCraft II game used as the primary source of match facts.
_Avoid_: Match document, replay row

**Metadata**:
Operator-authored or derived annotations attached to exactly one **Replay**.
_Avoid_: Replay extras, notes blob

**Player**:
A known StarCraft II identity represented by a toon handle, aliases, and portrait assets.
_Avoid_: User, account

**Session**:
A coaching run that groups related **Conversations** and accumulates usage totals.
_Avoid_: Thread, chat session

**Conversation**:
A persisted coaching exchange tied to a trigger and optionally linked to a **Session** and a **Replay**.
_Avoid_: Thread, transcript

