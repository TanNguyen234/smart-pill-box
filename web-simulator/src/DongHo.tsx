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

  useEffect(() => {
    fetchClock();
  }, []);

  const fetchClock = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/simulation/clock/state');
      if (res.ok) {
          const data = await res.json();
          setVirtualTime(data.virtual_clock);
      }
    } catch (err) {
      console.error(err);
      setError('Cannot connect to backend server');
    }
  };

  const handleAdvance = async (minutes: number) => {
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
          if (data.passed_milestones && data.passed_milestones.length > 0) {
            setPassedMilestones(prev => [...prev, ...data.passed_milestones]);
          }
      } else {
          const err = await res.json();
          setError(err.detail || 'Failed to advance clock');
      }
    } catch (err) {
      console.error(err);
      setError('Failed to advance clock');
    }
  };

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 800, margin: '0 auto', padding: 20 }}>
      <h1>Mô Phỏng Đồng Hồ Ảo (Thành viên 2)</h1>
      <div style={{ border: '1px solid #ccc', padding: 20, borderRadius: 8, backgroundColor: '#f9f9f9', marginBottom: 20 }}>
        <h2>Bảng Điều Khiển Giờ</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <p style={{ fontSize: '1.2em' }}>
          Thời gian mô phỏng hiện tại: <strong>{virtualTime ? new Date(virtualTime).toLocaleString('vi-VN') : 'Đang tải...'}</strong>
        </p>
        
        <div style={{ marginTop: 20 }}>
          <button style={{ marginRight: 10, padding: '10px 15px', backgroundColor: '#007bff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }} onClick={() => handleAdvance(1)}>+1 Phút</button>
          <button style={{ marginRight: 10, padding: '10px 15px', backgroundColor: '#007bff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }} onClick={() => handleAdvance(2)}>+2 Phút</button>
          <button style={{ marginRight: 10, padding: '10px 15px', backgroundColor: '#007bff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }} onClick={() => handleAdvance(5)}>+5 Phút</button>
        </div>
      </div>

      <div style={{ border: '1px solid #ccc', padding: 20, borderRadius: 8, backgroundColor: '#f9f9f9' }}>
        <h3>Lịch Sử Cảnh Báo / Các mốc vừa đi qua</h3>
        {passedMilestones.length === 0 ? (
          <p>Chưa đi qua mốc nào.</p>
        ) : (
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            {passedMilestones.map((ms, index) => (
              <li key={index} style={{ padding: 10, borderBottom: '1px solid #ddd' }}>
                <strong>Ngăn {ms.ngan} ({ms.thuoc})</strong> - Mốc tới hạn: {ms.thoi_gian_nhac}
                <br/><em style={{ color: '#d9534f' }}>Trạng thái: {ms.trang_thai}</em>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default DongHo;
