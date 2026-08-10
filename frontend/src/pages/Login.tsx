import { Link } from 'react-router-dom';
import { useState } from 'react';
import client from '../api/client';
import { useAuthStore } from '../store/auth';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const setTokens = useAuthStore((s) => s.setTokens);
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await client.post('/auth/login', { account, password });
      setTokens(data.access_token, data.refresh_token);
      navigate('/chat');
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.detail?.message || '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-logo">🕯️ 心光树洞</div>
        <h1>欢迎回来</h1>
        <p className="auth-sub">情绪被看见，心里就有了光</p>
        <input
          className="input"
          placeholder="邮箱或手机号"
          value={account}
          onChange={(e) => setAccount(e.target.value)}
        />
        <input
          className="input"
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="auth-error">{error}</div>}
        <button className="btn" disabled={loading || !account || !password}>
          {loading ? '登录中…' : '登录'}
        </button>
        <div className="auth-link">
          还没有账号？<Link to="/register">立即注册</Link>
        </div>
      </form>
    </div>
  );
}
