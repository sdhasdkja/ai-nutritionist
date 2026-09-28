"""端到端 API 测试脚本"""
import json
import time
import urllib.request

BASE = "http://localhost:8000/api"
PY = None


def req(method, path, data=None, token=None, timeout=300):
    url = BASE + path
    headers = {}
    body = None
    if data is not None:
        if isinstance(data, dict) and path == "/auth/login":
            body = "&".join(f"{k}={v}" for k, v in data.items()).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# 1. 登录
t0 = time.time()
login = req("POST", "/auth/login", {"username": "admin", "password": "admin123"})
token = login["access_token"]
print(f"[1] 登录 OK ({time.time()-t0:.1f}s)")

# 2. 创建健康报告
report = req("POST", "/health-reports", {
    "report_name": "2026年9月年度体检",
    "report_content": "体检日期：2026-09-01\n空腹血糖 6.8 mmol/L\n血压 128/82 mmHg\n血尿酸 468 μmol/L\n总胆固醇 5.1 mmol/L\n甘油三酯 2.3 mmol/L",
}, token=token)
print(f"[2] 报告创建 OK id={report['id']}")
print(f"    解析: {report['analysis_result']['summary']}")
for ind in report["analysis_result"]["indicators"]:
    print(f"    - {ind['name']}: {ind['value']}{ind['unit']} [{ind['status']}]")

# 3. 添加偏好（幂等跳过已存在）
try:
    req("POST", "/preferences", {"preference_type": "allergy", "preference_value": "花生"}, token=token)
    req("POST", "/preferences", {"preference_type": "cuisine", "preference_value": "川菜"}, token=token)
    print("[3] 偏好添加 OK")
except Exception as e:
    print(f"[3] 偏好已存在: {e}")

prefs = req("GET", "/preferences", token=token)
print(f"    当前偏好: {[p['preference_value'] for p in prefs]}")

# 4. AI生成食谱（多Agent工作流，约1-2分钟）
print("[4] 开始AI生成食谱（4个Agent接力+审核回环，预计1-2分钟）...")
t0 = time.time()
recipe = req("POST", "/recipes/generate", {"health_report_id": report["id"]}, token=token, timeout=300)
elapsed = time.time() - t0
print(f"    生成完成！耗时 {elapsed:.0f}s")
print(f"    食谱ID: {recipe['id']} | 状态: {recipe['status']} | 总热量: {recipe['total_calories']}kcal")
print(f"    审核轮次: {recipe['nutrition_info'].get('iterations')}")
print(f"    --- 前400字 ---")
print("   " + recipe["description"][:400].replace("\n", "\n   "))

# 5. 列表验证
recipes = req("GET", "/recipes", token=token)
reports = req("GET", "/health-reports", token=token)
print(f"[5] 列表验证: {len(recipes)}个食谱, {len(reports)}份报告")
print("=== 端到端测试全部通过 ===")
