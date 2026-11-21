import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import db

USERS = [
    ("advisor@autohub.local", "dealer123", "林顾问", "advisor"),
    ("manager@autohub.local", "dealer123", "周经理", "manager"),
    ("admin@autohub.local", "dealer123", "沈管理员", "admin"),
]
OWNERS = [
    ("OW-2401", "赵丽颖", "13800001001", "星越L", "沪A·7K21Q", "2027-01-20", "open", "phone", "徐汇"),
    ("OW-2402", "陈思远", "13800001002", "凯美瑞", "沪B·2M88P", "2026-12-18", "open", "wechat", "浦东"),
    ("OW-2403", "王月琴", "13800001003", "奥迪Q5L", "沪C·9R13T", "2027-02-08", "rejected", "phone", "闵行"),
    ("OW-2404", "李昊", "13800001004", "本田CR-V", "沪D·5H66K", "2026-11-02", "open", "sms", "静安"),
    ("OW-2405", "孙嘉怡", "13800001005", "奔驰C级", "沪E·1F09W", "2027-03-15", "open", "phone", "长宁"),
]
EVENTS = [
    ("OW-2401", "2026-10-28", 31800, "常规保养", 1680, 4.8, "林顾问", "更换机油与滤芯，车主关注延保"),
    ("OW-2401", "2026-06-14", 28600, "空调系统检查", 920, 4.7, "林顾问", "夏季前检查完成"),
    ("OW-2402", "2026-09-03", 45200, "常规保养", 2380, 4.1, "许顾问", "建议关注轮胎磨损"),
    ("OW-2402", "2026-02-18", 39800, "钣喷维修", 4860, 3.9, "许顾问", "右前门修复"),
    ("OW-2403", "2026-11-03", 52100, "事故维修", 12800, 4.4, "林顾问", "客户明确要求不再电话联系"),
    ("OW-2404", "2026-07-20", 21800, "常规保养", 1120, 4.6, "周顾问", "车辆保单已于本月初结束"),
    ("OW-2405", "2026-10-02", 60700, "大保养", 5620, 4.9, "林顾问", "客户询问置换和续保方案"),
]

with db() as conn:
    with conn.cursor() as cur:
        for email, password, name, role in USERS:
            cur.execute("INSERT INTO users(email,password,name,role,active) VALUES(%s,%s,%s,%s,1) ON DUPLICATE KEY UPDATE password=VALUES(password),name=VALUES(name),role=VALUES(role),active=1", (email,password,name,role))
        for row in OWNERS:
            cur.execute("INSERT INTO owners(owner_code,name,phone,vehicle_model,plate_no,policy_expires,contact_status,preferred_channel,region) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE name=VALUES(name),phone=VALUES(phone),vehicle_model=VALUES(vehicle_model),plate_no=VALUES(plate_no),policy_expires=VALUES(policy_expires),contact_status=VALUES(contact_status),preferred_channel=VALUES(preferred_channel),region=VALUES(region)", row)
        for owner_code, service_date, mileage, service_type, amount, satisfaction, advisor_name, notes in EVENTS:
            owner_id = cur.execute("SELECT id FROM owners WHERE owner_code=%s", (owner_code,))
            owner = cur.fetchone()
            cur.execute("INSERT INTO service_events(owner_id,service_date,mileage,service_type,amount,satisfaction,advisor_name,notes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE mileage=VALUES(mileage),amount=VALUES(amount),satisfaction=VALUES(satisfaction),advisor_name=VALUES(advisor_name),notes=VALUES(notes)", (owner["id"], service_date, mileage, service_type, amount, satisfaction, advisor_name, notes))
        for code, status in [("OW-2401", "predicted"), ("OW-2402", "predicted"), ("OW-2403", "frozen"), ("OW-2404", "expired"), ("OW-2405", "predicted")]:
            owner = cur.execute("SELECT id FROM owners WHERE owner_code=%s", (code,))
            owner_row = cur.fetchone()
            cur.execute("INSERT INTO renewal_leads(owner_id,score,status,feature_contrib) VALUES(%s,0,%s,'[]') ON DUPLICATE KEY UPDATE status=VALUES(status)", (owner_row["id"], status))
print("seed_demo ok: users=3 owners=5 service_events=7 leads=5")
