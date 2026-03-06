/**
 * BRIDGE Job Posting → .docx Auto-Generator
 * 
 * 구인자(업체) 채용공고 → 원어민에게 보낼 Job Description 워드 문서
 * PII 자동 제거된 공개용 버전 생성
 * 
 * Usage:
 *   node generate_job_docx.js                              (데모)
 *   node generate_job_docx.js --input job.json --output BRJ-BS-2506-001.docx
 *   node generate_job_docx.js --input job.json --admin     (PII 포함 관리자용)
 */

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, BorderStyle, WidthType, ShadingType,
  PageNumber,
} = require("docx");

const DARK = "1D1D1F";
const GRAY = "8E8E93";
const LIGHT = "F5F5F7";
const BLUE = "0071E3";
const BORDER = "E5E5EA";
const PW = 12240;
const MARGIN = 1440;
const CW = PW - MARGIN * 2;

const noBorder = { style: BorderStyle.NONE };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
const pad = { top: 60, bottom: 60, left: 120, right: 120 };

function val(v) {
  if (!v || (Array.isArray(v) && !v.length)) return "\u2014";
  return Array.isArray(v) ? v.join(", ") : String(v);
}

function heading(text) {
  return new Paragraph({
    spacing: { before: 280, after: 100 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 3, color: DARK, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 20, bold: true, color: DARK })],
  });
}

function kvTable(rows) {
  const lw = 3200;
  const vw = CW - lw;
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [lw, vw],
    rows: rows.map(([label, value]) =>
      new TableRow({
        children: [
          new TableCell({
            borders: noBorders, width: { size: lw, type: WidthType.DXA }, margins: pad,
            shading: { fill: LIGHT, type: ShadingType.CLEAR },
            children: [new Paragraph({ children: [new TextRun({ text: label, font: "Arial", size: 18, bold: true, color: GRAY })] })],
          }),
          new TableCell({
            borders: noBorders, width: { size: vw, type: WidthType.DXA }, margins: pad,
            children: [new Paragraph({ children: [new TextRun({ text: val(value), font: "Arial", size: 20, color: DARK })] })],
          }),
        ],
      })
    ),
  });
}

function longText(label, value) {
  return [
    new Paragraph({
      spacing: { before: 100, after: 40 },
      children: [new TextRun({ text: label, font: "Arial", size: 18, bold: true, color: GRAY })],
    }),
    new Paragraph({
      spacing: { after: 100 },
      shading: { fill: LIGHT, type: ShadingType.CLEAR },
      indent: { left: 200, right: 200 },
      children: [new TextRun({ text: val(value), font: "Arial", size: 20, color: DARK })],
    }),
  ];
}

function generateJobDocx(jobData, { admin = false } = {}) {
  const d = jobData.data || jobData;
  const jobId = jobData.id || "BRJ-DRAFT";
  const createdAt = jobData.created_at || new Date().toISOString().slice(0, 10);
  const status = jobData.status || "new";

  const children = [];

  // 제목
  children.push(
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
      children: [new TextRun({ text: "BRIDGE", font: "Arial", size: 28, bold: true, color: DARK })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
      children: [new TextRun({ text: admin ? "Job Posting \u2014 Internal (Admin)" : "Job Description", font: "Arial", size: 20, color: GRAY })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: DARK, space: 8 } },
      children: [new TextRun({ text: `${jobId}  |  ${createdAt}  |  ${status.toUpperCase()}`, font: "Arial", size: 16, color: GRAY })] }),
  );

  // 위치 정보
  children.push(heading("LOCATION"));
  const locationRows = [
    ["Region", d.region],
    ["City / District", d.city],
  ];
  if (admin && d.employer_name) locationRows.unshift(["School Name", d.employer_name]);
  if (admin && d.address) locationRows.push(["Address", d.address]);
  children.push(kvTable(locationRows));

  // 업체 연락처 (관리자 전용)
  if (admin) {
    children.push(heading("EMPLOYER CONTACT (CONFIDENTIAL)"));
    children.push(kvTable([
      ["Contact Person", d.contact_name],
      ["Phone", d.contact_phone],
      ["Email", d.contact_email],
      ["KakaoTalk", d.contact_kakao],
    ]));
  }

  // 채용 조건
  children.push(heading("JOB DETAILS"));
  children.push(kvTable([
    ["Teaching Age", d.teaching_age],
    ["Class Size", d.class_size],
    ["Working Hours", d.working_hours],
    ["Teaching Hours / Week", d.teaching_hours_weekly],
    ["Starting Date", d.start_date],
    ["Native Teachers Needed", d.native_count],
  ]));

  // 급여 & 복리후생
  children.push(heading("SALARY & BENEFITS"));
  children.push(kvTable([
    ["Monthly Salary (KRW)", d.salary ? `${d.salary} ${d.salary_negotiable === "Negotiable" ? "(Negotiable)" : "(Not Negotiable)"}` : null],
    ["Housing", d.housing],
    ["Housing Detail", d.housing_detail],
    ["Vacation", d.vacation],
    ["Benefits", d.benefits],
  ]));

  // 자격 요건
  children.push(heading("REQUIREMENTS"));
  children.push(kvTable([
    ["Degree", d.degree_req],
    ["F-Visa / Kyopo", d.f_visa_ok],
    ["Korea Residents Only", d.korea_resident_only],
  ]));

  // 공개 노트
  if (d.public_notes) {
    children.push(...longText("Additional Information", d.public_notes));
  }

  // 관리자 내부 메모
  if (admin && d.internal_notes) {
    children.push(heading("INTERNAL NOTES (CONFIDENTIAL)"));
    children.push(...longText("Admin Memo", d.internal_notes));
  }

  // 하단
  children.push(
    new Paragraph({ spacing: { before: 400 } }),
    new Paragraph({
      border: { top: { style: BorderStyle.SINGLE, size: 6, color: DARK, space: 8 } },
      alignment: AlignmentType.CENTER, spacing: { before: 120 },
      children: [new TextRun({ text: admin ? "BRIDGE Internal Document \u2014 Do Not Distribute" : "For inquiries, contact BRIDGE at bridgejob.co.kr", font: "Arial", size: 16, color: GRAY })],
    }),
  );

  return new Document({
    styles: { default: { document: { run: { font: "Arial", size: 20 } } } },
    sections: [{
      properties: {
        page: { size: { width: PW, height: 15840 }, margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({ alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: admin ? "BRIDGE INTERNAL \u2014 CONFIDENTIAL" : "BRIDGE \u2014 bridgejob.co.kr", font: "Arial", size: 14, color: "D1D1D6" })] })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({ alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", font: "Arial", size: 14, color: GRAY }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 14, color: GRAY }),
            ] })],
        }),
      },
      children,
    }],
  });
}

