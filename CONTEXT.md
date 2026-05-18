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

**Tool Definition**:
A registered coaching capability schema that describes how the assistant may request work.
_Avoid_: Tool metadata, function schema

**Tool Call**:
A request from the assistant to run a registered coaching capability during a **Conversation**.
_Avoid_: Function call, raw call

**Tool Result**:
The persisted output produced by a **Tool Call** during a **Conversation**.
_Avoid_: Function output, raw result

## Relationships

- A **Conversation** contains zero or more **Tool Calls**
- A **Tool Call** conforms to exactly one **Tool Definition**
- A **Tool Call** may produce exactly one **Tool Result**

## Example dialogue

> **Dev:** "When the assistant asks to inspect replay history, is that a **Tool Definition** or a **Tool Call**?"
> **Domain expert:** "The registered replay query capability is the **Tool Definition**; the assistant's request inside a **Conversation** is the **Tool Call**, and the returned replay data is the **Tool Result**."

