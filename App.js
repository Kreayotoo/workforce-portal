import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from './lib/supabase';
import './App.css';

const DEPTS = ['Engineering','HR','Sales','Finance','Operations','Marketing','Legal'];

// ─── HELPERS ─────────────────────────────────────────────────
const fmt = (n) => new Intl.NumberFormat('en-IN').format(Math.round(n || 0));
const initials = (name = '') => name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
const today = () => new Date().toISOString().split('T')[0];
const dateStr = () => new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ─── BADGE ───────────────────────────────────────────────────
function Badge({ status }) {
  const map = {
    Active: 'b-green', Approved: 'b-green', Present: 'b-green',
    Pending: 'b-amber', 'Half Day': 'b-amber', 'Not marked': 'b-gray',
    Inactive: 'b-red', Rejected: 'b-red', Absent: 'b-red',
    Casual: 'b-blue', Sick: 'b-blue', Earned: 'b-blue',
    Maternity: 'b-purple', Paternity: 'b-purple',
    info: 'b-blue', warning: 'b-amber', success: 'b-green', danger: 'b-red',
  };
  return <span className={`badge ${map[status] || 'b-gray'}`}>{status}</span>;
}

// ─── AVATAR ──────────────────────────────────────────────────
function Avatar({ name, size = 28 }) {
  const colors = ['#eff6ff','#f0fdf4','#fdf4ff','#fffbeb','#fef2f2'];
  const textColors = ['#1e40af','#166534','#6b21a8','#92400e','#991b1b'];
  const idx = (name || '').charCodeAt(0) % colors.length;
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: colors[idx], color: textColors[idx],
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.38, fontWeight: 500, flexShrink: 0
    }}>
      {initials(name)}
    </div>
  );
}

