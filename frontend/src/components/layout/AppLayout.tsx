import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { AI_EMOJI, AI_NAME, ONLINE_STATUS, greetingByHour } from '../../theme/companion';

const NAV = [
  { to: '/chat', label: '💬 聊天', end: false },
  { to: '/schedule', label: '📅 日程', end: false },
  { to: '/dashboard', label: '📊 心情看板', end: false },
  { to: '/memories', label: '🧠 长期记忆', end: false },
  { to: '/reports', label: '📄 周报', end: false },
  { to: '/settings', label: '⚙️ 设置', end: false },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const companion = greetingByHour(new Date().getHours());

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

        {/* AI 陪伴卡片：在线状态 + 时段状态语 */}
        <div className="companion-card">
          <div className="companion-avatar">{AI_EMOJI}</div>
          <div className="companion-info">
            <div className="companion-name">
              {AI_NAME}
              <span className="online-dot" />
              <span className="companion-status">{ONLINE_STATUS}</span>
            </div>
            <div className="companion-status">{companion.status}</div>
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
