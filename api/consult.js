// 상담 신청 → Resend 로 visionpencil@gmail.com 에 메일 발송 (Vercel Function)
// 필요 환경변수: RESEND_API_KEY (Vercel 프로젝트 설정에 저장)

const TO = 'visionpencil@gmail.com';
const FROM = '3H 안동구시장센터 <consult@visionpencil.co.kr>';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clip = (s, n) => String(s ?? '').trim().slice(0, n);

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  const body = typeof req.body === 'string' ? safeJson(req.body) : req.body || {};

  // 스팸 봇 차단용 숨김 필드. 사람이 채울 일이 없음
  if (body.website) return res.status(200).json({ ok: true });

  const name = clip(body.name, 50);
  const phone = clip(body.phone, 30);
  const product = clip(body.product, 100) || '미선택';
  const concern = clip(body.concern, 2000) || '없음';

  if (!name || !/^[0-9+\-\s()]{8,20}$/.test(phone)) {
    return res.status(400).json({ ok: false, error: 'invalid_input' });
  }
  if (!process.env.RESEND_API_KEY) {
    return res.status(500).json({ ok: false, error: 'not_configured' });
  }

  const sentAt = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  const rows = [['성함', name], ['연락처', phone], ['관심 제품', product], ['건강 고민', concern], ['신청 시각', sentAt]];
  const html = `
    <div style="font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:560px">
      <h2 style="color:#0056b3;margin:0 0 16px">새 상담 신청이 들어왔습니다</h2>
      <table style="border-collapse:collapse;width:100%;font-size:15px">
        ${rows.map(([k, v]) => `<tr><th style="text-align:left;background:#f0f4ff;padding:10px 12px;border:1px solid #dde5f5;width:110px">${k}</th><td style="padding:10px 12px;border:1px solid #dde5f5;white-space:pre-wrap">${esc(v)}</td></tr>`).join('')}
      </table>
      <p style="margin-top:18px"><a href="tel:${esc(phone.replace(/[^0-9+]/g, ''))}" style="background:#00a86b;color:#fff;padding:10px 18px;border-radius:50px;text-decoration:none;font-weight:700">${esc(phone)} 바로 전화</a></p>
      <p style="color:#888;font-size:12px;margin-top:20px">3H지압침대 안동구시장센터 홈페이지 상담 신청 폼에서 발송된 메일입니다.</p>
    </div>`;
  const text = rows.map(([k, v]) => `${k}: ${v}`).join('\n');

  try {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${process.env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [TO], subject: `[3H 안동] 상담 신청 · ${name} (${product})`, html, text }),
    });
    if (!r.ok) {
      console.error('Resend error', r.status, await r.text());
      return res.status(502).json({ ok: false, error: 'send_failed' });
    }
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('Resend fetch failed', err);
    return res.status(502).json({ ok: false, error: 'send_failed' });
  }
}

function safeJson(s) {
  try { return JSON.parse(s); } catch { return {}; }
}
