import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import client from '../api/client';

export default function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await client.post('/auth/register', { username, email, password });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || err.response?.data?.message || '注册失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-logo">🕯️ 心光树洞</div>
        <h1>创建账号</h1>
        <p className="auth-sub">这里是一个安全、温暖的树洞</p>
        <input
          className="input"
          placeholder="昵称（至少 2 个字符）"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="input"
          type="email"
          placeholder="邮箱"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="input"
          type="password"
          placeholder="密码（至少 8 位，含字母和数字）"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="auth-error">{error}</div>}
        <button className="btn" disabled={loading || !username || !email || password.length < 8}>
          {loading ? '注册中…' : '注册'}
        </button>
        <div className="auth-link">
          已有账号？<Link to="/login">去登录</Link>
        </div>
      </form>
    </div>
  );
}
