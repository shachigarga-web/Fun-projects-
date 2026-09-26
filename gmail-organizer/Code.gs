/**
 * Gmail Inbox Organizer (Google Apps Script)
 *
 * Sorts your inbox into labels, archives the noise, and emails you a short
 * daily digest listing what still needs your attention.
 *
 * Setup: paste this file into https://script.google.com, then run `setup` once.
 * See README.md for step-by-step instructions.
 */

// ---------------------------------------------------------------------------
// Settings. Edit these to change how the organizer behaves.
// ---------------------------------------------------------------------------

const SETTINGS = {
  // true = only log what would happen (View > Executions). Nothing is changed.
  DRY_RUN: false,

  // Unread inbox mail older than this many days is moved to "Old Unread".
  // Set to 0 to turn this off.
  STALE_AFTER_DAYS: 30,

  // How often the organizer runs, and the hour (0-23) the daily digest is sent.
  RUN_EVERY_MINUTES: 15,
  DIGEST_HOUR: 8,

  // Apps Script stops a run after 6 minutes, so we finish before that.
  MAX_RUNTIME_MS: 4.5 * 60 * 1000,
  BATCH_SIZE: 100,
};

// Job tools that forward employer email to you. Their mail is sorted by what
// it says (interview, rejection, ...) like any other email.
const JOB_TOOL_SENDERS = 'aiapplynotif.com OR aiapplymail.com OR aiapply.co OR tsenta.com';

/**
 * Rules run top to bottom. Each rule is a normal Gmail search (the same text
 * you would type in the Gmail search box). The first matching rule wins,
 * because anything archived by an earlier rule is no longer in the inbox.
 *
 *   label        label to apply (use "/" for nested labels)
 *   query        Gmail search that picks the emails
 *   archive      remove from the inbox (still findable under the label)
 *   markRead     mark as read
 *   scope        where to look (default: the inbox)
 *   moveToInbox  bring matches back into the inbox
 */
const RULES = [
  {
    // Interviews, assessments, video screens, offers: the emails that matter.
    // Also checks the Tsenta and AI APPLY labels, since those tools forward
    // real interview invites that would otherwise never reach your inbox.
    label: 'Job Hunt/Action Needed',
    query:
      'newer_than:30d (subject:(interview OR assessment OR "next step" OR ' +
      '"next steps" OR "phone screen" OR "your availability" OR ' +
      '"schedule a call" OR "job offer" OR "offer letter") OR ' +
      'from:(sparkhire.com OR hirevue.com OR calendly.com OR codesignal.com ' +
      'OR hackerrank.com OR testgorilla.com OR willo.video OR predictiveindex.com)) ' +
      '-category:promotions',
    scope: '{in:inbox label:tsenta label:ai-apply}',
    moveToInbox: true,
    archive: false,
    markRead: false,
  },
  {
    label: 'Job Hunt/Rejections',
    query:
      '"unfortunately" OR "regret to inform" OR "not to move forward" OR ' +
      '"not be moving forward" OR "not moving forward" OR ' +
      '"other candidates" OR "not been selected" OR "not selected" OR ' +
      '"position has been filled" OR "since filled" OR "wasn\'t a yes" OR ' +
      '"do not match"',
    archive: true,
    markRead: false,
  },
  {
    // "Thanks for applying", application copies, EEO forms.
    label: 'Job Hunt/Applied',
    query:
      'subject:("thanks for applying" OR "thank you for applying" OR ' +
      '"thank you for your application" OR "application received" OR ' +
      '"received your application" OR "received your resume" OR ' +
      '"your application for" OR "EEO survey" OR "form to complete") OR ' +
      '"received your application" OR "thank you for applying" OR ' +
      '"thanks for applying"',
    archive: true,
    markRead: true,
  },
  {
    label: 'Job Hunt/Job Alerts',
    query:
      'subject:("job alert" OR "jobs for you" OR "new job opportunities" OR ' +
      '"latest jobs" OR "recommended jobs" OR "jobs you may be interested") OR ' +
      'from:(jobalerts-noreply@linkedin.com OR indeed.com OR ziprecruiter.com ' +
      'OR glassdoor.com OR jobs2web.com)',
    archive: true,
    markRead: true,
  },
  {
    // One-time codes are only useful for a few minutes; tidy them after a day.
    label: 'Codes',
    query:
      'older_than:1d subject:("verification code" OR "security code" OR ' +
      '"one-time" OR "login code" OR "confirm your email")',
    archive: true,
    markRead: true,
  },
  {
    // Account alerts stay in the inbox so you notice them.
    label: 'Security',
    query:
      'from:(accounts.google.com OR noreply-accounts@google.com) OR ' +
      'subject:("security alert" OR "new sign-in" OR "password")',
    archive: false,
    markRead: false,
  },
  {
    label: 'Receipts',
    query:
      'subject:(receipt OR invoice OR "order confirmation" OR "payment received" ' +
      'OR renews OR subscription)',
    archive: true,
    markRead: false,
  },
  {
    // Whatever the job tools send that didn't match anything above.
    label: 'Job Hunt/Tool Updates',
    query: 'from:(' + JOB_TOOL_SENDERS + ')',
    archive: true,
    markRead: true,
  },
  {
    label: 'Promotions',
    query:
      'category:promotions OR category:social OR category:forums OR ' +
      'from:(newsletter OR newsletters OR marketing OR deals OR promo)',
    archive: true,
    markRead: true,
  },
];

