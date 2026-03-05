/**
 * generate_job_docx.js — Job Description .docx generator
 * Produces PUBLIC (no PII) + ADMIN (with PII) variants
 *
 * Usage:
 *   node generate_job_docx.js --input job.json
 *   node generate_job_docx.js --input job.json --admin
 *   node generate_job_docx.js --input job.json --output-dir ./output
 */

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, HeadingLevel,
  Header, Footer, PageNumber, NumberFormat,
} = require('docx');

// ── Parse CLI args ──
const args = process.argv.slice(2);
let inputPath = null;
let outputDir = '.';
let adminOnly = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--input' && args[i + 1]) inputPath = args[++i];
  else if (args[i] === '--output-dir' && args[i + 1]) outputDir = args[++i];
  else if (args[i] === '--admin') adminOnly = true;
}

if (!inputPath) {
  console.error('Usage: node generate_job_docx.js --input job.json [--admin] [--output-dir dir]');
  process.exit(1);
}

const job = JSON.parse(fs.readFileSync(inputPath, 'utf8'));

// ── Helpers ──
function val(v) {
  if (!v || v === 'None' || v === 'N/A') return '—';
  return String(v).trim();
}

function formatSalary(krw) {
  if (!krw) return '—';
  const num = Number(krw);
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M KRW`;
  if (num >= 10000) return `${(num / 10000).toFixed(0)}만원`;
  return `${num.toLocaleString()} KRW`;
}

const noBorder = {
  top: { style: BorderStyle.NONE, size: 0 },
  bottom: { style: BorderStyle.NONE, size: 0 },
  left: { style: BorderStyle.NONE, size: 0 },
  right: { style: BorderStyle.NONE, size: 0 },
};

const thinBorder = {
  top: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' },
  bottom: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' },
  left: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' },
  right: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' },
};

function makeRow(label, value, isAdmin = false) {
  return new TableRow({
    children: [
      new TableCell({
        width: { size: 2800, type: WidthType.DXA },
        borders: thinBorder,
        shading: { fill: 'F5F5F7' },
        children: [new Paragraph({
          children: [new TextRun({ text: label, font: 'Arial', size: 18, bold: true, color: '424245' })],
          spacing: { before: 60, after: 60 },
          indent: { left: 120 },
        })],
      }),
      new TableCell({
        width: { size: 7200, type: WidthType.DXA },
        borders: thinBorder,
        children: [new Paragraph({
          children: [new TextRun({
            text: value,
            font: 'Arial',
            size: 18,
            color: isAdmin ? 'CC0000' : '1D1D1F',
          })],
          spacing: { before: 60, after: 60 },
          indent: { left: 120 },
        })],
      }),
    ],
  });
}

function makeSection(title) {
  return new Paragraph({
    children: [new TextRun({ text: title, font: 'Arial', size: 22, bold: true, color: '0071E3' })],
    spacing: { before: 300, after: 100 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: '0071E3' } },
  });
}

// ── Generate Document ──
function generateDoc(isPublic) {
  const sections = [];

  // Header
  sections.push(
    new Paragraph({
      children: [
        new TextRun({ text: 'BRIDGE', font: 'Arial', size: 32, bold: true, color: '0071E3' }),
        new TextRun({ text: '  Job Description', font: 'Arial', size: 28, color: '86868B' }),
      ],
      spacing: { after: 60 },
    }),
    new Paragraph({
      children: [
        new TextRun({ text: val(job.brj_id || job.job_code), font: 'Consolas', size: 20, bold: true, color: '1D1D1F' }),
        new TextRun({ text: job.legacy_id ? `  (legacy: ${job.legacy_id})` : '', font: 'Arial', size: 16, color: '86868B' }),
      ],
      spacing: { after: 40 },
    }),
  );

  if (!isPublic) {
    sections.push(new Paragraph({
      children: [new TextRun({ text: '⚠ CONFIDENTIAL — ADMIN USE ONLY', font: 'Arial', size: 18, bold: true, color: 'CC0000' })],
      spacing: { after: 200 },
    }));
  }

  // ── Position Info ──
  sections.push(makeSection('Position Information'));
  const posRows = [
    makeRow('Region', `${val(job.region_name)} (${val(job.region)})`),
    makeRow('City / District', `${val(job.city)} ${val(job.district) !== '—' ? val(job.district) : ''}`),
    makeRow('Teaching Level', val(job.teaching_age)),
    makeRow('Class Size', val(job.class_size)),
    makeRow('Start Date', val(job.start_date)),
    makeRow('Status', val(job.status)),
  ];
  sections.push(new Table({ rows: posRows, width: { size: 10000, type: WidthType.DXA } }));

  // ── Salary & Benefits ──
  sections.push(makeSection('Salary & Benefits'));
  const salRows = [
    makeRow('Salary', formatSalary(job.salary_krw || job.salary_min)),
    makeRow('Negotiable', job.salary_negotiable ? 'Yes' : 'No'),
    makeRow('Housing', `${val(job.housing_type)} — ${val(job.housing_detail || job.housing)}`),
    makeRow('Vacation', job.vacation_days ? `${job.vacation_days} days` : val(job.vacation)),
    makeRow('Benefits', val(job.benefits)),
    makeRow('Visa Sponsorship', job.visa_sponsorship !== 0 ? 'Yes' : 'No'),
  ];
  sections.push(new Table({ rows: salRows, width: { size: 10000, type: WidthType.DXA } }));

  // ── Work Schedule ──
  sections.push(makeSection('Work Schedule'));
  const workRows = [
    makeRow('Working Hours', val(job.working_hours)),
    makeRow('Teaching Hours/Week', val(job.teaching_hours_weekly || job.teach_hrs_week)),
    makeRow('Native Teachers', val(job.native_count)),
  ];
  sections.push(new Table({ rows: workRows, width: { size: 10000, type: WidthType.DXA } }));

  // ── Employer (Admin only) ──
  if (!isPublic) {
    sections.push(makeSection('Employer Information (CONFIDENTIAL)'));
    const empRows = [
      makeRow('Employer', val(job.enc_employer_name || job.employer_display_name), true),
      makeRow('Contact Name', val(job.enc_contact_name), true),
      makeRow('Contact Phone', val(job.enc_contact_phone), true),
      makeRow('Contact Email', val(job.enc_contact_email), true),
      makeRow('Contact Kakao', val(job.enc_contact_kakao), true),
    ];
    sections.push(new Table({ rows: empRows, width: { size: 10000, type: WidthType.DXA } }));

    if (job.internal_notes || job.recruiter_memo) {
      sections.push(makeSection('Internal Notes'));
      sections.push(new Paragraph({
        children: [new TextRun({
          text: val(job.internal_notes || job.recruiter_memo),
          font: 'Arial', size: 18, color: '424245', italics: true,
        })],
        spacing: { before: 100 },
      }));
    }
  } else {
    // Public: employer display name only
    sections.push(makeSection('Employer'));
    const empRows = [
      makeRow('School', val(job.employer_display_name || `${val(job.city)} English Academy`)),
    ];
    sections.push(new Table({ rows: empRows, width: { size: 10000, type: WidthType.DXA } }));
  }

  // Footer note
  sections.push(new Paragraph({
    children: [new TextRun({
      text: `Generated: ${new Date().toISOString().slice(0, 10)} | bridgejob.co.kr`,
      font: 'Arial', size: 14, color: '86868B',
    })],
    spacing: { before: 400 },
    alignment: AlignmentType.CENTER,
  }));

  return new Document({
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children: sections,
    }],
  });
}

// ── Main ──
async function main() {
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  const id = job.brj_id || job.job_code || 'unknown';
  const safeName = id.replace(/[^a-zA-Z0-9_-]/g, '_');

  if (!adminOnly) {
    const pubDoc = generateDoc(true);
    const pubBuf = await Packer.toBuffer(pubDoc);
    const pubPath = path.join(outputDir, `${safeName}_PUBLIC.docx`);
    fs.writeFileSync(pubPath, pubBuf);
    console.log(`PUBLIC: ${pubPath}`);
  }

  const admDoc = generateDoc(false);
  const admBuf = await Packer.toBuffer(admDoc);
  const admPath = path.join(outputDir, `${safeName}_ADMIN.docx`);
  fs.writeFileSync(admPath, admBuf);
  console.log(`ADMIN:  ${admPath}`);
}

main().catch(e => { console.error(e); process.exit(1); });
