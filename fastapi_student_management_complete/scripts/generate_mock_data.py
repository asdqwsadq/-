"""
学生信息管理系统 - 模拟数据自动生成脚本（HTTP API 版）

用法:
  1. 先启动服务:  uvicorn app.main:app --reload --port 8000
  2. 运行本脚本: python scripts/generate_mock_data.py [学生数量]
     默认生成 50 条，例如: python scripts/generate_mock_data.py 100

说明:
  通过 HTTP API 接口写入数据（与前端走同一套认证+验证流程），
  数据生成后刷新页面即可看到，无需重启服务。
"""

import random
import sys
import time
import requests

# ==================== 配置 ====================

API_BASE = "http://127.0.0.1:8000"
USERNAME = "admin"
PASSWORD = "123456"

BATCH_SIZE = 20   # 每批提交数量（避免请求过大）
DELAY = 0.05      # 批次间延迟（秒）

# ==================== 模拟数据源 ====================

SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "高",
    "郑", "梁", "谢", "宋", "唐", "许", "邓", "冯", "韩", "曹",
    "曾", "彭", "萧", "蔡", "潘", "田", "董", "袁", "于", "余",
    "叶", "蒋", "杜", "苏", "魏", "程", "吕", "丁", "沈", "任",
]

GIVEN_NAMES_MALE = [
    "伟", "强", "磊", "军", "勇", "杰", "涛", "明", "超", "华",
    "刚", "辉", "鹏", "斌", "波", "宇", "浩", "凯", "健", "俊",
    "峰", "龙", "鑫", "亮", "建国", "建军", "志强", "志伟", "海涛",
]

GIVEN_NAMES_FEMALE = [
    "芳", "娟", "敏", "静", "丽", "艳", "娜", "秀英", "燕", "玲",
    "雪", "婷", "莉", "欣", "颖", "萍", "红", "琳", "倩", "慧",
    "佳", "璐", "莹", "洁", "文静", "雅琴", "梦瑶", "诗涵", "雨桐",
]

MAJORS = [
    "计算机科学与技术", "软件工程", "人工智能", "数据科学", "网络工程",
    "电子信息工程", "通信工程", "自动化", "机械工程", "土木工程",
    "工商管理", "会计学", "金融学", "国际经济与贸易", "市场营销",
    "英语", "法学", "数学与应用数学", "物理学", "化学工程与工艺",
]

DEPARTMENTS = [
    "信息科学与工程学院", "机电工程学院", "土木建筑工程学院",
    "经济管理学院", "外国语学院", "理学院", "人文社科学院",
    "艺术学院", "医学院", "教育学院",
]

TEACHER_TITLES = ["教授", "副教授", "讲师", "助教"]

COURSE_LISTS = {
    "计算机": ["数据结构", "算法分析", "操作系统", "计算机网络", "编译原理", "数据库系统"],
    "软件工程": ["软件需求工程", "软件架构设计", "软件测试", "敏捷开发", "DevOps实践"],
    "人工智能": ["机器学习", "深度学习", "自然语言处理", "计算机视觉", "神经网络与深度学习"],
    "数据科学": ["数据挖掘", "大数据技术", "统计分析", "Python数据分析", "数据可视化"],
    "电子": ["信号与系统", "数字信号处理", "嵌入式系统", "电路原理", "电磁场与电磁波"],
    "机械": ["机械设计基础", "工程力学", "材料力学", "流体力学", "热力学基础"],
    "工商": ["管理学原理", "组织行为学", "战略管理", "人力资源管理", "项目管理"],
    "会计": ["财务会计", "管理会计", "审计学", "税法", "财务管理"],
    "英语": ["综合英语", "英美文学", "翻译理论与实践", "语言学导论", "跨文化交际"],
    "法学": ["法理学", "宪法学", "刑法学", "民法学", "诉讼法学"],
}

COMPANIES = [
    "华为技术有限公司", "阿里巴巴集团", "腾讯科技有限公司", "字节跳动",
    "百度在线网络技术", "京东集团", "美团", "滴滴出行",
    "小米科技", "网易公司", "蚂蚁金服", "拼多多", "快手科技",
    "中国银行", "中国工商银行", "中国移动", "国家电网", "中石化",
    "比亚迪股份有限公司", "大疆创新科技", "商汤科技", "旷视科技",
]

POSITIONS = [
    "软件工程师", "前端开发工程师", "后端开发工程师", "算法工程师",
    "产品经理", "数据分析师", "测试工程师", "运维工程师",
    "UI设计师", "项目经理", "人事专员", "财务分析师",
    "市场专员", "销售经理", "管培生", "研发工程师",
]

EMPLOYMENT_STATUSES = ["已入职", "试用期", "已录用", "待入职"]


# ==================== 工具函数 ====================