// ─── MODAL ───────────────────────────────────────────────────
function Modal({ title, onClose, children, width = 480 }) {
  return (
    <div className="modal-overlay">
      <div className="modal-box" style={{ width }}>
        <div className="modal-hd">
          <h3>{title}</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ─── STAT CARD ───────────────────────────────────────────────
function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="stat-lbl">{label}</div>
      <div className="stat-val">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LOGIN PAGE
// ═══════════════════════════════════════════════════════════════
function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('login');

  const handle = async () => {
    if (!email || !password) { setError('Please fill in all fields.'); return; }
    setLoading(true); setError('');
    try {
      let result;
      if (mode === 'signup') {
        result = await supabase.auth.signUp({ email, password });
        if (result.error) throw result.error;
        setError('Check your email to confirm your account, then sign in.');
        setMode('login'); setLoading(false); return;
      } else {
        result = await supabase.auth.signInWithPassword({ email, password });
        if (result.error) throw result.error;
        onLogin(result.data.user);
      }
    } catch (e) {
      setError(e.message || 'Authentication failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-screen">
      <div className="login-left">
        <div className="login-logo">WF</div>
        <h1>WorkForce Portal</h1>
        <p>Complete HR & employee management system</p>
        <div className="login-features">
          {['Employee directory','Attendance tracking','Leave management','Payroll processing','Performance reviews','Expense claims'].map(f => (
            <div key={f} className="feat"><div className="feat-dot" />  {f}</div>
          ))}
        </div>
      </div>
      <div className="login-right">
        <div className="login-card">
          <h2>{mode === 'login' ? 'Welcome back' : 'Create account'}</h2>
          <p className="login-sub">{mode === 'login' ? 'Sign in to your portal' : 'Register your HR account'}</p>
          <div className="fld">
            <label>Email address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="admin@company.com" onKeyDown={e => e.key === 'Enter' && handle()} />
          </div>
          <div className="fld">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" onKeyDown={e => e.key === 'Enter' && handle()} />
          </div>
          {error && <div className={`alert ${error.includes('Check') ? 'alert-info' : 'alert-err'}`}>{error}</div>}
          <button className="btn-primary full" onClick={handle} disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
          <p className="login-toggle">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <span onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }}>
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// DASHBOARD PAGE
// ═══════════════════════════════════════════════════════════════
function Dashboard({ data, nav, user }) {
  const active = data.employees.filter(e => e.status === 'Active').length;
  const pendingLeaves = data.leaves.filter(l => l.status === 'Pending').length;
  const pendingExp = data.expenses.filter(e => e.status === 'Pending').length;
  const unread = data.notifications.filter(n => !n.is_read).length;

  const modules = [
    { icon: '👥', label: 'Directory', page: 'employees' },
    { icon: '📅', label: 'Attendance', page: 'attendance' },
    { icon: '🏖', label: 'Leave', page: 'leave' },
    { icon: '💰', label: 'Payroll', page: 'payroll' },
    { icon: '🧾', label: 'Expenses', page: 'expenses' },
    { icon: '⭐', label: 'Performance', page: 'performance' },
    { icon: '🔔', label: 'Notifications', page: 'notifications' },
    { icon: '⚙', label: 'Settings', page: 'settings' },
  ];

  return (
    <div>
      <div className="page-hd">
        <div>
          <div className="pg-title">Hi, {(user?.email || '').split('@')[0]}! 👋</div>
          <div className="pg-sub">{dateStr()}</div>
        </div>
        <button className="btn-primary" onClick={() => nav('employees', 'add')}>+ Add employee</button>
      </div>

      <div className="stat-grid">
        <Stat label="Total employees" value={data.employees.length} sub={`${DEPTS.length} departments`} />
        <Stat label="Active" value={active} sub={`${data.employees.length ? Math.round(active / data.employees.length * 100) : 0}% of workforce`} />
        <Stat label="Pending leaves" value={pendingLeaves} sub="Awaiting approval" />
        <Stat label="Open tasks" value={pendingLeaves + pendingExp} sub="Leaves + expenses" />
      </div>

      <div className="modules-grid">
        {modules.map(m => (
          <div key={m.page} className="mod-card" onClick={() => nav(m.page)}>
            <div className="mod-icon">{m.icon}</div>
            <div className="mod-label">{m.label}</div>
            {m.page === 'notifications' && unread > 0 && (
              <div className="mod-badge">{unread}</div>
            )}
          </div>
        ))}
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-hd">
            <h3>Recent employees</h3>
            <button className="btn-link" onClick={() => nav('employees')}>View all →</button>
          </div>
          <table><thead><tr>
            <th style={{width:'35%'}}>Name</th><th style={{width:'25%'}}>Dept</th>
            <th style={{width:'25%'}}>Role</th><th style={{width:'15%'}}>Status</th>
          </tr></thead><tbody>
            {data.employees.slice(0, 6).map(e => (
              <tr key={e.id}>
                <td><div style={{display:'flex',alignItems:'center',gap:8}}><Avatar name={e.name} />{e.name}</div></td>
                <td>{e.department}</td><td>{e.role}</td>
                <td><Badge status={e.status} /></td>
              </tr>
            ))}
          </tbody></table>
        </div>
        <div className="card">
          <div className="card-hd">
            <h3>Notifications</h3>
            <span className="muted-sm">{unread} unread</span>
          </div>
          {data.notifications.slice(0, 5).map(n => (
            <div key={n.id} className="notif-row">
              <div className={`notif-ic ni-${n.type}`}>{n.type === 'warning' ? '⚠' : n.type === 'success' ? '✓' : 'ℹ'}</div>
              <div>
                <div className="notif-msg">{n.message}</div>
                <div className="notif-time">{new Date(n.created_at).toLocaleDateString('en-IN')}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// EMPLOYEES PAGE
// ═══════════════════════════════════════════════════════════════
function EmployeesPage({ employees, onRefresh }) {
  const [search, setSearch] = useState('');
  const [deptF, setDeptF] = useState('');
  const [statusF, setStatusF] = useState('');
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  const filtered = employees.filter(e => {
    const mq = !search || e.name.toLowerCase().includes(search.toLowerCase()) ||
      e.email.toLowerCase().includes(search.toLowerCase()) ||
      e.department.toLowerCase().includes(search.toLowerCase());
    return mq && (!deptF || e.department === deptF) && (!statusF || e.status === statusF);
  });

  const openAdd = () => {
    setForm({ status: 'Active', department: 'Engineering', date_of_joining: today() });
    setModal('add');
  };
  const openEdit = (e) => { setForm({ ...e }); setModal('edit'); };

  const save = async () => {
    setSaving(true);
    const empId = form.emp_id || `EMP-${String(employees.length + 101).padStart(3, '0')}`;
    const payload = {
      emp_id: empId, name: form.name, email: form.email, phone: form.phone,
      department: form.department, role: form.role, status: form.status,
      salary: parseFloat(form.salary) || 30000, date_of_joining: form.date_of_joining
    };
    if (modal === 'edit') {
      await supabase.from('employees').update(payload).eq('id', form.id);
    } else {
      await supabase.from('employees').insert([payload]);
      await supabase.from('notifications').insert([{ message: `New employee ${form.name} added.`, type: 'info' }]);
    }
    setSaving(false); setModal(null); onRefresh();
  };

  const del = async (id, name) => {
    if (!window.confirm(`Delete ${name}? This cannot be undone.`)) return;
    await supabase.from('employees').delete().eq('id', id);
    onRefresh();
  };

  return (
    <div>
      <div className="page-hd">
        <div className="pg-title">Employee directory</div>
        <button className="btn-primary" onClick={openAdd}>+ Add employee</button>
      </div>
      <div className="search-bar">
        <input type="text" placeholder="Search name, email, dept..." value={search} onChange={e => setSearch(e.target.value)} style={{maxWidth:240}} />
        <select value={deptF} onChange={e => setDeptF(e.target.value)} style={{width:160}}>
          <option value="">All departments</option>
          {DEPTS.map(d => <option key={d}>{d}</option>)}
        </select>
        <select value={statusF} onChange={e => setStatusF(e.target.value)} style={{width:130}}>
          <option value="">All statuses</option>
          <option>Active</option><option>Pending</option><option>Inactive</option>
        </select>
        <span className="muted-sm">{filtered.length} results</span>
      </div>
      <div className="card" style={{padding:0}}>
        <table><thead><tr>
          <th style={{width:'4%',paddingLeft:12}}>#</th>
          <th style={{width:'20%'}}>Name</th>
          <th style={{width:'14%'}}>Dept</th>
          <th style={{width:'16%'}}>Role</th>
          <th style={{width:'20%'}}>Email</th>
          <th style={{width:'10%'}}>Salary</th>
          <th style={{width:'10%'}}>Status</th>
          <th style={{width:'6%'}}></th>
        </tr></thead><tbody>
          {filtered.map((e, i) => (
            <tr key={e.id}>
              <td style={{paddingLeft:12,color:'var(--color-text-secondary)'}}>{i + 1}</td>
              <td><div style={{display:'flex',alignItems:'center',gap:8}}><Avatar name={e.name} />{e.name}</div></td>
              <td>{e.department}</td>
              <td>{e.role}</td>
              <td style={{color:'var(--color-text-secondary)'}}>{e.email}</td>
              <td>₹{fmt(e.salary)}</td>
              <td><Badge status={e.status} /></td>
              <td>
                <button className="btn-icon" onClick={() => openEdit(e)} title="Edit">✏</button>
                <button className="btn-icon danger" onClick={() => del(e.id, e.name)} title="Delete">🗑</button>
              </td>
            </tr>
          ))}
          {filtered.length === 0 && <tr><td colSpan={8} style={{textAlign:'center',padding:'2rem',color:'var(--color-text-secondary)'}}>No employees found</td></tr>}
        </tbody></table>
      </div>

      {(modal === 'add' || modal === 'edit') && (
        <Modal title={modal === 'add' ? 'Add new employee' : 'Edit employee'} onClose={() => setModal(null)}>
          <div className="form-row">
            <div className="fld"><label>Full name</label><input type="text" value={form.name || ''} onChange={e => setForm({...form,name:e.target.value})} placeholder="Kiran Kumar" /></div>
            <div className="fld"><label>Email</label><input type="email" value={form.email || ''} onChange={e => setForm({...form,email:e.target.value})} /></div>
          </div>
          <div className="form-row">
            <div className="fld"><label>Phone</label><input type="text" value={form.phone || ''} onChange={e => setForm({...form,phone:e.target.value})} /></div>
            <div className="fld"><label>Date of joining</label><input type="date" value={form.date_of_joining || ''} onChange={e => setForm({...form,date_of_joining:e.target.value})} /></div>
          </div>
          <div className="form-row">
            <div className="fld"><label>Department</label>
              <select value={form.department || ''} onChange={e => setForm({...form,department:e.target.value})}>
                {DEPTS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div className="fld"><label>Role / Designation</label><input type="text" value={form.role || ''} onChange={e => setForm({...form,role:e.target.value})} /></div>
          </div>
          <div className="form-row">
            <div className="fld"><label>Salary (₹/month)</label><input type="number" value={form.salary || ''} onChange={e => setForm({...form,salary:e.target.value})} /></div>
            <div className="fld"><label>Status</label>
              <select value={form.status || 'Active'} onChange={e => setForm({...form,status:e.target.value})}>
                <option>Active</option><option>Pending</option><option>Inactive</option>
              </select>
            </div>
          </div>
          <div className="modal-ftr">
            <button className="btn-sec" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : modal === 'add' ? 'Add employee' : 'Save changes'}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ATTENDANCE PAGE
// ═══════════════════════════════════════════════════════════════
function AttendancePage({ employees, attendance, onRefresh }) {
  const [selDate, setSelDate] = useState(today());
  const [saving, setSaving] = useState(false);
  const [localRec, setLocalRec] = useState({});

  const todayRec = attendance.filter(a => a.date === selDate);
  const present = todayRec.filter(a => a.status === 'Present').length;

  const getRec = (empId) => localRec[empId] || todayRec.find(a => a.employee_id === empId) || { status: 'Not marked', in_time: '09:00', out_time: '18:00' };

  const update = (empId, field, val) => setLocalRec(prev => ({
    ...prev, [empId]: { ...getRec(empId), [field]: val }
  }));

  const saveAll = async () => {
    setSaving(true);
    for (const emp of employees.slice(0, 10)) {
      const rec = getRec(emp.id);
      const existing = todayRec.find(a => a.employee_id === emp.id);
      const payload = { employee_id: emp.id, employee_name: emp.name, date: selDate, status: rec.status, in_time: rec.in_time, out_time: rec.out_time };
      if (existing) {
        await supabase.from('attendance').update(payload).eq('id', existing.id);
      } else {
        await supabase.from('attendance').insert([payload]);
      }
    }
    setSaving(false); setLocalRec({}); onRefresh();
  };

  const markAll = async (status) => {
    setSaving(true);
    for (const emp of employees.slice(0, 10)) {
      const existing = todayRec.find(a => a.employee_id === emp.id);
      const payload = { employee_id: emp.id, employee_name: emp.name, date: selDate, status, in_time: '09:00', out_time: '18:00' };
      if (existing) await supabase.from('attendance').update(payload).eq('id', existing.id);
      else await supabase.from('attendance').insert([payload]);
    }
    setSaving(false); onRefresh();
  };

  return (
    <div>
      <div className="page-hd">
        <div className="pg-title">Attendance</div>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input type="date" value={selDate} onChange={e => setSelDate(e.target.value)} style={{width:160}} />
          <button className="btn-sec" onClick={() => markAll('Present')}>Mark all present</button>
          <button className="btn-sec" onClick={() => markAll('Absent')}>Mark all absent</button>
          <button className="btn-primary" onClick={saveAll} disabled={saving}>{saving ? 'Saving…' : 'Save attendance'}</button>
        </div>
      </div>
      <div className="stat-grid" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>
        <Stat label="Present" value={present} />
        <Stat label="Absent" value={todayRec.filter(a => a.status === 'Absent').length} />
        <Stat label="Rate" value={`${todayRec.length ? Math.round(present / todayRec.length * 100) : 0}%`} />
      </div>
      <div className="card" style={{padding:0,marginBottom:'1rem'}}>
        <div className="card-hd" style={{padding:'1rem 1rem 0'}}><h3>Mark attendance — {selDate}</h3></div>
        <table style={{marginTop:8}}><thead><tr>
          <th style={{width:'25%',paddingLeft:12}}>Employee</th>
          <th style={{width:'18%'}}>Department</th>
          <th style={{width:'16%'}}>In time</th>
          <th style={{width:'16%'}}>Out time</th>
          <th style={{width:'25%'}}>Status</th>
        </tr></thead><tbody>
          {employees.slice(0, 10).map(e => {
            const rec = getRec(e.id);
            return (
              <tr key={e.id}>
                <td style={{paddingLeft:12}}><div style={{display:'flex',alignItems:'center',gap:8}}><Avatar name={e.name} />{e.name}</div></td>
                <td>{e.department}</td>
                <td><input type="time" value={rec.in_time || '09:00'} onChange={ev => update(e.id, 'in_time', ev.target.value)} style={{width:100}} /></td>
                <td><input type="time" value={rec.out_time || '18:00'} onChange={ev => update(e.id, 'out_time', ev.target.value)} style={{width:100}} /></td>
                <td>
                  <select value={rec.status} onChange={ev => update(e.id, 'status', ev.target.value)} style={{width:130}}>
                    <option>Present</option><option>Absent</option><option>Half Day</option><option>Not marked</option>
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody></table>
      </div>
      <div className="card" style={{padding:0}}>
        <div className="card-hd" style={{padding:'1rem 1rem 0'}}><h3>Recent attendance log</h3></div>
        <table style={{marginTop:8}}><thead><tr>
          <th style={{width:'25%',paddingLeft:12}}>Employee</th>
          <th style={{width:'18%'}}>Date</th>
          <th style={{width:'16%'}}>In</th>
          <th style={{width:'16%'}}>Out</th>
          <th style={{width:'25%'}}>Status</th>
        </tr></thead><tbody>
          {attendance.slice(0, 30).map(a => (
            <tr key={a.id}>
              <td style={{paddingLeft:12}}>{a.employee_name}</td>
              <td>{a.date}</td>
              <td>{a.in_time || '--'}</td>
              <td>{a.out_time || '--'}</td>
              <td><Badge status={a.status} /></td>
            </tr>
          ))}
        </tbody></table>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LEAVE PAGE
// ═══════════════════════════════════════════════════════════════
function LeavePage({ employees, leaves, onRefresh }) {
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({});

  const updateStatus = async (id, status) => {
    await supabase.from('leaves').update({ status }).eq('id', id);
    onRefresh();
  };

  const submit = async () => {
    if (!form.employee_id || !form.from_date || !form.to_date) return;
    const emp = employees.find(e => e.id === form.employee_id);
    const days = Math.max(1, Math.round((new Date(form.to_date) - new Date(form.from_date)) / 86400000) + 1);
    await supabase.from('leaves').insert([{
      employee_id: form.employee_id, employee_name: emp.name,
      leave_type: form.leave_type || 'Casual', from_date: form.from_date,
      to_date: form.to_date, days, reason: form.reason || '', status: 'Pending'
    }]);
    await supabase.from('notifications').insert([{ message: `${emp.name} applied for ${days}-day ${form.leave_type || 'Casual'} leave.`, type: 'info' }]);
    setModal(false); onRefresh();
  };

  return (
    <div>
      <div className="page-hd">
        <div className="pg-title">Leave management</div>
        <button className="btn-primary" onClick={() => { setForm({ leave_type: 'Casual' }); setModal(true); }}>+ Apply leave</button>
      </div>
      <div className="stat-grid" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>
        <Stat label="Pending" value={leaves.filter(l => l.status === 'Pending').length} sub="Awaiting approval" />
        <Stat label="Approved" value={leaves.filter(l => l.status === 'Approved').length} />
        <Stat label="Total days" value={leaves.reduce((s, l) => s + (l.days || 0), 0)} />
      </div>
      <div className="card" style={{padding:0}}>
        <div className="card-hd" style={{padding:'1rem 1rem 0'}}><h3>All leave requests</h3></div>
        <table style={{marginTop:8}}><thead><tr>
          <th style={{width:'18%',paddingLeft:12}}>Employee</th>
          <th style={{width:'12%'}}>Type</th>
          <th style={{width:'12%'}}>From</th>
          <th style={{width:'12%'}}>To</th>
          <th style={{width:'6%'}}>Days</th>
          <th style={{width:'20%'}}>Reason</th>
          <th style={{width:'20%'}}>Status / Action</th>
        </tr></thead><tbody>
          {leaves.map(l => (
            <tr key={l.id}>
              <td style={{paddingLeft:12}}>{l.employee_name}</td>
              <td><Badge status={l.leave_type} /></td>
              <td>{l.from_date}</td><td>{l.to_date}</td><td>{l.days}</td>
              <td>{l.reason}</td>
              <td>
                {l.status === 'Pending' ? (
                  <div style={{display:'flex',gap:4}}>
                    <button className="btn-sm-green" onClick={() => updateStatus(l.id, 'Approved')}>Approve</button>
                    <button className="btn-sm-red" onClick={() => updateStatus(l.id, 'Rejected')}>Reject</button>
                  </div>
                ) : <Badge status={l.status} />}
              </td>
            </tr>
          ))}
          {leaves.length === 0 && <tr><td colSpan={7} style={{textAlign:'center',padding:'2rem',color:'var(--color-text-secondary)'}}>No leave requests</td></tr>}
        </tbody></table>
      </div>

      {modal && (
        <Modal title="Apply for leave" onClose={() => setModal(false)}>
          <div className="form-row">
            <div className="fld"><label>Employee</label>
              <select value={form.employee_id || ''} onChange={e => setForm({...form,employee_id:e.target.value})}>
                <option value="">Select employee</option>
                {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </div>
            <div className="fld"><label>Leave type</label>
              <select value={form.leave_type || 'Casual'} onChange={e => setForm({...form,leave_type:e.target.value})}>
                <option>Casual</option><option>Sick</option><option>Earned</option><option>Maternity</option><option>Paternity</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="fld"><label>From date</label><input type="date" value={form.from_date || ''} onChange={e => setForm({...form,from_date:e.target.value})} /></div>
            <div className="fld"><label>To date</label><input type="date" value={form.to_date || ''} onChange={e => setForm({...form,to_date:e.target.value})} /></div>
          </div>
          <div className="fld"><label>Reason</label><textarea rows={2} value={form.reason || ''} onChange={e => setForm({...form,reason:e.target.value})} placeholder="Brief reason..." /></div>
          <div className="modal-ftr">
            <button className="btn-sec" onClick={() => setModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={submit}>Submit request</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PAYROLL PAGE
// ═══════════════════════════════════════════════════════════════
function PayrollPage({ employees, onRefresh }) {
  const total = employees.reduce((s, e) => s + (e.salary || 0), 0);
  const avg = employees.length ? total / employees.length : 0;

  const updateSalary = async (id, salary) => {
    const val = parseFloat(salary);
    if (!isNaN(val) && val > 0) await supabase.from('employees').update({ salary: val }).eq('id', id);
    onRefresh();
  };

  return (
    <div>
      <div className="page-hd"><div className="pg-title">Payroll management</div></div>
      <div className="stat-grid">
        <Stat label="Monthly payroll" value={`₹${fmt(total)}`} />
        <Stat label="Average salary" value={`₹${fmt(avg)}`} />
        <Stat label="Employees" value={employees.filter(e => e.status === 'Active').length} sub="Active" />
        <Stat label="Period" value="Apr 2026" />
      </div>
      <div className="card" style={{padding:0}}>
        <div className="card-hd" style={{padding:'1rem 1rem 0'}}>
          <h3>Payroll register — April 2026</h3>
          <div className="muted-sm">PF: 12% | TDS: 10%</div>
        </div>
        <table style={{marginTop:8}}><thead><tr>
          <th style={{width:'18%',paddingLeft:12}}>Employee</th>
          <th style={{width:'14%'}}>Department</th>
          <th style={{width:'13%'}}>Gross (₹)</th>
          <th style={{width:'11%'}}>PF (₹)</th>
          <th style={{width:'11%'}}>TDS (₹)</th>
          <th style={{width:'13%'}}>Net pay (₹)</th>
          <th style={{width:'10%'}}>Status</th>
          <th style={{width:'10%'}}>Edit salary</th>
        </tr></thead><tbody>
          {employees.map(e => {
            const pf = Math.round((e.salary || 0) * 0.12);
            const tds = Math.round((e.salary || 0) * 0.10);
            const net = (e.salary || 0) - pf - tds;
            return (
              <tr key={e.id}>
                <td style={{paddingLeft:12}}><div style={{display:'flex',alignItems:'center',gap:8}}><Avatar name={e.name} />{e.name}</div></td>
                <td>{e.department}</td>
                <td>₹{fmt(e.salary)}</td>
                <td>₹{fmt(pf)}</td>
                <td>₹{fmt(tds)}</td>
                <td><strong>₹{fmt(net)}</strong></td>
                <td><Badge status={e.status === 'Active' ? 'Approved' : 'Pending'} /></td>
                <td>
                  <input type="number" defaultValue={e.salary} style={{width:90}}
                    onBlur={ev => updateSalary(e.id, ev.target.value)} />
                </td>
              </tr>
            );
          })}
        </tbody></table>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// EXPENSES PAGE
// ═══════════════════════════════════════════════════════════════
function ExpensesPage({ employees, expenses, onRefresh }) {
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({});

  const updateStatus = async (id, status) => {
    await supabase.from('expenses').update({ status }).eq('id', id);
    onRefresh();
  };

  const submit = async () => {
    if (!form.employee_id || !form.amount) return;
    const emp = employees.find(e => e.id === form.employee_id);
    await supabase.from('expenses').insert([{
      employee_id: form.employee_id, employee_name: emp.name,
      category: form.category || 'Travel', amount: parseFloat(form.amount),
      expense_date: form.expense_date || today(), description: form.description || '', status: 'Pending'
    }]);
    setModal(false); onRefresh();
  };

  const totalApproved = expenses.filter(e => e.status === 'Approved').reduce((s, e) => s + (e.amount || 0), 0);

  return (
    <div>
      <div className="page-hd">
        <div className="pg-title">Expense claims</div>
        <button className="btn-primary" onClick={() => { setForm({ category: 'Travel', expense_date: today() }); setModal(true); }}>+ Add claim</button>
      </div>
      <div className="stat-grid" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>
        <Stat label="Total claimed" value={`₹${fmt(expenses.reduce((s, e) => s + (e.amount || 0), 0))}`} />
        <Stat label="Approved" value={`₹${fmt(totalApproved)}`} />
        <Stat label="Pending" value={expenses.filter(e => e.status === 'Pending').length} sub="Awaiting review" />
      </div>
      <div className="card" style={{padding:0}}>
        <div className="card-hd" style={{padding:'1rem 1rem 0'}}><h3>All expense claims</h3></div>
        <table style={{marginTop:8}}><thead><tr>
          <th style={{width:'18%',paddingLeft:12}}>Employee</th>
          <th style={{width:'12%'}}>Category</th>
          <th style={{width:'11%'}}>Amount</th>
          <th style={{width:'13%'}}>Date</th>
          <th style={{width:'26%'}}>Description</th>
          <th style={{width:'20%'}}>Status</th>
        </tr></thead><tbody>
          {expenses.map(e => (
            <tr key={e.id}>
              <td style={{paddingLeft:12}}>{e.employee_name}</td>
              <td><Badge status={e.category} /></td>
              <td>₹{fmt(e.amount)}</td>
              <td>{e.expense_date}</td>
              <td>{e.description}</td>
              <td>
                {e.status === 'Pending' ? (
                  <div style={{display:'flex',gap:4}}>
                    <button className="btn-sm-green" onClick={() => updateStatus(e.id, 'Approved')}>Approve</button>
                    <button className="btn-sm-red" onClick={() => updateStatus(e.id, 'Rejected')}>Reject</button>
                  </div>
                ) : <Badge status={e.status} />}
              </td>
            </tr>
          ))}
          {expenses.length === 0 && <tr><td colSpan={6} style={{textAlign:'center',padding:'2rem',color:'var(--color-text-secondary)'}}>No expense claims</td></tr>}
        </tbody></table>
      </div>

      {modal && (
        <Modal title="Add expense claim" onClose={() => setModal(false)}>
          <div className="form-row">
            <div className="fld"><label>Employee</label>
              <select value={form.employee_id || ''} onChange={e => setForm({...form,employee_id:e.target.value})}>
                <option value="">Select employee</option>
                {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </div>
            <div className="fld"><label>Category</label>
              <select value={form.category || 'Travel'} onChange={e => setForm({...form,category:e.target.value})}>
                <option>Travel</option><option>Food</option><option>Training</option><option>Accommodation</option><option>Other</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="fld"><label>Amount (₹)</label><input type="number" value={form.amount || ''} onChange={e => setForm({...form,amount:e.target.value})} /></div>
            <div className="fld"><label>Date</label><input type="date" value={form.expense_date || ''} onChange={e => setForm({...form,expense_date:e.target.value})} /></div>
          </div>
          <div className="fld"><label>Description</label><textarea rows={2} value={form.description || ''} onChange={e => setForm({...form,description:e.target.value})} /></div>
          <div className="modal-ftr">
            <button className="btn-sec" onClick={() => setModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={submit}>Submit</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PERFORMANCE PAGE
// ═══════════════════════════════════════════════════════════════
function PerformancePage({ employees, performance, onRefresh }) {
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({});
  const avg = performance.length ? performance.reduce((s, p) => s + (p.rating || 0), 0) / performance.length : 0;

  const submit = async () => {
    if (!form.employee_id) return;
    const emp = employees.find(e => e.id === form.employee_id);
    await supabase.from('performance').insert([{
      employee_id: form.employee_id, employee_name: emp.name,
      quarter: form.quarter || 'Q1 2026', rating: parseFloat(form.rating) || 3,
      goals_set: parseInt(form.goals_set) || 4, goals_achieved: parseInt(form.goals_achieved) || 3,
      review_notes: form.review_notes || ''
    }]);
    setModal(false); onRefresh();
  };

  return (
    <div>
      <div className="page-hd">
        <div className="pg-title">Performance management</div>
        <button className="btn-primary" onClick={() => { setForm({ quarter: 'Q1 2026' }); setModal(true); }}>+ Add review</button>
      </div>
      <div className="stat-grid" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>
        <Stat label="Avg rating" value={`${avg.toFixed(1)}/5`} sub="Q1 2026" />
        <Stat label="Reviews done" value={performance.length} />
        <Stat label="Pending" value={Math.max(0, employees.length - performance.length)} sub="Not reviewed" />
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:10}}>
        {performance.map(p => (
          <div key={p.id} className="card">
            <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:10}}>
              <div style={{display:'flex',alignItems:'center',gap:10}}>
                <Avatar name={p.employee_name} size={36} />
                <div>
                  <div style={{fontWeight:500,fontSize:14}}>{p.employee_name}</div>
                  <div style={{fontSize:11,color:'var(--color-text-secondary)'}}>{p.quarter}</div>
                </div>
              </div>
              <div style={{display:'flex',alignItems:'center',gap:8}}>
                <span style={{fontSize:15,fontWeight:500}}>{p.rating}/5</span>
                <Badge status={p.rating >= 4 ? 'Approved' : p.rating >= 3 ? 'Pending' : 'Rejected'} />
              </div>
            </div>
            <div style={{marginBottom:6}}>
              <div style={{fontSize:11,color:'var(--color-text-secondary)',marginBottom:3}}>Goals: {p.goals_achieved}/{p.goals_set} achieved</div>
              <div style={{background:'var(--color-border-tertiary)',borderRadius:4,height:6,overflow:'hidden'}}>
                <div style={{height:6,borderRadius:4,width:`${Math.min(100, Math.round((p.goals_achieved / Math.max(p.goals_set, 1)) * 100))}%`,background: p.rating >= 4 ? '#22c55e' : p.rating >= 3 ? '#f59e0b' : '#ef4444'}} />
              </div>
            </div>
            <div style={{fontSize:12,color:'var(--color-text-secondary)'}}>{p.review_notes}</div>
          </div>
        ))}
        {performance.length === 0 && <div className="card" style={{textAlign:'center',color:'var(--color-text-secondary)'}}>No reviews yet. Add the first one!</div>}
      </div>

      {modal && (
        <Modal title="Add performance review" onClose={() => setModal(false)}>
          <div className="form-row">
            <div className="fld"><label>Employee</label>
              <select value={form.employee_id || ''} onChange={e => setForm({...form,employee_id:e.target.value})}>
                <option value="">Select employee</option>
                {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
              </select>
            </div>
            <div className="fld"><label>Quarter</label>
              <select value={form.quarter || 'Q1 2026'} onChange={e => setForm({...form,quarter:e.target.value})}>
                <option>Q1 2026</option><option>Q2 2026</option><option>Q3 2026</option><option>Q4 2026</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="fld"><label>Rating (1–5)</label><input type="number" min="1" max="5" step="0.1" value={form.rating || ''} onChange={e => setForm({...form,rating:e.target.value})} /></div>
            <div className="fld"><label>Goals set</label><input type="number" value={form.goals_set || ''} onChange={e => setForm({...form,goals_set:e.target.value})} /></div>
          </div>
          <div className="fld"><label>Goals achieved</label><input type="number" value={form.goals_achieved || ''} onChange={e => setForm({...form,goals_achieved:e.target.value})} /></div>
          <div className="fld"><label>Review notes</label><textarea rows={2} value={form.review_notes || ''} onChange={e => setForm({...form,review_notes:e.target.value})} /></div>
          <div className="modal-ftr">
            <button className="btn-sec" onClick={() => setModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={submit}>Save review</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// NOTIFICATIONS PAGE
// ═══════════════════════════════════════════════════════════════
function NotificationsPage({ notifications, onRefresh }) {
  const unread = notifications.filter(n => !n.is_read).length;

  const markRead = async (id) => {
    await supabase.from('notifications').update({ is_read: true }).eq('id', id);
    onRefresh();
  };
  const markAll = async () => {
    await supabase.from('notifications').update({ is_read: true }).eq('is_read', false);
    onRefresh();
  };

  return (
    <div>
      <div className="page-hd">
        <div>
          <div className="pg-title">Notifications</div>
          <div className="pg-sub">{unread} unread</div>
        </div>
        {unread > 0 && <button className="btn-sec" onClick={markAll}>Mark all read</button>}
      </div>
      <div className="card">
        {notifications.map(n => (
          <div key={n.id} className={`notif-row ${!n.is_read ? 'notif-unread' : ''}`} onClick={() => markRead(n.id)} style={{cursor:'pointer'}}>
            <div className={`notif-ic ni-${n.type}`}>{n.type === 'warning' ? '⚠' : n.type === 'success' ? '✓' : 'ℹ'}</div>
            <div style={{flex:1}}>
              <div className="notif-msg" style={{fontWeight: n.is_read ? 400 : 500}}>{n.message}</div>
              <div className="notif-time">{new Date(n.created_at).toLocaleString('en-IN')}</div>
            </div>
            {!n.is_read && <div style={{width:8,height:8,borderRadius:'50%',background:'#3b82f6',flexShrink:0,marginTop:4}} />}
          </div>
        ))}
        {notifications.length === 0 && <div style={{textAlign:'center',color:'var(--color-text-secondary)',padding:'2rem'}}>No notifications</div>}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SETTINGS PAGE
// ═══════════════════════════════════════════════════════════════
function SettingsPage({ settings, employees, onRefresh }) {
  const [form, setForm] = useState(settings || {});
  const [saved, setSaved] = useState(false);

  const save = async () => {
    await supabase.from('settings').update({
      company_name: form.company_name, company_email: form.company_email,
      timezone: form.timezone, currency: form.currency, work_hours: parseInt(form.work_hours) || 9,
      updated_at: new Date().toISOString()
    }).eq('id', form.id);
    setSaved(true); setTimeout(() => setSaved(false), 2000); onRefresh();
  };

  const deptCounts = DEPTS.map(d => ({ dept: d, count: employees.filter(e => e.department === d).length }));
  const max = Math.max(...deptCounts.map(d => d.count), 1);

  return (
    <div>
      <div className="page-hd"><div className="pg-title">Settings</div></div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1rem'}}>
        <div className="card">
          <div className="card-hd"><h3>Company details</h3></div>
          <div className="fld"><label>Company name</label><input type="text" value={form.company_name || ''} onChange={e => setForm({...form,company_name:e.target.value})} /></div>
          <div className="fld"><label>HR email</label><input type="email" value={form.company_email || ''} onChange={e => setForm({...form,company_email:e.target.value})} /></div>
          <div className="form-row">
            <div className="fld"><label>Timezone</label>
              <select value={form.timezone || 'Asia/Kolkata'} onChange={e => setForm({...form,timezone:e.target.value})}>
                <option>Asia/Kolkata</option><option>Asia/Dubai</option><option>UTC</option><option>America/New_York</option>
              </select>
            </div>
            <div className="fld"><label>Currency</label>
              <select value={form.currency || 'INR'} onChange={e => setForm({...form,currency:e.target.value})}>
                <option>INR</option><option>USD</option><option>EUR</option>
              </select>
            </div>
          </div>
          <div className="fld"><label>Work hours per day</label><input type="number" value={form.work_hours || 9} onChange={e => setForm({...form,work_hours:e.target.value})} /></div>
          <button className="btn-primary" onClick={save}>{saved ? '✓ Saved!' : 'Save changes'}</button>
        </div>

        <div className="card">
          <div className="card-hd"><h3>Department headcount</h3></div>
          {deptCounts.map(d => (
            <div key={d.dept} style={{marginBottom:10}}>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:12,marginBottom:3}}>
                <span>{d.dept}</span><span style={{color:'var(--color-text-secondary)'}}>{d.count} employees</span>
              </div>
              <div style={{background:'var(--color-border-tertiary)',borderRadius:4,height:6}}>
                <div style={{height:6,borderRadius:4,width:`${Math.round(d.count / max * 100)}%`,background:'#3b82f6'}} />
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-hd"><h3>Leave policy</h3></div>
          {[['Casual leave','12 days/year'],['Sick leave','8 days/year'],['Earned leave','20 days/year'],['Maternity leave','26 weeks'],['Paternity leave','2 weeks']].map(([t, v]) => (
            <div key={t} style={{display:'flex',justifyContent:'space-between',padding:'7px 0',borderBottom:'0.5px solid var(--color-border-tertiary)',fontSize:13}}>
              <span>{t}</span><span style={{color:'var(--color-text-secondary)'}}>{v}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-hd"><h3>Quick stats</h3></div>
          <div style={{display:'flex',flexDirection:'column',gap:10}}>
            {[
              ['Total employees', employees.length],
              ['Active', employees.filter(e => e.status === 'Active').length],
              ['Inactive', employees.filter(e => e.status === 'Inactive').length],
              ['Total monthly payroll', `₹${fmt(employees.reduce((s, e) => s + (e.salary || 0), 0))}`],
            ].map(([l, v]) => (
              <div key={l} style={{display:'flex',justifyContent:'space-between',fontSize:13}}>
                <span style={{color:'var(--color-text-secondary)'}}>{l}</span>
                <span style={{fontWeight:500}}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════
export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState('dashboard');
  const [data, setData] = useState({ employees: [], attendance: [], leaves: [], expenses: [], performance: [], notifications: [], settings: {} });

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const fetchAll = useCallback(async () => {
    const [emp, att, lv, exp, perf, notif, set] = await Promise.all([
      supabase.from('employees').select('*').order('created_at'),
      supabase.from('attendance').select('*').order('date', { ascending: false }),
      supabase.from('leaves').select('*').order('created_at', { ascending: false }),
      supabase.from('expenses').select('*').order('created_at', { ascending: false }),
      supabase.from('performance').select('*').order('created_at', { ascending: false }),
      supabase.from('notifications').select('*').order('created_at', { ascending: false }),
      supabase.from('settings').select('*').limit(1),
    ]);
    setData({
      employees: emp.data || [], attendance: att.data || [],
      leaves: lv.data || [], expenses: exp.data || [],
      performance: perf.data || [], notifications: notif.data || [],
      settings: set.data?.[0] || {}
    });
  }, []);

  useEffect(() => { if (user) fetchAll(); }, [user, fetchAll]);

  const nav = (pg) => setPage(pg);
  const unread = data.notifications.filter(n => !n.is_read).length;

  const navItems = [
    { icon: '⊞', page: 'dashboard', title: 'Dashboard' },
    { icon: '👥', page: 'employees', title: 'Employees' },
    { icon: '📅', page: 'attendance', title: 'Attendance' },
    { icon: '🏖', page: 'leave', title: 'Leave' },
    { icon: '💰', page: 'payroll', title: 'Payroll' },
    { icon: '🧾', page: 'expenses', title: 'Expenses' },
    { icon: '⭐', page: 'performance', title: 'Performance' },
    { icon: '🔔', page: 'notifications', title: 'Notifications', badge: unread },
    { icon: '⚙', page: 'settings', title: 'Settings', bottom: true },
  ];

  if (loading) return <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',color:'var(--color-text-secondary)'}}>Loading…</div>;
  if (!user) return <LoginPage onLogin={(u) => { setUser(u); fetchAll(); }} />;

  const pages = {
    dashboard: <Dashboard data={data} nav={nav} user={user} />,
    employees: <EmployeesPage employees={data.employees} onRefresh={fetchAll} />,
    attendance: <AttendancePage employees={data.employees} attendance={data.attendance} onRefresh={fetchAll} />,
    leave: <LeavePage employees={data.employees} leaves={data.leaves} onRefresh={fetchAll} />,
    payroll: <PayrollPage employees={data.employees} onRefresh={fetchAll} />,
    expenses: <ExpensesPage employees={data.employees} expenses={data.expenses} onRefresh={fetchAll} />,
    performance: <PerformancePage employees={data.employees} performance={data.performance} onRefresh={fetchAll} />,
    notifications: <NotificationsPage notifications={data.notifications} onRefresh={fetchAll} />,
    settings: <SettingsPage settings={data.settings} employees={data.employees} onRefresh={fetchAll} />,
  };

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="tb-logo">WORK<span>FORCE</span></div>
        <div style={{flex:1}} />
        <div style={{position:'relative',cursor:'pointer',fontSize:16,color:'#fff'}} onClick={() => nav('notifications')}>
          🔔
          {unread > 0 && <div style={{position:'absolute',top:-4,right:-4,background:'#ef4444',color:'#fff',fontSize:9,borderRadius:'50%',width:14,height:14,display:'flex',alignItems:'center',justifyContent:'center'}}>{unread}</div>}
        </div>
        <div style={{width:30,height:30,borderRadius:'50%',background:'#60a5fa',display:'flex',alignItems:'center',justifyContent:'center',fontSize:11,fontWeight:600,color:'#1e3a8a'}}>
          {initials(user.email.split('@')[0])}
        </div>
        <span style={{fontSize:12,color:'rgba(255,255,255,.7)'}}>{user.email}</span>
        <button style={{fontSize:12,background:'rgba(255,255,255,.1)',border:'0.5px solid rgba(255,255,255,.2)',color:'#fff',padding:'5px 10px',borderRadius:6,cursor:'pointer'}}
          onClick={() => supabase.auth.signOut()}>Log out</button>
      </div>
      <div style={{display:'flex'}}>
        <nav className="sidebar">
          {navItems.filter(n => !n.bottom).map(n => (
            <div key={n.page} className={`si-btn ${page === n.page ? 'active' : ''}`} onClick={() => nav(n.page)} title={n.title}>
              {n.icon}
              {n.badge > 0 && <div className="si-badge">{n.badge}</div>}
            </div>
          ))}
          <div style={{flex:1}} />
          {navItems.filter(n => n.bottom).map(n => (
            <div key={n.page} className={`si-btn ${page === n.page ? 'active' : ''}`} onClick={() => nav(n.page)} title={n.title}>{n.icon}</div>
          ))}
        </nav>
        <main className="main-content">{pages[page]}</main>
      </div>
    </div>
  );
}
