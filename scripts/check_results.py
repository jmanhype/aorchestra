import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

report = json.load(open("results/evaluation_report.json"))
details = report["results"]["single"]["task_details"]
for t in details:
    score = t.get("score", 0)
    mark = "PASS" if score >= 1.0 else "FAIL"
    ans = str(t.get("answer", ""))[:80].replace("\n", " ")
    exp = str(t.get("expected", ""))[:40]
    task = t["task"]
    print(f"[{mark}] {task}")
    if mark == "FAIL":
        print(f"  got:      {ans}")
        print(f"  expected: {exp}")
