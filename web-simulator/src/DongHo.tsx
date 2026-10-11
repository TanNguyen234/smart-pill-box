import { useState, useEffect } from 'react';

interface Milestone {
  ngan: number;
  thuoc: string;
  thoi_gian_nhac: string;
  trang_thai: string;
}

interface Compartment {
  slot: number;
  medication_name?: string;
  pill_count: number;
  weight_grams: number;
  lid_open: boolean;
  led: string;
  buzzer?: string;
  reminder: string;
}

function DongHo() {
  const [virtualTime, setVirtualTime] = useState<string>('');
  const [compartments, setCompartments] = useState<Compartment[]>([]);
  const [passedMilestones, setPassedMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    fetchClock();
    const interval = setInterval(fetchClock, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchClock = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/simulation/clock/state');
      if (res.ok) {
        const data = await res.json();
        setVirtualTime(data.virtual_clock);
        if (data.compartments) setCompartments(data.compartments);
        setError('');
      } else {
        setError(`Lỗi máy chủ (${res.status})`);
      }
    } catch {
      setError('Không thể kết nối đến backend (http://localhost:8000). Hãy đảm bảo backend uvicorn đang chạy!');
    }
  };

  const handleAdvance = async (minutes: number) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/simulation/clock/advance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ minutes }),
      });
      if (res.ok) {
        const data = await res.json();
        setVirtualTime(data.virtual_clock);
        if (data.compartments) setCompartments(data.compartments);
        setError('');
        if (data.passed_milestones && data.passed_milestones.length > 0) {
          setPassedMilestones((prev) => [...prev, ...data.passed_milestones]);
        }
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Không thể cộng thời gian');
      }
    } catch {
      setError('Lỗi kết nối khi cộng thời gian. Hãy kiểm tra máy chủ backend!');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/simulation/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ confirmation: 'RESET_DEMO' }),
      });
      if (res.ok) {
        const data = await res.json();
        setVirtualTime(data.virtual_clock);
        if (data.compartments) setCompartments(data.compartments);
        setPassedMilestones([]);
        setError('');
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Không thể đặt lại mô phỏng');
      }
    } catch {
      setError('Không thể kết nối đến backend');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDose = async (slot: number) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/simulation/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_uuid: crypto.randomUUID(),
          slot,
          event_type: 'CONFIRMED',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.compartments) setCompartments(data.compartments);
        setPassedMilestones((prev) => [
          ...prev,
          {
            ngan: slot,
            thuoc: `Ngăn ${slot}`,
            thoi_gian_nhac: 'Vừa xong',
            trang_thai: 'Đã nhấn xác nhận uống thuốc! Còi và đèn đã tắt.',
          },
        ]);
        setError('');
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Không thể xác nhận uống thuốc');
      }
    } catch {
      setError('Lỗi kết nối máy chủ khi xác nhận uống thuốc');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', maxWidth: 880, margin: '24px auto', padding: '0 16px', color: '#1f2937' }}>
      <header style={{ marginBottom: 20, textAlign: 'center' }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: '#111827' }}>
          Mô Phỏng Đồng Hồ Ảo (Thành viên 2)
        </h1>
        <p style={{ color: '#4b5563', fontSize: 14, margin: '6px 0 0' }}>
          Quy trình nhắc giờ: 08:00 (Nhắc lần 1) &rarr; 08:02 (Nhắc lại lần 2) &rarr; 08:05 (Quá hạn & Sinh Cảnh Báo)
        </p>
      </header>

      {error && (
        <div style={{ backgroundColor: '#fee2e2', border: '1px solid #f87171', color: '#b91c1c', padding: '12px 16px', borderRadius: 8, marginBottom: 20, fontSize: 14 }}>
          <strong>Lỗi:</strong> {error}
        </div>
      )}

      {/* Bảng điều khiển thời gian */}
      <div style={{ border: '1px solid #e5e7eb', padding: 20, borderRadius: 12, backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', marginBottom: 20 }}>
        <h2 style={{ fontSize: 17, fontWeight: 600, marginTop: 0, marginBottom: 12 }}>Bảng Điều Khiển Giờ</h2>
        <p style={{ fontSize: 16, margin: '8px 0' }}>
          Thời gian mô phỏng hiện tại:{' '}
          <strong style={{ color: '#047857', fontSize: 22, fontFamily: 'monospace' }}>
            {virtualTime ? new Date(virtualTime).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }) : 'Đang tải...'}
          </strong>
        </p>

        <div style={{ marginTop: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            style={{ padding: '10px 18px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            disabled={loading}
            onClick={() => handleAdvance(1)}
          >
            +1 Phút
          </button>
          <button
            style={{ padding: '10px 18px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            disabled={loading}
            onClick={() => handleAdvance(2)}
          >
            +2 Phút
          </button>
          <button
            style={{ padding: '10px 18px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            disabled={loading}
            onClick={() => handleAdvance(5)}
          >
            +5 Phút
          </button>
          <button
            style={{ padding: '10px 18px', backgroundColor: '#0284c7', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            disabled={loading}
            onClick={() => handleAdvance(60)}
          >
            +1 Tiếng
          </button>
          <button
            style={{ padding: '10px 18px', backgroundColor: '#dc2626', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, marginLeft: 'auto' }}
            disabled={loading}
            onClick={handleReset}
          >
            Đặt lại demo (07:59)
          </button>
        </div>
      </div>

      {/* Trạng thái 3 ngăn hộp thuốc thực tế */}
      <div style={{ border: '1px solid #e5e7eb', padding: 20, borderRadius: 12, backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', marginBottom: 20 }}>
        <h3 style={{ fontSize: 17, fontWeight: 600, marginTop: 0, marginBottom: 12 }}>
          Trạng Thái 3 Ngăn Hộp Thuốc (Đèn LED, Còi Buzzer & Lời Nhắc)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
          {compartments.map((comp) => {
            const isAlerting = comp.led === 'Bật' || (comp.reminder && comp.reminder.includes('NHẮC LẠI'));
            const isOverdue = comp.reminder && comp.reminder.includes('quá hạn');
            return (
              <div
                key={comp.slot}
                style={{
                  border: isAlerting ? '2px solid #ef4444' : isOverdue ? '2px solid #f97316' : '1px solid #e5e7eb',
                  backgroundColor: isAlerting ? '#fef2f2' : isOverdue ? '#fff7ed' : '#f9fafb',
                  borderRadius: 10,
                  padding: 14,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong style={{ fontSize: 16 }}>Ngăn {comp.slot} {comp.medication_name ? `(${comp.medication_name})` : ''}</strong>
                  <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4, backgroundColor: comp.lid_open ? '#fef08a' : '#e5e7eb' }}>
                    {comp.lid_open ? 'Nắp đang mở' : 'Nắp đóng'}
                  </span>
                </div>
                <div style={{ fontSize: 14, lineHeight: 1.6 }}>
                  <div>Đèn LED: <strong style={{ color: comp.led === 'Bật' ? '#dc2626' : '#6b7280' }}>{comp.led}</strong></div>
                  <div>Còi Buzzer: <strong style={{ color: comp.buzzer === 'Bật' ? '#dc2626' : '#6b7280' }}>{comp.buzzer || 'Tắt'}</strong></div>
                  <div>Lời nhắc: <strong style={{ color: isAlerting ? '#dc2626' : isOverdue ? '#ea580c' : '#1f2937' }}>{comp.reminder}</strong></div>
                  <div>Số viên: <strong>{comp.pill_count}</strong> &bull; Trọng lượng: <strong>{comp.weight_grams}g</strong></div>
                </div>
                {isAlerting && (
                  <button
                    style={{ marginTop: 10, width: '100%', padding: '6px 12px', backgroundColor: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer' }}
                    onClick={() => handleConfirmDose(comp.slot)}
                  >
                    Xác nhận uống thuốc
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Lịch sử các mốc */}
      <div style={{ border: '1px solid #e5e7eb', padding: 20, borderRadius: 12, backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <h3 style={{ fontSize: 17, fontWeight: 600, marginTop: 0, marginBottom: 12 }}>
          Lịch Sử Cảnh Báo & Các Mốc Vừa Đi Qua
        </h3>
        {passedMilestones.length === 0 ? (
          <p style={{ color: '#6b7280', margin: 0 }}>Chưa đi qua mốc nào. Nhấn cộng phút để tiến tới 08:00 (mốc uống thuốc A).</p>
        ) : (
          <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
            {passedMilestones.map((ms, index) => (
              <li
                key={index}
                style={{
                  padding: '12px 14px',
                  borderBottom: '1px solid #f3f4f6',
                  backgroundColor: index % 2 === 0 ? '#f9fafb' : '#ffffff',
                  borderRadius: 6,
                  marginBottom: 6,
                }}
              >
                <div>
                  <strong>Ngăn {ms.ngan} ({ms.thuoc})</strong> &bull; Mốc nhắc: <strong>{ms.thoi_gian_nhac}</strong>
                </div>
                <div style={{ color: ms.trang_thai.includes('quá hạn') ? '#dc2626' : ms.trang_thai.includes('lần 2') ? '#d97706' : '#2563eb', fontSize: 14, marginTop: 4 }}>
                  <em>{ms.trang_thai}</em>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default DongHo;