def generate_name(gender: str) -> str:
    surname = random.choice(SURNAMES)
    given = random.choice(GIVEN_NAMES_MALE if gender == "男" else GIVEN_NAMES_FEMALE)
    return surname + given


def generate_phone() -> str:
    prefixes = ["138", "139", "150", "151", "152", "158", "159", "186", "187", "188"]
    return random.choice(prefixes) + "".join(random.choices("0123456789", k=8))


def generate_email(name: str) -> str:
    domains = ["qq.com", "163.com", "gmail.com", "outlook.com", "edu.cn"]
    username = f"{name}{random.randint(1, 999)}".lower()
    return f"{username}@{random.choice(domains)}"


def generate_student_no(index: int, year: int) -> str:
    major_code = random.randint(10, 99)
    class_seq = random.randint(1, 5)
    return f"{year}{major_code}{class_seq:02d}{index:03d}"


class APIClient:
    """HTTP API 客户端，封装登录认证和 CRUD 操作"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()

    def login(self, username: str, password: str) -> bool:
        """登录获取 token"""
        resp = self.session.post(
            f"{self.base_url}/api/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            self.token = resp.json()["token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "X-Token": self.token,
                "Content-Type": "application/json",
            })
            return True
        print(f"  [ERROR] 登录失败: {resp.json().get('detail', resp.text)}")
        return False

    def _post(self, endpoint: str, payload: dict) -> dict | None:
        """POST 创建资源"""
        resp = self.session.post(f"{self.base_url}{endpoint}", json=payload, timeout=15)
        if resp.status_code in (200, 201):
            return resp.json()
        error_detail = resp.json().get("detail", resp.text) if resp.status_code != 204 else ""
        # 学号/编码重复等错误仅跳过不中断
        if resp.status_code == 400 and ("已存在" in str(error_detail) or "duplicate" in str(error_detail).lower()):
            return None
        print(f"  [WARN] POST {endpoint} 失败 ({resp.status_code}): {error_detail}")
        return None

    def _post_batch(self, endpoint: str, items: list[dict], label: str = "") -> list:
        """批量提交 POST 请求"""
        results = []
        total = len(items)
        for i in range(0, total, BATCH_SIZE):
            batch = items[i : i + BATCH_SIZE]
            ok_count = 0
            for item in batch:
                result = self._post(endpoint, item)
                if result is not None:
                    results.append(result)
                    ok_count += 1
            time.sleep(DELAY)

        print(f"  [OK] {label}: 成功 {len(results)}/{total} 条")
        return results

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


# ==================== 数据生成函数 ====================

def build_teachers(count: int) -> list[dict]:
    """构造教师数据字典列表"""
    used_names = set()
    items = []
    for _ in range(count):
        gender = random.choice(["男", "女"])
        name = generate_name(gender)
        while name in used_names:
            name = generate_name(gender)
        used_names.add(name)
        items.append({
            "name": name,
            "title": random.choice(TEACHER_TITLES),
            "department": random.choice(DEPARTMENTS),
            "phone": generate_phone(),
            "email": f"{name.lower()}@university.edu.cn",
        })
    return items


def build_students(count: int) -> list[dict]:
    """构造学生数据字典列表"""
    year = random.choice([2021, 2022, 2023, 2024])
    items = []
    for i in range(1, count + 1):
        gender = random.choice(["男", "女"])
        name = generate_name(gender)
        major = random.choice(MAJORS)
        enrollment = f"{year}-09-{random.randint(1, 28):02d}"
        items.append({
            "student_no": generate_student_no(i, year),
            "name": name,
            "gender": gender,
            "age": random.randint(18, 26),
            "major": major,
            "phone": generate_phone(),
            "email": generate_email(name),
            "enrollment_date": enrollment,
        })
    return items


def build_courses(teacher_names: list[str]) -> list[dict]:
    """根据教师名单构造课程数据字典列表"""
    items = []
    codes_used = set()
    for course_list in COURSE_LISTS.values():
        for course_name in course_list:
            prefix = "".join(c for c in course_name if c.isalpha())[:3].upper()
            code = f"{prefix}{random.randint(100, 999)}"
            while code in codes_used:
                code = f"{prefix}{random.randint(100, 999)}"
            codes_used.add(code)
            items.append({
                "code": code,
                "name": course_name,
                "teacher_name": random.choice(teacher_names),
                "credit": round(random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]), 1),
            })
    return items


def build_classes(count: int) -> list[dict]:
    """构造班级数据字典列表"""
    grades = ["2021级", "2022级", "2023级", "2024级"]
    items = []
    for i in range(count):
        major = random.choice(MAJORS[:6])
        grade = random.choice(grades)
        items.append({
            "name": f"{grade} {major} {i + 1}班",
            "grade": grade,
            "major": major,
            "head_teacher": generate_name(random.choice(["男", "女"])),
            "student_count": random.randint(25, 50),
        })
    return items


def build_grades(students: list[dict], course_names: list[str]) -> list[dict]:
    """根据学生和课程列表构造成绩数据"""
    items = []
    for student in students:
        selected = random.sample(course_names, k=min(random.randint(3, 6), len(course_names)))
        for cname in selected:
            score = round(min(max(random.gauss(75, 12), 40), 100), 1)
            month, day = random.randint(1, 6), random.randint(1, 28)
            items.append({
                "student_no": student["student_no"],
                "student_name": student["name"],
                "course_name": cname,
                "score": score,
                "exam_date": f"2024-{month:02d}-{day:02d}",
            })
    return items


def build_employments(students: list[dict]) -> list[dict]:
    """根据学生列表构造就业数据（约55%覆盖率）"""
    items = []
    for student in students:
        if random.random() < 0.55:
            y, m, d = random.randint(2024, 2025), random.randint(1, 12), random.randint(1, 28)
            items.append({
                "student_name": student["name"],
                "company": random.choice(COMPANIES),
                "position": random.choice(POSITIONS),
                "salary": round(random.uniform(6000, 25000), 2),
                "status": random.choice(EMPLOYMENT_STATUSES),
                "employment_date": f"{y}-{m:02d}-{d:02d}",
            })
    return items


# ==================== 主流程 ====================

def main():
    student_count = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    print("=" * 55)
    print("  学生信息管理系统 - 模拟数据生成器 (API版)")
    print("=" * 55)
    print(f"  目标学生数量: {student_count}")
    print(f"  API 地址:      {API_BASE}")
    print("-" * 55)

    # ---- Step 0: 健康检查 ----
    print("\n[0/7] 检查服务状态...")
    client = APIClient(API_BASE)
    if not client.health_check():
        print(f"  [ERROR] 无法连接到 {API_BASE}")
        print("  请先启动服务: uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    print("  [OK] 服务运行正常")

    # ---- Step 1: 登录 ----
    print("\n[1/7] 登录系统...")
    if not client.login(USERNAME, PASSWORD):
        sys.exit(1)
    print(f"  [OK] 登录成功 (用户: {USERNAME})")

    # ---- Step 2: 清理旧数据 ----
    print("\n[2/7] 清理旧数据...")
    old_data = {}
    for endpoint, label in [
        ("/api/grades", "成绩"), ("/api/employments", "就业"),
        ("/api/students", "学生"), ("/api/teachers", "教师"),
        ("/api/courses", "课程"), ("/api/classes", "班级"),
    ]:
        try:
            resp = client.session.get(f"{API_BASE}{endpoint}", timeout=10)
            if resp.status_code == 200:
                items = resp.json()
                old_data[label] = len(items)
                for item in items:
                    client.session.delete(f"{API_BASE}{endpoint}/{item['id']}", timeout=5)
        except Exception:
            pass
    summary = ", ".join(f"{k}:{v}" for k, v in old_data.items())
    print(f"  [OK] 已清理 ({summary or '无'})")
    time.sleep(0.2)

    # ---- Step 3: 教师 ----
    teacher_count = max(student_count // 5, 15)
    print(f"\n[3/7] 生成教师数据 ({teacher_count})...")
    teacher_items = build_teachers(teacher_count)
    teachers = client._post_batch("/api/teachers", teacher_items, "教师")
    teacher_names = [t["name"] for t in teachers]
    time.sleep(0.1)

    # ---- Step 4: 学生 ----
    print(f"\n[4/7] 生成学生数据 ({student_count})...")
    student_items = build_students(student_count)
    students = client._post_batch("/api/students", student_items, "学生")
    time.sleep(0.1)

    # ---- Step 5: 课程 ----
    print("\n[5/7] 生成课程数据...")
    course_items = build_courses(teacher_names)
    courses = client._post_batch("/api/courses", course_items, "课程")
    course_names = [c["name"] for c in courses]
    time.sleep(0.1)

    # ---- Step 6: 班级 & 成绩 & 就业 ----
    class_count = max(student_count // 8, 5)
    print(f"\n[6/7] 生成班级数据 ({class_count})...")
    class_items = build_classes(class_count)
    client._post_batch("/api/classes", class_items, "班级")

    print(f"\n  生成成绩数据...")
    grade_items = build_grades(students, course_names)
    client._post_batch("/api/grades", grade_items, "成绩")

    print(f"\n  生成就业数据...")
    employment_items = build_employments(students)
    client._post_batch("/api/employments", employment_items, "就业")

    # ---- 完成 ----
    print("\n" + "=" * 55)
    print("  全部模拟数据生成完成!")
    print("=" * 55)
    print(f"  学生: {len(students)} | 教师: {len(teachers)} | 课程: {len(courses)}")
    print(f"\n  请刷新前端页面查看数据。")


if __name__ == "__main__":
    main()