// ─── CLI ─────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  let inputPath = null, outputPath = null, admin = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--input" || args[i] === "-i") inputPath = args[++i];
    if (args[i] === "--output" || args[i] === "-o") outputPath = args[++i];
    if (args[i] === "--admin") admin = true;
  }

  let jobData;
  if (inputPath) {
    jobData = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
  } else {
    // 데모 데이터
    jobData = {
      id: "BRJ-BS-2506-001", legacy_id: "1003", status: "active", created_at: "2025-06-01",
      data: {
        employer_name: "브릿지영어1호점", contact_name: "***원장", contact_phone: "010-****-0333",
        contact_email: "b****@nave.com", contact_kakao: "", region: "Busan", city: "Haeundae",
        address: "부산시 해운대구 ****",
        teaching_age: ["Kindergarten", "Elementary"], class_size: "~10",
        working_hours: "09:00 ~ 16:00", teaching_hours_weekly: "23",
        start_date: "September, March", native_count: "3",
        salary: "2,400,000", salary_negotiable: "Not Negotiable",
        housing: "Allowance", housing_detail: "Allowance 400k, No deposit",
        vacation: "Total 5 weeks + 2 sick days",
        benefits: ["Visa Sponsorship", "Severance Pay", "Pension", "Insurance", "Paid Vacation", "Airfare Support"],
        degree_req: "Bachelor's or higher", f_visa_ok: "No", korea_resident_only: "Yes",
        internal_notes: "담임교사아님, 한국어보조교사있음, 남자 교육전공선호",
        public_notes: "Only hiring teachers residing in Korea. Good reputation and team players preferred.",
      },
    };
  }

  // 공개용 + 관리자용 각각 생성
  if (admin) {
    const doc = generateJobDocx(jobData, { admin: true });
    const buf = await Packer.toBuffer(doc);
    const out = outputPath || `${jobData.id}_ADMIN.docx`;
    fs.writeFileSync(out, buf);
    console.log(`[ADMIN] ${out} (${(buf.length / 1024).toFixed(1)} KB)`);
  } else {
    // 공개용
    const pubDoc = generateJobDocx(jobData, { admin: false });
    const pubBuf = await Packer.toBuffer(pubDoc);
    const pubOut = outputPath || `${jobData.id}.docx`;
    fs.writeFileSync(pubOut, pubBuf);
    console.log(`[PUBLIC] ${pubOut} (${(pubBuf.length / 1024).toFixed(1)} KB)`);

    // 관리자용도 같이
    const admDoc = generateJobDocx(jobData, { admin: true });
    const admBuf = await Packer.toBuffer(admDoc);
    const admOut = `${jobData.id}_ADMIN.docx`;
    fs.writeFileSync(admOut, admBuf);
    console.log(`[ADMIN]  ${admOut} (${(admBuf.length / 1024).toFixed(1)} KB)`);
  }
}

main().catch((e) => { console.error("[ERROR]", e.message); process.exit(1); });
module.exports = { generateJobDocx };