// ---------------------------------------------------------------------------
// Entry points (run these from the Apps Script editor).
// ---------------------------------------------------------------------------

/** Run once: creates labels, installs the schedules, and does a first pass. */
function setup() {
  allRules_().forEach(function (rule) { getOrCreateLabel_(rule.label); });
  teardown();
  ScriptApp.newTrigger('organizeInbox')
    .timeBased().everyMinutes(SETTINGS.RUN_EVERY_MINUTES).create();
  ScriptApp.newTrigger('sendDigest')
    .timeBased().everyDays(1).atHour(SETTINGS.DIGEST_HOUR).create();
  Logger.log('Schedules installed. Running a first pass now...');
  organizeInbox();
}

/** Removes the schedules. Your labels and emails are left as they are. */
function teardown() {
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    const fn = trigger.getHandlerFunction();
    if (fn === 'organizeInbox' || fn === 'sendDigest') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

/**
 * Applies every rule to the inbox. Safe to run as often as you like: it works
 * through a large backlog a few hundred threads at a time and picks up where
 * it left off on the next run.
 */
function organizeInbox() {
  const started = Date.now();
  const counts = {};

  for (const rule of allRules_()) {
    const label = SETTINGS.DRY_RUN ? null : getOrCreateLabel_(rule.label);
    const query = buildQuery_(rule);
    let processed = 0;

    while (Date.now() - started < SETTINGS.MAX_RUNTIME_MS) {
      const threads = GmailApp.search(query, 0, SETTINGS.BATCH_SIZE);
      if (threads.length === 0) break;

      if (SETTINGS.DRY_RUN) {
        Logger.log('[dry run] %s: %s+ threads, e.g. "%s"',
          rule.label, threads.length, threads[0].getFirstMessageSubject());
        processed += threads.length;
        break;
      }

      label.addToThreads(threads);
      if (rule.moveToInbox) GmailApp.moveThreadsToInbox(threads);
      if (rule.markRead) GmailApp.markThreadsRead(threads);
      if (rule.archive) GmailApp.moveThreadsToArchive(threads);
      processed += threads.length;
    }

    if (processed > 0) {
      counts[rule.label] = processed;
      Logger.log('%s: %s threads', rule.label, processed);
    }
  }

  if (!SETTINGS.DRY_RUN) addToDigestCounts_(counts);
  if (Date.now() - started >= SETTINGS.MAX_RUNTIME_MS) {
    Logger.log('Out of time for this run; the next run will continue.');
  }
}

/** Emails you a summary: what needs action, and what was tidied away. */
function sendDigest() {
  const props = PropertiesService.getUserProperties();
  const counts = JSON.parse(props.getProperty('digestCounts') || '{}');
  const actionLabel = RULES[0].label;
  const actionThreads = GmailApp.search(
    'label:' + labelToSearchName_(actionLabel) + ' is:unread', 0, 25);
  const inboxUnread = GmailApp.getInboxUnreadCount();

  let html = '<div style="font-family:Arial,sans-serif;font-size:14px">';
  html += '<h2 style="margin:0 0 8px">Your inbox digest</h2>';
  html += '<p>Unread in inbox: <b>' + inboxUnread + '</b></p>';

  html += '<h3>Needs your attention (' + actionThreads.length + ')</h3>';
  if (actionThreads.length === 0) {
    html += '<p>Nothing waiting on you.</p>';
  } else {
    html += '<ul>';
    actionThreads.forEach(function (t) {
      const url = 'https://mail.google.com/mail/u/0/#all/' + t.getId();
      html += '<li><a href="' + url + '">' + escapeHtml_(t.getFirstMessageSubject()) +
        '</a> <span style="color:#666">(' + formatDate_(t.getLastMessageDate()) +
        ')</span></li>';
    });
    html += '</ul>';
  }

  const labels = Object.keys(counts);
  html += '<h3>Sorted since the last digest</h3>';
  if (labels.length === 0) {
    html += '<p>Nothing new.</p>';
  } else {
    html += '<table cellpadding="4">';
    labels.sort(function (a, b) { return counts[b] - counts[a]; }).forEach(function (name) {
      html += '<tr><td>' + escapeHtml_(name) + '</td><td align="right"><b>' +
        counts[name] + '</b></td></tr>';
    });
    html += '</table>';
  }
  html += '</div>';

  const me = Session.getEffectiveUser().getEmail();
  GmailApp.sendEmail(me, 'Inbox digest: ' + actionThreads.length + ' need attention',
    'Open this email in Gmail to see the digest.', { htmlBody: html, name: 'Inbox Organizer' });
  props.deleteProperty('digestCounts');
}

// ---------------------------------------------------------------------------
// Helpers.
// ---------------------------------------------------------------------------

/** RULES plus the optional "Old Unread" sweep, which always runs last. */
function allRules_() {
  const rules = RULES.slice();
  if (SETTINGS.STALE_AFTER_DAYS > 0) {
    rules.push({
      label: 'Old Unread',
      query: 'is:unread older_than:' + SETTINGS.STALE_AFTER_DAYS + 'd',
      archive: true,
      markRead: false,
    });
  }
  return rules;
}

/**
 * Limits a rule to the inbox and skips threads it already handled. Rules that
 * archive also skip starred mail and anything a keep-in-inbox rule labeled
 * (so an interview email is never archived by a later, broader rule).
 */
function buildQuery_(rule) {
  const parts = [rule.scope || 'in:inbox', '(' + rule.query + ')',
    '-label:' + labelToSearchName_(rule.label)];
  if (rule.archive) {
    parts.push('-is:starred');
    RULES.forEach(function (other) {
      if (!other.archive) parts.push('-label:' + labelToSearchName_(other.label));
    });
  }
  return parts.join(' ');
}

/** Gmail search wants "Job Hunt/Applied" written as "job-hunt-applied". */
function labelToSearchName_(name) {
  return name.toLowerCase().replace(/[\s\/]+/g, '-');
}

/** Creates the label, and any parent labels, if they don't exist yet. */
function getOrCreateLabel_(name) {
  const parts = name.split('/');
  let label = null;
  for (let i = 1; i <= parts.length; i++) {
    const path = parts.slice(0, i).join('/');
    label = GmailApp.getUserLabelByName(path) || GmailApp.createLabel(path);
  }
  return label;
}

function addToDigestCounts_(counts) {
  if (Object.keys(counts).length === 0) return;
  const lock = LockService.getUserLock();
  lock.waitLock(10000);
  try {
    const props = PropertiesService.getUserProperties();
    const totals = JSON.parse(props.getProperty('digestCounts') || '{}');
    Object.keys(counts).forEach(function (name) {
      totals[name] = (totals[name] || 0) + counts[name];
    });
    props.setProperty('digestCounts', JSON.stringify(totals));
  } finally {
    lock.releaseLock();
  }
}

function formatDate_(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), 'MMM d');
}

function escapeHtml_(text) {
  return String(text || '(no subject)')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
