import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';

const NAV = [
  { to: '/chat', label: '💬 聊天', end: false },
  { to: '/dashboard', label: '📊 心情看板', end: false },
  { to: '/memories', label: '🧠 长期记忆', end: false },
  { to: '/reports', label: '📄 周报', end: false },
  { to: '/settings', label: '⚙️ 设置', end: false },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo" onClick={() => navigate('/chat')}>
          <span className="logo-icon">🕯️</span>
          <div>
            <div className="logo-title">心光树洞</div>
            <div className="logo-sub">情绪被看见，心里就有了光</div>
          </div>
        </div>
        <nav>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">{user?.username ?? '用户'}</div>
          <button
            className="btn btn-ghost"
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            退出登录
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
