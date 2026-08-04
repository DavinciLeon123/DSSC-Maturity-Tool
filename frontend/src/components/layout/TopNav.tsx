import { useState } from 'react';
import { Link, useNavigate } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Drawer, Button } from 'antd';
import { authStore } from '../../lib/auth';
import { api } from '../../lib/api';
import logoSrc from '../../assets/logo-dssc-color.png';

export function TopNav() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();

  const { data: currentUser } = useQuery<{ role: string; email: string }>({
    queryKey: ['current-user-role'],
    queryFn: async () => {
      const res = await api.get<{ role: string; email: string }>('/auth/me');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const isAdmin = currentUser?.role === 'ADMIN';

  const navItems: Array<{ label: string; to: '/dashboard' | '/questionnaire' | '/about' | '/admin' }> = [
    { label: 'Dashboard', to: '/dashboard' },
    { label: 'Dataspace Maturity Assessment', to: '/questionnaire' },
    { label: 'About', to: '/about' },
    ...(isAdmin ? [{ label: 'Admin', to: '/admin' as const }] : []),
  ];

  const handleLogout = () => {
    authStore.clearToken();
    navigate({ to: '/login' });
  };

  return (
    <>
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 2rem',
        height: '96px',
        background: '#ffffff',
        borderBottom: '1px solid rgba(0,142,207,0.1)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Logo — left side */}
        <Link to="/dashboard" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <img src={logoSrc} alt="DSSC" height={75} />
        </Link>

        {/* Hamburger + Menu label — right side */}
        <button
          onClick={() => setDrawerOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '0.5rem',
            color: '#008ecf',
            fontFamily: "'Open Sans', sans-serif",
            fontWeight: 500,
            fontSize: '1rem',
          }}
          aria-label="Open navigation menu"
        >
          {/* Hamburger icon (three lines) */}
          <span style={{ display: 'flex', flexDirection: 'column', gap: '5px', width: '22px' }}>
            <span style={{ display: 'block', height: '2px', background: '#008ecf', borderRadius: '1px' }} />
            <span style={{ display: 'block', height: '2px', background: '#008ecf', borderRadius: '1px' }} />
            <span style={{ display: 'block', height: '2px', background: '#008ecf', borderRadius: '1px' }} />
          </span>
          Menu
        </button>
      </header>

      {/* Navigation drawer */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        placement="right"
        width={280}
        title={
          <div style={{ fontFamily: "'Open Sans', sans-serif", fontWeight: 600, color: '#008ecf', fontSize: '1rem' }}>
            Navigation
          </div>
        }
        styles={{
          body: { padding: '1rem 0', display: 'flex', flexDirection: 'column' },
        }}
      >
        <nav style={{ flex: 1 }}>
          {navItems.map(({ label, to }) => (
            <Link
              key={to}
              to={to}
              onClick={() => setDrawerOpen(false)}
              style={{
                display: 'block',
                padding: '0.875rem 1.5rem',
                color: '#008ecf',
                textDecoration: 'none',
                fontFamily: "'Open Sans', sans-serif",
                fontWeight: 500,
                fontSize: '1rem',
                borderBottom: '1px solid rgba(0,142,207,0.06)',
              }}
              activeProps={{
                style: {
                  display: 'block',
                  padding: '0.875rem 1.5rem',
                  color: '#76b82a',
                  textDecoration: 'none',
                  fontFamily: "'Open Sans', sans-serif",
                  fontWeight: 600,
                  fontSize: '1rem',
                  borderBottom: '1px solid rgba(0,142,207,0.06)',
                  background: 'rgba(118,184,42,0.06)',
                },
              }}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid rgba(0,142,207,0.1)' }}>
          <Button
            onClick={() => { setDrawerOpen(false); handleLogout(); }}
            block
            style={{
              border: '1px solid rgba(0,142,207,0.3)',
              color: '#008ecf',
              fontFamily: "'Open Sans', sans-serif",
              fontWeight: 500,
            }}
          >
            Log Out
          </Button>
        </div>
      </Drawer>
    </>
  );
}
