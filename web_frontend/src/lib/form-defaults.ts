/**
 * form-defaults.ts — Apply / Inquiry 폼 하드코딩 기본값
 * ApplyForm.tsx, InquiryForm.tsx, admin/form-config/page.tsx 공통 참조
 */

export const APPLY_DEFAULTS: Record<string, string[]> = {
  HOW_TO: [
    'Friend Referral','Previous Experience','Google','Reddit',
    'Facebook','Instagram','YouTube','ESL Cafe','LinkedIn','Other',
  ],
  NATIONALITIES: [
    'USA','United Kingdom','Canada','Ireland',
    'Australia','New Zealand','South Africa',
    'F (Korean diaspora or overseas Korean)','South Korea','Other',
  ],
  ANCESTRY: [
    'Korean','Chinese, Hong Kong, or Taiwanese','Japanese',
    'Mongolian or Other East Asian (excluding above)','Indian','Native American',
    'White or European','Pakistani, Afghan, Bangladeshi','Black or African American',
    'Middle Eastern or North African','Hispanic or Latino','Mixed or Multiracial',
    'Pacific Islander','Other','Prefer not to disclose',
  ],
  EDUCATION: [
    'Graduated, but diploma not available',
    "Bachelor's degree from one of the 7 eligible countries",
    "Bachelor's degree (other country)",
    'Master','Doctor','Associate','Online degree','Did not graduate',
    "I have a bachelor's or higher from Korea",
  ],
  CERTIFICATION: [
    'Teaching license (Official Teaching License/Credential)',
    'PGCE (Postgraduate Certificate in Education)',
    'TEFL','TESOL','DELTA','CELTA','On the process','No certification',
  ],
  E_VISA: ['Recorded','Never obtained an E visa'],
  PASSPORT: [
    'Expires within 2 years',
    'Valid for more than 2 years',
    'Scheduled for renewal within the period',
  ],
  CRIMINAL_RECORD: [
    'Issued and apostille completed',
    'Issued but awaiting apostille',
    'Never applied for a new one',
    'Holding a visa and recently left Korea',
  ],
  DOC_STATUS: [
    'Already have a valid visa',
    'All documents completed (Criminal check + Degree apostilled)',
    'Degree / CBC at final apostille stage (confirmed return date)',
    'Never applied for any documents',
    'Holding a visa and recently left Korea within 1 month',
    'Other',
  ],
  TARGET_AGE: [
    'Pre-K ~ Kindergarten','Elementary school level','Middle school level',
    'High school level','Adults','No preferences',
  ],
  AREA_PREFS: ['Metropolitan city','Medium size city','Small city','No preference'],
  EXPERIENCE: [
    'None','Less than 6 months','6 months to 1 year',
    'over 1 year','over 2 year','over 3 year','over 4 year','over 5 year',
    'over 6 year','over 7 year','over 8 year','over 9 year','over 10 year',
    'over 15 year','over 20 year','Overseas full-time teaching experience only',
  ],
  EMPLOYMENT: [
    'The school is aware','Not working in Korea','Do not know',
    'I will inform them very soon',
    'School do know, but references cannot be verified',
    'Contract terminated early I have a Letter of Release',
  ],
  MARITAL: [
    'Married','Coming with Dependents (Children or Family)',
    'Single or Coming Alone','Divorced','No comment',
    'Planning to get married within a year',
  ],
  HOUSING: [
    'I would like to use the school provided housing',
    'I am willing to pay monthly for better housing',
    'I have enough deposit and will handle the monthly rent on my own',
    'I have housing so no support is needed',
  ],
  DEPENDENTS_PETS: [
    'I am coming alone','Young children (under age 6)',
    'School age children or Family members','Dog(s)','Cat(s)','Other pets',
  ],
  PERSONAL: [
    'Zero tattoos or piercings','Visible but can be covered',
    'Visible tattoo (cannot be covered)',
    'Facial piercings (nose lip eyebrow etc cannot be removed)',
  ],
  RELIGION: [
    'Irreligious','Christianity','Buddhism','Judaism','Islam','Hinduism',
    'Does not celebrate events such as births due to specific beliefs or affiliations',
    'Other',
  ],
  HEALTH:  ['I have not','I have a condition','Prefer not to say'],
  CRC:     ['Clean record','I have a record','Prefer not to answer'],
  KR_CRC:  ['Clean record','I have a record','Not applicable (never lived in Korea)','Prefer not to answer'],
}

