import { useState, useEffect } from 'react';

interface Milestone {
  ngan: number;
  thuoc: string;
  thoi_gian_nhac: string;
  trang_thai: string;
}

function DongHo() {
  const [virtualTime, setVirtualTime] = useState<string>('');
  const [passedMilestones, setPassedMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    fetchClock();
    const interval = setInterval(fetchClock, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchClock = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/simulation/clock/state');
      if (res.ok) {
        const data = await res.json();
        setVirtualTime(data.virtual_clock);
        setError('');
      } else {
        setError(`Lỗi máy chủ (${res.status})`);
      }
    } catch {
      setError('Không thể kết nối đến backend (http://localhost:8000). Bạn nhớ bật backend bằng uvicorn nhé!');
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

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', maxWidth: 840, margin: '24px auto', padding: '0 16px', color: '#1f2937' }}>
      <header style={{ marginBottom: 24, textAlign: 'center' }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: '#111827' }}>
          Mô Phỏng Đồng Hồ Ảo (Thành viên 2)
        </h1>
        <p style={{ color: '#4b5563', fontSize: 14, margin: '6px 0 0' }}>
          Điều khiển thời gian độc lập, không thay đổi đồng hồ máy tính
        </p>
      </header>

      {error && (
        <div style={{ backgroundColor: '#fee2e2', border: '1px solid #f87171', color: '#b91c1c', padding: '12px 16px', borderRadius: 8, marginBottom: 20, fontSize: 14 }}>
          <strong>Lỗi:</strong> {error}
        </div>
      )}

      <div style={{ border: '1px solid #e5e7eb', padding: 24, borderRadius: 12, backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginTop: 0, marginBottom: 16 }}>Bảng Điều Khiển Giờ</h2>
        <p style={{ fontSize: 16, margin: '12px 0' }}>
          Thời gian mô phỏng hiện tại:{' '}
          <strong style={{ color: '#047857', fontSize: 20, fontFamily: 'monospace' }}>
            {virtualTime ? new Date(virtualTime).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }) : 'Đang tải...'}
          </strong>
        </p>

        <div style={{ marginTop: 20, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
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
            Đặt lại demo
          </button>
        </div>
      </div>

      <div style={{ border: '1px solid #e5e7eb', padding: 24, borderRadius: 12, backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, marginTop: 0, marginBottom: 12 }}>
          Lịch Sử Cảnh Báo & Các Mốc Vừa Đi Qua
        </h3>
        {passedMilestones.length === 0 ? (
          <p style={{ color: '#6b7280', margin: 0 }}>Chưa đi qua mốc nào. Nhấn cộng phút để tiến tới 08:00 (mốc uống thuốc A).</p>
        ) : (
          <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
            {passedMilestones.map((ms, index) => (
              <li key={index} style={{ padding: '12px 14px', borderBottom: '1px solid #f3f4f6', backgroundColor: index % 2 === 0 ? '#f9fafb' : '#ffffff', borderRadius: 6, marginBottom: 4 }}>
                <div>
                  <strong>Ngăn {ms.ngan} ({ms.thuoc})</strong> &bull; Mốc nhắc: <strong>{ms.thoi_gian_nhac}</strong>
                </div>
                <div style={{ color: '#dc2626', fontSize: 14, marginTop: 4 }}>
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
