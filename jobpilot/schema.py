"""canonical 字段登记表：字段 id、中文标签、别名、类型、是否敏感、是否首建。

约定：
- 字段 id 形如 ``person.name``；可重复块用 ``education.0.school`` 访问。
- 值不是裸字符串，而是 ``{"v": ..., "type": ...}``；见 values.py。
- 站点卡可以覆盖映射，但 canonical id 只在这里定义。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    id: str
    label: str
    type: str = "text"
    group: str = "person"
    aliases: tuple[str, ...] = ()
    sensitive: bool = False
    maxlen: int | None = None
    l0: bool = False

    @property
    def repeat(self) -> bool:
        return self.group in REPEAT_GROUPS


# (id, 标签, 类型, 分组, 别名, 敏感, 最大长度, 首建必问)
_RAW = [
    # 一、身份
    ("person.name", "姓名", "text", "person", ("中文姓名", "本人姓名"), False, None, False),
    ("person.name_en", "姓名（英文）", "text", "person", ("英文姓名",), False, None, False),
    ("person.gender", "性别", "enum", "person", (), False, None, False),
    ("person.birth_date", "出生日期", "date", "person", ("出生年月",), False, None, False),
    ("person.id_no", "身份证号", "text", "person", ("身份证号码", "证件号码"), True, 18, False),
    ("person.nation", "民族", "text", "person", (), False, None, False),
    ("person.nationality", "国籍", "text", "person", (), False, None, False),
    ("person.politics", "政治面貌", "enum", "person", (), False, None, False),
    ("person.marital", "婚姻状况", "enum", "person", (), False, None, False),
    ("person.hukou", "户籍所在地", "region", "person", ("户口所在地",), False, None, False),
    ("person.hometown", "籍贯", "region", "person", (), False, None, False),
    ("person.height", "身高", "number", "person", ("身高（cm）",), False, None, False),
    ("person.weight", "体重", "number", "person", ("体重（kg）",), False, None, False),
    ("person.archive", "档案存放处", "text", "person", ("人事档案存放单位",), False, None, False),
    ("person.first_job", "是否首次就业", "bool", "person", (), False, None, False),
    ("person.social_insurance", "是否有社保记录", "bool", "person", (), False, None, False),
    ("person.photo", "证件照", "file", "person", ("照片", "免冠照片"), False, None, False),
    ("person.english_level", "英语水平", "enum", "person", ("英语等级", "外语水平", "英语"), False, None, True),
    # 二、联系方式
    ("contact.phone", "手机号码", "tel", "contact", ("手机号", "联系电话"), True, None, False),
    ("contact.email", "电子邮箱", "email", "contact", ("邮箱",), True, None, False),
    ("contact.wechat", "微信号", "text", "contact", ("微信",), True, None, False),
    ("contact.address", "通讯地址", "text", "contact", ("家庭地址",), False, None, False),
    ("contact.postcode", "邮编", "text", "contact", ("邮政编码",), False, None, False),
    ("contact.current_address", "现居住地址", "text", "contact", (), False, None, False),
    ("contact.emergency_name", "紧急联系人姓名", "text", "contact", (), False, None, False),
    ("contact.emergency_phone", "紧急联系人电话", "tel", "contact", (), True, None, False),
    ("contact.emergency_relation", "紧急联系人关系", "text", "contact", (), False, None, False),
    # 三、教育（可重复）
    ("education.level", "学历层次", "enum", "education", ("学历", "最高学历", "培养层次"), False, None, True),
    ("education.school", "学校名称", "text", "education", ("毕业院校", "学校", "院校名称"), False, 20, True),
    ("education.school_en", "学校名称（英文）", "text", "education", (), False, None, False),
    ("education.major", "专业", "text", "education", ("所学专业",), False, None, True),
    ("education.major_en", "专业（英文）", "text", "education", (), False, None, False),
    ("education.college", "学院", "text", "education", ("院系", "分院"), False, None, False),
    ("education.degree", "学位", "enum", "education", ("学位类型",), False, None, False),
    ("education.study_mode", "学习形式", "enum", "education", (), False, None, False),
    ("education.start_date", "入学日期", "month", "education", ("入学时间",), False, None, False),
    ("education.end_date", "毕业日期", "month", "education", ("毕（结）业日期",), False, None, False),
    ("education.grad_date", "预计毕业时间", "month", "education", ("最高学历毕业时间",), False, None, True),
    ("education.student_id", "学号", "text", "education", ("学生编号", "Student ID"), False, None, False),
    ("education.gpa", "总GPA", "number", "education", ("GPA",), False, None, False),
    ("education.rank", "班级排名", "text", "education", ("成绩排名",), False, None, False),
    ("education.courses", "主修课程", "long_text", "education", (), False, None, False),
    ("education.honors", "荣誉与奖项", "long_text", "education", (), False, None, False),
    ("education.cert_no", "毕业证书编号", "text", "education", (), False, None, False),
    # 四、语言（可重复）
    ("languages.test", "考试类型", "enum", "languages", ("语言考试",), False, None, False),
    ("languages.score", "总分", "number", "languages", ("成绩",), False, None, False),
    ("languages.sub_scores", "单项分数", "long_text", "languages", (), False, None, False),
    ("languages.test_date", "考试日期", "month", "languages", (), False, None, False),
    ("languages.cert_no", "证书编号", "text", "languages", (), False, None, False),
    # 五、实习与项目（可重复）
    ("experiences.company", "公司全称", "text", "experiences", ("单位名称",), False, None, False),
    ("experiences.company_short", "公司简称", "text", "experiences", (), False, None, False),
    ("experiences.industry", "所属行业", "enum", "experiences", (), False, None, False),
    ("experiences.org_type", "单位性质", "enum", "experiences", (), False, None, False),
    ("experiences.title", "职位名称", "text", "experiences", ("岗位名称",), False, None, False),
    ("experiences.job_level", "岗位级别", "enum", "experiences", (), False, None, False),
    ("experiences.employment_type", "用工性质", "enum", "experiences", (), False, None, False),
    ("experiences.start_date", "开始日期", "month", "experiences", (), False, None, False),
    ("experiences.end_date", "结束日期", "month", "experiences", (), False, None, False),
    ("experiences.location", "工作地点", "text", "experiences", (), False, None, False),
    ("experiences.department", "部门", "text", "experiences", (), False, None, False),
    ("experiences.supervisor", "证明人姓名", "text", "experiences", (), False, None, False),
    ("experiences.supervisor_phone", "证明人电话", "tel", "experiences", (), True, None, False),
    ("experiences.duties", "工作内容", "long_text", "experiences", (), False, None, False),
    ("experiences.reason", "离职原因", "text", "experiences", (), False, None, False),
    # 六、家庭（可重复）
    ("family.relation", "关系", "text", "family", ("称谓",), False, None, False),
    ("family.name", "姓名", "text", "family", (), False, None, False),
    ("family.birth_date", "出生年月", "month", "family", (), False, None, False),
    ("family.employer", "工作单位", "text", "family", (), False, None, False),
    ("family.title", "职务", "text", "family", (), False, None, False),
    ("family.politics", "政治面貌", "enum", "family", (), False, None, False),
    ("family.phone", "联系电话", "tel", "family", (), True, None, False),
    ("family.id_no", "身份证号", "text", "family", (), True, 18, False),
    # 七、奖惩（可重复）
    ("awards.name", "奖项名称", "text", "awards", ("奖励名称",), False, None, False),
    ("awards.date", "获奖日期", "month", "awards", (), False, None, False),
    ("awards.level", "奖项级别", "enum", "awards", (), False, None, False),
    # 八、求职意向
    ("intent.directions", "求职方向", "list", "intent", ("应聘方向",), False, None, True),
    ("intent.cities", "意向城市", "list", "intent", ("工作地点", "意向工作地"), False, None, True),
    ("intent.city_first", "工作城市首选", "text", "intent", (), False, None, False),
    ("intent.city_second", "工作城市次选", "text", "intent", (), False, None, False),
    ("intent.position_first", "工作职位首选", "text", "intent", (), False, None, False),
    ("intent.position_second", "工作职位次选", "text", "intent", (), False, None, False),
    ("intent.available_from", "可到岗时间", "month", "intent", (), False, None, True),
    ("intent.salary_expect", "期望薪资", "text", "intent", (), False, None, False),
    ("intent.salary_min", "薪资下限", "number", "intent", ("期望薪资下限", "最低薪资", "薪资要求"), False, None, True),
    ("intent.employer_types", "目标机构类型", "list", "intent", ("意向机构类型", "公司类型"), False, None, True),
    ("intent.exclude", "排除项", "list", "intent", ("不投清单", "排除公司"), False, None, True),
    ("intent.exam_city", "笔试城市", "text", "intent", (), False, None, False),
    ("intent.referral", "内推方式", "text", "intent", (), False, None, False),
    ("intent.adjust", "是否服从调剂", "bool", "intent", (), False, None, False),
    # 九、文案
    ("narratives.self_eval", "自我评价", "long_text", "narratives", (), False, None, False),
    ("narratives.strengths", "优势与不足", "long_text", "narratives", (), False, None, False),
    ("narratives.why_company", "应聘理由", "long_text", "narratives", ("求职理由",), False, None, False),
    ("narratives.hobby", "爱好", "long_text", "narratives", (), False, None, False),
    ("narratives.specialty", "特长", "long_text", "narratives", (), False, None, False),
    ("narratives.supplement", "补充说明", "long_text", "narratives", (), False, None, False),
    # 十、声明类
    ("flags.fresh_grad", "是否应届生", "bool", "flags", (), False, None, True),
    ("flags.relative_in_company", "是否有亲属在本公司任职", "bool", "flags", (), False, None, False),
    ("flags.second_major", "是否有第二专业", "bool", "flags", (), False, None, False),
    ("flags.retake", "是否有补考重修", "bool", "flags", (), False, None, False),
    ("flags.scholarship", "是否获得奖学金", "bool", "flags", (), False, None, False),
    # 十一、偏好（不是网申字段）
    ("prefs.resume", "简历版本", "file", "prefs", (), False, None, False),
    ("prefs.submit", "提交模式", "enum", "prefs", (), False, None, False),
    ("prefs.fill_mode", "填写模式", "enum", "prefs", (), False, None, False),
    ("prefs.photo", "证件照", "file", "prefs", (), False, None, False),
]

FIELDS: dict[str, Field] = {
    r[0]: Field(id=r[0], label=r[1], type=r[2], group=r[3], aliases=r[4], sensitive=r[5],
                maxlen=r[6], l0=r[7])
    for r in _RAW
}

REPEAT_GROUPS = ("education", "languages", "experiences", "family", "awards")
L0: tuple[str, ...] = tuple(f.id for f in FIELDS.values() if f.l0)
# 网申里这些字段即使页面没标星，也不该空着
CORE_REQUIRED: frozenset[str] = frozenset({
    "person.name", "contact.phone", "contact.email", "person.id_no",
    "person.birth_date", "education.level", "education.school",
    "education.major", "education.grad_date", "prefs.resume",
})

# 允许「明确回答为空」的字段（例如：没有要排除的公司）
ALLOW_EMPTY: frozenset[str] = frozenset({"intent.exclude"})

# 第一次填网申时才问的基础项（首建不问）
APPLY_BASICS: tuple[str, ...] = (
    "person.name", "contact.phone", "contact.email",
    "person.id_no", "person.birth_date", "prefs.resume",
)
GROUPS: tuple[str, ...] = tuple(dict.fromkeys(f.group for f in FIELDS.values()))


def field_for(path: str) -> Field | None:
    """``education.0.school`` → education.school；``person.name`` 原样。"""
    parts = path.split(".")
    if len(parts) >= 3 and parts[1].isdigit():
        return FIELDS.get(f"{parts[0]}.{parts[2]}")
    return FIELDS.get(path)


def label_for(path: str) -> str:
    f = field_for(path)
    if f:
        return f.label
    return path.split(".")[-1]


_PUNCT = re.compile(r"[\s\*＊:：，,。\.、/／\[\]【】]+")


def normalize_label(text: str) -> str:
    """把页面标签归一化：全角转半角、去空白标点、去「请输入/请选择」前缀。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).strip()
    s = re.sub(r"^(请输入|请选择|请填写|请上传|选择|输入)", "", s)
    s = _PUNCT.sub("", s)
    return s


def alias_index() -> dict[str, tuple[str, ...]]:
    """一个标签可能对应多个字段（如「姓名」既可能是本人也可能是家属），全部保留。"""
    idx: dict[str, list[str]] = {}
    for f in FIELDS.values():
        for name in (f.label, *f.aliases):
            key = normalize_label(name)
            if key:
                idx.setdefault(key, []).append(f.id)
    return {k: tuple(dict.fromkeys(v)) for k, v in idx.items()}