export const INQUIRY_DEFAULTS: Record<string, string[]> = {
  BUSINESS_REG:        ['등록기관 Registered Institution','현시간 미등록 Unregistered Institution'],
  HIRE_HIST:           ['채용이력O','채용이력X'],
  NATIVE_COUNT:        ['없음','1명','2명','3명','4명','5명','6명','7~9명','10~14명','15~20명','20명이상','30명이상'],
  VACANCIES:           ['1명','2명','3명','4명','5명','6명','7명','8명','9명','10명'],
  CONTRACT_TYPE:       ['Full time','Part time'],
  TEACHING_AGE:        [
    '48개월 미만 baby','영유아 Pre-K, ~5세미만','유치원 Kindergarten',
    '초등학생 Elementary','중학생 Middle School',
    '고등학생 High School','대학생/ 성인 Adult',
  ],
  CLASS_SIZE:          ['~5명 이내','~8명 이내','~12명 이내','12명 이상','20명이상'],
  AVG_LESSONS:         ['주 10-15시간','주 15-20시간','주 20-25시간','주 25-30시간','주 30-35시간','주 35시간 이상'],
  PREFERRED_CANDIDATE: ['영어권 원어민 Native Teachers','교포 Kyopo','F비자 소지자 F Visa','한국인 Koreans','무관 No Preference'],
  SALARY_RANGES:       [
    '2,20 KRW - 2,30 KRW','2,30 KRW - 2,40 KRW','2,40 KRW - 2,50 KRW',
    '2,50 KRW - 2,60 KRW','2,60 KRW - 2,70 KRW','2,70 KRW - 2,80 KRW',
    '2,80 KRW - 2,90 KRW','2,90 KRW - 3,00 KRW','3,00 KRW - 3,20 KRW',
    '3,20 KRW - 3,50 KRW','3,50 KRW - 4,50 KRW','4,50 KRW - 6,50 KRW','시급제 또는 기타',
  ],
  TRAVEL_SUPPORT:      [
    '국내교통비지원 Domestic allowance','왕복항공지원 Round trip support',
    '입국만지원 Entry','출국만지원 Departure',
    '규정에따른비용지원 Travel expenses','제공없음 Not provided',
  ],
  MEAL_OPTS:           ['식사제공','식대제공','식사식대제공없음'],
  HOUSING_OPTS:        [
    '풀옵션 하우징 Fully furnished housing','개인기숙사 Dormitory',
    '월세지원 Housing allowance','월세 및 보증금지원 Allowance and deposit support',
    '다양한 지원가능 Negotiable','숙소미제공 No housing provided',
  ],
  BENEFITS_OPTS:       [
    '비자스폰 (E) Working Visa sponsorship','퇴직금 Severance Pay (월급제 필수*)',
    '교통비 Transportation expenses','국민연금 National Pension (SA제외 월급제 필수*)',
    '건강보험 Medical Insurance','비자 건강검진 Medical check support',
    '정착 지원금 Settlement Allowance','재계약 보너스 Renewal Bonus',
    '계약완료 보너스 Contract Completion Bonus','본인/자녀 교육지원 Education support',
    '기타 Bonus (연휴, 생일, 성과금등)',
  ],
  VACATION_INC:        ['포함 Including weekends','주말,공휴일제외 Excluding weekends'],
}
