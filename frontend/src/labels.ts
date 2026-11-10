export const parseStatus: Record<string, string> = {
  none: "未解析",
  pending: "待解析",
  processing: "解析中",
  success: "成功",
  failed: "失败",
};

export const diagnosisStatus: Record<string, string> = {
  none: "未诊断",
  pending: "诊断中",
  processing: "诊断中",
  success: "已诊断",
  failed: "诊断失败",
};

export const skillStatus: Record<string, string> = {
  matched: "已匹配",
  partial: "部分匹配",
  missing: "未体现",
  unknown: "无法判断",
};

export const skillType: Record<string, string> = {
  required: "必备技能",
  bonus: "加分技能",
  engineering: "工程能力",
  business: "业务能力",
};

export const taskStatus: Record<string, string> = {
  PENDING: "等待执行",
  PROCESSING: "正在执行",
  SUCCESS: "执行成功",
  FAILED: "执行失败",
  CANCELLED: "已取消",
};
