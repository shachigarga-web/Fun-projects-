# Gmail Inbox Organizer

A free Google Apps Script that runs inside your own Google account. Every 15
minutes it sorts your inbox into labels and archives the noise. Once a day it
emails you a short digest of what actually needs your attention.

No servers, no third-party apps, and nothing is ever deleted. Archived mail
stays searchable under its label.

## What it does

The rules are built for a busy job search:

| Label | What goes there | Stays in inbox? | Marked read? |
|---|---|---|---|
| **Job Hunt/Action Needed** | Interviews, assessments, "next steps", phone screens, video screens (SparkHire, HireVue, ...), offers. Also pulls these out of the **Tsenta** and **AI APPLY** labels, so forwarded interview invites don't get buried. | Yes | No |
| **Job Hunt/Rejections** | "Unfortunately...", "other candidates", "not selected", ... | No | No |
| **Job Hunt/Applied** | "Thanks for applying", application copies, EEO forms | No | Yes |
| **Job Hunt/Job Alerts** | Job recommendation emails (LinkedIn, Indeed, company career sites) | No | Yes |
| **Codes** | Verification or security codes older than a day | No | Yes |
| **Security** | Google account alerts, new sign-ins, password changes | Yes | No |
| **Receipts** | Receipts, invoices, subscription renewals | No | No |
| **Job Hunt/Tool Updates** | Anything else from AI Apply / Tsenta | No | Yes |
| **Promotions** | Gmail's Promotions/Social/Forums tabs, newsletters | No | Yes |
| **Old Unread** | Anything still unread in the inbox after 30 days | No | No |

Rules run top to bottom, and the first match wins. An email that mentions an
interview is never archived by a later rule, and neither is anything you
starred.

**Daily digest** (8am): your inbox unread count, a clickable list of unread
**Action Needed** emails, and how many emails went into each label. Mark an
Action Needed email as read once you've dealt with it, and it drops off the
next digest.

## Setup (about 5 minutes)

1. Go to <https://script.google.com> and click **New project**.
2. Delete the sample code, then paste in everything from [`Code.gs`](Code.gs).
3. Click the project name at the top and rename it to `Inbox Organizer`.
4. **Optional, recommended first:** set `DRY_RUN: true` near the top, choose
   `organizeInbox` in the function dropdown, and click **Run**. Open
   **Executions** in the left sidebar to see what it *would* do. Set it back to
   `false` when you're happy.
5. In the function dropdown, choose **`setup`** and click **Run**.
6. Google will ask for permission. Click **Review permissions**, choose your
   account, then **Advanced > Go to Inbox Organizer (unsafe)** > **Allow**.
   The "unsafe" warning appears because this is your own script and Google
   hasn't reviewed it. It only runs in your account.

That's it. `setup` does a first pass immediately and schedules the rest.
A backlog of a few thousand emails is cleared over the first hour or so,
because Apps Script limits each run to 6 minutes.

## Customizing

Everything lives at the top of `Code.gs`:

- **`SETTINGS`**: dry-run mode, how old unread mail must be before it's swept
  into Old Unread (`STALE_AFTER_DAYS`, 0 turns it off), run frequency, digest
  hour.
- **`RULES`**: each rule is a normal Gmail search. To test a rule, paste its
  `query` into the Gmail search box and check the results. To add a rule, copy
  an existing one, change the `label` and `query`, and put it where it should
  rank.

Example: keep all mail from a recruiter you're talking to in the inbox, flagged:

```js
{
  label: 'Job Hunt/Action Needed',
  query: 'from:(recruiter@company.com)',
  archive: false,
  markRead: false,
},
```

(Put it at the top of `RULES`.)

## Undo / uninstall

- **Stop it:** run `teardown`. Schedules are removed, and your labels and mail
  stay as they are.
- **Put something back:** open its label, select the emails, and click
  **Move to Inbox**.
- **Remove everything:** run `teardown`, delete the labels in Gmail (this only
  removes the labels, not the emails), then delete the Apps Script project.

## Heads-up

Rules match on keywords, so they won't be perfect. For example, a recruiter
email that says "unfortunately I need to reschedule" lands in Rejections. For
the first week, glance at **Rejections** and **Old Unread** now and then. If
something is consistently mis-sorted, adjust that rule's query.
